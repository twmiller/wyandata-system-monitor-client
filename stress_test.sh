#!/bin/bash

# Script to increase system load for monitoring tests
# Usage: ./increase_load.sh [duration_in_seconds] [intensity]
# Example: ./increase_load.sh 60 8 (runs for 60 seconds with 8 CPU threads)

# Default values
DURATION=${1:-30}  # Default duration: 30 seconds
INTENSITY=${2:-$(nproc)}  # Default intensity: use all available CPU cores

echo "Starting system load test..."
echo "Duration: $DURATION seconds"
echo "Intensity: $INTENSITY parallel processes"
echo "Press Ctrl+C to stop earlier"

# Function to stress CPU
stress_cpu() {
    end_time=$(($(date +%s) + DURATION))
    
    # Start background processes to generate load
    for i in $(seq 1 $INTENSITY); do
        (
            while [ $(date +%s) -lt $end_time ]; do
                # Generate CPU load with intense calculation
                for j in {1..10000}; do
                    echo "scale=5000; 4*a(1)" | bc -l &>/dev/null
                done
            done
        ) &
        echo "Started process $i"
    done
    
    # Wait for duration
    echo "Running load test, please wait $DURATION seconds..."
    sleep $DURATION
    
    # Cleanup any remaining processes
    pkill -P $$
    echo "Load test completed"
}

# Function to stress memory
stress_memory() {
    # Use dd to allocate memory
    dd if=/dev/zero of=/dev/shm/load_test bs=1M count=1024 &>/dev/null
    sleep $DURATION
    rm -f /dev/shm/load_test
}

# Run the stress tests
stress_cpu &
stress_memory &

# Show real-time resource usage
echo "Resource usage during test:"
top -b -d 1 -n $DURATION | grep -E "Cpu|Mem|Swap" &

# Wait for all background processes to complete
wait

echo "System load test completed"
