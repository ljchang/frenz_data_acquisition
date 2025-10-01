#!/usr/bin/env python3
"""
Discover all SCORES from FRENZ device by connecting and waiting for ML models to compute.
This script connects, waits for scores to populate, then displays all available metrics.
"""

import sys
import os
import time

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from frenz_collector import FrenzCollector

def main():
    print("\n" + "="*70)
    print("FRENZ SCORES DISCOVERY TOOL")
    print("="*70)

    collector = FrenzCollector()

    # Connect if not already connected
    if not collector.device_manager.is_connected():
        print("\n📡 Connecting to device...")
        result = collector.device_manager.connect()
        if not result:
            print("❌ Failed to connect to device")
            print("   Make sure device is on and FRENZ_ID/FRENZ_KEY are set in .env")
            return 1
        print("✅ Connected successfully!")
    else:
        print("\n✅ Device already connected")

    streamer = collector.device_manager.get_streamer()
    if not streamer or not hasattr(streamer, 'SCORES'):
        print("❌ No SCORES attribute available")
        return 1

    print("\n⏳ Waiting for ML models to compute scores...")
    print("   (This takes ~30-60 seconds as the device collects EEG data)")

    # Monitor SCORES over time
    seen_keys = set()
    max_wait = 60  # Wait up to 60 seconds
    start = time.time()

    while time.time() - start < max_wait:
        current_keys = set(streamer.SCORES.keys())
        new_keys = current_keys - seen_keys

        if new_keys:
            for key in sorted(new_keys):
                print(f"   ✓ Found new score: {key}")
            seen_keys = current_keys

        # Check if we have the main scores we expect
        expected = {'focus_score', 'alpha', 'beta', 'poas', 'sqc_scores'}
        if expected.issubset(seen_keys):
            print("\n✅ All expected scores are now available!")
            break

        time.sleep(2)

    elapsed = time.time() - start
    print(f"\n⏱️  Monitoring complete ({elapsed:.1f}s elapsed)")

    # Display final results
    all_keys = sorted(streamer.SCORES.keys())

    print("\n" + "="*70)
    print(f"AVAILABLE SCORES METRICS ({len(all_keys)} total)")
    print("="*70)

    for key in all_keys:
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

    saved_and_present = [k for k in currently_saved if k in all_keys]
    missing = set(all_keys) - set(currently_saved)

    print(f"\n✅ CURRENTLY SAVED ({len(saved_and_present)} metrics):")
    for key in saved_and_present:
        print(f"  • {key}")

    if missing:
        print(f"\n⚠️  NOT CURRENTLY SAVED ({len(missing)} metrics):")
        for key in sorted(missing):
            print(f"  • {key}")
    else:
        print("\n🎉 All available scores are being saved!")

    print()

    # Disconnect cleanly
    print("🔌 Disconnecting from device...")
    collector.device_manager.disconnect()

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
