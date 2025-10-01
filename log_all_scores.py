#!/usr/bin/env python3
"""
Add this code snippet to your dashboard or collector to log all SCORES keys once.
This will show you what metrics are available.
"""

# Add this to your dashboard or running collector:

# In dashboard.py, you can add a cell like this:
"""
@app.cell
def _(collector):
    if collector.is_recording:
        streamer = collector.device_manager.get_streamer()
        if streamer and hasattr(streamer, 'SCORES'):
            print("\\n" + "="*70)
            print("ALL AVAILABLE SCORES KEYS:")
            print("="*70)
            for key in sorted(streamer.SCORES.keys()):
                value = streamer.SCORES.get(key)
                type_name = type(value).__name__
                shape_info = ""
                if hasattr(value, 'shape'):
                    shape_info = f" shape={value.shape}"
                elif hasattr(value, '__len__') and not isinstance(value, str):
                    shape_info = f" len={len(value)}"
                print(f"  {key:25s} : {type_name}{shape_info}")
            print("="*70 + "\\n")
    return
"""

print(__doc__)
print("\nTo use this, add the code above to your dashboard.py as a new cell.")
print("It will print all available SCORES keys when recording starts.")
