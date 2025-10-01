#!/usr/bin/env python3
"""
Test script to verify live data access from FrenzCollector.
This simulates what the dashboard does when accessing streaming data.
"""

import time
import sys
from frenz_collector import FrenzCollector

def test_live_data_access():
    """Test that we can access live streaming data from the collector."""

    print("=" * 60)
    print("Testing Live Data Access from FrenzCollector")
    print("=" * 60)

    # Initialize collector
    collector = FrenzCollector()

    # Check if device is already connected
    if not collector.device_manager.is_connected():
        print("\n❌ Device not connected. Please connect device first.")
        print("   Attempting to connect...")

        # Try to connect using env vars
        result = collector.device_manager.connect()
        if not result:
            print("   ❌ Failed to connect. Exiting.")
            return False

        print("   ✅ Device connected")
    else:
        print("\n✅ Device already connected")

    # Get the streamer
    streamer = collector.device_manager.get_streamer()

    if not streamer:
        print("❌ No streamer available")
        return False

    print(f"✅ Streamer obtained: {type(streamer)}")

    # Check if SCORES attribute exists
    if not hasattr(streamer, 'SCORES'):
        print("❌ Streamer has no SCORES attribute")
        return False

    print(f"✅ SCORES attribute exists: {type(streamer.SCORES)}")

    # Try to access data
    print("\n" + "=" * 60)
    print("Monitoring live data for 10 seconds...")
    print("=" * 60)

    for i in range(10):
        print(f"\n[{i+1}/10] Reading scores...")

        try:
            focus = streamer.SCORES.get("focus_score")
            poas = streamer.SCORES.get("poas_score")
            power_bands = streamer.SCORES.get("power_bands", {})
            signal_quality = streamer.SCORES.get("signal_quality")

            print(f"  Focus: {focus}")
            print(f"  POAS: {poas}")
            print(f"  Power bands: {list(power_bands.keys()) if isinstance(power_bands, dict) else 'N/A'}")
            print(f"  Signal quality: {type(signal_quality)} - {signal_quality if isinstance(signal_quality, (list, tuple)) else 'N/A'}")

            # Check if we're getting non-None values
            if focus is not None or poas is not None:
                print("  ✅ Getting live data!")
            else:
                print("  ⚠️  All values are None")

        except Exception as e:
            print(f"  ❌ Error reading data: {e}")

        time.sleep(1)

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

    return True

if __name__ == "__main__":
    try:
        success = test_live_data_access()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)