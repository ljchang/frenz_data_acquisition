#!/usr/bin/env python3
"""
Inspect all available SCORES from a running FRENZ device.
This should be run while the device is connected and streaming.
"""

import sys
import time

# Import the collector - it should already be connected in another session
from frenz_collector import FrenzCollector

def main():
    print("=" * 70)
    print("INSPECTING ALL AVAILABLE SCORES FROM FRENZ DEVICE")
    print("=" * 70)

    collector = FrenzCollector()

    if not collector.device_manager.is_connected():
        print("\n⚠️  Device not connected. Please ensure device is connected first.")
        print("   (You mentioned it's connected in another terminal)")
        print("\nAttempting to connect...")
        result = collector.device_manager.connect()
        if not result:
            print("❌ Failed to connect")
            return 1
        time.sleep(5)

    streamer = collector.device_manager.get_streamer()

    if not streamer:
        print("❌ ERROR: No streamer available")
        return 1

    if not hasattr(streamer, 'SCORES'):
        print("❌ ERROR: Streamer has no SCORES attribute")
        return 1

    print("\n✅ Connected to device, reading SCORES...\n")

    # Get all keys
    all_keys = sorted(streamer.SCORES.keys())

    print(f"Found {len(all_keys)} total SCORES keys:\n")

    # Categorize by type
    scalars = []
    arrays = []

    for key in all_keys:
        value = streamer.SCORES.get(key)

        # Determine type and shape
        type_name = type(value).__name__

        if hasattr(value, 'shape'):
            shape_str = f"shape={value.shape}"
            arrays.append((key, type_name, shape_str, value))
        elif hasattr(value, '__len__') and not isinstance(value, str):
            length_str = f"len={len(value)}"
            arrays.append((key, type_name, length_str, value))
        else:
            scalars.append((key, type_name, value))

    # Display scalars
    print("SCALAR VALUES:")
    print("-" * 70)
    for key, type_name, value in scalars:
        print(f"  {key:25s} : {type_name:10s} = {value}")

    # Display arrays
    print("\nARRAY VALUES:")
    print("-" * 70)
    for key, type_name, shape_str, value in arrays:
        print(f"  {key:25s} : {type_name:10s} {shape_str:15s}")
        # Show first few values if array
        if hasattr(value, '__len__'):
            if len(value) <= 5:
                print(f"    → values: {list(value)}")
            else:
                print(f"    → values: {list(value[:5])}... (showing first 5)")

    print("\n" + "=" * 70)
    print(f"SUMMARY: {len(scalars)} scalars, {len(arrays)} arrays")
    print("=" * 70)

    # Check what's currently being saved
    print("\nCURRENTLY SAVED in frenz_collector.py:")
    currently_saved = [
        "focus_score", "poas", "posture", "sleep_stage", "sqc_scores",
        "alpha", "beta", "gamma", "theta", "delta"
    ]
    print(f"  {', '.join(currently_saved)}")

    # Find what's missing
    missing = set(all_keys) - set(currently_saved)
    if missing:
        print(f"\n⚠️  NOT CURRENTLY SAVED ({len(missing)} metrics):")
        for key in sorted(missing):
            print(f"  - {key}")
    else:
        print("\n✅ All available scores are being saved!")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
