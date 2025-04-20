#!/bin/bash

# System Monitor Client Uninstaller Script
# This script removes the system monitor client and its auto-start configuration

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
VENV_DIR="$SCRIPT_DIR/venv"

# Check OS type
OS_TYPE=$(uname -s)

echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "${BLUE}${BOLD}      System Monitor Client Uninstaller            ${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "Detected OS: ${YELLOW}${OS_TYPE}${NC}"

# Remove startup configuration based on OS
echo -e "\n${BOLD}Removing auto-start configuration...${NC}"

if [ "$OS_TYPE" == "Linux" ]; then
    # For systemd-based Linux systems
    echo -e "Removing systemd service..."
    
    SERVICE_FILE="$HOME/.config/systemd/user/system-monitor.service"
    
    # Stop and disable the service if it exists
    if [ -f "$SERVICE_FILE" ]; then
        systemctl --user stop system-monitor.service 2>/dev/null || true
        systemctl --user disable system-monitor.service 2>/dev/null || true
        rm -f "$SERVICE_FILE"
        systemctl --user daemon-reload
        echo -e "${GREEN}✓ Systemd service removed${NC}"
    else
        echo -e "${YELLOW}No systemd service found${NC}"
    fi
    
elif [ "$OS_TYPE" == "Darwin" ]; then
    # For macOS using launchd
    echo -e "Removing launch agent..."
    
    PLIST_FILE="$HOME/Library/LaunchAgents/com.systemmonitor.client.plist"
    
    # Unload and remove the plist if it exists
    if [ -f "$PLIST_FILE" ]; then
        launchctl unload -w "$PLIST_FILE" 2>/dev/null || true
        rm -f "$PLIST_FILE"
        echo -e "${GREEN}✓ Launch agent removed${NC}"
    else
        echo -e "${YELLOW}No launch agent found${NC}"
    fi
else
    echo -e "${YELLOW}Unsupported operating system. Manual removal may be required.${NC}"
fi

# Ask if user wants to remove virtual environment
echo -e "\n${BOLD}Do you want to remove the virtual environment?${NC}"
read -p "This will delete the $VENV_DIR directory [y/N]: " REMOVE_VENV
REMOVE_VENV=${REMOVE_VENV:-N}

if [[ "$REMOVE_VENV" =~ ^[Yy]$ ]]; then
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
        echo -e "${GREEN}✓ Virtual environment removed${NC}"
    else
        echo -e "${YELLOW}Virtual environment not found${NC}"
    fi
else
    echo -e "${YELLOW}Keeping virtual environment${NC}"
fi

# Final instructions
echo -e "\n${BLUE}${BOLD}==================================================${NC}"
echo -e "${GREEN}${BOLD}Uninstallation Complete!${NC}"
echo -e "${BLUE}${BOLD}==================================================${NC}"
echo -e "\nThe System Monitor Client has been removed from auto-start."
echo -e "Configuration files and scripts are still available in: ${YELLOW}$SCRIPT_DIR${NC}"
echo -e "You can reinstall at any time by running: ${YELLOW}$SCRIPT_DIR/install.sh${NC}\n"
