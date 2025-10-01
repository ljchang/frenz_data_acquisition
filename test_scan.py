#!/usr/bin/env python3
"""Test device scanning"""

from device_manager import DeviceManager

# Initialize device manager
dm = DeviceManager()

# Scan for devices
print("Scanning for FRENZ devices...")
devices = dm.scan_devices()

if devices:
    print(f"\nFound {len(devices)} FRENZ device(s):")
    for device in devices:
        print(f"  - ID: {device['id']}")
        print(f"    Name: {device['name']}")
        print(f"    RSSI: {device['rssi']}")
else:
    print("No FRENZ devices found")

# Try to connect if devices found
if devices:
    first_device = devices[0]
    print(f"\nAttempting to connect to {first_device['id']}...")

    streamer = dm.connect(device_id=first_device['id'])
    if streamer:
        print("✓ Successfully connected!")
        dm.disconnect()
    else:
        print("✗ Connection failed")