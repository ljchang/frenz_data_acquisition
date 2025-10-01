#!/usr/bin/env python3
"""Test script to list all available SCORES metrics from the FRENZ device."""

import time
from frenz_collector import FrenzCollector

def main():
    collector = FrenzCollector()

    # Check if device is already connected
    if not collector.device_manager.is_connected():
        print("Connecting to device...")
        collector.device_manager.connect()
        time.sleep(5)

    streamer = collector.device_manager.get_streamer()

    if not streamer:
        print("ERROR: No streamer available")
        return

    if not hasattr(streamer, 'SCORES'):
        print("ERROR: Streamer has no SCORES attribute")
        return

    print("=" * 70)
    print("AVAILABLE SCORES METRICS")
    print("=" * 70)

    all_keys = sorted(streamer.SCORES.keys())

    for key in all_keys:
        value = streamer.SCORES.get(key)
        type_str = type(value).__name__

        extra_info = ''
        if hasattr(value, '__len__') and not isinstance(value, str):
            extra_info = f' (len={len(value)})'
        if hasattr(value, 'shape'):
            extra_info = f' shape={value.shape}'

        # Display value for scalars, indicate array for arrays
        if hasattr(value, '__len__') and not isinstance(value, str):
            value_display = '[array data]'
        else:
            value_display = str(value)

        print(f"  {key:20s} : {type_str:10s}{extra_info:20s} = {value_display}")

    print(f"\nTotal: {len(all_keys)} score metrics available")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
