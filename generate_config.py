#!/usr/bin/env python3

import os
import sys
import platform
import socket
import psutil
import configparser
import subprocess
import re
from pathlib import Path


def is_valid_shortname(name):
    """Check if the short name is valid (alphanumeric with underscores, no spaces)"""
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))


def get_storage_devices():
    """Get list of all storage devices on the system"""
    storage_devices = []
    
    print("\nDetecting storage devices...")
    
    try:
        # Get list of all mount points
        partitions = psutil.disk_partitions(all=False)
        
        # macOS specific filtering
        if platform.system() == 'Darwin':
            filtered_partitions = []
            for p in partitions:
                # Skip virtual/system partitions on macOS
                if any(skip_pattern in p.mountpoint for skip_pattern in [
                    '/Library/Developer/CoreSimulator',
                    '/Volumes/com.apple',
                    '/private/var/vm',
                    '/System/Volumes/VM',
                    '/System/Volumes/Preboot',
                    '/System/Volumes/Data',
                    '/System/Volumes/Update',
                    'TimeMachine'
                ]):
                    continue
                    
                # Only include root volume and real Volumes
                if p.mountpoint == '/' or p.mountpoint.startswith('/Volumes/'):
                    filtered_partitions.append(p)
                    
            partitions = filtered_partitions
            
        # Process partitions
        for i, partition in enumerate(partitions):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                # Skip small partitions
                if usage.total < 1e9:  # Less than 1GB
                    continue
                    
                # Get device type
                if platform.system() == 'Linux':
                    device_type = "unknown"
                    if 'nvme' in partition.device.lower() or 'ssd' in partition.device.lower():
                        device_type = "SSD"
                    elif 'sd' in partition.device.lower() or 'hd' in partition.device.lower():
                        device_type = "HDD"
                else:
                    device_type = "SSD" if platform.system() == 'Darwin' else "unknown"
                
                # Add to list
                storage_devices.append({
                    'index': i,
                    'mountpoint': partition.mountpoint,
                    'device': partition.device,
                    'fstype': partition.fstype,
                    'size_gb': round(usage.total / (1024**3), 2),
                    'type': device_type
                })
                
            except PermissionError:
                continue
                
    except Exception as e:
        print(f"Error detecting storage devices: {e}")
    
    return storage_devices


def get_network_interfaces():
    """Get list of all network interfaces on the system"""
    network_interfaces = []
    
    print("\nDetecting network interfaces...")
    
    try:
        # Get network address information
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        # Process interfaces
        index = 0
        for interface_name, interface_addresses in net_if_addrs.items():
            # Skip loopback interfaces
            if interface_name.startswith('lo') or interface_name.startswith('veth'):
                continue
                
            # Get IP and MAC
            ip_address = None
            mac_address = None
            
            for addr in interface_addresses:
                if addr.family == socket.AF_INET:
                    ip_address = addr.address
                elif getattr(addr, 'family', None) == psutil.AF_LINK:
                    mac_address = addr.address
            
            # Add both interfaces with and without IPs (user can choose)
            is_up = interface_name in net_if_stats and net_if_stats[interface_name].isup
            
            network_interfaces.append({
                'index': index,
                'name': interface_name,
                'ip_address': ip_address or "Not assigned",
                'mac_address': mac_address or "Not available",
                'is_up': is_up
            })
            index += 1
                
    except Exception as e:
        print(f"Error detecting network interfaces: {e}")
    
    return network_interfaces


def generate_config():
    """Generate the config.ini file"""
    config = configparser.ConfigParser()
    
    # Clear screen
    os.system('cls' if platform.system() == 'Windows' else 'clear')
    
    print("=" * 70)
    print("             System Monitor Configuration Generator")
    print("=" * 70)
    print("\nThis utility will help you create a config.ini file for the system monitor.")
    print("This file will determine which devices are monitored and reported.")
    
    # System Information
    while True:
        short_name = input("\nEnter a short name for this system (letters, numbers, underscores only): ")
        if is_valid_shortname(short_name):
            break
        else:
            print("Invalid short name. Please use only letters, numbers, underscores, and hyphens.")
    
    description = input("\nEnter a description for this system: ")
    
    # Storage Devices
    storage_devices = get_storage_devices()
    
    print("\n----- Storage Devices -----")
    if not storage_devices:
        print("No storage devices detected!")
    else:
        print("ID  | Mount Point                        | Size      | Type | Device")
        print("-" * 80)
        for device in storage_devices:
            print(f"{device['index']:<3} | {device['mountpoint']:<35} | {device['size_gb']:6.2f} GB | {device['type']:<4} | {device['device']}")
    
    # Select storage devices
    selected_storage = []
    if storage_devices:
        storage_input = input("\nEnter the IDs of storage devices to monitor (comma-separated, or 'all'): ")
        
        if storage_input.lower().strip() == 'all':
            selected_storage = [d for d in storage_devices]
        else:
            try:
                selected_ids = [int(id.strip()) for id in storage_input.split(',') if id.strip()]
                selected_storage = [d for d in storage_devices if d['index'] in selected_ids]
            except:
                print("Invalid input. No storage devices selected.")
    
    # Network Interfaces
    network_interfaces = get_network_interfaces()
    
    print("\n----- Network Interfaces -----")
    if not network_interfaces:
        print("No network interfaces detected!")
    else:
        print("ID  | Interface | IP Address         | Status | MAC Address")
        print("-" * 70)
        for iface in network_interfaces:
            status = "Up" if iface['is_up'] else "Down"
            print(f"{iface['index']:<3} | {iface['name']:<9} | {iface['ip_address']:<18} | {status:<6} | {iface['mac_address']}")
    
    # Select network interfaces
    selected_network = []
    if network_interfaces:
        network_input = input("\nEnter the IDs of network interfaces to monitor (comma-separated, or 'all'): ")
        
        if network_input.lower().strip() == 'all':
            selected_network = [n for n in network_interfaces]
        else:
            try:
                selected_ids = [int(id.strip()) for id in network_input.split(',') if id.strip()]
                selected_network = [n for n in network_interfaces if n['index'] in selected_ids]
            except:
                print("Invalid input. No network interfaces selected.")
    
    # Create the config
    config['system'] = {
        'short_name': short_name,
        'description': description,
        'hostname': socket.gethostname()
    }
    
    if selected_storage:
        config['storage'] = {}
        for i, device in enumerate(selected_storage):
            config['storage'][f'device_{i}'] = f"{device['mountpoint']}|{device['type']}"
    
    if selected_network:
        config['network'] = {}
        for i, iface in enumerate(selected_network):
            config['network'][f'interface_{i}'] = iface['name']
    
    # Save the config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    print("\n" + "=" * 70)
    print(f"Configuration saved to {config_path}")
    print("=" * 70)
    print("\nYou can now run the system monitor which will use this configuration.")
    print("To regenerate this configuration, run this script again.")


if __name__ == "__main__":
    generate_config()
