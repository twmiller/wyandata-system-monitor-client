# system_monitor_client.py

import asyncio
import websockets
import json
import socket
import platform
import psutil
import uuid
import time
import logging
import re
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path
import configparser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitor.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('system_monitor_client')

# Configuration
WEBSOCKET_URL = "ws://ghoest:8000/ws/system/metrics/"
CLIENT_ID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_id.txt")
HOSTNAME = socket.gethostname()

# Add this function to read the configuration file
def read_config():
    """Read configuration from config.ini if it exists"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    config = configparser.ConfigParser()
    
    if os.path.exists(config_path):
        config.read(config_path)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    else:
        logger.warning(f"No configuration file found at {config_path}")
        return None

# Initialize configuration globally
CONFIG = read_config()

# Get or generate a persistent client ID
def get_client_id():
    try:
        # First check if client_id is defined in the config file
        if CONFIG and 'system' in CONFIG and 'client_id' in CONFIG['system']:
            client_id = CONFIG['system']['client_id']
            logger.info(f"Using client ID from config file: {client_id}")
            return client_id
            
        # If not in config, try to load existing client ID from file
        if os.path.exists(CLIENT_ID_FILE):
            with open(CLIENT_ID_FILE, 'r') as f:
                client_id = f.read().strip()
                if client_id:
                    logger.info(f"Using existing client ID: {client_id}")
                    return client_id
        
        # Generate new client ID if none exists
        client_id = str(uuid.uuid4())
        
        # Try to save it
        try:
            with open(CLIENT_ID_FILE, 'w') as f:
                f.write(client_id)
            logger.info(f"Generated and saved new client ID: {client_id}")
        except Exception as e:
            logger.warning(f"Could not save client ID to file: {e}")
            logger.info(f"Using temporary client ID: {client_id}")
            
        return client_id
    except Exception as e:
        logger.error(f"Error managing client ID: {e}")
        return str(uuid.uuid4())  # Fallback to a temporary ID

# Initialize client ID
CLIENT_ID = get_client_id()

async def collect_system_info():
    """Collect basic system information"""
    try:
        info = {
            "hostname": HOSTNAME,
            "client_id": CLIENT_ID,
            "system_type": determine_system_type(),
            "cpu_model": get_cpu_model(),
            "cpu_cores": psutil.cpu_count(logical=True),
            "ram_total": psutil.virtual_memory().total,
            "os_version": f"{platform.system()} {platform.release()}",
            "ip_address": get_primary_ip(),
        }
        
        # Add GPU info
        info['gpu_model'] = get_gpu_info()
        
        # Add information from config file if available
        if CONFIG and 'system' in CONFIG:
            if 'short_name' in CONFIG['system']:
                info['short_name'] = CONFIG['system']['short_name']
            if 'description' in CONFIG['system']:
                info['description'] = CONFIG['system']['description']
        
        return info
    except Exception as e:
        logger.error(f"Error collecting system info: {e}")
        return {"hostname": HOSTNAME, "system_type": determine_system_type()}

def get_cpu_model():
    """Get a more descriptive CPU model name"""
    try:
        if platform.system() == 'Linux':
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        return line.split(':', 1)[1].strip()
            # Fallback
            return platform.processor()
        elif platform.system() == 'Darwin':  # macOS
            cmd = ['sysctl', '-n', 'machdep.cpu.brand_string']
            return subprocess.check_output(cmd).decode('utf-8').strip()
        else:
            return platform.processor()
    except:
        return platform.processor()

def get_primary_ip():
    """Get the primary IP address"""
    try:
        # This gets the IP used to connect to the internet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        # Fallback
        return socket.gethostbyname(socket.gethostname())

def get_gpu_info():
    """Get GPU information in a more robust way"""
    try:
        if platform.system() == 'Linux':
            # Try lspci first for AMD and NVIDIA cards
            try:
                cmd = ['lspci', '-v']
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
                
                # Look for graphics cards
                for line in output.split('\n'):
                    if re.search(r'VGA|3D|Display|Graphics', line, re.IGNORECASE):
                        # Get the GPU model from the line
                        if "AMD" in line or "ATI" in line or "Radeon" in line:
                            match = re.search(r'.*?:\s(AMD|ATI).*?(Radeon[^[]*)', line)
                            if match:
                                return match.group(2).strip()
                        elif "NVIDIA" in line:
                            match = re.search(r'.*?:\sNVIDIA\s(.*?)\s[\[(]', line)
                            if match:
                                return f"NVIDIA {match.group(1).strip()}"
                
                # Second pass for Intel graphics
                for line in output.split('\n'):
                    if "Intel" in line and re.search(r'VGA|3D|Display|Graphics', line, re.IGNORECASE):
                        match = re.search(r'.*?:\s(Intel.*?)\s[\[(]', line)
                        if match:
                            return match.group(1).strip()
            except:
                pass
                
            # Fallback to glxinfo for Linux
            try:
                cmd = ['glxinfo', '-B']
                output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
                for line in output.split('\n'):
                    if 'OpenGL renderer string' in line:
                        return line.split(':', 1)[1].strip()
            except:
                pass
                
        elif platform.system() == 'Darwin':  # macOS
            try:
                cmd = ['system_profiler', 'SPDisplaysDataType']
                output = subprocess.check_output(cmd).decode('utf-8')
                for line in output.split('\n'):
                    if 'Chipset Model:' in line:
                        return line.split(':', 1)[1].strip()
            except:
                pass
        
        # Last resort
        return "Unknown GPU"
    except Exception as e:
        logger.error(f"Error getting GPU info: {e}")
        return "Unknown GPU"

def determine_system_type():
    """Determine the system type based on the platform"""
    system = platform.system().lower()
    if 'linux' in system:
        if 'arm' in platform.machine().lower():
            return 'RASPBERRY'
        return 'LINUX'
    elif 'darwin' in system:
        return 'MACOS'
    elif 'windows' in system:
        return 'WINDOWS'
    return 'OTHER'

def get_linux_drive_type(device_path):
    """
    Determine if a Linux device is an SSD or HDD using more reliable methods.
    Returns "SSD", "HDD", or "unknown"
    """
    try:
        # Extract the base device name (e.g., sda from /dev/sda1)
        if '/dev/' in device_path:
            base_device = re.sub(r'p?\d+$', '', device_path)  # Remove partition number
            device_name = base_device.split('/')[-1]  # Get just the device name
        else:
            return "unknown"
            
        # Check rotational flag in sysfs - the most reliable way in Linux
        # 0 means SSD, 1 means HDD
        rotational_path = f"/sys/block/{device_name}/queue/rotational"
        if os.path.exists(rotational_path):
            with open(rotational_path, 'r') as f:
                rotational = int(f.read().strip())
                return "HDD" if rotational == 1 else "SSD"
                
        # Try by using SMART data
        try:
            cmd = ['smartctl', '-i', base_device]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8').lower()
            
            # Check for SSD indicators in SMART output
            if 'solid state device' in output or 'ssd' in output:
                return "SSD"
            elif 'rotation rate' in output or 'rpm' in output:
                return "HDD"
        except:
            pass
            
        # Fallback to name-based detection
        device_lower = device_path.lower()
        if "nvme" in device_lower or "ssd" in device_lower:
            return "SSD"
        elif "sd" in device_lower:
            # Most modern "/dev/sd*" devices are HDDs, but not always
            return "HDD"
            
        return "unknown"
    except Exception as e:
        logger.error(f"Error determining drive type: {e}")
        return "unknown"

async def collect_storage_devices():
    """Collect information about storage devices"""
    try:
        storage_devices = []
        physical_devices = {}
        
        # If we have a configuration, only collect configured devices
        if CONFIG and 'storage' in CONFIG:
            logger.info("Using storage devices from configuration file")
            
            config_devices = []
            for key, value in CONFIG['storage'].items():
                if key.startswith('device_'):
                    try:
                        mountpoint, device_type = value.split('|')
                        config_devices.append((mountpoint, device_type))
                        logger.debug(f"Config: Storage device {mountpoint} ({device_type})")
                    except:
                        logger.warning(f"Invalid storage device format in config: {value}")
            
            # Only check configured mountpoints
            for mountpoint, config_type in config_devices:
                try:
                    usage = psutil.disk_usage(mountpoint)
                    
                    storage_devices.append({
                        "id": str(uuid.uuid4()),
                        "name": mountpoint,
                        "device_type": config_type,
                        "total_bytes": usage.total,
                    })
                    
                    logger.info(f"Added configured storage device: {mountpoint} ({config_type})")
                except Exception as e:
                    logger.error(f"Error accessing configured mountpoint {mountpoint}: {e}")
                    
            return storage_devices
            
        # If no configuration, proceed with default detection
        for partition in psutil.disk_partitions(all=False):
            # Skip certain filesystem types and small partitions
            if partition.fstype == '' or partition.fstype == 'squashfs':
                continue
                
            # Skip EFI partitions by mount point
            if 'efi' in partition.mountpoint.lower() or 'boot/efi' in partition.mountpoint.lower():
                continue
                
            # macOS specific filtering
            if platform.system() == 'Darwin':
                # Skip iOS/watchOS simulator volumes, development volumes, and other non-physical drives
                if any(skip_pattern in partition.mountpoint for skip_pattern in [
                    '/Library/Developer/CoreSimulator',
                    '/Volumes/com.apple',
                    '/private/var/vm',
                    '/System/Volumes/VM',
                    '/System/Volumes/Preboot',
                    '/System/Volumes/Data',
                    '/System/Volumes/Update',
                    'TimeMachine'
                ]):
                    logger.debug(f"Skipping macOS special volume: {partition.mountpoint}")
                    continue
                
                # Only include root volume and /Volumes/* mounts (real external drives)
                if partition.mountpoint != '/' and not partition.mountpoint.startswith('/Volumes/'):
                    logger.debug(f"Skipping non-root, non-Volumes macOS mount: {partition.mountpoint}")
                    continue
            
            # Get device name
            device = partition.device
            
            # Extract the physical device identifier - platform specific approach
            physical_device = None
            
            if platform.system() == 'Linux':
                # For Linux, extract the physical device name from the partition name
                if 'nvme' in device.lower():
                    # Handle NVMe drives which use a different naming scheme
                    match = re.match(r'(/dev/nvme[0-9]+n[0-9]+)p?[0-9]*', device)
                    if match:
                        physical_device = match.group(1)
                else:
                    # Standard drives like /dev/sda1 -> /dev/sda
                    match = re.match(r'(/dev/[a-zA-Z]+)[0-9]*', device)
                    if match:
                        physical_device = match.group(1)
            
            elif platform.system() == 'Darwin':  # macOS
                # For macOS, use diskutil to map the device to its physical disk
                try:
                    # For macOS, set device type more accurately
                    device_type = "SSD"  # Most modern Macs use SSDs by default
                    
                    # If this is an external drive, try to determine its type
                    if partition.mountpoint.startswith('/Volumes/'):
                        # Check if it's a real physical drive and what type
                        try:
                            cmd = ['diskutil', 'info', partition.mountpoint]
                            output = subprocess.check_output(cmd).decode('utf-8').lower()
                            
                            # Look for indicators of drive type
                            if any(ssd_indicator in output for ssd_indicator in ['solid state', 'ssd']):
                                device_type = "SSD"
                            elif any(hdd_indicator in output for hdd_indicator in ['rotational', 'hard drive', 'hdd']):
                                device_type = "HDD"
                            # Also check if it's a network drive or other virtual drive
                            if any(fake_indicator in output for fake_indicator in ['network', 'virtual', 'synthesized']):
                                logger.debug(f"Skipping non-physical drive: {partition.mountpoint}")
                                continue
                        except:
                            # If diskutil fails, still include the drive but mark as unknown type
                            device_type = "unknown"
                    
                    # Get the disk identifier from the device name (only needed for physical device grouping)
                    if '/dev/disk' in device:
                        disk_id = device.split('/')[-1]
                        
                        # Run diskutil info to get the parent disk
                        cmd = ['diskutil', 'info', disk_id]
                        output = subprocess.check_output(cmd).decode('utf-8')
                        
                        # Look for "Part of Whole" to find the physical disk
                        for line in output.split('\n'):
                            if "Part of Whole:" in line:
                                parent_disk = line.split(':', 1)[1].strip()
                                physical_device = f"/dev/{parent_disk}"
                                break
                        
                    # If we couldn't find a parent, use the partition itself
                    if not physical_device:
                        physical_device = device or partition.mountpoint
                        
                    # Store the device type for later use
                    if physical_device not in physical_devices:
                        physical_devices[physical_device] = {
                            "device": physical_device,
                            "device_type": device_type,
                            "partitions": []
                        }
                except:
                    # If diskutil fails, use the device as is
                    physical_device = device or partition.mountpoint
            
            elif platform.system() == 'Windows':
                # Windows devices are already drive letters (C:, D:, etc.)
                physical_device = device
            
            # If we couldn't determine the physical device, use the device as is
            if not physical_device:
                physical_device = device or partition.mountpoint
            
            # Initialize physical device entry if it doesn't exist
            if physical_device not in physical_devices:
                # Determine device type based on the platform
                device_type = "unknown"
                
                if platform.system() == 'Linux':
                    # Use our enhanced Linux device type detection
                    device_type = get_linux_drive_type(physical_device)
                else:
                    # Fallback for other platforms
                    if "ssd" in device.lower() or "nvme" in device.lower() or "flash" in device.lower():
                        device_type = "SSD"
                    elif "sd" in device.lower() or "hd" in device.lower():
                        device_type = "HDD"
                
                physical_devices[physical_device] = {
                    "device": physical_device,
                    "device_type": device_type,
                    "partitions": []
                }
            
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                # Skip tiny partitions (less than 1GB generally indicates boot partitions or recovery partitions)
                if usage.total < 1e9:
                    logger.debug(f"Skipping small partition: {partition.mountpoint} ({usage.total / 1e6:.2f} MB)")
                    continue
                    
                physical_devices[physical_device]["partitions"].append({
                    "mountpoint": partition.mountpoint,
                    "device": device,
                    "total_bytes": usage.total,
                })
                logger.debug(f"Adding partition: {partition.mountpoint} ({usage.total / 1e9:.2f} GB)")
            except PermissionError:
                # Some mount points might not be accessible
                logger.debug(f"Permission error accessing: {partition.mountpoint}")
                continue
        
        # Second pass: Create the final storage devices list
        # Only include primary mount points for each physical device
        for device_info in physical_devices.values():
            # Skip if no valid partitions were found
            if not device_info["partitions"]:
                continue
                
            # Find main partitions - typically the largest ones or root partitions
            primary_partitions = []
            
            # First check for root partition
            root_partition = next((p for p in device_info["partitions"] 
                                  if p["mountpoint"] == "/" or p["mountpoint"] == "C:"), None)
                
            if root_partition:
                primary_partitions.append(root_partition)
            
            # Then add other significant partitions (non-system partitions)
            for partition in device_info["partitions"]:
                # Skip if already added as root
                if root_partition and partition["mountpoint"] == root_partition["mountpoint"]:
                    continue
                    
                # Skip system-related partitions
                if any(name in partition["mountpoint"].lower() for name in ["boot", "efi", "recovery", "system"]):
                    continue
                
                # For macOS, only add real volumes (root and /Volumes)
                if platform.system() == 'Darwin':
                    if partition.mountpoint == '/' or partition.mountpoint.startswith('/Volumes/'):
                        primary_partitions.append(partition)
                else:
                    # For other OSes, add all significant partitions
                    primary_partitions.append(partition)
            
            # Create storage device entries for each primary partition
            for partition in primary_partitions:
                storage_devices.append({
                    "id": str(uuid.uuid4()),
                    "name": partition["mountpoint"],
                    "device_type": device_info["device_type"],
                    "total_bytes": partition["total_bytes"],
                })
        
        # Log collected storage devices
        if logger.isEnabledFor(logging.DEBUG):
            for device in storage_devices:
                logger.debug(f"Storage device: {device['name']} ({device['device_type']}, {device['total_bytes'] / 1e9:.2f} GB)")
                
        return storage_devices
    except Exception as e:
        logger.error(f"Error collecting storage devices: {e}")
        return []

async def collect_network_interfaces():
    """Collect information about network interfaces"""
    try:
        network_interfaces = []
        
        # If we have a configuration, only collect configured interfaces
        if CONFIG and 'network' in CONFIG:
            logger.info("Using network interfaces from configuration file")
            
            config_interfaces = []
            for key, interface_name in CONFIG['network'].items():
                if key.startswith('interface_'):
                    config_interfaces.append(interface_name)
                    logger.debug(f"Config: Network interface {interface_name}")
            
            # Only check interfaces in config
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            
            for interface_name in config_interfaces:
                if interface_name in net_if_addrs:
                    interface_addresses = net_if_addrs[interface_name]
                    
                    # Initialize interface info
                    interface_info = {
                        "name": interface_name,
                        "mac_address": "",
                        "ip_address": None,
                        "is_up": interface_name in net_if_stats and net_if_stats[interface_name].isup
                    }
                    
                    # Get MAC address and IP
                    for addr in interface_addresses:
                        if getattr(addr, 'family', None) == psutil.AF_LINK:
                            interface_info['mac_address'] = addr.address
                        elif addr.family == socket.AF_INET:
                            interface_info['ip_address'] = addr.address
                    
                    # Always include configured interfaces whether they have IPs or not
                    network_interfaces.append(interface_info)
                    logger.info(f"Added configured network interface: {interface_name} (IP: {interface_info['ip_address'] or 'Not assigned'})")
                else:
                    logger.warning(f"Configured interface {interface_name} not found on system")
                    
            return network_interfaces
            
        # If no configuration, proceed with default detection
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        # Debug log all interfaces found
        if logger.isEnabledFor(logging.DEBUG):
            for name, addrs in net_if_addrs.items():
                ip_addr = next((addr.address for addr in addrs if addr.family == socket.AF_INET), "No IP")
                mac_addr = next((addr.address for addr in addrs if getattr(addr, 'family', None) == psutil.AF_LINK), "No MAC")
                is_up = name in net_if_stats and net_if_stats[name].isup
                logger.debug(f"Found interface: {name}, IP: {ip_addr}, MAC: {mac_addr}, UP: {is_up}")
        
        # Process interfaces - ONLY include those with IP addresses
        for interface_name, interface_addresses in net_if_addrs.items():
            # Skip loopback interfaces explicitly
            if interface_name.startswith('lo') or interface_name.startswith('veth'):
                logger.debug(f"Skipping loopback interface: {interface_name}")
                continue
                
            # Initialize interface info
            interface_info = {
                "name": interface_name,
                "mac_address": "",
                "ip_address": None,
                "is_up": interface_name in net_if_stats and net_if_stats[interface_name].isup
            }
            
            # Get MAC address
            for addr in interface_addresses:
                if getattr(addr, 'family', None) == psutil.AF_LINK:
                    interface_info['mac_address'] = addr.address
            
            # Check if there's an IPv4 address assigned
            ip_addresses = [addr.address for addr in interface_addresses if addr.family == socket.AF_INET]
            
            if ip_addresses:
                # Use the first IPv4 address
                interface_info['ip_address'] = ip_addresses[0]
                
                # Only append interfaces with IP addresses
                network_interfaces.append(interface_info)
                logger.info(f"Including network interface: {interface_name} with IP: {interface_info['ip_address']}")
            else:
                logger.debug(f"Skipping network interface: {interface_name} (no IP address)")
        
        # Log summary of collected interfaces
        if network_interfaces:
            interfaces_summary = ", ".join([f"{i['name']} ({i['ip_address']})" for i in network_interfaces])
            logger.info(f"Collected {len(network_interfaces)} network interfaces with IPs: {interfaces_summary}")
        else:
            logger.warning("No network interfaces with IP addresses found")
            
        return network_interfaces
    except Exception as e:
        logger.error(f"Error collecting network interfaces: {e}")
        return []

async def collect_metrics():
    """Collect current system metrics"""
    try:
        # Basic system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Create metrics dictionary
        metrics = {
            "cpu_usage": {
                "value": cpu_percent,
                "unit": "%",
                "data_type": "FLOAT",
                "category": "CPU"
            },
            "memory_used": {
                "value": memory.used,
                "unit": "bytes",
                "data_type": "INT",
                "category": "MEMORY"
            },
            "memory_percent": {
                "value": memory.percent,
                "unit": "%",
                "data_type": "FLOAT",
                "category": "MEMORY"
            },
            "swap_used": {
                "value": swap.used,
                "unit": "bytes",
                "data_type": "INT",
                "category": "MEMORY"
            },
            "swap_percent": {
                "value": swap.percent,
                "unit": "%",
                "data_type": "FLOAT",
                "category": "MEMORY"
            },
            "boot_time": {
                "value": psutil.boot_time(),
                "unit": "timestamp",
                "data_type": "INT",
                "category": "SYSTEM"
            },
            "process_count": {
                "value": len(psutil.pids()),
                "unit": "count",
                "data_type": "INT",
                "category": "SYSTEM"
            }
        }
        
        # Add load averages on Unix systems
        if hasattr(psutil, "getloadavg"):
            load1, load5, load15 = psutil.getloadavg()
            metrics["load_avg_1min"] = {
                "value": load1,
                "unit": "load",
                "data_type": "FLOAT",
                "category": "SYSTEM"
            }
            metrics["load_avg_5min"] = {
                "value": load5,
                "unit": "load",
                "data_type": "FLOAT",
                "category": "SYSTEM"
            }
            metrics["load_avg_15min"] = {
                "value": load15,
                "unit": "load",
                "data_type": "FLOAT",
                "category": "SYSTEM"
            }
        
        # Add disk usage for each partition
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partition_name = partition.mountpoint.replace(':', '').replace('\\', '/').replace(' ', '_')
                
                metrics[f"disk_used_{partition_name}"] = {
                    "value": usage.used,
                    "unit": "bytes",
                    "data_type": "INT",
                    "category": "STORAGE",
                    "storage_device": partition.mountpoint
                }
                metrics[f"disk_percent_{partition_name}"] = {
                    "value": usage.percent,
                    "unit": "%",
                    "data_type": "FLOAT",
                    "category": "STORAGE",
                    "storage_device": partition.mountpoint
                }
            except (PermissionError, FileNotFoundError):
                continue
        
        # Add network IO counters
        net_io = psutil.net_io_counters(pernic=True)
        for interface, counters in net_io.items():
            # Skip loopback interfaces
            if interface.startswith('lo') or interface.startswith('veth'):
                continue
                
            metrics[f"net_bytes_sent_{interface}"] = {
                "value": counters.bytes_sent,
                "unit": "bytes",
                "data_type": "INT",
                "category": "NETWORK",
                "network_interface": interface
            }
            metrics[f"net_bytes_recv_{interface}"] = {
                "value": counters.bytes_recv,
                "unit": "bytes",
                "data_type": "INT",
                "category": "NETWORK",
                "network_interface": interface
            }
        
        return metrics
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return {}

async def register_host(websocket):
    """Register the host with the monitoring server"""
    try:
        logger.info(f"Beginning host registration process for {HOSTNAME}...")
        
        # Collect system information
        logger.info("Collecting system information...")
        system_info = await collect_system_info()
        
        # Get the fields we need to explicitly add at the root level
        explicit_client_id = system_info.get("client_id", CLIENT_ID)
        explicit_short_name = system_info.get("short_name", "")
        explicit_description = system_info.get("description", "")
        
        logger.info("Collecting storage device information...")
        storage_devices = await collect_storage_devices()
        
        logger.info("Collecting network interface information...")
        network_interfaces = await collect_network_interfaces()
        
        # Create registration message with explicit fields at root level
        registration_message = {
            "type": "register_host",
            "hostname": HOSTNAME,
            "client_id": explicit_client_id,
            "short_name": explicit_short_name,
            "description": explicit_description,
            "system_info": system_info,
            "storage_devices": storage_devices,
            "network_interfaces": network_interfaces,
            "timestamp": datetime.now().isoformat()
        }
        
        # Log the exact message structure we're sending
        logger.info(f"Registration message includes: client_id={registration_message['client_id']}, " +
                   f"short_name='{registration_message['short_name']}', " +
                   f"description='{registration_message['description']}'")
        
        # Send registration message
        logger.info(f"Sending registration data to server")
        await websocket.send(json.dumps(registration_message))
        logger.info(f"Registration data sent successfully")
        
        # Wait for confirmation
        logger.info("Waiting for server confirmation...")
        
        # Set a reasonable timeout
        max_wait_time = 10  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                response_data = json.loads(response)
                
                logger.info(f"Received response: {response_data.get('type')}")
                
                if response_data.get('type') == 'registration_confirmed':
                    logger.info(f"✅ Host registration confirmed with ID: {response_data.get('host_id')}")
                    return True
            except asyncio.TimeoutError:
                logger.warning("Timed out waiting for registration response, continuing to wait...")
        
        logger.error("❌ Host registration timed out")
        return False
            
    except Exception as e:
        logger.error(f"❌ Error during host registration: {e}")
        return False

async def send_metrics(websocket):
    """Send metrics to the monitoring server"""
    try:
        start_time = time.time()
        logger.debug(f"Collecting metrics for {HOSTNAME}...")
        
        # Check if websocket is still open using a safer method that doesn't rely on internal attributes
        # We'll just proceed and let the send operation handle any connection issues
        
        # Collect metrics
        metrics = await collect_metrics()
        
        # Count metrics by category
        categories = {}
        for key, metric in metrics.items():
            category = metric.get("category", "OTHER")
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        categories_str = ", ".join([f"{cat}: {count}" for cat, count in categories.items()])
        logger.info(f"Sending {len(metrics)} metrics ({categories_str})")
        
        # Create metrics message
        metrics_message = {
            "type": "metrics_update",
            "hostname": HOSTNAME,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send metrics message - this will fail if the connection is closed
        await websocket.send(json.dumps(metrics_message))
        
        # Calculate elapsed time
        elapsed = time.time() - start_time
        logger.info(f"Metrics sent successfully in {elapsed:.2f} seconds")
        
        return True
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket connection closed while sending metrics: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending metrics: {e}")
        # Don't immediately break connection for minor errors
        if isinstance(e, (websockets.exceptions.WebSocketException, ConnectionError)):
            return False
        return True

async def monitor_system():
    """Main monitoring function"""
    reconnect_delay = 5  # seconds
    metrics_interval = 10  # seconds
    connection_attempts = 0
    max_backoff = 60  # Maximum reconnect delay in seconds
    
    # Initial delay to allow system to fully boot before connecting
    if os.path.exists("/.dockerenv"):
        # We're in a container, no need to wait
        initial_delay = 1
    else:
        # We're on a physical system, wait longer
        initial_delay = 5
    
    logger.info(f"Starting monitor in {initial_delay} seconds...")
    await asyncio.sleep(initial_delay)
    
    while True:
        try:
            # Implement exponential backoff for reconnection attempts
            if connection_attempts > 0:
                # Calculate backoff time (min of 5 * 2^attempts and max_backoff)
                current_delay = min(reconnect_delay * (2 ** (connection_attempts - 1)), max_backoff)
                logger.info(f"Connection attempt {connection_attempts}, backing off for {current_delay} seconds")
                await asyncio.sleep(current_delay)
            
            connection_attempts += 1
            logger.info(f"Connecting to {WEBSOCKET_URL} (attempt {connection_attempts})...")
            
            try:
                # Using context manager for websocket connection (automatically closes when exiting the context)
                async with websockets.connect(WEBSOCKET_URL) as websocket:
                    logger.info("✅ WebSocket connection established")
                    connection_attempts = 0  # Reset counter on successful connection
                    
                    # First receive the welcome message if it exists
                    try:
                        welcome = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        welcome_data = json.loads(welcome)
                        logger.info(f"Received initial message: {welcome_data}")
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.warning(f"No initial message received or error: {e}")
                    
                    # Register this host
                    registered = await register_host(websocket)
                    if not registered:
                        logger.error("Failed to register host. Will reconnect...")
                        continue
                    
                    # Start sending metrics
                    send_count = 0
                    failure_count = 0
                    while True:
                        try:
                            # Ping the server to verify connection is still alive
                            try:
                                # Send a small ping (some servers might not support actual websocket pings)
                                ping_message = {"type": "ping", "timestamp": datetime.now().isoformat()}
                                await websocket.send(json.dumps(ping_message))
                                logger.debug("Connection ping sent")
                            except Exception as e:
                                logger.error(f"Connection ping failed: {e}")
                                break
                                
                            # Send metrics
                            send_count += 1
                            logger.debug(f"Sending metrics batch #{send_count}")
                            
                            # Try to send metrics and track failures
                            sent = await send_metrics(websocket)
                            if not sent:
                                failure_count += 1
                                logger.error(f"Failed to send metrics (failure {failure_count}/3)")
                                
                                # Break after 3 consecutive failures
                                if failure_count >= 3:
                                    logger.error("Too many consecutive failures, reconnecting...")
                                    break
                            else:
                                # Reset failure count on success
                                failure_count = 0
                            
                            # Wait before sending next update
                            await asyncio.sleep(metrics_interval)
                        except websockets.exceptions.ConnectionClosed as e:
                            logger.error(f"Connection closed during metrics loop: {e}")
                            break
                        except Exception as e:
                            logger.error(f"Error in metrics sending loop: {e}")
                            break
                            
            except websockets.exceptions.InvalidStatusCode as e:
                logger.error(f"Invalid status code: {e}")
                # If we get 404, the endpoint might be wrong - wait longer
                if hasattr(e, 'status_code') and e.status_code == 404:
                    await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Error in connection handling: {e}")
            
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"WebSocket connection closed: {e}")
        except ConnectionRefusedError:
            logger.error(f"Connection refused. Server might be down or unreachable.")
        except OSError as e:
            logger.error(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error in monitor_system: {e}", exc_info=True)
            
            # Add a small delay before reconnecting after unexpected errors
            await asyncio.sleep(5)

# Main entry point
if __name__ == "__main__":
    # Parse command-line arguments
    import argparse
    parser = argparse.ArgumentParser(description="WyanData System Monitor Client")
    parser.add_argument("--server", help="WebSocket server address (e.g., hostname:port)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        websockets_logger = logging.getLogger('websockets')
        websockets_logger.setLevel(logging.DEBUG)
    
    # Update server address if provided
    if args.server:
        WEBSOCKET_URL = f"ws://{args.server}/ws/system/metrics/"
        logger.info(f"Using server address: {WEBSOCKET_URL}")
    
    # Ensure we have the required modules
    import os
    import glob
    
    # Print startup banner
    print("\n" + "=" * 70)
    print(f"  WyanData System Monitor Client")
    print(f"  Host: {HOSTNAME}")
    print(f"  Server: {WEBSOCKET_URL}")
    print(f"  Client ID: {CLIENT_ID}")
    print("=" * 70 + "\n")
    
    # Start the monitoring loop
    try:
        asyncio.run(monitor_system())
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
        print("\nMonitoring stopped. Thank you for using WyanData System Monitor!")
    except Exception as e:
        logger.error(f"Fatal error in monitoring loop: {e}", exc_info=True)
        import traceback
        traceback.print_exc()