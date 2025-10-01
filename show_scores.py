#!/usr/bin/env python3
"""Quick script to show all SCORES keys from a connected device."""

import sys
import os

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from frenz_collector import FrenzCollector

def main():
    collector = FrenzCollector()

    if not collector.device_manager.is_connected():
        print("📡 Device not connected. Connecting...")
        result = collector.device_manager.connect()
        if not result:
            print("❌ Failed to connect to device")
            print("   Make sure device is on and FRENZ_ID/FRENZ_KEY are set in .env")
            return 1
        print("✅ Connected successfully!")

        # Wait a moment for data to start flowing
        import time
        print("⏳ Waiting for data stream to initialize...")
        time.sleep(5)

    streamer = collector.device_manager.get_streamer()
    if not streamer or not hasattr(streamer, 'SCORES'):
        print("❌ No SCORES available")
        return 1

    keys = sorted(streamer.SCORES.keys())

    print("\n" + "="*70)
    print(f"AVAILABLE SCORES METRICS ({len(keys)} total)")
    print("="*70)

    for key in keys:
        value = streamer.SCORES.get(key)
        type_name = type(value).__name__
        shape_info = ""

        if hasattr(value, 'shape'):
            shape_info = f" shape={value.shape}"
        elif hasattr(value, '__len__') and not isinstance(value, str):
            shape_info = f" len={len(value)}"

        print(f"  {key:25s} : {type_name:10s}{shape_info}")

    print("="*70)

    # Show what's currently being saved
    currently_saved = [
        "focus_score", "poas", "posture", "sleep_stage", "sqc_scores",
        "alpha", "beta", "gamma", "theta", "delta"
    ]

    missing = set(keys) - set(currently_saved)
    if missing:
        print(f"\n⚠️  NOT CURRENTLY SAVED ({len(missing)} metrics):")
        for key in sorted(missing):
            print(f"  • {key}")
    else:
        print("\n✅ All available scores are being saved!")

    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
