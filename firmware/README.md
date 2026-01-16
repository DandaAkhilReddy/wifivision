# ESP32 Firmware Setup

This directory contains configuration defaults for the ESP32 CSI firmware.

## Quick Setup

1. **Clone esp-csi repository:**
   ```cmd
   cd %USERPROFILE%\Desktop
   git clone --recursive https://github.com/espressif/esp-csi.git
   ```

2. **Navigate to csi_recv_router example:**
   ```cmd
   cd esp-csi\examples\get-started\csi_recv_router
   ```

3. **Copy configuration (optional):**
   ```cmd
   copy C:\Users\akhil\wifivision\firmware\sdkconfig.defaults .
   ```

4. **Set target and configure:**
   ```cmd
   idf.py set-target esp32
   idf.py menuconfig
   ```

5. **Configure WiFi in menuconfig:**
   - Navigate to `Example Connection Configuration`
   - Set `WiFi SSID` to your network name
   - Set `WiFi Password` to your network password

6. **Build and flash:**
   ```cmd
   idf.py build
   idf.py -p COM3 flash monitor
   ```

## Critical Settings

These settings MUST be configured for proper CSI collection:

| Setting | Path | Value |
|---------|------|-------|
| WiFi CSI | `Component config → Wi-Fi → WiFi CSI` | **ENABLE** |
| Tick Rate | `Component config → FreeRTOS → Kernel → Tick rate` | **1000 Hz** |
| Baud Rate | `Serial flasher config → Default baud rate` | **921600** |
| CPU Freq | `Component config → ESP System Settings → CPU frequency` | **240 MHz** |

## Expected Output

When successfully running, you should see CSI data lines:
```
CSI_DATA,0,ac:bc:32:xx:xx:xx,-45,11,0,0,20,...
CSI_DATA,0,ac:bc:32:xx:xx:xx,-44,11,0,0,20,...
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No CSI_DATA lines | Check WiFi credentials, ensure router is 2.4GHz |
| Low data rate | Increase baud rate, check tick rate is 1000Hz |
| Build errors | Run `idf.py fullclean` and rebuild |
| Flash fails | Check COM port, try different USB cable |
