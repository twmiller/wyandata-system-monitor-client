#!/usr/bin/env python3
"""
Temperature sensor diagnostic tool for WyanData system monitor.
Run this directly on the system where temperature sensors aren't working.
"""

import os
import sys
import glob
import subprocess
import platform

def print_section(title):
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)

def check_coretemp_module():
    print_section("Checking coretemp module")
    try:
        lsmod_output = subprocess.check_output(['lsmod'], universal_newlines=True)
        if 'coretemp' in lsmod_output:
            print("✅ coretemp module is loaded")
        else:
            print("❌ coretemp module is NOT loaded")
            print("\nTry loading it with:")
            print("  sudo modprobe coretemp")
            print("\nTo load it automatically at boot:")
            print("  echo \"coretemp\" | sudo tee -a /etc/modules")
    except Exception as e:
        print(f"Error checking coretemp module: {e}")

def scan_hwmon_devices():
    print_section("Scanning hwmon devices")
    
    try:
        hwmon_base = "/sys/class/hwmon"
        if not os.path.exists(hwmon_base):
            print(f"❌ {hwmon_base} directory does not exist")
            return
            
        hwmon_devices = os.listdir(hwmon_base)
        print(f"Found {len(hwmon_devices)} hwmon devices")
        
        for device in hwmon_devices:
            device_path = os.path.join(hwmon_base, device)
            print(f"\nChecking device: {device_path}")
            
            # Try to get device name
            name_path = os.path.join(device_path, "name")
            device_name = "Unknown"
            if os.path.exists(name_path):
                with open(name_path, 'r') as f:
                    device_name = f.read().strip()
            
            print(f"  Device name: {device_name}")
            
            # Look for temperature inputs
            temp_files = [f for f in os.listdir(device_path) if f.startswith("temp") and f.endswith("_input")]
            if temp_files:
                print(f"  ✅ Found {len(temp_files)} temperature sensors")
                
                for temp_file in temp_files:
                    temp_path = os.path.join(device_path, temp_file)
                    with open(temp_path, 'r') as f:
                        temp_value = float(f.read().strip()) / 1000.0
                    
                    # Check for label
                    label = "N/A"
                    label_file = temp_file.replace("_input", "_label")
                    label_path = os.path.join(device_path, label_file)
                    if os.path.exists(label_path):
                        with open(label_path, 'r') as f:
                            label = f.read().strip()
                    
                    print(f"    → {temp_file}: {temp_value}°C (Label: {label})")
            else:
                print("  ❌ No temperature sensors found in this device")
    except Exception as e:
        print(f"Error scanning hwmon devices: {e}")

def check_thermal_zones():
    print_section("Checking thermal zones")
    
    try:
        thermal_base = "/sys/class/thermal"
        if not os.path.exists(thermal_base):
            print(f"❌ {thermal_base} directory does not exist")
            return
            
        thermal_zones = [d for d in os.listdir(thermal_base) if d.startswith("thermal_zone")]
        print(f"Found {len(thermal_zones)} thermal zones")
        
        for zone in thermal_zones:
            zone_path = os.path.join(thermal_base, zone)
            print(f"\nChecking zone: {zone_path}")
            
            # Get zone type
            type_path = os.path.join(zone_path, "type")
            zone_type = "Unknown"
            if os.path.exists(type_path):
                with open(type_path, 'r') as f:
                    zone_type = f.read().strip()
            
            print(f"  Zone type: {zone_type}")
            
            # Get temperature
            temp_path = os.path.join(zone_path, "temp")
            if os.path.exists(temp_path):
                with open(temp_path, 'r') as f:
                    temp_value = float(f.read().strip()) / 1000.0
                print(f"  Temperature: {temp_value}°C")
            else:
                print("  ❌ No temperature reading available")
    except Exception as e:
        print(f"Error checking thermal zones: {e}")

def check_lm_sensors():
    print_section("Checking lm-sensors output")
    
    try:
        # Check if sensors command exists
        try:
            subprocess.check_output(['which', 'sensors'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            print("❌ 'sensors' command not found")
            print("\nTry installing lm-sensors:")
            print("  sudo apt-get install lm-sensors")
            print("  sudo sensors-detect --auto")
            return
            
        # Run sensors command
        print("Output of 'sensors' command:")
        sensors_output = subprocess.check_output(['sensors'], universal_newlines=True)
        print(sensors_output)
    except Exception as e:
        print(f"Error running lm-sensors: {e}")

def check_system_info():
    print_section("System information")
    
    try:
        print(f"Platform: {platform.platform()}")
        print(f"Machine: {platform.machine()}")
        print(f"Processor: {platform.processor()}")
        
        # Get CPU model from /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        print(f"CPU Model: {line.split(':', 1)[1].strip()}")
                        break
        except:
            pass
            
        # Try to get system product name
        try:
            with open('/sys/class/dmi/id/product_name', 'r') as f:
                print(f"Product Name: {f.read().strip()}")
        except:
            pass
            
        # Try to get system manufacturer
        try:
            with open('/sys/class/dmi/id/sys_vendor', 'r') as f:
                print(f"Manufacturer: {f.read().strip()}")
        except:
            pass
    except Exception as e:
        print(f"Error getting system info: {e}")

if __name__ == "__main__":
    print("Temperature Sensor Diagnostic Tool")
    print("=================================")
    
    if platform.system() != 'Linux':
        print("This tool only works on Linux systems.")
        sys.exit(1)
    
    check_system_info()
    check_coretemp_module()
    scan_hwmon_devices()
    check_thermal_zones()
    check_lm_sensors()
    
    print("\nDiagnostic completed. If you see temperature readings above but they're")
    print("not showing in the monitoring client, please share this output with the developer.")
