# FRENZ SCORES Reference

Based on your running session logs and frenztoolkit, here are the scores we know are available:

## Currently Saved (11 metrics)

1. **focus_score** - Focus/concentration level (0-100)
2. **poas** - Physical and Occupational Activity Score (~0-1)
3. **posture** - Body posture classification (string: "upright", "slouching", etc.)
4. **sleep_stage** - Sleep stage classification (integer)
5. **sqc_scores** - Signal Quality per Channel (array of 4 values, 0-1)
6. **alpha** - Alpha band power (5 values: LF, OTEL, RF, OTER, AVG) in dB
7. **beta** - Beta band power (5 values) in dB
8. **gamma** - Gamma band power (5 values) in dB
9. **theta** - Theta band power (5 values) in dB
10. **delta** - Delta band power (5 values) in dB

## Likely Available (need confirmation)

These are typical metrics from EEG/biometric devices but not yet confirmed:

- **heart_rate** or **hr** - Heart rate in BPM
- **spo2** - Blood oxygen saturation (%)
- **respiration_rate** or **rr** - Breathing rate
- **hrv** - Heart rate variability
- **stress_score** - Stress level
- **relaxation_score** - Relaxation level
- **movement** - Movement/activity level
- **battery_level** - Device battery status

## To Discover All Metrics

Run `python show_scores.py` while the dashboard is connected and recording.
This will print all available SCORES keys that the device provides.

## Auto-Save All Scores

To automatically save all available scores (including any we haven't discovered yet),
you can modify `frenz_collector.py` to dynamically discover and save all SCORES.
