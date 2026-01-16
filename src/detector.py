"""
Human Detection Module

Implements variance-based presence detection and ML-based activity classification
using WiFi CSI data.
"""

import numpy as np
from scipy import signal
from scipy.ndimage import uniform_filter1d
from collections import deque
import pickle
from typing import Tuple, Dict, List, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler


class CSIPreprocessor:
    """Preprocess raw CSI data for detection."""

    def __init__(
        self,
        sampling_rate: int = 100,
        filter_order: int = 4,
        cutoff_freq: float = 10.0
    ):
        """
        Initialize preprocessor.

        Args:
            sampling_rate: Expected CSI sampling rate (Hz)
            filter_order: Butterworth filter order
            cutoff_freq: Lowpass filter cutoff frequency (Hz)
        """
        self.sampling_rate = sampling_rate
        self.filter_order = filter_order
        self.cutoff_freq = cutoff_freq

        # Design Butterworth lowpass filter
        nyquist = sampling_rate / 2
        normalized_cutoff = min(cutoff_freq / nyquist, 0.99)  # Prevent invalid values
        self.b, self.a = signal.butter(filter_order, normalized_cutoff, btype='low')

    def hampel_filter(
        self,
        data: np.ndarray,
        window_size: int = 10,
        n_sigma: float = 3.0
    ) -> np.ndarray:
        """
        Remove outliers using Hampel filter.

        Args:
            data: 1D array of values
            window_size: Half-window size for median calculation
            n_sigma: Number of MAD (median absolute deviation) for threshold

        Returns:
            Filtered data with outliers replaced by median
        """
        filtered = np.copy(data)
        n = len(data)

        for i in range(window_size, n - window_size):
            window = data[i - window_size:i + window_size + 1]
            median = np.median(window)
            mad = np.median(np.abs(window - median))
            threshold = n_sigma * 1.4826 * mad

            if np.abs(data[i] - median) > threshold:
                filtered[i] = median

        return filtered

    def preprocess(self, amplitude_data: np.ndarray) -> np.ndarray:
        """
        Apply preprocessing pipeline to CSI amplitude data.

        Args:
            amplitude_data: Array of shape (n_frames, n_subcarriers)

        Returns:
            Preprocessed data of same shape
        """
        if amplitude_data.ndim == 1:
            amplitude_data = amplitude_data.reshape(-1, 1)

        processed = np.zeros_like(amplitude_data, dtype=np.float64)

        for i in range(amplitude_data.shape[1]):  # For each subcarrier
            subcarrier = amplitude_data[:, i].astype(np.float64)

            # 1. Remove outliers
            subcarrier = self.hampel_filter(subcarrier)

            # 2. Apply lowpass filter (if enough samples)
            if len(subcarrier) > self.filter_order * 3:
                try:
                    subcarrier = signal.filtfilt(self.b, self.a, subcarrier)
                except ValueError:
                    pass  # Skip filtering if signal too short

            # 3. Smooth with running mean
            subcarrier = uniform_filter1d(subcarrier, size=5)

            processed[:, i] = subcarrier

        return processed


