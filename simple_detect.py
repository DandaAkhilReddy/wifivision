"""
Simple WiFi CSI Human Detection
No complex imports - standalone script
"""
import serial
import time
import numpy as np
from collections import deque

# Configuration
PORT = 'COM5'
BAUD_RATE = 921600
WINDOW_SIZE = 100
THRESHOLD_MULTIPLIER = 3.0

def parse_csi_line(line):
    """Parse CSI_DATA line and extract amplitude."""
    try:
        parts = line.split(',')
        if len(parts) < 26:
            return None

        rssi = int(parts[3]) if parts[3].lstrip('-').isdigit() else 0

        # Extract raw CSI data (starts around index 24-25)
        raw_data = []
        for x in parts[24:]:
            x_clean = x.strip()
            if x_clean and x_clean.lstrip('-').isdigit():
                raw_data.append(int(x_clean))

        # Convert to amplitude (magnitude of complex pairs)
        amplitudes = []
        for i in range(0, len(raw_data) - 1, 2):
            imag, real = raw_data[i], raw_data[i + 1]
            amp = np.sqrt(real**2 + imag**2)
            amplitudes.append(amp)

        if len(amplitudes) > 2:
            amplitudes = amplitudes[2:]  # Skip first 2 (invalid)

        return {'rssi': rssi, 'amplitude': np.array(amplitudes)}
    except:
        return None

def main():
    print("=" * 50)
    print("WiFiVision - Simple CSI Human Detection")
    print("=" * 50)
    print(f"Port: {PORT}")
    print(f"Baud: {BAUD_RATE}")
    print()

    # Connect
    print("Connecting to ESP32...")
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        ser.flushInput()
        print("Connected!")
    except Exception as e:
        print(f"ERROR: Could not connect to {PORT}")
        print(f"Details: {e}")
        print("\nMake sure:")
        print("  1. ESP32 is plugged in")
        print("  2. No other program is using COM5")
        print("  3. You ran 'idf.py -p COM5 flash' to program it")
        return

    # Calibration
    print()
    print("=" * 50)
    print("CALIBRATION - Keep the room EMPTY for 10 seconds")
    print("=" * 50)
    print("Starting in 3...")
    time.sleep(1)
    print("2...")
    time.sleep(1)
    print("1...")
    time.sleep(1)
    print("Collecting baseline...")

    baseline_amplitudes = []
    start_time = time.time()

    while time.time() - start_time < 10:
        if ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('CSI_DATA'):
                    parsed = parse_csi_line(line)
                    if parsed and len(parsed['amplitude']) > 0:
                        baseline_amplitudes.append(np.mean(parsed['amplitude']))
                        print(f"\r  Samples: {len(baseline_amplitudes)}", end='')
            except:
                pass

    print()

    if len(baseline_amplitudes) < 100:
        print(f"WARNING: Only got {len(baseline_amplitudes)} samples (expected 500+)")
        print("The ESP32 may not be sending CSI data.")
        print("\nCheck in ESP-IDF CMD:")
        print("  idf.py -p COM5 monitor")
        print("Do you see CSI_DATA lines?")
        if len(baseline_amplitudes) == 0:
            ser.close()
            return

    baseline_var = np.var(baseline_amplitudes)
    threshold = baseline_var * THRESHOLD_MULTIPLIER
    print(f"Baseline variance: {baseline_var:.2f}")
    print(f"Detection threshold: {threshold:.2f}")

    # Detection loop
    print()
    print("=" * 50)
    print("LIVE DETECTION - Walk around to test!")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    print()

    buffer = deque(maxlen=WINDOW_SIZE)

    try:
        while True:
            if ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith('CSI_DATA'):
                        parsed = parse_csi_line(line)
                        if parsed and len(parsed['amplitude']) > 0:
                            mean_amp = np.mean(parsed['amplitude'])
                            buffer.append(mean_amp)

                            if len(buffer) >= WINDOW_SIZE // 2:
                                current_var = np.var(list(buffer))
                                is_present = current_var > threshold
                                confidence = min(1.0, current_var / (threshold * 2))

                                # Visual display
                                status = "PRESENCE!" if is_present else "Empty    "
                                bar_len = int(confidence * 20)
                                bar = '█' * bar_len + '░' * (20 - bar_len)

                                print(f"\r{status} [{bar}] Var:{current_var:8.1f} RSSI:{parsed['rssi']:4d}dBm", end='')
                except:
                    pass

    except KeyboardInterrupt:
        print("\n\nStopped!")
    finally:
        ser.close()
        print("Disconnected from ESP32")

if __name__ == '__main__':
    main()
