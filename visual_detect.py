"""
WiFiVision - Visual Dashboard
Real-time graphical display of WiFi CSI human detection
"""
import serial
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import matplotlib.patches as mpatches

# Configuration
PORT = 'COM5'
BAUD_RATE = 921600
WINDOW_SIZE = 100
MAX_POINTS = 200

# Global data buffers
amplitude_history = deque(maxlen=MAX_POINTS)
variance_history = deque(maxlen=MAX_POINTS)
rssi_history = deque(maxlen=MAX_POINTS)
time_history = deque(maxlen=MAX_POINTS)

# Detection state
baseline_var = 1.0
threshold = 3.0
is_present = False
confidence = 0.0
current_rssi = -50
start_time = None

# Serial connection
ser = None

def parse_csi_line(line):
    """Parse CSI_DATA line and extract amplitude."""
    try:
        parts = line.split(',')
        if len(parts) < 26:
            return None

        rssi = int(parts[3]) if parts[3].lstrip('-').isdigit() else 0

        raw_data = []
        for x in parts[24:]:
            x_clean = x.strip()
            if x_clean and x_clean.lstrip('-').isdigit():
                raw_data.append(int(x_clean))

        amplitudes = []
        for i in range(0, len(raw_data) - 1, 2):
            imag, real = raw_data[i], raw_data[i + 1]
            amp = np.sqrt(real**2 + imag**2)
            amplitudes.append(amp)

        if len(amplitudes) > 2:
            amplitudes = amplitudes[2:]

        return {'rssi': rssi, 'amplitude': np.array(amplitudes)}
    except:
        return None

def init_plot():
    """Initialize the matplotlib figure."""
    global fig, ax1, ax2, ax3, ax4
    global line_amp, line_var, presence_circle, rssi_bar

    plt.style.use('dark_background')
    fig = plt.figure(figsize=(14, 10))
    fig.suptitle('WiFiVision - Real-Time Human Detection', fontsize=16, fontweight='bold', color='cyan')

    # Create grid of subplots
    ax1 = fig.add_subplot(2, 2, 1)  # Amplitude over time
    ax2 = fig.add_subplot(2, 2, 2)  # Variance (movement intensity)
    ax3 = fig.add_subplot(2, 2, 3)  # Presence indicator
    ax4 = fig.add_subplot(2, 2, 4)  # Room visualization

    # Plot 1: Amplitude
    ax1.set_title('Signal Amplitude (Live)', color='white')
    ax1.set_xlabel('Time (samples)')
    ax1.set_ylabel('Amplitude')
    ax1.set_xlim(0, MAX_POINTS)
    ax1.set_ylim(0, 50)
    ax1.grid(True, alpha=0.3)
    line_amp, = ax1.plot([], [], 'c-', linewidth=1.5, label='Amplitude')
    ax1.legend(loc='upper right')

    # Plot 2: Variance (Movement Detector)
    ax2.set_title('Movement Intensity', color='white')
    ax2.set_xlabel('Time (samples)')
    ax2.set_ylabel('Variance')
    ax2.set_xlim(0, MAX_POINTS)
    ax2.set_ylim(0, 20)
    ax2.grid(True, alpha=0.3)
    line_var, = ax2.plot([], [], 'lime', linewidth=2, label='Variance')
    ax2.axhline(y=threshold, color='red', linestyle='--', label=f'Threshold ({threshold:.1f})')
    ax2.legend(loc='upper right')

    # Plot 3: Presence Indicator
    ax3.set_title('Presence Detection', color='white')
    ax3.set_xlim(-1.5, 1.5)
    ax3.set_ylim(-1.5, 1.5)
    ax3.set_aspect('equal')
    ax3.axis('off')
    presence_circle = plt.Circle((0, 0), 1, color='gray', alpha=0.8)
    ax3.add_patch(presence_circle)
    ax3.text(0, -1.3, 'NO PRESENCE', ha='center', fontsize=14, color='gray')

    # Plot 4: Room Visualization
    ax4.set_title('Room View (Signal Strength)', color='white')
    ax4.set_xlim(0, 10)
    ax4.set_ylim(0, 10)
    ax4.set_aspect('equal')

    # Draw room
    room = plt.Rectangle((0.5, 0.5), 9, 9, fill=False, edgecolor='white', linewidth=2)
    ax4.add_patch(room)

    # Router icon
    ax4.plot(1.5, 8.5, 'g^', markersize=15, label='Router')
    ax4.text(1.5, 7.8, 'Router', ha='center', fontsize=9, color='green')

    # ESP32 icon
    ax4.plot(8.5, 1.5, 'bs', markersize=12, label='ESP32')
    ax4.text(8.5, 0.8, 'ESP32', ha='center', fontsize=9, color='blue')

    # Signal path
    ax4.plot([1.5, 8.5], [8.5, 1.5], 'y--', alpha=0.5, linewidth=2, label='WiFi Signal')

    # Person indicator (will be updated)
    ax4.plot(5, 5, 'ro', markersize=20, alpha=0.3)
    ax4.text(5, 4, 'Detection\nZone', ha='center', fontsize=9, color='red', alpha=0.5)

    ax4.legend(loc='upper right', fontsize=8)
    ax4.axis('off')

    plt.tight_layout()
    return fig

