#!/bin/bash

# System Monitor Client System Service Uninstaller
# This script removes the system-level service

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}${BOLD}Error: This script must be run as root to uninstall system services${NC}"
  echo -e "Please run with: ${YELLOW}sudo $0${NC}"
  exit 1
fi

echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "${BLUE}${BOLD}    System Monitor - System Service Uninstaller    ${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"

# Service file path
SERVICE_FILE="/etc/systemd/system/system-monitor.service"

# Check if service exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${YELLOW}No system service found at $SERVICE_FILE${NC}"
    echo -e "Nothing to uninstall."
    exit 0
fi

# Stop and disable the service
echo -e "\n${BOLD}Stopping and disabling the service...${NC}"
systemctl stop system-monitor.service
systemctl disable system-monitor.service
echo -e "${GREEN}✓ Service stopped and disabled${NC}"

# Remove the service file
echo -e "\n${BOLD}Removing service file...${NC}"
rm -f "$SERVICE_FILE"
systemctl daemon-reload
echo -e "${GREEN}✓ Service file removed${NC}"

# Ask about removing the system user
read -p "Do you want to remove the system user 'sysmonitor'? [y/N]: " REMOVE_USER
REMOVE_USER=${REMOVE_USER:-N}

if [[ "$REMOVE_USER" =~ ^[Yy]$ ]]; then
    if id -u sysmonitor &>/dev/null; then
        userdel sysmonitor
        echo -e "${GREEN}✓ System user 'sysmonitor' removed${NC}"
    else
        echo -e "${YELLOW}User 'sysmonitor' not found${NC}"
    fi
fi

echo -e "\n${BLUE}${BOLD}==================================================${NC}"
echo -e "${GREEN}${BOLD}System Service Uninstallation Complete!${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "\nThe System Monitor service has been completely removed."
echo -e "The monitor script and virtual environment remain untouched."
echo -e "To remove those as well, delete the script directory.\n"
