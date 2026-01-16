"""
CSI Data Visualizer

Provides visualization tools for CSI amplitude, phase, and detection results.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from typing import List, Optional, Dict, Tuple
from collections import deque


class CSIVisualizer:
    """Static and animated visualization of CSI data."""

    def __init__(self, figsize: Tuple[int, int] = (12, 10)):
        """
        Initialize visualizer.

        Args:
            figsize: Figure size (width, height)
        """
        self.figsize = figsize

    def plot_amplitude_heatmap(
        self,
        amplitudes: np.ndarray,
        title: str = "CSI Amplitude Heatmap",
        save_path: Optional[str] = None
    ):
        """
        Plot amplitude heatmap over time.

        Args:
            amplitudes: Array of shape (n_frames, n_subcarriers)
            title: Plot title
            save_path: Optional path to save figure
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        im = ax.imshow(
            amplitudes.T,
            aspect='auto',
            cmap='viridis',
            interpolation='nearest'
        )
        ax.set_xlabel('Time (packets)')
        ax.set_ylabel('Subcarrier Index')
        ax.set_title(title)
        plt.colorbar(im, ax=ax, label='Amplitude')

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150)
            print(f"Saved to {save_path}")
        plt.show()

    def plot_amplitude_over_time(
        self,
        amplitudes: np.ndarray,
        rssi: Optional[np.ndarray] = None,
        title: str = "CSI Amplitude Over Time",
        save_path: Optional[str] = None
    ):
        """
        Plot mean amplitude over time with variance indicator.

        Args:
            amplitudes: Array of shape (n_frames, n_subcarriers)
            rssi: Optional RSSI values array
            title: Plot title
            save_path: Optional path to save figure
        """
        n_plots = 3 if rssi is None else 4
        fig, axes = plt.subplots(n_plots, 1, figsize=self.figsize)

        mean_amp = np.mean(amplitudes, axis=1)

        # 1. Amplitude heatmap
        ax = axes[0]
        im = ax.imshow(
            amplitudes.T,
            aspect='auto',
            cmap='viridis',
            interpolation='nearest'
        )
        ax.set_xlabel('Time (packets)')
        ax.set_ylabel('Subcarrier Index')
        ax.set_title('CSI Amplitude Heatmap')
        plt.colorbar(im, ax=ax, label='Amplitude')

        # 2. Mean amplitude over time
        ax = axes[1]
        ax.plot(mean_amp, 'b-', linewidth=0.5)
        ax.set_xlabel('Time (packets)')
        ax.set_ylabel('Mean Amplitude')
        ax.set_title('Mean Amplitude Over Time')
        ax.grid(True, alpha=0.3)

        # 3. Variance (motion indicator)
        ax = axes[2]
        window_size = min(50, len(mean_amp) // 10)
        if window_size > 1:
            variance = []
            for i in range(len(mean_amp) - window_size):
                variance.append(np.var(mean_amp[i:i + window_size]))
            ax.plot(variance, 'r-', linewidth=0.5)
        ax.set_xlabel('Time (packets)')
        ax.set_ylabel('Amplitude Variance')
        ax.set_title(f'Rolling Variance (window={window_size}) - Motion Indicator')
        ax.grid(True, alpha=0.3)

        # 4. RSSI (if provided)
        if rssi is not None:
            ax = axes[3]
            ax.plot(rssi, 'g-', linewidth=0.5)
            ax.set_xlabel('Time (packets)')
            ax.set_ylabel('RSSI (dBm)')
            ax.set_title('Received Signal Strength')
            ax.grid(True, alpha=0.3)

        plt.suptitle(title)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
            print(f"Saved to {save_path}")
        plt.show()

    def plot_comparison(
        self,
        baseline: np.ndarray,
        motion: np.ndarray,
        labels: Tuple[str, str] = ("Baseline (Empty Room)", "Motion"),
        save_path: Optional[str] = None
    ):
        """
        Compare baseline and motion CSI data.

        Args:
            baseline: Baseline amplitude data
            motion: Motion amplitude data
            labels: Labels for baseline and motion
            save_path: Optional path to save figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        baseline_mean = np.mean(baseline, axis=1)
        motion_mean = np.mean(motion, axis=1)

        # Baseline heatmap
        ax = axes[0, 0]
        im = ax.imshow(baseline.T, aspect='auto', cmap='viridis')
        ax.set_title(f'{labels[0]} - Heatmap')
        ax.set_xlabel('Time')
        ax.set_ylabel('Subcarrier')
        plt.colorbar(im, ax=ax)

        # Motion heatmap
        ax = axes[0, 1]
        im = ax.imshow(motion.T, aspect='auto', cmap='viridis')
        ax.set_title(f'{labels[1]} - Heatmap')
        ax.set_xlabel('Time')
        ax.set_ylabel('Subcarrier')
        plt.colorbar(im, ax=ax)

        # Mean amplitude comparison
        ax = axes[1, 0]
        ax.plot(baseline_mean, 'b-', alpha=0.7, label=labels[0])
        ax.plot(motion_mean, 'r-', alpha=0.7, label=labels[1])
        ax.set_title('Mean Amplitude Comparison')
        ax.set_xlabel('Time')
        ax.set_ylabel('Mean Amplitude')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Variance comparison (boxplot)
        ax = axes[1, 1]
        baseline_var = np.var(baseline, axis=0)
        motion_var = np.var(motion, axis=0)
        ax.boxplot([baseline_var, motion_var], labels=labels)
        ax.set_title('Per-Subcarrier Variance Distribution')
        ax.set_ylabel('Variance')
        ax.grid(True, alpha=0.3)

        # Add statistics text
        baseline_stats = f"Baseline: mean={np.mean(baseline_mean):.1f}, var={np.var(baseline_mean):.1f}"
        motion_stats = f"Motion: mean={np.mean(motion_mean):.1f}, var={np.var(motion_mean):.1f}"
        fig.text(0.5, 0.02, f"{baseline_stats}  |  {motion_stats}",
                 ha='center', fontsize=10)

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.08)

        if save_path:
            plt.savefig(save_path, dpi=150)
            print(f"Saved to {save_path}")
        plt.show()

    def plot_detection_results(
        self,
        amplitudes: np.ndarray,
        detections: List[bool],
        confidences: List[float],
        threshold: float,
        save_path: Optional[str] = None
    ):
        """
        Plot detection results with amplitude data.

        Args:
            amplitudes: CSI amplitude data
            detections: Boolean detection results per frame
            confidences: Detection confidence per frame
            threshold: Detection threshold used
            save_path: Optional path to save figure
        """
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))

        mean_amp = np.mean(amplitudes, axis=1)
        n_frames = len(mean_amp)

        # 1. Amplitude with detection overlay
        ax = axes[0]
        ax.plot(mean_amp, 'b-', linewidth=0.5, label='Mean Amplitude')

        # Shade detection regions
        detection_arr = np.array(detections[:n_frames])
        ax.fill_between(
            range(len(detection_arr)),
            0, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else max(mean_amp),
            where=detection_arr,
            alpha=0.3,
            color='red',
            label='Presence Detected'
        )
        ax.set_xlabel('Time (frames)')
        ax.set_ylabel('Mean Amplitude')
        ax.set_title('Amplitude with Detection Overlay')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. Detection confidence
        ax = axes[1]
        ax.plot(confidences[:n_frames], 'g-', linewidth=0.5)
        ax.axhline(y=0.5, color='r', linestyle='--', label='50% confidence')
        ax.set_xlabel('Time (frames)')
        ax.set_ylabel('Confidence')
        ax.set_title('Detection Confidence Over Time')
        ax.set_ylim(0, 1)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 3. Variance with threshold
        ax = axes[2]
        window_size = 50
        variances = []
        for i in range(len(mean_amp) - window_size):
            variances.append(np.var(mean_amp[i:i + window_size]))
        ax.plot(variances, 'b-', linewidth=0.5, label='Rolling Variance')
        ax.axhline(y=threshold, color='r', linestyle='--', label=f'Threshold ({threshold:.1f})')
        ax.set_xlabel('Time (frames)')
        ax.set_ylabel('Variance')
        ax.set_title('Variance vs Detection Threshold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
            print(f"Saved to {save_path}")
        plt.show()


class LiveVisualizer:
    """Real-time visualization for live detection."""

    def __init__(
        self,
        window_size: int = 200,
        n_subcarriers: int = 52
    ):
        """
        Initialize live visualizer.

        Args:
            window_size: Number of frames to display
            n_subcarriers: Expected number of subcarriers
        """
        self.window_size = window_size
        self.n_subcarriers = n_subcarriers

        self.amplitude_buffer = deque(maxlen=window_size)
        self.variance_buffer = deque(maxlen=window_size)
        self.detection_buffer = deque(maxlen=window_size)

        self.fig = None
        self.axes = None
        self.lines = {}
        self.is_running = False

    def setup(self):
        """Set up the live plot."""
        plt.ion()
        self.fig, self.axes = plt.subplots(2, 1, figsize=(12, 8))

        # Amplitude line
        ax = self.axes[0]
        self.lines['amplitude'], = ax.plot([], [], 'b-', linewidth=0.5)
        ax.set_xlim(0, self.window_size)
        ax.set_ylim(0, 100)
        ax.set_xlabel('Time (frames)')
        ax.set_ylabel('Mean Amplitude')
        ax.set_title('Real-time CSI Amplitude')
        ax.grid(True, alpha=0.3)

        # Variance line
        ax = self.axes[1]
        self.lines['variance'], = ax.plot([], [], 'r-', linewidth=0.5)
        self.lines['threshold'] = ax.axhline(y=50, color='g', linestyle='--')
        ax.set_xlim(0, self.window_size)
        ax.set_ylim(0, 200)
        ax.set_xlabel('Time (frames)')
        ax.set_ylabel('Variance')
        ax.set_title('Real-time Variance (Motion Indicator)')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        self.fig.canvas.draw()
        self.is_running = True

    def update(
        self,
        amplitude: np.ndarray,
        variance: float,
        is_detected: bool,
        threshold: float
    ):
        """
        Update the live plot with new data.

        Args:
            amplitude: Current frame amplitude
            variance: Current variance value
            is_detected: Whether presence was detected
            threshold: Current detection threshold
        """
        if not self.is_running:
            self.setup()

        mean_amp = np.mean(amplitude)
        self.amplitude_buffer.append(mean_amp)
        self.variance_buffer.append(variance)
        self.detection_buffer.append(is_detected)

        # Update amplitude plot
        x = list(range(len(self.amplitude_buffer)))
        self.lines['amplitude'].set_data(x, list(self.amplitude_buffer))
        self.axes[0].set_ylim(
            min(self.amplitude_buffer) * 0.9,
            max(self.amplitude_buffer) * 1.1
        )

        # Update title with detection status
        status = "PRESENCE DETECTED" if is_detected else "No presence"
        self.axes[0].set_title(f'Real-time CSI Amplitude - {status}')

        # Update variance plot
        self.lines['variance'].set_data(x, list(self.variance_buffer))
        self.lines['threshold'].set_ydata([threshold, threshold])
        self.axes[1].set_ylim(0, max(max(self.variance_buffer) * 1.1, threshold * 2))

        # Refresh display
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.001)

    def close(self):
        """Close the live plot."""
        self.is_running = False
        plt.ioff()
        plt.close(self.fig)
