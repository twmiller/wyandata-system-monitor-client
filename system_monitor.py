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
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('system_monitor_client')

# Configuration
WEBSOCKET_URL = "ws://ghoest:8000/ws/system/metrics/"
CLIENT_ID = str(uuid.uuid4())
HOSTNAME = socket.gethostname()

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
        
        # First pass: Identify physical devices and their partitions
        for partition in psutil.disk_partitions(all=False):
            # Skip certain filesystem types and small partitions
            if partition.fstype == '' or partition.fstype == 'squashfs':
                continue
                
            # Skip EFI partitions by mount point
            if 'efi' in partition.mountpoint.lower() or 'boot/efi' in partition.mountpoint.lower():
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
                    # Get the disk identifier from the device name
                    disk_id = None
                    if '/dev/disk' in device:
                        disk_id = device.split('/')[-1]
                    
                    if disk_id:
                        # Run diskutil info to get the parent disk
                        cmd = ['diskutil', 'info', disk_id]
                        output = subprocess.check_output(cmd).decode('utf-8')
                        
                        # Look for "Part of Whole" to find the physical disk
                        for line in output.split('\n'):
                            if "Part of Whole:" in line:
                                parent_disk = line.split(':', 1)[1].strip()
                                physical_device = f"/dev/{parent_disk}"
                                break
                        
                        # If we couldn't find a parent, this might be a whole disk already
                        if not physical_device:
                            physical_device = device
                except:
                    # If diskutil fails, use the device as is
                    physical_device = device
            
            elif platform.system() == 'Windows':
                # Windows devices are already drive letters (C:, D:, etc.)
                physical_device = device
            
            # If we couldn't determine the physical device, use the device as is
            if not physical_device:
                physical_device = device
            
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
                    continue
                    
                physical_devices[physical_device]["partitions"].append({
                    "mountpoint": partition.mountpoint,
                    "device": device,
                    "total_bytes": usage.total,
                })
            except PermissionError:
                # Some mount points might not be accessible
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
                
                # Add this partition
                primary_partitions.append(partition)
            
            # Create storage device entries for each primary partition
            for partition in primary_partitions:
                storage_devices.append({
                    "id": str(uuid.uuid4()),
                    "name": partition["mountpoint"],
                    "device_type": device_info["device_type"],
                    "total_bytes": partition["total_bytes"],
                })
        
        return storage_devices
    except Exception as e:
        logger.error(f"Error collecting storage devices: {e}")
        return []

