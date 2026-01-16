"""
CSI Data Collector

Collects CSI data from ESP32 serial port.
"""

import serial
import csv
import time
import threading
from datetime import datetime
from typing import Optional, Callable, List
from collections import deque

from .parser import parse_csi_line


class CSICollector:
    """
    Collects CSI data from ESP32 via serial port.

    Supports both blocking collection (for data recording) and
    non-blocking collection (for real-time processing).
    """

    def __init__(
        self,
        port: str = "COM3",
        baud_rate: int = 921600,
        buffer_size: int = 1000
    ):
        """
        Initialize CSI collector.

        Args:
            port: Serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baud_rate: Serial baud rate (921600 recommended for high sampling)
            buffer_size: Size of frame buffer for real-time collection
        """
        self.port = port
        self.baud_rate = baud_rate
        self.buffer_size = buffer_size

        self.serial: Optional[serial.Serial] = None
        self.buffer: deque = deque(maxlen=buffer_size)
        self.is_collecting = False
        self._collection_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []

        # Statistics
        self.packets_received = 0
        self.packets_parsed = 0
        self.start_time: Optional[float] = None

    def connect(self) -> bool:
        """
        Connect to ESP32 serial port.

        Returns:
            True if connection successful
        """
        try:
            self.serial = serial.Serial(
                self.port,
                self.baud_rate,
                timeout=1
            )
            time.sleep(2)  # Wait for connection to stabilize
            self.serial.flushInput()
            print(f"Connected to {self.port} at {self.baud_rate} baud")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from serial port."""
        self.stop_collection()
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Disconnected from serial port")

    def add_callback(self, callback: Callable):
        """
        Add callback function for real-time frame processing.

        Callback receives parsed CSI frame dictionary.
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        """Remove a callback function."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def collect_blocking(
        self,
        duration_seconds: float,
        output_file: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[dict]:
        """
        Collect CSI data for specified duration (blocking).

        Args:
            duration_seconds: Collection duration
            output_file: Optional CSV file to save data
            progress_callback: Optional callback(packets, elapsed) for progress

        Returns:
            List of collected CSI frames
        """
        if not self.serial or not self.serial.is_open:
            if not self.connect():
                return []

        frames = []
        self.packets_received = 0
        self.packets_parsed = 0
        self.start_time = time.time()

        # Prepare output file if specified
        csv_writer = None
        csv_file = None
        if output_file:
            csv_file = open(output_file, 'w', newline='')
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['timestamp', 'raw_line'])

        try:
            print(f"Collecting CSI data for {duration_seconds} seconds...")

            while (time.time() - self.start_time) < duration_seconds:
                if self.serial.in_waiting:
                    try:
                        line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                        self.packets_received += 1

                        if line.startswith('CSI_DATA'):
                            timestamp = datetime.now().isoformat()

                            # Save to file
                            if csv_writer:
                                csv_writer.writerow([timestamp, line])

                            # Parse frame
                            parsed = parse_csi_line(line)
                            if parsed and len(parsed.get('amplitude', [])) > 0:
                                parsed['timestamp'] = timestamp
                                frames.append(parsed)
                                self.packets_parsed += 1

                                # Call callbacks
                                for callback in self._callbacks:
                                    callback(parsed)

                        # Progress callback
                        if progress_callback and self.packets_parsed % 100 == 0:
                            elapsed = time.time() - self.start_time
                            progress_callback(self.packets_parsed, elapsed)

                    except (UnicodeDecodeError, serial.SerialException):
                        continue

            elapsed = time.time() - self.start_time
            rate = self.packets_parsed / elapsed if elapsed > 0 else 0
            print(f"Collection complete: {self.packets_parsed} frames in {elapsed:.1f}s ({rate:.1f} fps)")

        finally:
            if csv_file:
                csv_file.close()

        return frames

    def start_collection(self):
        """Start non-blocking background collection."""
        if self.is_collecting:
            return

        if not self.serial or not self.serial.is_open:
            if not self.connect():
                return

        self.is_collecting = True
        self.packets_received = 0
        self.packets_parsed = 0
        self.start_time = time.time()

        self._collection_thread = threading.Thread(target=self._collection_loop)
        self._collection_thread.daemon = True
        self._collection_thread.start()
        print("Started background collection")

    def stop_collection(self):
        """Stop background collection."""
        self.is_collecting = False
        if self._collection_thread:
            self._collection_thread.join(timeout=2)
            self._collection_thread = None
        print("Stopped background collection")

    def _collection_loop(self):
        """Background collection loop."""
        while self.is_collecting:
            if self.serial and self.serial.in_waiting:
                try:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    self.packets_received += 1

                    if line.startswith('CSI_DATA'):
                        parsed = parse_csi_line(line)
                        if parsed and len(parsed.get('amplitude', [])) > 0:
                            parsed['timestamp'] = datetime.now().isoformat()
                            self.buffer.append(parsed)
                            self.packets_parsed += 1

                            # Call callbacks
                            for callback in self._callbacks:
                                try:
                                    callback(parsed)
                                except Exception as e:
                                    print(f"Callback error: {e}")

                except (UnicodeDecodeError, serial.SerialException):
                    continue
            else:
                time.sleep(0.001)  # Small sleep to prevent CPU spinning

    def get_latest_frame(self) -> Optional[dict]:
        """Get most recent frame from buffer."""
        if self.buffer:
            return self.buffer[-1]
        return None

    def get_recent_frames(self, n: int = 100) -> List[dict]:
        """Get n most recent frames from buffer."""
        return list(self.buffer)[-n:]

    def get_statistics(self) -> dict:
        """Get collection statistics."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'packets_received': self.packets_received,
            'packets_parsed': self.packets_parsed,
            'elapsed_seconds': elapsed,
            'parse_rate': self.packets_parsed / elapsed if elapsed > 0 else 0,
            'buffer_size': len(self.buffer),
            'is_collecting': self.is_collecting,
        }

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
