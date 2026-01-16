# WiFiVision - ESP32 WiFi CSI Human Detection

> Camera-free human detection using WiFi signals

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![ESP-IDF 5.x](https://img.shields.io/badge/ESP--IDF-5.x-green.svg)](https://docs.espressif.com/projects/esp-idf/)

## Overview

WiFiVision uses WiFi Channel State Information (CSI) to detect human presence without cameras. By analyzing how WiFi signals are affected by human movement, we can detect presence, motion, and activity levels while preserving privacy.

## How It Works

```
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│  WiFi Router │◄──── Ping/Reply ──►│    ESP32     │◄── Serial 921600 ─►│  Windows PC  │
│   (Source)   │                    │  (Receiver)  │                    │   (Python)   │
└──────────────┘                    └──────┬───────┘                    └──────────────┘
                                          │
                                   CSI Extraction
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │  Amplitude Analysis   │
                              │         ↓             │
                              │  Human Detection      │
                              └───────────────────────┘
```

The ESP32 pings your router and extracts Channel State Information (CSI) from replies. Human movement disturbs WiFi signals, causing measurable changes in amplitude variance.

## Hardware Requirements

| Component | Details |
|-----------|---------|
| ESP32 | 1x ESP32 DevKit (original, S2, S3, C3, or C6) |
| Computer | Windows 10/11 (tested on ASUS Zenbook) |
| WiFi Router | Any 2.4GHz 802.11 b/g/n router |
| USB Cable | Data cable (not charge-only) |

## Quick Start

### 1. Install ESP-IDF

Download from https://dl.espressif.com/dl/esp-idf/ and install to `C:\Espressif`

### 2. Flash ESP32 Firmware

```cmd
git clone --recursive https://github.com/espressif/esp-csi.git
cd esp-csi\examples\get-started\csi_recv_router
idf.py set-target esp32
idf.py menuconfig   # Set WiFi SSID/password
idf.py -p COM3 flash monitor
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Live Detection

```bash
python scripts/live_detect.py --port COM3 --calibrate
```

---

## Installation

### Step 1: ESP-IDF Setup (Windows)

1. Download **ESP-IDF Tools Installer**
   - URL: https://dl.espressif.com/dl/esp-idf/
   - File: `esp-idf-tools-setup-offline-5.4.3.exe`

2. Install to `C:\Espressif` (no spaces in path!)

3. Launch **ESP-IDF 5.4 CMD** from Start Menu

4. Verify:
   ```cmd
   idf.py --version
   ```

### Step 2: USB Driver Installation

| Driver | Download |
|--------|----------|
| CP2102 (Silicon Labs) | https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers |
| CH340 (WCH) | http://www.wch.cn/downloads/CH341SER_EXE.html |

After connecting ESP32, check Device Manager for COM port.

### Step 3: ESP32 Firmware

```cmd
cd %USERPROFILE%\Desktop
git clone --recursive https://github.com/espressif/esp-csi.git
cd esp-csi\examples\get-started\csi_recv_router
idf.py set-target esp32
idf.py menuconfig
```

**Required menuconfig settings:**

| Setting Path | Value |
|--------------|-------|
| `Component config → Wi-Fi → WiFi CSI` | **ENABLE** |
| `Component config → FreeRTOS → Kernel → Tick rate` | **1000 Hz** |
| `Serial flasher config → Baud rate` | **921600** |
| `Example Connection Configuration → WiFi SSID` | *Your WiFi* |
| `Example Connection Configuration → WiFi Password` | *Your password* |
| `Component config → ESP System Settings → CPU frequency` | **240 MHz** |

Build and flash:
```cmd
idf.py build
idf.py -p COM3 flash monitor
```

### Step 4: Python Environment

```bash
cd wifivision
pip install -r requirements.txt
```

---

## Usage

### Collect CSI Data

```bash
# Collect 60 seconds of baseline data (empty room)
python scripts/collect_data.py --port COM3 --duration 60 --output data/raw/baseline.csv

# Collect data with motion
python scripts/collect_data.py --port COM3 --duration 60 --output data/raw/motion.csv
```

### Visualize CSI Data

```bash
python scripts/visualize_csi.py --input data/raw/baseline.csv --output plots/baseline.png
```

### Live Detection

```bash
# With calibration (recommended for first run)
python scripts/live_detect.py --port COM3 --calibrate

# Without calibration (uses default threshold)
python scripts/live_detect.py --port COM3
```

### Train Custom Model

```bash
# Organize labeled data in data/labeled/{no_presence,static,small_movement,large_movement}/
python scripts/train_model.py --data data/labeled --output models/activity_classifier.pkl
```

---

## Project Structure

```
wifivision/
├── README.md
├── requirements.txt
├── .gitignore
├── firmware/
│   └── sdkconfig.defaults      # ESP-IDF recommended settings
├── src/
│   ├── __init__.py
│   ├── collector.py            # Serial data collection
│   ├── parser.py               # CSI data parsing
│   ├── detector.py             # Detection algorithms
│   └── visualizer.py           # Data visualization
├── scripts/
│   ├── collect_data.py         # Data collection utility
│   ├── live_detect.py          # Real-time detection
│   ├── visualize_csi.py        # CSI visualization
│   └── train_model.py          # Model training
├── models/
│   └── .gitkeep
└── data/
    ├── raw/
    ├── processed/
    └── labeled/
```

---

## Detection Approach

### Variance-Based Presence Detection

1. **Calibration**: Collect baseline CSI data from empty room
2. **Threshold Calculation**: threshold = baseline_variance × 3
3. **Detection**: If current_variance > threshold → presence detected

### ML-Based Activity Classification

| Class | Description |
|-------|-------------|
| `no_presence` | No human in detection zone |
| `static_presence` | Human present but stationary |
| `small_movement` | Minor movement (breathing, typing) |
| `large_movement` | Walking, gesturing |

Features extracted:
- Amplitude mean, std, variance, range
- Per-subcarrier variance statistics
- Temporal gradient features
- Frequency domain features

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| COM port not detected | Install CP2102/CH340 driver, try different USB cable |
| Build fails | Run `idf.py fullclean` then `idf.py build` |
| No CSI data | Check WiFi credentials, ensure 2.4GHz router |
| Low sampling rate | Increase baud to 921600+, set tick rate 1000Hz |
| High false positives | Recalibrate in empty room, increase threshold |
| Serial permission denied | Run as admin or add user to dialout group |

---

## Command Reference

```bash
# ESP-IDF Commands
idf.py --version              # Check ESP-IDF version
idf.py set-target esp32       # Set target chip
idf.py menuconfig             # Open configuration menu
idf.py build                  # Compile firmware
idf.py -p COM3 flash          # Flash to ESP32
idf.py -p COM3 monitor        # View serial output
idf.py -p COM3 flash monitor  # Flash and monitor
idf.py fullclean              # Clean build files

# Python Scripts
python scripts/collect_data.py --port COM3 --duration 60
python scripts/live_detect.py --port COM3 --calibrate
python scripts/visualize_csi.py --input data.csv
python scripts/train_model.py --data data/labeled
```

---

## References

- [Espressif ESP-CSI](https://github.com/espressif/esp-csi) - Official ESP32 CSI examples
- [WiFi-Densepose](https://github.com/Abinand2631/WiFi-Densepose) - ESP32 pose estimation
- [ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool) - Research CSI toolkit
- [ESP-IDF Documentation](https://docs.espressif.com/projects/esp-idf/)

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