def update_plot(frame):
    """Update function for animation."""
    global is_present, confidence, current_rssi, baseline_var, threshold
    global amplitude_history, variance_history, time_history

    # Read data from serial
    lines_read = 0
    while ser.in_waiting and lines_read < 10:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith('CSI_DATA'):
                parsed = parse_csi_line(line)
                if parsed and len(parsed['amplitude']) > 0:
                    mean_amp = np.mean(parsed['amplitude'])
                    amplitude_history.append(mean_amp)
                    current_rssi = parsed['rssi']
                    rssi_history.append(current_rssi)

                    elapsed = time.time() - start_time
                    time_history.append(elapsed)

                    # Calculate variance
                    if len(amplitude_history) >= 20:
                        recent = list(amplitude_history)[-50:]
                        var = np.var(recent)
                        variance_history.append(var)

                        is_present = var > threshold
                        confidence = min(1.0, var / (threshold * 2))
            lines_read += 1
        except:
            pass

    # Update Plot 1: Amplitude
    if len(amplitude_history) > 0:
        x_data = list(range(len(amplitude_history)))
        y_data = list(amplitude_history)
        line_amp.set_data(x_data, y_data)
        ax1.set_ylim(min(y_data) * 0.8, max(y_data) * 1.2)

    # Update Plot 2: Variance
    if len(variance_history) > 0:
        x_data = list(range(len(variance_history)))
        y_data = list(variance_history)
        line_var.set_data(x_data, y_data)
        max_var = max(max(y_data) * 1.2, threshold * 2)
        ax2.set_ylim(0, max_var)

        # Update threshold line
        ax2.lines[1].set_ydata([threshold, threshold])

    # Update Plot 3: Presence Circle
    ax3.clear()
    ax3.set_xlim(-1.5, 1.5)
    ax3.set_ylim(-1.5, 1.5)
    ax3.set_aspect('equal')
    ax3.axis('off')
    ax3.set_title('Presence Detection', color='white')

    if is_present:
        color = 'lime'
        text = 'PRESENCE\nDETECTED!'
        text_color = 'lime'
        # Pulsing effect based on confidence
        radius = 0.8 + 0.2 * confidence
    else:
        color = 'gray'
        text = 'NO\nPRESENCE'
        text_color = 'gray'
        radius = 0.8

    circle = plt.Circle((0, 0), radius, color=color, alpha=0.8)
    ax3.add_patch(circle)
    ax3.text(0, 0, text, ha='center', va='center', fontsize=16, fontweight='bold', color='black')

    # Confidence bar
    conf_text = f'Confidence: {confidence*100:.0f}%'
    ax3.text(0, -1.3, conf_text, ha='center', fontsize=12, color=text_color)

    # RSSI display
    rssi_text = f'RSSI: {current_rssi} dBm'
    ax3.text(0, 1.3, rssi_text, ha='center', fontsize=10, color='yellow')

    # Update Plot 4: Room visualization
    ax4.clear()
    ax4.set_xlim(0, 10)
    ax4.set_ylim(0, 10)
    ax4.set_aspect('equal')
    ax4.set_title('Room View', color='white')
    ax4.axis('off')

    # Draw room
    room = plt.Rectangle((0.5, 0.5), 9, 9, fill=False, edgecolor='white', linewidth=2)
    ax4.add_patch(room)

    # Router
    ax4.plot(1.5, 8.5, 'g^', markersize=15)
    ax4.text(1.5, 9.2, 'Router', ha='center', fontsize=9, color='green')

    # ESP32
    ax4.plot(8.5, 1.5, 'bs', markersize=12)
    ax4.text(8.5, 0.6, 'ESP32', ha='center', fontsize=9, color='blue')

    # Signal path
    if is_present:
        ax4.plot([1.5, 8.5], [8.5, 1.5], 'r-', alpha=0.8, linewidth=3)
        ax4.text(5, 6, 'BLOCKED!', ha='center', fontsize=12, color='red', fontweight='bold')

        # Person icon (stick figure)
        person_x, person_y = 5, 5
        # Head
        head = plt.Circle((person_x, person_y + 0.8), 0.4, color='lime', alpha=0.9)
        ax4.add_patch(head)
        # Body
        ax4.plot([person_x, person_x], [person_y + 0.4, person_y - 0.6], 'lime', linewidth=3)
        # Arms
        ax4.plot([person_x - 0.5, person_x + 0.5], [person_y + 0.1, person_y + 0.1], 'lime', linewidth=3)
        # Legs
        ax4.plot([person_x, person_x - 0.4], [person_y - 0.6, person_y - 1.2], 'lime', linewidth=3)
        ax4.plot([person_x, person_x + 0.4], [person_y - 0.6, person_y - 1.2], 'lime', linewidth=3)

        ax4.text(person_x, person_y - 1.8, 'Person Detected!', ha='center', fontsize=10, color='lime')
    else:
        ax4.plot([1.5, 8.5], [8.5, 1.5], 'g--', alpha=0.5, linewidth=2)
        ax4.text(5, 5, 'Clear', ha='center', fontsize=14, color='green', alpha=0.5)

    return line_amp, line_var

