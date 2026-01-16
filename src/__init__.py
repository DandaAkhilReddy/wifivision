"""
WiFiVision - WiFi CSI Human Detection

Camera-free human detection using WiFi Channel State Information.
"""

__version__ = "0.1.0"
__author__ = "Akhil Reddy"

from .parser import CSIParser, parse_csi_line
from .collector import CSICollector
from .detector import PresenceDetector, ActivityClassifier, CSIPreprocessor
from .visualizer import CSIVisualizer

__all__ = [
    "CSIParser",
    "parse_csi_line",
    "CSICollector",
    "PresenceDetector",
    "ActivityClassifier",
    "CSIPreprocessor",
    "CSIVisualizer",
]
