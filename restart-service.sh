#!/bin/bash

echo "Restarting System Monitor Service..."

# For a user service running under a login session
loginctl enable-linger $USER
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user daemon-reload
systemctl --user restart system-monitor

# Check status
systemctl --user status system-monitor

echo "Done. Service restart attempted."