def calibrate():
    """Calibrate with empty room."""
    global baseline_var, threshold

    print("\n" + "="*50)
    print("CALIBRATION - Keep room EMPTY for 10 seconds")
    print("="*50)

    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)

    # Flush serial buffer before calibration
    ser.flushInput()
    time.sleep(0.5)

    print("Collecting baseline...")
    baseline_amps = []
    start = time.time()

    while time.time() - start < 10:
        try:
            # Always try to read (with timeout)
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith('CSI_DATA'):
                parsed = parse_csi_line(line)
                if parsed and len(parsed['amplitude']) > 0:
                    baseline_amps.append(np.mean(parsed['amplitude']))
                    print(f"\r  Samples: {len(baseline_amps)}", end='', flush=True)
        except Exception as e:
            pass

    print()

    if len(baseline_amps) > 50:
        baseline_var = np.var(baseline_amps)
        threshold = baseline_var * 3.0
        print(f"Baseline variance: {baseline_var:.2f}")
        print(f"Detection threshold: {threshold:.2f}")
    else:
        print(f"Warning: Low sample count ({len(baseline_amps)}), using defaults")
        baseline_var = 1.0
        threshold = 3.0

    return True

def main():
    global ser, start_time, threshold

    print("="*50)
    print("WiFiVision - Visual Dashboard")
    print("="*50)
    print(f"Port: {PORT}")
    print(f"Baud: {BAUD_RATE}")
    print()

    # Connect
    print("Connecting to ESP32...")
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)
        ser.flushInput()
        print("Connected!")
    except Exception as e:
        print(f"ERROR: Could not connect to {PORT}")
        print(f"Make sure ESP32 is plugged in and no other program is using the port.")
        return

    # Calibrate
    calibrate()

    # Start visualization
    print()
    print("="*50)
    print("Starting Visual Dashboard...")
    print("Close the window to exit")
    print("="*50)

    start_time = time.time()

    fig = init_plot()

    # Update threshold in plot
    ax2.lines[1].set_ydata([threshold, threshold])

    ani = FuncAnimation(fig, update_plot, interval=50, blit=False, cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("\nDisconnected from ESP32")

if __name__ == '__main__':
    main()
