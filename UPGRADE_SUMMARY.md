# Dashboard Upgrade Summary

## Discovery Results

Ran `discover_scores.py` and found **21 total metrics** available from the FRENZ device, including the **HR and SpO2** you requested!

### All Available SCORES

1. **alpha** - ndarray(5): Alpha band power
2. **array__alpha** - list[25]: Alpha history buffer
3. **array__beta** - list[25]: Beta history buffer
4. **array__delta** - list[25]: Delta history buffer
5. **array__focus_score** - list[25]: Focus history buffer
6. **array__gamma** - list[25]: Gamma history buffer
7. **array__posture** - list[9]: Posture history buffer
8. **array__sqc_scores** - list[9]: Signal quality history buffer
9. **array__theta** - list[25]: Theta history buffer
10. **beta** - ndarray(5): Beta band power
11. **delta** - ndarray(5): Delta band power
12. **end_time** - float: Session end timestamp
13. **focus_score** - float64: Focus/concentration level
14. **gamma** - ndarray(5): Gamma band power
15. **hr** - int: ⭐ **Heart rate (BPM)**
16. **imu_calibration** - tuple[6]: IMU calibration parameters
17. **posture** - str: Body posture classification
18. **spo2** - int: ⭐ **Blood oxygen saturation (%)**
19. **sqc_scores** - list[4]: Signal quality per channel
20. **start_time** - float: Session start timestamp
21. **theta** - ndarray(5): Theta band power

## Changes Made

### 1. Data Collection (frenz_collector.py)
✅ Added `hr` and `spo2` to the scores_map for automatic collection and storage

```python
scores_map = {
    "focus_score": "scores/focus",
    "poas": "scores/poas",
    "posture": "scores/posture",
    "sleep_stage": "scores/sleep_stage",
    "sqc_scores": "scores/signal_quality",
    "hr": "scores/hr",  # Heart rate (BPM) - NEW
    "spo2": "scores/spo2"  # Blood oxygen saturation (%) - NEW
}
```

### 2. Dashboard Visualizations (dashboard.py)

#### Added Heart Rate Panel
- Real-time line plot with markers
- BPM on Y-axis, time on X-axis
- Auto-scales with typical HR range (40-180 BPM)
- Updates every 2 seconds

#### Added SpO2 Panel
- Real-time line plot with color-coded markers
  - Green: >95% (normal)
  - Orange: 90-95% (low)
  - Red: <90% (critical)
- Percentage on Y-axis, time on X-axis
- Auto-scales with typical SpO2 range (85-100%)
- Updates every 2 seconds

#### Added Current Status Card
- Displays real-time status of:
  - **Posture**: 🧍 Upright / 📉 Slouching / ❓ Unknown
  - **Heart Rate**: ❤️ with BPM value
  - **SpO2**: 🫁 with percentage value
- Color-coded indicators (green when available, gray when waiting)
- Updates automatically with recording status refresh

### 3. New Tabs in Dashboard
- "Heart Rate" tab with HR visualization
- "SpO2" tab with blood oxygen visualization

## What's Being Saved Now

The system now saves **10 score metrics** (up from 8):

1. focus_score
2. poas
3. posture
4. sleep_stage
5. sqc_scores (4 channels)
6. alpha, beta, gamma, theta, delta (5 values each)
7. **hr** ⭐ NEW
8. **spo2** ⭐ NEW

Plus all raw sensor data (EEG, EOG, EMG, IMU, PPG).

## How to Use

1. **Start the dashboard:**
   ```bash
   marimo run dashboard.py
   ```

2. **Connect to device** and **Start Recording**

3. **View real-time data** in the tabs:
   - Focus, POAS, Power Bands (brain activity)
   - Signal Quality (electrode contact)
   - IMU (movement), PPG (blood flow)
   - **Heart Rate** ⭐ NEW
   - **SpO2** ⭐ NEW

4. **Check Current Status card** for at-a-glance posture, HR, and SpO2

## Notes

- HR and SpO2 are computed by the device's onboard algorithms (not derived from PPG)
- These metrics appear after ~30-60 seconds of recording (ML models need data)
- All data is automatically saved to HDF5 files in `data/session_YYYYMMDD_HHMMSS/`

## No Need to Compute From PPG

You asked: *"Or do we need to figure out how to compute HR, SP02, respiration from the 3 PPG channels?"*

**Answer:** No! The device provides HR and SpO2 directly via `streamer.SCORES.get('hr')` and `streamer.SCORES.get('spo2')`. These are computed by the device's proprietary algorithms and are ready to use.

**Respiration:** Not found in the available scores. This may not be provided by the device, or might require additional processing of PPG/IMU data.
