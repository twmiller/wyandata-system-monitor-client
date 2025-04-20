#!/bin/bash

echo "Updating WyanData System Monitor Client..."

# Pull latest code
git pull

# Check if running as user service first
if systemctl --user is-active system-monitor &>/dev/null; then
    echo "Restarting user service..."
    systemctl --user restart system-monitor
    sleep 2
    systemctl --user status system-monitor
    exit 0
fi

# If not found as user service, try system service
if sudo systemctl is-active system-monitor &>/dev/null; then
    echo "Restarting system service..."
    sudo systemctl restart system-monitor
    sleep 2
    sudo systemctl status system-monitor
    exit 0
fi

echo "Service not found. Is it installed as a service?"
echo "See README.md for installation instructions."
chmod +x update.sh
