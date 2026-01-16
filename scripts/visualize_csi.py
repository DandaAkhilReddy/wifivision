#!/usr/bin/env python3
"""
CSI Data Visualization Script

Visualizes CSI data from collected CSV files.

Usage:
    python visualize_csi.py --input data.csv --output plot.png
    python visualize_csi.py --baseline baseline.csv --motion motion.csv --compare
"""

import sys
import os
import argparse
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from parser import CSIParser
from visualizer import CSIVisualizer


def main():
    parser = argparse.ArgumentParser(
        description='Visualize CSI data'
    )
    parser.add_argument(
        '--input', '-i',
        help='Input CSV file path'
    )
    parser.add_argument(
        '--baseline',
        help='Baseline CSV file (for comparison)'
    )
    parser.add_argument(
        '--motion',
        help='Motion CSV file (for comparison)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output image path (optional)'
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare baseline and motion data'
    )
    parser.add_argument(
        '--heatmap',
        action='store_true',
        help='Show amplitude heatmap only'
    )

    args = parser.parse_args()

    viz = CSIVisualizer()
    csi_parser = CSIParser()

    if args.compare:
        if not args.baseline or not args.motion:
            print("Error: --compare requires both --baseline and --motion files")
            sys.exit(1)

        print(f"Loading baseline: {args.baseline}")
        baseline_frames = csi_parser.load_file(args.baseline)
        baseline_amp = csi_parser.get_amplitudes()

        print(f"Loading motion: {args.motion}")
        motion_frames = csi_parser.load_file(args.motion)
        motion_amp = csi_parser.get_amplitudes()

        if len(baseline_amp) == 0 or len(motion_amp) == 0:
            print("Error: No valid CSI data in files")
            sys.exit(1)

        print(f"\nBaseline: {len(baseline_amp)} frames, {baseline_amp.shape[1]} subcarriers")
        print(f"Motion: {len(motion_amp)} frames, {motion_amp.shape[1]} subcarriers")

        # Statistics
        baseline_var = np.var(np.mean(baseline_amp, axis=1))
        motion_var = np.var(np.mean(motion_amp, axis=1))
        print(f"\nBaseline variance: {baseline_var:.2f}")
        print(f"Motion variance: {motion_var:.2f}")
        print(f"Variance ratio: {motion_var / baseline_var:.1f}x")

        viz.plot_comparison(
            baseline_amp,
            motion_amp,
            labels=("Baseline (Empty)", "Motion"),
            save_path=args.output
        )

    elif args.input:
        print(f"Loading: {args.input}")
        frames = csi_parser.load_file(args.input)
        amplitudes = csi_parser.get_amplitudes()
        rssi = csi_parser.get_rssi()

        if len(amplitudes) == 0:
            print("Error: No valid CSI data in file")
            sys.exit(1)

        print(f"Loaded {len(amplitudes)} frames, {amplitudes.shape[1]} subcarriers")
        print(f"RSSI range: {min(rssi)} to {max(rssi)} dBm")
        print(f"Mean amplitude: {np.mean(amplitudes):.2f}")
        print(f"Amplitude variance: {np.var(np.mean(amplitudes, axis=1)):.2f}")

        if args.heatmap:
            viz.plot_amplitude_heatmap(
                amplitudes,
                title=f"CSI Amplitude - {os.path.basename(args.input)}",
                save_path=args.output
            )
        else:
            viz.plot_amplitude_over_time(
                amplitudes,
                rssi=rssi,
                title=f"CSI Analysis - {os.path.basename(args.input)}",
                save_path=args.output
            )

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python visualize_csi.py --input data.csv")
        print("  python visualize_csi.py --input data.csv --heatmap --output heatmap.png")
        print("  python visualize_csi.py --baseline empty.csv --motion walk.csv --compare")


if __name__ == '__main__':
    main()
