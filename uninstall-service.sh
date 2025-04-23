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

# Service paths
SERVICE_FILE="/etc/systemd/system/system-monitor.service"
SERVICE_DIR="/opt/system-monitor"

# Check if service exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${YELLOW}No system service found at $SERVICE_FILE${NC}"
    echo -e "Nothing to uninstall."
    exit 0
fi

# Display current service configuration
echo -e "\n${BOLD}Current Service Configuration:${NC}"
systemctl status system-monitor.service --no-pager || true

# Stop and disable the service
echo -e "\n${BOLD}Stopping and disabling the service...${NC}"
systemctl stop system-monitor.service || true
systemctl disable system-monitor.service || true
echo -e "${GREEN}✓ Service stopped and disabled${NC}"

# Remove the service file
echo -e "\n${BOLD}Removing service file...${NC}"
rm -f "$SERVICE_FILE"
systemctl daemon-reload
echo -e "${GREEN}✓ Service file removed${NC}"

# Check if service directory exists
if [ -d "$SERVICE_DIR" ]; then
    echo -e "\n${BOLD}Service directory found at $SERVICE_DIR${NC}"
    read -p "Do you want to remove the service directory and all its contents? [y/N]: " REMOVE_DIR
    REMOVE_DIR=${REMOVE_DIR:-N}

    if [[ "$REMOVE_DIR" =~ ^[Yy]$ ]]; then
        rm -rf "$SERVICE_DIR"
        echo -e "${GREEN}✓ Service directory removed${NC}"
    else
        echo -e "${YELLOW}Keeping service directory${NC}"
    fi
fi

# Ask about removing the system user
if id -u sysmonitor &>/dev/null; then
    echo -e "\n${BOLD}System user 'sysmonitor' exists${NC}"
    read -p "Do you want to remove the system user 'sysmonitor'? [y/N]: " REMOVE_USER
    REMOVE_USER=${REMOVE_USER:-N}

    if [[ "$REMOVE_USER" =~ ^[Yy]$ ]]; then
        userdel sysmonitor
        echo -e "${GREEN}✓ System user 'sysmonitor' removed${NC}"
    else
        echo -e "${YELLOW}Keeping system user 'sysmonitor'${NC}"
    fi
fi

echo -e "\n${BLUE}${BOLD}==================================================${NC}"
echo -e "${GREEN}${BOLD}System Service Uninstallation Complete!${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "\nThe System Monitor service has been completely removed."
echo -e "To reinstall, use: ${YELLOW}sudo ./install-service.sh${NC}\n"
