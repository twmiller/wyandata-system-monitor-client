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

def check_kernel_modules():
    print_section("Checking temperature-related kernel modules")
    try:
        lsmod_output = subprocess.check_output(['lsmod'], universal_newlines=True)
        modules_to_check = ['coretemp', 'k10temp', 'intel_powerclamp', 'thermal', 'acpi_thermal_rel']
        
        found_modules = []
        for module in modules_to_check:
            if module in lsmod_output:
                found_modules.append(module)
                print(f"✅ {module} module is loaded")
            else:
                print(f"❌ {module} module is NOT loaded")
        
        if not found_modules:
            print("\nNo temperature-related modules found. Try loading appropriate modules:")
            print("  For Intel CPUs:")
            print("    sudo modprobe intel_powerclamp")
            print("  For AMD CPUs:")
            print("    sudo modprobe k10temp")
            print("\nTo check available modules:")
            print("  find /lib/modules/$(uname -r) -name '*temp*.ko*'")
    except Exception as e:
        print(f"Error checking kernel modules: {e}")

def list_available_modules():
    print_section("Available temperature modules")
    try:
        kernel_version = subprocess.check_output(['uname', '-r'], universal_newlines=True).strip()
        module_paths = subprocess.check_output(
            ['find', f'/lib/modules/{kernel_version}', '-name', '*temp*.ko*'], 
            stderr=subprocess.STDOUT,
            universal_newlines=True
        ).strip().split('\n')
        
        if module_paths and module_paths[0]:
            print(f"Found {len(module_paths)} temperature-related modules:")
            for path in module_paths:
                print(f"  → {path}")
        else:
            print("No temperature modules found in kernel modules directory")
        
        # Also check thermal modules
        thermal_paths = subprocess.check_output(
            ['find', f'/lib/modules/{kernel_version}', '-name', '*thermal*.ko*'], 
            stderr=subprocess.STDOUT,
            universal_newlines=True
        ).strip().split('\n')
        
        if thermal_paths and thermal_paths[0]:
            print(f"\nFound {len(thermal_paths)} thermal-related modules:")
            for path in thermal_paths:
                print(f"  → {path}")
            
    except Exception as e:
        print(f"Error listing available modules: {e}")

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
                    try:
                        temp_value = float(f.read().strip()) / 1000.0
                        print(f"  Temperature: {temp_value}°C")
                    except ValueError:
                        print(f"  Error reading temperature: invalid value")
            else:
                print("  ❌ No temperature reading available")
    except Exception as e:
        print(f"Error checking thermal zones: {e}")

def check_acpi_thermal():
    print_section("Checking ACPI thermal information")
    
    try:
        if os.path.exists("/proc/acpi/thermal_zone"):
            thermal_zones = os.listdir("/proc/acpi/thermal_zone")
            print(f"Found {len(thermal_zones)} ACPI thermal zones")
            
            for zone in thermal_zones:
                print(f"\nZone: {zone}")
                
                # Check temperature
                temp_path = f"/proc/acpi/thermal_zone/{zone}/temperature"
                if os.path.exists(temp_path):
                    with open(temp_path, 'r') as f:
                        print(f"  Temperature: {f.read().strip()}")
                else:
                    print("  No temperature data available")
        else:
            print("ACPI thermal zone information not available")

        # Check for ACPI data in sysfs
        print("\nChecking ACPI in sysfs:")
        for path in glob.glob("/sys/class/thermal/thermal_zone*/device/acpi*"):
            print(f"Found: {path}")
            try:
                with open(path, 'r') as f:
                    print(f"  Value: {f.read().strip()}")
            except:
                print("  Cannot read file")
                
    except Exception as e:
        print(f"Error checking ACPI thermal: {e}")

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
        try:
            sensors_output = subprocess.check_output(['sensors'], universal_newlines=True)
            print(sensors_output)
        except subprocess.CalledProcessError as e:
            print(f"Error running sensors command: {e}")
            print("Try running 'sudo sensors-detect --auto' to configure sensors")
    except Exception as e:
        print(f"Error running lm-sensors: {e}")

def check_system_info():
    print_section("System information")
    
    try:
        print(f"Platform: {platform.platform()}")
        print(f"Machine: {platform.machine()}")
        print(f"Processor: {platform.processor()}")
        print(f"Kernel: {os.uname().release}")
        
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

def check_proc_temperatures():
    print_section("Checking /proc for temperature data")
    
    try:
        # Some systems have CPU temperature here
        if os.path.exists("/proc/acpi/ibm/thermal"):
            print("ThinkPad-specific thermal data:")
            with open("/proc/acpi/ibm/thermal", 'r') as f:
                print(f.read())
        else:
            print("No ThinkPad-specific thermal data available")
            
        # Check for other temperature sources in /proc
        # Exclude IPv6 configuration which has "temp" in the name but is unrelated
        temp_files = []
        for root, dirs, files in os.walk("/proc"):
            # Skip IPv6 configuration directories
            if "ipv6/conf" in root:
                continue
                
            for file in files:
                if "temp" in file.lower() and not file.startswith("temp_"):
                    temp_files.append(os.path.join(root, file))
        
        if temp_files:
            print(f"\nFound {len(temp_files)} potential temperature-related files in /proc:")
            for file in temp_files[:10]:  # Limit to first 10 to avoid excessive output
                print(f"  {file}")
                try:
                    with open(file, 'r') as f:
                        content = f.read().strip()
                        if len(content) < 100:  # Only print short content
                            print(f"    Content: {content}")
                except Exception:
                    pass
        else:
            print("No temperature-related files found in /proc")
    except Exception as e:
        print(f"Error checking /proc temperatures: {e}")

def suggest_next_steps():
    print_section("Recommended Next Steps")
    
    print("Based on your Ubuntu 24.04 system and HP Z240 workstation:")
    print("")
    print("1. Install and configure lm-sensors:")
    print("   sudo apt-get update")
    print("   sudo apt-get install lm-sensors")
    print("   sudo sensors-detect --auto")
    print("")
    print("2. Load appropriate kernel modules for Intel CPU:")
    print("   sudo modprobe intel_powerclamp  # For newer kernels")
    print("   echo 'intel_powerclamp' | sudo tee -a /etc/modules")
    print("")
    print("3. Configure system to use ACPI thermal sensors:")
    print("   sudo apt-get install acpi")
    print("   sudo systemctl restart acpid")
    print("")
    print("4. Update the system monitor client to use thermal_zone entries if available.")
    print("")
    print("5. Check if the temp sensor is exposed through MSR (Model-Specific Registers):")
    print("   sudo apt-get install msr-tools")
    print("   sudo modprobe msr")
    print("   sudo rdmsr --all")

if __name__ == "__main__":
    print("Temperature Sensor Diagnostic Tool")
    print("=================================")
    
    if platform.system() != 'Linux':
        print("This tool only works on Linux systems.")
        sys.exit(1)
    
    check_system_info()
    check_kernel_modules()
    list_available_modules()
    scan_hwmon_devices()
    check_thermal_zones()
    check_acpi_thermal()
    check_lm_sensors()
    check_proc_temperatures()
    suggest_next_steps()
    
    print("\nDiagnostic completed. Please share this output with the developer.")
