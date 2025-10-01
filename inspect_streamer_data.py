#!/usr/bin/env python3
"""
Inspect streamer temp data to find all available channels.
"""
import sys
from pathlib import Path
from frenztoolkit.reader import load_experiment

# Load most recent streamer data
streamer_dir = Path("data/frenz_streamer_temp")
folders = sorted(streamer_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)

if not folders:
    print("No streamer data found")
    sys.exit(1)

latest = folders[0]
print(f"Loading: {latest.name}")
print("=" * 70)

try:
    data = load_experiment(str(latest))

    print("\n📊 DATA Keys:")
    print("-" * 70)
    for key in sorted(data.get("DATA", {}).keys()):
        print(f"  DATA/{key}")
        subkeys = data["DATA"][key]
        if isinstance(subkeys, dict):
            for subkey in sorted(subkeys.keys()):
                val = subkeys[subkey]
                if hasattr(val, 'shape'):
                    print(f"    {subkey:15s} shape={val.shape} dtype={val.dtype}")
                elif val is None:
                    print(f"    {subkey:15s} = None")
                else:
                    print(f"    {subkey:15s} type={type(val).__name__}")

    print("\n🎯 SCORE Keys:")
    print("-" * 70)
    for key in sorted(data.get("SCORE", {}).keys()):
        val = data["SCORE"][key]
        if hasattr(val, 'shape'):
            print(f"  {key:30s} shape={val.shape} dtype={val.dtype}")
        elif hasattr(val, '__len__') and not isinstance(val, str):
            print(f"  {key:30s} len={len(val)} type={type(val).__name__}")
        else:
            print(f"  {key:30s} = {val} type={type(val).__name__}")

    print("\n" + "=" * 70)

    # Check for EMG/EOG specifically
    print("\n🔍 Checking for EMG/EOG:")
    print("-" * 70)

    raw_data = data.get("DATA", {}).get("RAW", {})
    filtered_data = data.get("DATA", {}).get("FILTERED", {})

    emg = raw_data.get("EMG")
    eog = raw_data.get("EOG")

    print(f"  RAW/EMG: {emg if emg is not None else 'Not available'}")
    print(f"  RAW/EOG: {eog if eog is not None else 'Not available'}")

    emg_filt = filtered_data.get("EMG")
    eog_filt = filtered_data.get("EOG")

    print(f"  FILTERED/EMG: {emg_filt if emg_filt is not None else 'Not available'}")
    print(f"  FILTERED/EOG: {eog_filt if eog_filt is not None else 'Not available'}")

except Exception as e:
    print(f"Error loading data: {e}")
    import traceback
    traceback.print_exc()