class FeatureExtractor:
    """Extract features from preprocessed CSI data for classification."""

    def __init__(self, window_size: int = 100):
        """
        Initialize feature extractor.

        Args:
            window_size: Number of frames per feature window
        """
        self.window_size = window_size

    def extract_features(self, amplitude_window: np.ndarray) -> np.ndarray:
        """
        Extract features from a window of CSI amplitude data.

        Args:
            amplitude_window: Array of shape (window_size, n_subcarriers)

        Returns:
            1D feature vector
        """
        features = []

        # Mean amplitude per frame
        mean_amp = np.mean(amplitude_window, axis=1)

        # 1. Overall statistics
        features.append(np.mean(mean_amp))
        features.append(np.std(mean_amp))
        features.append(np.var(mean_amp))
        features.append(np.max(mean_amp) - np.min(mean_amp))  # Range

        # 2. Per-subcarrier variance (motion indicator)
        subcarrier_var = np.var(amplitude_window, axis=0)
        features.extend([
            np.mean(subcarrier_var),
            np.std(subcarrier_var),
            np.max(subcarrier_var),
        ])

        # 3. Temporal gradient features
        gradient = np.diff(mean_amp)
        features.extend([
            np.mean(np.abs(gradient)),
            np.std(gradient),
            np.max(np.abs(gradient)),
        ])

        # 4. Frequency domain features
        if len(mean_amp) >= 32:
            # Remove DC component and compute FFT
            fft = np.abs(np.fft.fft(mean_amp - np.mean(mean_amp)))[:len(mean_amp) // 2]
            features.extend([
                np.mean(fft[1:10]) if len(fft) > 10 else 0,  # Low frequency energy
                np.mean(fft[10:20]) if len(fft) > 20 else 0,  # Mid frequency energy
                np.max(fft[1:]) if len(fft) > 1 else 0,  # Peak frequency magnitude
            ])
        else:
            features.extend([0, 0, 0])

        # 5. Cross-subcarrier correlation
        if amplitude_window.shape[1] >= 2:
            corr = np.corrcoef(amplitude_window[:, 0], amplitude_window[:, -1])[0, 1]
            features.append(corr if not np.isnan(corr) else 0)
        else:
            features.append(0)

        return np.array(features)

    def get_feature_names(self) -> List[str]:
        """Get names of extracted features."""
        return [
            'mean_amplitude',
            'std_amplitude',
            'var_amplitude',
            'range_amplitude',
            'mean_subcarrier_var',
            'std_subcarrier_var',
            'max_subcarrier_var',
            'mean_abs_gradient',
            'std_gradient',
            'max_abs_gradient',
            'low_freq_energy',
            'mid_freq_energy',
            'peak_freq_magnitude',
            'cross_subcarrier_corr',
        ]


class PresenceDetector:
    """
    Simple threshold-based presence detection using amplitude variance.

    Detects human presence by monitoring the variance of CSI amplitude
    over a sliding window. When variance exceeds a calibrated threshold,
    presence is detected.
    """

    def __init__(
        self,
        variance_threshold: float = 50.0,
        window_size: int = 100
    ):
        """
        Initialize presence detector.

        Args:
            variance_threshold: Initial variance threshold for detection
            window_size: Number of frames in sliding window
        """
        self.variance_threshold = variance_threshold
        self.window_size = window_size
        self.buffer: deque = deque(maxlen=window_size)
        self.baseline_variance: Optional[float] = None
        self.is_calibrated = False

    def calibrate(
        self,
        empty_room_data: np.ndarray,
        duration_frames: int = 500,
        threshold_multiplier: float = 3.0
    ):
        """
        Calibrate detector with empty room baseline.

        Args:
            empty_room_data: CSI amplitude data from empty room
                           Shape: (n_frames, n_subcarriers)
            duration_frames: Number of frames to use for calibration
            threshold_multiplier: Multiply baseline variance by this for threshold
        """
        data = empty_room_data[:duration_frames]
        mean_amplitude = np.mean(data, axis=1)
        self.baseline_variance = np.var(mean_amplitude)
        self.variance_threshold = self.baseline_variance * threshold_multiplier
        self.is_calibrated = True

        print(f"Calibrated: baseline_variance={self.baseline_variance:.2f}, "
              f"threshold={self.variance_threshold:.2f}")

    def detect(self, amplitude_frame: np.ndarray) -> Tuple[bool, float, float]:
        """
        Detect presence from a single frame.

        Args:
            amplitude_frame: 1D array of amplitudes for current frame

        Returns:
            Tuple of (is_present, confidence, variance)
        """
        mean_amp = np.mean(amplitude_frame)
        self.buffer.append(mean_amp)

        if len(self.buffer) < self.window_size // 2:
            return False, 0.0, 0.0

        current_variance = np.var(list(self.buffer))

        # Presence detection based on variance exceeding threshold
        is_present = current_variance > self.variance_threshold

        # Confidence based on how much variance exceeds threshold
        if self.variance_threshold > 0:
            confidence = min(1.0, current_variance / (self.variance_threshold * 2))
        else:
            confidence = 0.5

        return is_present, confidence, current_variance

    def reset(self):
        """Reset detection buffer."""
        self.buffer.clear()


class ActivityClassifier:
    """
    ML-based activity classification using Random Forest.

    Classes:
    - no_presence: No human in detection zone
    - static_presence: Human present but stationary
    - small_movement: Minor movement (breathing, typing)
    - large_movement: Walking, gesturing
    """

    CLASSES = ['no_presence', 'static_presence', 'small_movement', 'large_movement']

    def __init__(self, n_estimators: int = 100, random_state: int = 42):
        """
        Initialize activity classifier.

        Args:
            n_estimators: Number of trees in Random Forest
            random_state: Random seed for reproducibility
        """
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=random_state
        )
        self.scaler = StandardScaler()
        self.feature_extractor = FeatureExtractor()
        self.is_trained = False

    def train(self, X_windows: List[np.ndarray], y_labels: List[str]):
        """
        Train the activity classifier.

        Args:
            X_windows: List of amplitude windows (each: window_size x n_subcarriers)
            y_labels: List of activity labels (strings from CLASSES)
        """
        # Extract features from all windows
        features = np.array([
            self.feature_extractor.extract_features(w) for w in X_windows
        ])

        # Scale features
        features_scaled = self.scaler.fit_transform(features)

        # Train model
        self.model.fit(features_scaled, y_labels)
        self.is_trained = True

        print(f"Trained on {len(X_windows)} samples")
        print(f"Feature importance: {self.model.feature_importances_}")

    def predict(self, amplitude_window: np.ndarray) -> Tuple[str, Dict[str, float]]:
        """
        Predict activity class for a CSI window.

        Args:
            amplitude_window: Array of shape (window_size, n_subcarriers)

        Returns:
            Tuple of (predicted_class, class_probabilities)
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        features = self.feature_extractor.extract_features(amplitude_window)
        features_scaled = self.scaler.transform(features.reshape(1, -1))

        prediction = self.model.predict(features_scaled)[0]
        probabilities = dict(zip(
            self.CLASSES,
            self.model.predict_proba(features_scaled)[0]
        ))

        return prediction, probabilities

    def save(self, filepath: str):
        """Save trained model to file."""
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained
            }, f)
        print(f"Model saved to {filepath}")

    def load(self, filepath: str):
        """Load trained model from file."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.is_trained = data['is_trained']
        print(f"Model loaded from {filepath}")


def create_windows(
    amplitudes: np.ndarray,
    window_size: int = 100,
    stride: int = 50
) -> List[np.ndarray]:
    """
    Create overlapping windows from amplitude data.

    Args:
        amplitudes: Array of shape (n_frames, n_subcarriers)
        window_size: Number of frames per window
        stride: Step size between windows

    Returns:
        List of windows
    """
    windows = []
    for i in range(0, len(amplitudes) - window_size, stride):
        windows.append(amplitudes[i:i + window_size])
    return windows
