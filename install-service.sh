#!/bin/bash

# System Monitor Client System Service Installer
# This script sets up the system monitor as a system-level service

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
VENV_DIR="$SCRIPT_DIR/venv"

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}${BOLD}Error: This script must be run as root to install system services${NC}"
  echo -e "Please run with: ${YELLOW}sudo $0${NC}"
  exit 1
fi

# Check OS type
OS_TYPE=$(uname -s)

echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "${BLUE}${BOLD}    System Monitor - System Service Installer      ${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "Detected OS: ${YELLOW}${OS_TYPE}${NC}"

if [ "$OS_TYPE" != "Linux" ]; then
    echo -e "${RED}${BOLD}Error: System-level service installation is currently only supported on Linux${NC}"
    echo -e "For macOS, please use the regular installer which sets up a LaunchAgent"
    exit 1
fi

# Check if Python venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}${BOLD}Error: Python virtual environment not found at $VENV_DIR${NC}"
    echo -e "Please run the regular installer first: ${YELLOW}./install.sh${NC}"
    exit 1
fi

# Check if the monitor script exists
if [ ! -f "$MONITOR_SCRIPT" ]; then
    echo -e "${RED}${BOLD}Error: Monitor script not found at $MONITOR_SCRIPT${NC}"
    echo -e "Please ensure the script exists before installing the service"
    exit 1
fi

# Create system user for the service if it doesn't exist
echo -e "\n${BOLD}Setting up system user for the service...${NC}"
if ! id -u sysmonitor &>/dev/null; then
    useradd --system --no-create-home --shell /sbin/nologin sysmonitor
    echo -e "${GREEN}✓ Created system user: sysmonitor${NC}"
else
    echo -e "${YELLOW}System user sysmonitor already exists${NC}"
fi

# Make script directory readable by the service user
chmod -R +r "$SCRIPT_DIR"
echo -e "${GREEN}✓ Set permissions on script directory${NC}"

# Create systemd service file
echo -e "\n${BOLD}Creating systemd service...${NC}"
SERVICE_FILE="/etc/systemd/system/system-monitor.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=System Monitor Client
After=network.target

[Service]
Type=simple
User=sysmonitor
Group=sysmonitor
ExecStart=$VENV_DIR/bin/python $MONITOR_SCRIPT
WorkingDirectory=$SCRIPT_DIR
Restart=on-failure
RestartSec=10s

# Security settings
ProtectSystem=full
ProtectHome=read-only
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Created system service file: $SERVICE_FILE${NC}"

# Reload systemd, enable and start the service
echo -e "\n${BOLD}Enabling and starting the service...${NC}"
systemctl daemon-reload
systemctl enable system-monitor.service
systemctl start system-monitor.service

# Check if service started successfully
if systemctl is-active --quiet system-monitor.service; then
    echo -e "${GREEN}${BOLD}✓ Service successfully installed and started!${NC}"
else
    echo -e "${RED}${BOLD}⚠ Service installation completed but service failed to start!${NC}"
    echo -e "Check service status with: ${YELLOW}systemctl status system-monitor.service${NC}"
    echo -e "Check logs with: ${YELLOW}journalctl -u system-monitor.service${NC}"
fi

echo -e "\n${BLUE}${BOLD}==================================================${NC}"
echo -e "${GREEN}${BOLD}System Service Installation Complete!${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "\n${BOLD}Service Management:${NC}"
echo -e "• Check service status: ${YELLOW}systemctl status system-monitor.service${NC}"
echo -e "• View service logs: ${YELLOW}journalctl -u system-monitor.service${NC}"
echo -e "• Start/stop service: ${YELLOW}systemctl [start|stop|restart] system-monitor.service${NC}"
echo -e "• Disable service: ${YELLOW}systemctl disable system-monitor.service${NC}"
echo -e "\n"
