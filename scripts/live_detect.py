#!/usr/bin/env python3
"""
Live Human Detection Script

Performs real-time presence detection using CSI data from ESP32.

Usage:
    python live_detect.py --port COM3 --calibrate
"""

import sys
import os
import argparse
import time
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from collector import CSICollector
from detector import PresenceDetector, CSIPreprocessor
from parser import parse_csi_line


class LiveDetector:
    """Real-time CSI-based human detection."""

    def __init__(
        self,
        port: str,
        baud_rate: int = 921600,
        window_size: int = 100
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.window_size = window_size

        self.collector = CSICollector(port, baud_rate)
        self.preprocessor = CSIPreprocessor()
        self.presence_detector = PresenceDetector(window_size=window_size)

        self.amplitude_buffer = []

    def calibrate(self, duration_seconds: float = 10.0):
        """
        Calibrate detection threshold with empty room data.

        Args:
            duration_seconds: Duration for calibration data collection
        """
        print(f"\n=== CALIBRATION ===")
        print(f"Please ensure the room is empty for {duration_seconds} seconds...")
        print("Starting in 3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print("Collecting baseline data...")

        frames = self.collector.collect_blocking(
            duration_seconds=duration_seconds,
            progress_callback=lambda p, e: print(f"\r  {p} frames...", end='')
        )

        if len(frames) > 100:
            amplitudes = np.array([f['amplitude'] for f in frames])
            self.presence_detector.calibrate(amplitudes)
            print("\nCalibration complete!")
            return True
        else:
            print("\nNot enough data for calibration. Using default threshold.")
            return False

    def run(self, visualize: bool = False):
        """
        Run real-time detection loop.

        Args:
            visualize: If True, show live plot (requires display)
        """
        print("\n=== LIVE DETECTION ===")
        print("Press Ctrl+C to stop\n")

        # Set up visualization if requested
        live_viz = None
        if visualize:
            try:
                from visualizer import LiveVisualizer
                live_viz = LiveVisualizer(window_size=200)
                live_viz.setup()
            except Exception as e:
                print(f"Could not initialize visualization: {e}")
                visualize = False

        # Start collection
        self.collector.start_collection()

        # Add detection callback
        def detection_callback(frame):
            amplitude = frame['amplitude']

            # Detect presence
            is_present, confidence, variance = self.presence_detector.detect(amplitude)

            # Display result
            status = "PRESENCE DETECTED" if is_present else "No presence      "
            bar_len = int(confidence * 20)
            bar = '\u2588' * bar_len + '\u2591' * (20 - bar_len)

            print(f"\r{status} | Conf: [{bar}] {confidence:.2f} | Var: {variance:8.1f} | RSSI: {frame['rssi']:4d} dBm", end='')

            # Update visualization
            if live_viz:
                live_viz.update(
                    amplitude,
                    variance,
                    is_present,
                    self.presence_detector.variance_threshold
                )

        self.collector.add_callback(detection_callback)

        try:
            while True:
                time.sleep(0.1)

                # Print statistics periodically
                stats = self.collector.get_statistics()
                if stats['packets_parsed'] > 0 and stats['packets_parsed'] % 1000 == 0:
                    print(f"\n[Stats] {stats['parse_rate']:.1f} fps, buffer: {stats['buffer_size']}")

        except KeyboardInterrupt:
            print("\n\nStopping detection...")
        finally:
            self.collector.stop_collection()
            self.collector.disconnect()
            if live_viz:
                live_viz.close()

    def test_connection(self) -> bool:
        """Test if ESP32 is sending CSI data."""
        print(f"Testing connection to {self.port}...")

        if not self.collector.connect():
            print("Failed to connect to serial port")
            return False

        print("Waiting for CSI data...")
        frames = self.collector.collect_blocking(duration_seconds=5)

        if len(frames) > 0:
            print(f"Received {len(frames)} frames")
            print(f"Subcarriers: {len(frames[0]['amplitude'])}")
            print(f"RSSI: {frames[0]['rssi']} dBm")
            self.collector.disconnect()
            return True
        else:
            print("No CSI data received. Check:")
            print("  1. ESP32 is flashed with csi_recv_router firmware")
            print("  2. WiFi credentials are correct in menuconfig")
            print("  3. ESP32 is connected to the router")
            self.collector.disconnect()
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Live WiFi CSI Human Detection'
    )
    parser.add_argument(
        '--port', '-p',
        default='COM3',
        help='Serial port (default: COM3)'
    )
    parser.add_argument(
        '--baud', '-b',
        type=int,
        default=921600,
        help='Baud rate (default: 921600)'
    )
    parser.add_argument(
        '--calibrate', '-c',
        action='store_true',
        help='Run calibration before detection'
    )
    parser.add_argument(
        '--calibrate-time',
        type=float,
        default=10,
        help='Calibration duration in seconds (default: 10)'
    )
    parser.add_argument(
        '--visualize', '-v',
        action='store_true',
        help='Show live visualization plot'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test connection only'
    )
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=50.0,
        help='Manual variance threshold (default: 50.0, ignored if --calibrate)'
    )

    args = parser.parse_args()

    print(f"WiFiVision Live Detection")
    print(f"=" * 40)
    print(f"Port: {args.port}")
    print(f"Baud rate: {args.baud}")
    print(f"=" * 40)

    detector = LiveDetector(args.port, args.baud)

    if args.test:
        success = detector.test_connection()
        sys.exit(0 if success else 1)

    # Connect
    if not detector.collector.connect():
        print("Failed to connect. Exiting.")
        sys.exit(1)

    # Set manual threshold or calibrate
    if args.calibrate:
        detector.calibrate(args.calibrate_time)
    else:
        detector.presence_detector.variance_threshold = args.threshold
        print(f"Using manual threshold: {args.threshold}")

    # Run detection
    detector.run(visualize=args.visualize)


if __name__ == '__main__':
    main()