async def collect_network_interfaces():
    """Collect information about network interfaces"""
    try:
        network_interfaces = []
        
        # Get network address information
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        for interface_name, interface_addresses in net_if_addrs.items():
            # Skip loopback interfaces
            if interface_name.startswith('lo') or interface_name.startswith('veth'):
                continue
                
            interface_info = {
                "name": interface_name,
                "mac_address": "",
                "ip_address": None,
                "is_up": interface_name in net_if_stats and net_if_stats[interface_name].isup
            }
            
            for addr in interface_addresses:
                if addr.family == socket.AF_INET:
                    interface_info['ip_address'] = addr.address
                elif addr.family == psutil.AF_LINK:
                    interface_info['mac_address'] = addr.address
            
            network_interfaces.append(interface_info)
            
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
        
        # Add temperature sensors if available
        if hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                
                # Print information about available sensors
                logger.info(f"Temperature sensors detected via psutil: {list(temps.keys() if temps else [])}")
                
                if temps:
                    # Standard psutil approach - use it if available
                    for chip, sensors in temps.items():
                        for i, sensor in enumerate(sensors):
                            metrics[f"temp_{chip}_{i}"] = {
                                "value": sensor.current,
                                "unit": "°C",
                                "data_type": "FLOAT",
                                "category": "TEMPERATURE",
                                "label": sensor.label if hasattr(sensor, 'label') and sensor.label else f"{chip}_{i}"
                            }
                            logger.info(f"Added temperature sensor via psutil: {chip}_{i} = {sensor.current}°C ({sensor.label if hasattr(sensor, 'label') and sensor.label else 'unlabeled'})")
                else:
                    logger.info("No temperature sensors found via psutil, trying alternative methods")
            except Exception as e:
                logger.error(f"Error reading temperature sensors via psutil: {e}")

        # Try alternative temperature detection methods for systems 
        # where psutil fails to detect sensors
        try:
            # First check thermal_zone entries (most universally available)
            thermal_base = "/sys/class/thermal"
            thermal_found = False
            
            if os.path.exists(thermal_base):
                thermal_zones = [d for d in os.listdir(thermal_base) if d.startswith("thermal_zone")]
                logger.info(f"Found {len(thermal_zones)} thermal zones")
                
                for zone in thermal_zones:
                    try:
                        zone_path = os.path.join(thermal_base, zone)
                        
                        # Get zone type
                        type_path = os.path.join(zone_path, "type")
                        zone_type = "unknown"
                        if os.path.exists(type_path):
                            with open(type_path, 'r') as f:
                                zone_type = f.read().strip()
                        
                        # Get temperature
                        temp_path = os.path.join(zone_path, "temp")
                        if os.path.exists(temp_path):
                            with open(temp_path, 'r') as f:
                                temp_value = float(f.read().strip()) / 1000.0  # Convert from millidegrees
                                metrics[f"temp_zone_{zone}"] = {
                                    "value": temp_value,
                                    "unit": "°C",
                                    "data_type": "FLOAT",
                                    "category": "TEMPERATURE",
                                    "label": f"Thermal Zone {zone_type}"
                                }
                                logger.info(f"Added thermal zone temperature: {zone} ({zone_type}) = {temp_value}°C")
                                thermal_found = True
                    except Exception as e:
                        logger.debug(f"Error reading thermal zone {zone}: {e}")
            
            # Next, try with hwmon devices if thermal zones didn't work
            if not thermal_found:
                hwmon_base = "/sys/class/hwmon"
                if os.path.exists(hwmon_base):
                    hwmon_devices = os.listdir(hwmon_base)
                    logger.info(f"Found {len(hwmon_devices)} hwmon devices")
                    
                    for device in hwmon_devices:
                        try:
                            device_path = os.path.join(hwmon_base, device)
                            
                            # Try to get device name
                            name_path = os.path.join(device_path, "name")
                            device_name = "unknown"
                            if os.path.exists(name_path):
                                with open(name_path, 'r') as f:
                                    device_name = f.read().strip()
                            
                            # Look for temperature inputs
                            for file in os.listdir(device_path):
                                if file.startswith("temp") and file.endswith("_input"):
                                    with open(os.path.join(device_path, file), 'r') as f:
                                        temp_value = float(f.read().strip()) / 1000.0
                                    
                                    # Try to get a label if available
                                    label = None
                                    label_file = file.replace("_input", "_label")
                                    if os.path.exists(os.path.join(device_path, label_file)):
                                        with open(os.path.join(device_path, label_file), 'r') as f:
                                            label = f.read().strip()
                                    
                                    metrics[f"temp_{device_name}_{file.split('_')[0]}"] = {
                                        "value": temp_value,
                                        "unit": "°C",
                                        "data_type": "FLOAT",
                                        "category": "TEMPERATURE",
                                        "label": label or f"{device_name} {file}"
                                    }
                                    logger.info(f"Added hwmon temperature: {device_name} {file} = {temp_value}°C")
                                    thermal_found = True
                        except Exception as e:
                            logger.debug(f"Error reading hwmon device {device}: {e}")
            
            # If we still don't have temps, try to read CPU package temp using ACPI
            if not thermal_found and platform.system() == 'Linux':
                try:
                    # Try reading from proc/acpi for CPU temp
                    acpi_paths = [
                        "/proc/acpi/thermal_zone",
                        "/proc/acpi/ibm/thermal"
                    ]
                    
                    for path in acpi_paths:
                        if os.path.exists(path):
                            logger.info(f"Found ACPI temperature path: {path}")
                            
                            if os.path.isdir(path):
                                # Directory structure
                                zones = os.listdir(path)
                                for zone in zones:
                                    zone_path = os.path.join(path, zone)
                                    temp_path = os.path.join(zone_path, "temperature")
                                    
                                    if os.path.exists(temp_path):
                                        with open(temp_path, 'r') as f:
                                            temp_line = f.read().strip()
                                            # Format varies, try to extract the number
                                            temp_value = float(re.search(r'\d+', temp_line).group())
                                            metrics[f"temp_acpi_{zone}"] = {
                                                "value": temp_value,
                                                "unit": "°C",
                                                "data_type": "FLOAT",
                                                "category": "TEMPERATURE",
                                                "label": f"ACPI {zone}"
                                            }
                                            logger.info(f"Added ACPI temperature: {zone} = {temp_value}°C")
                                            thermal_found = True
                            else:
                                # Direct file (like ThinkPad's thermal file)
                                with open(path, 'r') as f:
                                    content = f.read().strip()
                                    # Extract the first temperature value
                                    match = re.search(r'(\d+)', content)
                                    if match:
                                        temp_value = float(match.group(1))
                                        metrics["temp_acpi"] = {
                                            "value": temp_value,
                                            "unit": "°C",
                                            "data_type": "FLOAT",
                                            "category": "TEMPERATURE",
                                            "label": "ACPI CPU Temperature"
                                        }
                                        logger.info(f"Added ACPI temperature: CPU = {temp_value}°C")
                                        thermal_found = True
                except Exception as e:
                    logger.debug(f"Failed to read from ACPI temperature sources: {e}")
                    
            if not thermal_found:
                logger.warning("Could not find temperature sensors through any method")
            
        except Exception as e:
            logger.error(f"Error in alternative temperature detection: {e}")
                
        return metrics
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return {}

