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

The system monitor client attempts to read temperature data in multiple ways:

### For Ubuntu/Debian Systems:

1. Install the necessary packages:
   ```bash
   sudo apt-get update
   sudo apt-get install lm-sensors
   ```

2. Detect and configure sensors:
   ```bash
   sudo sensors-detect --auto
   ```

3. View available sensors:
   ```bash
   sensors
   ```

4. For HP workstations (Z240, Z4, etc.) running newer kernels:
   ```bash
   # Check if the k10temp module is available (AMD CPUs)
   ls /lib/modules/$(uname -r)/kernel/drivers/hwmon/k10temp.ko*

   # Check if the intel_powerclamp module is available (Intel CPUs)
   ls /lib/modules/$(uname -r)/kernel/drivers/thermal/intel/intel_powerclamp.ko*

   # Load appropriate modules
   sudo modprobe k10temp  # For AMD CPUs
   sudo modprobe intel_powerclamp  # For Intel CPUs
   ```

5. Run the diagnostic script to check your system:
   ```bash
   python debug-temp-sensors.py
   ```

6. Restart the service after making changes:
   ```bash
   systemctl --user restart system-monitor  # For user service
   sudo systemctl restart system-monitor    # For system service
   ```

### Manual Configuration for HP Z240 (Ubuntu 24.04):

If your system is using newer kernel modules:

1. Create a custom temperature reading solution:
   ```bash
   sudo apt-get install lm-sensors
   sudo sensors-detect --auto
   ```

2. Make sure appropriate modules are loaded (they may have different names than coretemp):
   ```bash
   # For Intel CPUs on newer kernels
   sudo modprobe intel_powerclamp
   echo "intel_powerclamp" | sudo tee -a /etc/modules
   ```

3. Use the debug script to identify available temperature sensors.
