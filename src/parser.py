"""
CSI Data Parser

Parses raw CSI data from ESP32 serial output into structured format.
"""

import numpy as np
import csv
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class CSIFrame:
    """Represents a single CSI frame with metadata and signal data."""

    timestamp: str
    frame_type: str
    frame_id: int
    mac: str
    rssi: int
    rate: int
    sig_mode: int
    mcs: int
    bandwidth: int
    channel: int
    local_timestamp: int
    sig_len: int
    rx_state: int
    csi_len: int
    amplitude: np.ndarray
    phase: np.ndarray
    csi_complex: np.ndarray
    raw_data: List[int]


def parse_csi_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single CSI_DATA line from ESP32.

    Expected format:
    CSI_DATA,type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,
    not_sounding,aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,
    channel,secondary_channel,local_timestamp,ant,sig_len,rx_state,len,
    first_word,data[0],data[1],...,data[n]

    Args:
        line: Raw CSI_DATA line from serial output

    Returns:
        Dictionary with parsed metadata and CSI values, or None if parsing fails
    """
    parts = line.split(',')

    if len(parts) < 26:
        return None

    if not parts[0].startswith('CSI_DATA'):
        return None

    try:
        # Extract metadata
        metadata = {
            'type': parts[0],
            'id': int(parts[1]) if parts[1].strip().lstrip('-').isdigit() else 0,
            'mac': parts[2],
            'rssi': int(parts[3]) if parts[3].strip().lstrip('-').isdigit() else 0,
            'rate': int(parts[4]) if parts[4].strip().isdigit() else 0,
            'sig_mode': int(parts[5]) if parts[5].strip().isdigit() else 0,
            'mcs': int(parts[6]) if parts[6].strip().isdigit() else 0,
            'bandwidth': int(parts[7]) if parts[7].strip().isdigit() else 0,
            'smoothing': int(parts[8]) if parts[8].strip().isdigit() else 0,
            'not_sounding': int(parts[9]) if parts[9].strip().isdigit() else 0,
            'aggregation': int(parts[10]) if parts[10].strip().isdigit() else 0,
            'stbc': int(parts[11]) if parts[11].strip().isdigit() else 0,
            'fec_coding': int(parts[12]) if parts[12].strip().isdigit() else 0,
            'sgi': int(parts[13]) if parts[13].strip().isdigit() else 0,
            'noise_floor': int(parts[14]) if parts[14].strip().lstrip('-').isdigit() else 0,
            'ampdu_cnt': int(parts[15]) if parts[15].strip().isdigit() else 0,
            'channel': int(parts[16]) if parts[16].strip().isdigit() else 0,
            'secondary_channel': int(parts[17]) if parts[17].strip().isdigit() else 0,
            'local_timestamp': int(parts[18]) if parts[18].strip().isdigit() else 0,
            'ant': int(parts[19]) if parts[19].strip().isdigit() else 0,
            'sig_len': int(parts[20]) if parts[20].strip().isdigit() else 0,
            'rx_state': int(parts[21]) if parts[21].strip().isdigit() else 0,
            'len': int(parts[22]) if parts[22].strip().isdigit() else 0,
            'first_word': int(parts[23]) if parts[23].strip().isdigit() else 0,
        }

        # Extract raw CSI data (starts at index 24)
        # Format: imaginary, real pairs for each subcarrier
        raw_data = []
        for x in parts[24:]:
            x_clean = x.strip()
            if x_clean and (x_clean.lstrip('-').isdigit()):
                raw_data.append(int(x_clean))

        # Convert to complex numbers (pairs of imag, real)
        csi_complex = []
        for i in range(0, len(raw_data) - 1, 2):
            imag = raw_data[i]
            real = raw_data[i + 1]
            csi_complex.append(complex(real, imag))

        # Skip first 2 values (invalid per ESP32 spec - first 4 bytes)
        if len(csi_complex) > 2:
            csi_complex = csi_complex[2:]

        metadata['csi_complex'] = np.array(csi_complex)
        metadata['amplitude'] = np.abs(metadata['csi_complex'])
        metadata['phase'] = np.angle(metadata['csi_complex'])
        metadata['raw_data'] = raw_data

        return metadata

    except (ValueError, IndexError) as e:
        return None


class CSIParser:
    """Parser for CSI data files."""

    def __init__(self):
        self.frames: List[Dict] = []

    def load_file(self, filepath: str, has_timestamp_column: bool = True) -> List[Dict]:
        """
        Load and parse CSI data from a CSV file.

        Args:
            filepath: Path to CSV file
            has_timestamp_column: If True, expects first column to be timestamp

        Returns:
            List of parsed CSI frames
        """
        self.frames = []

        with open(filepath, 'r') as f:
            reader = csv.reader(f)

            # Skip header if present
            first_row = next(reader, None)
            if first_row and 'CSI_DATA' in str(first_row):
                # First row is data, not header
                self._parse_row(first_row, has_timestamp_column)

            for row in reader:
                self._parse_row(row, has_timestamp_column)

        return self.frames

    def _parse_row(self, row: List[str], has_timestamp: bool):
        """Parse a single CSV row."""
        if not row:
            return

        if has_timestamp and len(row) >= 2:
            timestamp = row[0]
            csi_line = row[1]
        else:
            timestamp = ""
            csi_line = ','.join(row)

        parsed = parse_csi_line(csi_line)
        if parsed and len(parsed.get('amplitude', [])) > 0:
            parsed['timestamp'] = timestamp
            self.frames.append(parsed)

    def get_amplitudes(self) -> np.ndarray:
        """Get amplitude matrix (n_frames x n_subcarriers)."""
        if not self.frames:
            return np.array([])
        return np.array([f['amplitude'] for f in self.frames])

    def get_phases(self) -> np.ndarray:
        """Get phase matrix (n_frames x n_subcarriers)."""
        if not self.frames:
            return np.array([])
        return np.array([f['phase'] for f in self.frames])

    def get_rssi(self) -> np.ndarray:
        """Get RSSI values for all frames."""
        if not self.frames:
            return np.array([])
        return np.array([f['rssi'] for f in self.frames])

    def get_metadata(self, key: str) -> List[Any]:
        """Get specific metadata field from all frames."""
        return [f.get(key) for f in self.frames]


def load_csi_file(filepath: str) -> List[Dict]:
    """
    Convenience function to load CSI data from file.

    Args:
        filepath: Path to CSV file

    Returns:
        List of parsed CSI frames
    """
    parser = CSIParser()
    return parser.load_file(filepath)
