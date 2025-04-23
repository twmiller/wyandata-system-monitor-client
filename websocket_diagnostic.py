#!/usr/bin/env python3
"""
WebSocket diagnostic tool to analyze server behavior.
"""

import asyncio
import websockets
import json
import logging
import argparse
import sys
import uuid
import socket
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('websocket_diagnostic')

# Default configuration
DEFAULT_URL = "ws://ghoest:8000/ws/system/metrics/"
CLIENT_ID = str(uuid.uuid4())
HOSTNAME = socket.gethostname()

async def send_ping_message(websocket):
    """Send a simple ping message to keep connection alive"""
    ping_message = {
        "type": "ping",
        "client_id": CLIENT_ID,
        "timestamp": datetime.now().isoformat()
    }
    await websocket.send(json.dumps(ping_message))
    logger.info("Sent ping message")

async def send_dummy_registration(websocket):
    """Send minimal registration message"""
    registration_message = {
        "type": "register_host",
        "hostname": f"DIAGNOSTIC-{HOSTNAME}",
        "system_info": {
            "hostname": f"DIAGNOSTIC-{HOSTNAME}",
            "client_id": CLIENT_ID,
            "system_type": "DIAGNOSTIC",
            "cpu_model": "Diagnostic CPU",
            "cpu_cores": 1,
            "ram_total": 1073741824,  # 1GB
            "os_version": "Diagnostic OS",
            "ip_address": "127.0.0.1",
            "gpu_model": "Diagnostic GPU"
        },
        "storage_devices": [],
        "network_interfaces": [],
        "timestamp": datetime.now().isoformat()
    }
    
    await websocket.send(json.dumps(registration_message))
    logger.info("Sent diagnostic registration")
    
    # Wait for response
    response = await websocket.recv()
    logger.info(f"Registration response: {response}")
    return json.loads(response)

async def send_dummy_metrics(websocket):
    """Send minimal metrics message"""
    metrics_message = {
        "type": "metrics_update",
        "hostname": f"DIAGNOSTIC-{HOSTNAME}",
        "metrics": {
            "diagnostic_metric": {
                "value": 42.0,
                "unit": "test",
                "data_type": "FLOAT",
                "category": "DIAGNOSTIC"
            }
        },
        "timestamp": datetime.now().isoformat()
    }
    
    await websocket.send(json.dumps(metrics_message))
    logger.info("Sent diagnostic metric")
    
    # Try to receive response if server sends one
    try:
        # Set a short timeout
        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
        logger.info(f"Server response to metrics: {response}")
    except asyncio.TimeoutError:
        logger.info("No response from server after sending metrics (this is normal)")

async def analyze_connection(url, ping_interval=30, duration=120):
    """Analyze WebSocket connection behavior"""
    try:
        logger.info(f"Connecting to {url}...")
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + duration
        
        async with websockets.connect(url) as websocket:
            logger.info("✅ Connection established")
            
            # Send registration
            response_data = await send_dummy_registration(websocket)
            
            # Send a few metrics and pings while keeping connection alive
            ping_time = asyncio.get_event_loop().time() + ping_interval
            next_metric_time = asyncio.get_event_loop().time() + 5  # First metric after 5 seconds
            
            while asyncio.get_event_loop().time() < end_time:
                current_time = asyncio.get_event_loop().time()
                
                # Check if it's time to send a ping
                if current_time >= ping_time:
                    await send_ping_message(websocket)
                    ping_time = current_time + ping_interval
                
                # Check if it's time to send metrics
                if current_time >= next_metric_time:
                    await send_dummy_metrics(websocket)
                    next_metric_time = current_time + 10  # Send metrics every 10 seconds
                
                # Sleep a bit to avoid busy waiting
                await asyncio.sleep(1)
                
                # Print connection status every 10 seconds
                if int(current_time) % 10 == 0:
                    logger.info(f"Connection is {'open' if websocket.open else 'closed'}, "
                                f"running for {current_time - start_time:.1f} seconds")
            
            logger.info("Test completed successfully. Connection remained open for the entire duration.")
            
    except websockets.exceptions.ConnectionClosed as e:
        elapsed = asyncio.get_event_loop().time() - start_time
        logger.error(f"⚠️ WebSocket connection closed after {elapsed:.1f} seconds with code {e.code}: {e.reason}")
        if e.code == 1000:
            logger.info("Server closed connection gracefully. Server may expect new connections per session.")
        elif e.code == 1006:
            logger.info("Connection closed abnormally (likely network issue or server dropped connection).")
        return False
    except Exception as e:
        logger.error(f"Error during connection analysis: {e}")
        return False
        
    return True

async def main():
    parser = argparse.ArgumentParser(description='WebSocket Connection Diagnostic Tool')
    parser.add_argument('--url', default=DEFAULT_URL, help='WebSocket URL to connect to')
    parser.add_argument('--duration', type=int, default=120, help='Test duration in seconds')
    parser.add_argument('--ping', type=int, default=30, help='Ping interval in seconds')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    print(f"\n{'=' * 70}")
    print(f"  WebSocket Connection Diagnostic")
    print(f"  URL: {args.url}")
    print(f"  Duration: {args.duration} seconds")
    print(f"{'=' * 70}\n")
    
    result = await analyze_connection(args.url, args.ping, args.duration)
    
    print(f"\n{'=' * 70}")
    if result:
        print("  ✅ Connection test PASSED - Server maintains persistent connections")
    else:
        print("  ⚠️ Connection test FAILED - Server may be closing connections prematurely")
    print(f"{'=' * 70}\n")
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
