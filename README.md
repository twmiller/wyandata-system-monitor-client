# WyanData System Monitoring Client

A client application for collecting and reporting system metrics to a central monitoring server.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/wyandata-system-monitor-client.git
   cd wyandata-system-monitor-client
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the WebSocket URL:
   Edit `system_monitor.py` to set the correct `WEBSOCKET_URL` for your environment.

## Running as a User Service (Recommended for Development)

1. Install as a user service:
   ```bash
   mkdir -p ~/.config/systemd/user/
   cp system-monitor.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable system-monitor
   systemctl --user start system-monitor
   ```

2. Check service status:
   ```bash
   systemctl --user status system-monitor
   ```

3. View logs:
   ```bash
   journalctl --user -u system-monitor -f
   ```

## Running as a System Service (For Production)

1. Install as a system service:
   ```bash
   sudo cp system-monitor-system.service /etc/systemd/system/system-monitor.service
   sudo systemctl daemon-reload
   sudo systemctl enable system-monitor
   sudo systemctl start system-monitor
   ```

2. Check service status:
   ```bash
   sudo systemctl status system-monitor
   ```

3. View logs:
   ```bash
   sudo journalctl -u system-monitor -f
   ```

## Updating the Client

If you installed as a user service:

```bash
# Pull the latest code
git pull

# Restart the service
systemctl --user restart system-monitor

# Check that it's running
systemctl --user status system-monitor
```

If you installed as a system service:

```bash
# Pull the latest code
git pull

# Restart the service
sudo systemctl restart system-monitor

# Check that it's running
sudo systemctl status system-monitor
```

## Temperature Sensor Troubleshooting

### Diagnostic Process

1. First, diagnose available temperature sources:
   ```bash
   python debug-temp-sensors.py > temperature-report.txt
   ```

2. Review the report to understand what temperature sources are available on your system.

3. Install necessary packages based on your findings:
   ```bash
   sudo apt-get update
   sudo apt-get install lm-sensors
   ```

4. Configure sensors for your specific hardware:
   ```bash
   sudo sensors-detect --auto
   ```

5. Only after confirming available temperature sources, modify the configuration.

### HP Z-Series Workstation Notes (Ubuntu 24.04)

For HP Z240 workstations running Ubuntu 24.04 with newer kernels, there are several options:

1. The standard `coretemp` module might not be available in newer kernels
2. Check for alternative temperature monitoring locations:
   - `/sys/class/thermal/thermal_zone*/temp` (ACPI thermal sources)
   - `/sys/class/hwmon/hwmon*/temp*_input` (Hardware monitoring interfaces)

3. For Z240 with Intel CPUs, you may need to use the thermal_zone interface instead of traditional sensors.
