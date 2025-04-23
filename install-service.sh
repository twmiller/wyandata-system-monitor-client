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

# Get the owner of the installation directory
DIR_OWNER=$(stat -c '%U' "$SCRIPT_DIR")
echo -e "Current directory owner: ${YELLOW}${DIR_OWNER}${NC}"

# Ask if service should run as current user
echo -e "\n${BOLD}System Service User Options:${NC}"
echo -e "1. Run service as the current user (${YELLOW}${DIR_OWNER}${NC})"
echo -e "2. Create a dedicated system user for the service"

read -p "Select an option [1/2]: " USER_OPTION
USER_OPTION=${USER_OPTION:-1}

# Configure server address if needed
echo -e "\n${BOLD}Configuring server address...${NC}"
read -p "Enter WebSocket server address (default: ghoest:8000): " SERVER_ADDRESS
SERVER_ADDRESS=${SERVER_ADDRESS:-ghoest:8000}

SERVICE_DIR="/opt/system-monitor"

if [ "$USER_OPTION" == "1" ]; then
    # Use current user
    SERVICE_USER="$DIR_OWNER"
    echo -e "\n${GREEN}✓ Will configure service to run as: ${SERVICE_USER}${NC}"
    
    # Make sure the script directory is readable
    chmod -R +r "$SCRIPT_DIR"
    
    # Choose whether to run from source directory or copy
    echo -e "\n${BOLD}Installation Location:${NC}"
    echo -e "1. Run directly from source directory (${YELLOW}${SCRIPT_DIR}${NC})"
    echo -e "2. Copy files to system directory (${YELLOW}${SERVICE_DIR}${NC})"
    
    read -p "Select an option [1/2]: " LOCATION_OPTION
    LOCATION_OPTION=${LOCATION_OPTION:-1}
    
    if [ "$LOCATION_OPTION" == "2" ]; then
        # Create the service directory and copy files
        echo -e "\n${BOLD}Setting up service directory...${NC}"
        mkdir -p "$SERVICE_DIR"
        cp -r "$SCRIPT_DIR"/* "$SERVICE_DIR/"
        
        # Update monitor script path
        MONITOR_SCRIPT="$SERVICE_DIR/system_monitor.py"
        VENV_DIR="$SERVICE_DIR/venv"
        
        # Set ownership
        chown -R "$SERVICE_USER:$(id -gn "$SERVICE_USER")" "$SERVICE_DIR"
        echo -e "${GREEN}✓ Files copied to $SERVICE_DIR with correct permissions${NC}"
    fi
    
else
    # Create system user
    echo -e "\n${BOLD}Setting up system user for the service...${NC}"
    if ! id -u sysmonitor &>/dev/null; then
        useradd --system --no-create-home --shell /sbin/nologin sysmonitor
        echo -e "${GREEN}✓ Created system user: sysmonitor${NC}"
    else
        echo -e "${YELLOW}System user sysmonitor already exists${NC}"
    fi
    SERVICE_USER="sysmonitor"
    
    # Create a specific directory for the service
    echo -e "\n${BOLD}Setting up service directory...${NC}"
    mkdir -p "$SERVICE_DIR"
    
    # Copy all necessary files
    echo -e "Copying files to $SERVICE_DIR..."
    cp -r "$SCRIPT_DIR"/* "$SERVICE_DIR/"
    
    # Update paths
    MONITOR_SCRIPT="$SERVICE_DIR/system_monitor.py"
    VENV_DIR="$SERVICE_DIR/venv"
    
    # Make sure virtual environment is usable
    echo -e "\n${BOLD}Ensuring Python environment is ready...${NC}"
    PYTHON_PATH=$(which python3 || which python)
    
    # Check if we should rebuild the venv
    if [ -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Existing virtual environment found. Checking requirements...${NC}"
        
        # Create fresh venv to ensure it works with system Python
        rm -rf "$VENV_DIR"
        $PYTHON_PATH -m venv "$VENV_DIR"
        
        # Install requirements
        $VENV_DIR/bin/pip install --upgrade pip
        
        # Check if requirements.txt exists
        if [ -f "$SERVICE_DIR/requirements.txt" ]; then
            $VENV_DIR/bin/pip install -r "$SERVICE_DIR/requirements.txt"
            echo -e "${GREEN}✓ Installed required packages${NC}"
        else
            echo -e "${YELLOW}Warning: requirements.txt not found. Installing minimum requirements...${NC}"
            $VENV_DIR/bin/pip install psutil websockets
        fi
    fi
    
    # Fix permissions
    echo -e "Setting proper permissions..."
    chown -R "$SERVICE_USER:$SERVICE_USER" "$SERVICE_DIR"
    chmod -R 755 "$SERVICE_DIR"
    chmod +x "$MONITOR_SCRIPT"
    
    echo -e "${GREEN}✓ Service files installed to $SERVICE_DIR with correct permissions${NC}"
fi

# Create systemd service file
echo -e "\n${BOLD}Creating systemd service...${NC}"
SERVICE_FILE="/etc/systemd/system/system-monitor.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=System Monitor Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
EOF

# Add group only for regular user
if [ "$USER_OPTION" == "1" ]; then
    GROUP=$(id -gn "$SERVICE_USER")
    echo "Group=${GROUP}" >> "$SERVICE_FILE"
fi

# Complete the service file with environment variables
cat >> "$SERVICE_FILE" << EOF
ExecStart=${VENV_DIR}/bin/python ${MONITOR_SCRIPT} --server ${SERVER_ADDRESS}
WorkingDirectory=$(dirname "$MONITOR_SCRIPT")
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Created system service file: $SERVICE_FILE${NC}"

# Reload systemd, enable and start the service
echo -e "\n${BOLD}Enabling and starting the service...${NC}"
systemctl daemon-reload
systemctl enable system-monitor.service
systemctl start system-monitor.service
sleep 3  # Give the service a moment to start

# Check if service started successfully
if systemctl is-active --quiet system-monitor.service; then
    echo -e "${GREEN}${BOLD}✓ Service successfully installed and started!${NC}"
else
    echo -e "${RED}${BOLD}⚠ Service installation completed but service failed to start!${NC}"
    echo -e "${YELLOW}Showing service status:${NC}"
    systemctl status system-monitor.service
    echo -e "\n${YELLOW}Showing service logs:${NC}"
    journalctl -u system-monitor.service --no-pager -n 20
    echo -e "\n${YELLOW}Please check the logs above for errors.${NC}"
fi

echo -e "\n${BLUE}${BOLD}==================================================${NC}"
echo -e "${GREEN}${BOLD}System Service Installation Complete!${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "\n${BOLD}Service Management:${NC}"
echo -e "• Check service status: ${YELLOW}systemctl status system-monitor.service${NC}"
echo -e "• View service logs: ${YELLOW}journalctl -u system-monitor.service -f${NC}"
echo -e "• Start/stop service: ${YELLOW}systemctl [start|stop|restart] system-monitor.service${NC}"
echo -e "• Disable service: ${YELLOW}systemctl disable system-monitor.service${NC}"
echo -e "\nService configuration file: ${YELLOW}${SERVICE_FILE}${NC}"
echo -e "Service files location: ${YELLOW}$(dirname "$MONITOR_SCRIPT")${NC}"
echo -e "\n"
