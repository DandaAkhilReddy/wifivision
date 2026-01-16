#!/usr/bin/env python3
"""
CSI Data Collection Script

Collects CSI data from ESP32 serial port and saves to CSV file.

Usage:
    python collect_data.py --port COM3 --duration 60 --output data.csv
"""

import sys
import os
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from collector import CSICollector


def progress_callback(packets: int, elapsed: float):
    """Print progress during collection."""
    rate = packets / elapsed if elapsed > 0 else 0
    print(f"\rCollected {packets} packets ({rate:.1f} fps)...", end='', flush=True)


def main():
    parser = argparse.ArgumentParser(
        description='Collect CSI data from ESP32'
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
        '--duration', '-d',
        type=float,
        default=60,
        help='Collection duration in seconds (default: 60)'
    )
    parser.add_argument(
        '--output', '-o',
        default='csi_data.csv',
        help='Output CSV file path (default: csi_data.csv)'
    )

    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"WiFiVision CSI Data Collection")
    print(f"=" * 40)
    print(f"Port: {args.port}")
    print(f"Baud rate: {args.baud}")
    print(f"Duration: {args.duration} seconds")
    print(f"Output: {args.output}")
    print(f"=" * 40)
    print()

    collector = CSICollector(port=args.port, baud_rate=args.baud)

    try:
        frames = collector.collect_blocking(
            duration_seconds=args.duration,
            output_file=args.output,
            progress_callback=progress_callback
        )

        print()  # New line after progress
        print(f"\nCollection Summary:")
        print(f"  Total frames: {len(frames)}")
        print(f"  Output file: {args.output}")

        if frames:
            print(f"  Subcarriers: {len(frames[0].get('amplitude', []))}")
            rssi_values = [f['rssi'] for f in frames]
            print(f"  RSSI range: {min(rssi_values)} to {max(rssi_values)} dBm")

    except KeyboardInterrupt:
        print("\n\nCollection interrupted by user")
    finally:
        collector.disconnect()


if __name__ == '__main__':
    main()