async def register_host(websocket):
    """Register the host with the monitoring server"""
    try:
        # Collect system information
        system_info = await collect_system_info()
        storage_devices = await collect_storage_devices()
        network_interfaces = await collect_network_interfaces()
        
        # Create registration message
        registration_message = {
            "type": "register_host",
            "hostname": HOSTNAME,
            "system_info": system_info,
            "storage_devices": storage_devices,
            "network_interfaces": network_interfaces,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send registration message
        await websocket.send(json.dumps(registration_message))
        logger.info(f"Host registration sent for {HOSTNAME}")
        
        # Wait for confirmation
        response = await websocket.recv()
        response_data = json.loads(response)
        
        if response_data.get('type') == 'registration_confirmed':
            logger.info(f"Host registration confirmed with ID: {response_data.get('host_id')}")
            return True
        else:
            logger.error(f"Host registration failed: {response_data}")
            return False
            
    except Exception as e:
        logger.error(f"Error during host registration: {e}")
        return False

async def send_metrics(websocket):
    """Send metrics to the monitoring server"""
    try:
        # Collect metrics
        metrics = await collect_metrics()
        
        # Create metrics message
        metrics_message = {
            "type": "metrics_update",
            "hostname": HOSTNAME,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send metrics message
        await websocket.send(json.dumps(metrics_message))
        logger.info(f"Metrics sent for {HOSTNAME}")
        
        return True
    except Exception as e:
        logger.error(f"Error sending metrics: {e}")
        return False

async def monitor_system():
    """Main monitoring function"""
    reconnect_delay = 5  # seconds
    
    while True:
        try:
            logger.info(f"Connecting to {WEBSOCKET_URL}")
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                logger.info("WebSocket connection established")
                
                # Register this host
                registered = await register_host(websocket)
                if not registered:
                    logger.error("Failed to register host. Reconnecting...")
                    await asyncio.sleep(reconnect_delay)
                    continue
                
                # Start sending metrics
                while True:
                    sent = await send_metrics(websocket)
                    if not sent:
                        break
                    
                    # Wait before sending next update
                    await asyncio.sleep(10)  # Send metrics every 10 seconds
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"WebSocket connection closed: {e}")
        except Exception as e:
            logger.error(f"Error in monitor_system: {e}")
        
        # Wait before trying to reconnect
        logger.info(f"Reconnecting in {reconnect_delay} seconds...")
        await asyncio.sleep(reconnect_delay)

async def print_system_summary():
    """Print a summary of the system information at startup"""
    try:
        # Get system information
        info = await collect_system_info()
        storage = await collect_storage_devices()
        network = await collect_network_interfaces()
        
        # Format and print system summary
        separator = "=" * 50
        
        print(separator)
        print(f"SYSTEM MONITOR CLIENT - {info['hostname']}")
        print(separator)
        
        # System info
        print(f"System Type:    {info['system_type']}")
        print(f"OS Version:     {info['os_version']}")
        print(f"CPU:            {info['cpu_model']}")
        print(f"CPU Cores:      {info['cpu_cores']}")
        print(f"RAM:            {format_bytes(info['ram_total'])}")
        print(f"GPU:            {info['gpu_model']}")
        print(f"IP Address:     {info['ip_address']}")
        print(separator)
        
        # Storage devices
        print("STORAGE DEVICES:")
        if storage:
            for device in storage:
                print(f"  • {device['name']} ({device['device_type']}): {format_bytes(device['total_bytes'])}")
        else:
            print("  No storage devices detected")
        print(separator)
        
        # Network interfaces
        print("NETWORK INTERFACES:")
        if network:
            for interface in network:
                status = "UP" if interface['is_up'] else "DOWN"
                ip = interface['ip_address'] if interface['ip_address'] else "No IP"
                print(f"  • {interface['name']}: {status}, {ip}")
                if interface['mac_address']:
                    print(f"    MAC: {interface['mac_address']}")
        else:
            print("  No network interfaces detected")
        
        print(separator)
        print(f"WebSocket URL:  {WEBSOCKET_URL}")
        print(separator)
    except Exception as e:
        logger.error(f"Error printing system summary: {e}")
        print("Failed to generate complete system summary")

def format_bytes(bytes_value):
    """Format bytes into a human-readable string"""
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    value = float(bytes_value)
    
    while value > 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
        
    return f"{value:.2f} {units[unit_index]}"

if __name__ == "__main__":
    # Fill in your actual server address here
    WEBSOCKET_URL = "ws://ghoest:8000/ws/system/metrics/"
    
    # Ensure we have the os module imported for temperature metrics
    import os
    import glob
    
    # Enable debug logging temporarily to help troubleshoot temperature sensors
    logger.setLevel(logging.INFO)
    
    # Print system summary at startup
    asyncio.run(print_system_summary())
    
    logger.info(f"Starting system monitoring client for {HOSTNAME}")
    logger.info(f"Connecting to WebSocket server at {WEBSOCKET_URL}")
    
    # Start the monitoring loop
    asyncio.run(monitor_system())
