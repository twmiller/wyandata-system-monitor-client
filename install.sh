#!/bin/bash

# System Monitor Client Installer Script
# This script sets up the system monitor client to run automatically on system boot

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get script directory for reference
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
MONITOR_SCRIPT="$SCRIPT_DIR/system_monitor.py"

# Check OS type
OS_TYPE=$(uname -s)

echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "${BLUE}${BOLD}      System Monitor Client Installer              ${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "Detected OS: ${YELLOW}${OS_TYPE}${NC}"

# Check Python version
echo -e "\n${BOLD}Checking for Python 3...${NC}"
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
    echo -e "${GREEN}✓ Python 3 found!${NC}"
elif command -v python &>/dev/null; then
    PY_VERSION=$(python --version 2>&1 | grep -oP '(?<=Python )([0-9]+)')
    if [ "$PY_VERSION" == "3" ]; then
        PYTHON_CMD="python"
        echo -e "${GREEN}✓ Python 3 found as 'python'!${NC}"
    else
        echo -e "${RED}✗ Python 3 not found. Please install Python 3 to continue.${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Python 3 not found. Please install Python 3 to continue.${NC}"
    exit 1
fi

# Configure server address
echo -e "\n${BOLD}Configuring server address...${NC}"
DEFAULT_SERVER="ghoest:8000"
read -p "Enter WebSocket server address (default: $DEFAULT_SERVER): " SERVER_ADDRESS
SERVER_ADDRESS=${SERVER_ADDRESS:-$DEFAULT_SERVER}

# Update the server address in the monitor script
echo -e "Updating server address to: ${GREEN}$SERVER_ADDRESS${NC}"
sed -i.bak "s|WEBSOCKET_URL = \"ws://.*\"|WEBSOCKET_URL = \"ws://$SERVER_ADDRESS/ws/system/metrics/\"|g" "$MONITOR_SCRIPT"
# For macOS compatibility (in case sed -i doesn't work)
if [ -f "$MONITOR_SCRIPT.bak" ]; then
    if [ "$OS_TYPE" == "Darwin" ] && ! diff "$MONITOR_SCRIPT" "$MONITOR_SCRIPT.bak" &>/dev/null; then
        mv "$MONITOR_SCRIPT.bak" "$MONITOR_SCRIPT"
        sed -i "" "s|WEBSOCKET_URL = \"ws://.*\"|WEBSOCKET_URL = \"ws://$SERVER_ADDRESS/ws/system/metrics/\"|g" "$MONITOR_SCRIPT"
    fi
fi

# Create and activate a Python virtual environment
echo -e "\n${BOLD}Creating Python virtual environment...${NC}"
VENV_DIR="$SCRIPT_DIR/venv"

