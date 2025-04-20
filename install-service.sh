#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}WyanData System Monitor Client - Service Installer${NC}"
echo "==========================================================="

# Determine the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create the systemd service file
cat > system-monitor.service << EOF
[Unit]
Description=WyanData System Monitoring Client
After=network.target

[Service]
Type=simple
ExecStart=$(which python) ${SCRIPT_DIR}/system_monitor.py
WorkingDirectory=${SCRIPT_DIR}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Detect if running as root
if [ "$EUID" -eq 0 ]; then
    # System-wide installation
    echo -e "${YELLOW}Running as root, installing as system service${NC}"
    
    # Move service file to system location
    cp system-monitor.service /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable and start the service
    systemctl enable system-monitor
    systemctl start system-monitor
    
    echo -e "${GREEN}Service installed and started!${NC}"
    echo -e "Manage with: ${YELLOW}systemctl [start|stop|restart|status] system-monitor${NC}"
    echo -e "View logs with: ${YELLOW}journalctl -u system-monitor -f${NC}"
else
    # User installation
    echo -e "${YELLOW}Running as user, installing as user service${NC}"
    
    # Create user systemd directory if it doesn't exist
    mkdir -p ~/.config/systemd/user/
    
    # Copy service file
    cp system-monitor.service ~/.config/systemd/user/
    
    # Check if XDG_RUNTIME_DIR is set (required for user systemd)
    if [ -z "$XDG_RUNTIME_DIR" ]; then
        echo -e "${RED}XDG_RUNTIME_DIR not set, user systemd might not work${NC}"
        echo -e "${YELLOW}Consider running as root instead or setting up user systemd properly${NC}"
    fi
    
    # Try to enable lingering (keeps user services running after logout)
    if command -v loginctl &> /dev/null; then
        echo "Enabling lingering to keep service running after logout"
        loginctl enable-linger "$USER" 2>/dev/null || echo -e "${YELLOW}Couldn't enable lingering, service might stop after logout${NC}"
    fi
    
    # Reload systemd user instance
    systemctl --user daemon-reload
    
    # Enable and start the service
    systemctl --user enable system-monitor
    systemctl --user start system-monitor
    
    echo -e "${GREEN}Service installed and started!${NC}"
    echo -e "Manage with: ${YELLOW}systemctl --user [start|stop|restart|status] system-monitor${NC}"
    echo -e "View logs with: ${YELLOW}journalctl --user -u system-monitor -f${NC}"
    echo ""
    echo -e "${YELLOW}Note: If you get 'Failed to connect to bus' errors, run this instead:${NC}"
    echo -e "XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user restart system-monitor"
fi

# Clean up temporary service file
rm system-monitor.service

echo ""
echo -e "${GREEN}Installation complete!${NC}"
