#!/usr/bin/env python3
"""Test what scores are available from the live streamer."""

import time
from frenz_collector import FrenzCollector

collector = FrenzCollector()

# Check if connected
if not collector.device_manager.is_connected():
    print("Device not connected. Connecting...")
    collector.device_manager.connect()
    time.sleep(5)

streamer = collector.device_manager.get_streamer()

if streamer and hasattr(streamer, 'SCORES'):
    print("Available SCORES keys:")
    print(list(streamer.SCORES.keys()))
    print("\nSCORES values:")
    for key, value in streamer.SCORES.items():
        print(f"  {key}: {type(value)} = {value}")
else:
    print("No streamer or no SCORES attribute")