# Check if venv module is available
if ! $PYTHON_CMD -c "import venv" 2>/dev/null; then
    echo -e "${RED}Python venv module not found. Installing...${NC}"
    if [ "$OS_TYPE" == "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y python3-venv
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3-venv
        elif command -v yum &>/dev/null; then
            sudo yum install -y python3-venv
        else
            echo -e "${RED}✗ Unable to install python3-venv automatically. Please install it manually.${NC}"
            exit 1
        fi
    elif [ "$OS_TYPE" == "Darwin" ]; then
        echo -e "${YELLOW}On macOS, venv should be included with Python 3. If not, reinstall Python.${NC}"
    fi
fi

# Create virtual environment
$PYTHON_CMD -m venv "$VENV_DIR"
echo -e "${GREEN}✓ Virtual environment created at: $VENV_DIR${NC}"

# Activate virtual environment
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install required packages
echo -e "\n${BOLD}Installing required packages...${NC}"
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"
echo -e "${GREEN}✓ Packages installed successfully${NC}"

# Set executable permission on monitor script
chmod +x "$MONITOR_SCRIPT"

# Create startup configuration based on OS
echo -e "\n${BOLD}Setting up auto-start on system boot...${NC}"

if [ "$OS_TYPE" == "Linux" ]; then
    # For systemd-based Linux systems
    echo -e "Setting up systemd service for Linux..."
    
    # Create user systemd directory if it doesn't exist
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SYSTEMD_DIR"
    
    # Create systemd service file
    SERVICE_FILE="$SYSTEMD_DIR/system-monitor.service"
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=System Monitor Client
After=network.target

[Service]
Type=simple
ExecStart=$VENV_DIR/bin/python $MONITOR_SCRIPT
WorkingDirectory=$SCRIPT_DIR
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=default.target
EOF

    echo -e "${GREEN}✓ Created systemd service file: $SERVICE_FILE${NC}"
    
    # Enable and start the service
    systemctl --user daemon-reload
    systemctl --user enable system-monitor.service
    systemctl --user start system-monitor.service
    
    # Make sure lingering is enabled to run the service at boot time
    loginctl enable-linger "$(whoami)" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Service enabled and started${NC}"
    echo -e "\nYou can check service status with: ${YELLOW}systemctl --user status system-monitor.service${NC}"
    
elif [ "$OS_TYPE" == "Darwin" ]; then
    # For macOS using launchd
    echo -e "Setting up launch agent for macOS..."
    
    # Create LaunchAgents directory if it doesn't exist
    LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCH_AGENTS_DIR"
    
    # Create plist file
    PLIST_FILE="$LAUNCH_AGENTS_DIR/com.systemmonitor.client.plist"
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.systemmonitor.client</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python</string>
        <string>$MONITOR_SCRIPT</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/system-monitor.log</string>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/system-monitor.log</string>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
</dict>
</plist>
EOF

    echo -e "${GREEN}✓ Created launch agent plist: $PLIST_FILE${NC}"
    
    # Load the launch agent
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load -w "$PLIST_FILE"
    
    echo -e "${GREEN}✓ Launch agent loaded${NC}"
    echo -e "\nYou can check service status with: ${YELLOW}launchctl list | grep com.systemmonitor.client${NC}"
    echo -e "Logs will be available at: ${YELLOW}$HOME/Library/Logs/system-monitor.log${NC}"
else
    echo -e "${RED}Unsupported operating system. Auto-start setup failed.${NC}"
    echo -e "${YELLOW}You can manually run the monitor with: $VENV_DIR/bin/python $MONITOR_SCRIPT${NC}"
fi

# Create a manual run script
echo -e "\n${BOLD}Creating manual run script...${NC}"
RUN_SCRIPT="$SCRIPT_DIR/run_monitor.sh"

cat > "$RUN_SCRIPT" << EOF
#!/bin/bash
# Activate the virtual environment and run the system monitor
source "$VENV_DIR/bin/activate"
python "$MONITOR_SCRIPT"
EOF

chmod +x "$RUN_SCRIPT"
echo -e "${GREEN}✓ Created manual run script: $RUN_SCRIPT${NC}"

# Final instructions
echo -e "\n${BLUE}${BOLD}==================================================${NC}"
echo -e "${GREEN}${BOLD}Installation Complete!${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "\n${BOLD}Next steps:${NC}"

if [ "$OS_TYPE" == "Linux" ]; then
    echo -e "• The system monitor is running and will start automatically on boot."
    echo -e "• To manually manage the service: ${YELLOW}systemctl --user [start|stop|restart] system-monitor.service${NC}"
elif [ "$OS_TYPE" == "Darwin" ]; then
    echo -e "• The system monitor is running and will start automatically on boot."
    echo -e "• To manually manage the service: ${YELLOW}launchctl [load|unload] $PLIST_FILE${NC}"
fi

echo -e "• To manually run the monitor: ${YELLOW}$RUN_SCRIPT${NC}"
echo -e "• Monitor configurations are saved in: ${YELLOW}$SCRIPT_DIR${NC}"
echo -e "\n"
