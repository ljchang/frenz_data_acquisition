# Session Metadata Collection

## What Gets Saved

When you start a recording session, the system now saves comprehensive metadata about the device and session.

### Files Created Per Session

```
data/session_YYYYMMDD_HHMMSS/
├── session_data.h5           # All sensor data (EEG, IMU, PPG, scores)
├── events.json                # Event annotations with timestamps
├── session_info.json          # Session statistics (created at end)
└── device_config.json         # Device configuration (NEW!)
```

## Device Configuration Data

**Source**: Extracted from `streamer.SCORES.get('imu_calibration')` during session initialization

**File**: `device_config.json`

**Contents**:
```json
{
  "device_id": "FRENZI85",
  "session_start_time": 1759276983.6588612,
  "imu_calibration": [41, 43, 40, 3482, 3828, 2853],
  "device_configuration": {
    "eeg_sampling_rate": 125,
    "imu_sampling_rate": 50,
    "ppg_sampling_rate": 25,
    "hr_sampling_rate": 1,
    "spo2_sampling_rate": 1
  }
}
```

### IMU Calibration

The 6-element array `[41, 43, 40, 3482, 3828, 2853]` contains calibration parameters for the IMU sensor:
- Elements 0-2: Likely accelerometer offsets (x, y, z)
- Elements 3-5: Likely gyroscope offsets or scale factors

These values are device-specific and used by the firmware to calibrate raw IMU readings.

### Sampling Rates

Documented sampling rates for each sensor channel:
- **EEG**: 125 Hz (7 channels)
- **IMU**: 50 Hz (3-axis accelerometer)
- **PPG**: 25 Hz (3 channels: Green, Red, IR)
- **HR**: 1 Hz (computed from PPG)
- **SpO2**: 1 Hz (computed from PPG)

## Score Metrics Being Saved

**Currently saved in HDF5**:
1. focus_score
2. poas
3. posture (encoded as int: 1=upright, 2=slouching, 0=unknown)
4. sleep_stage (integer 0-5)
5. sqc_scores (4-channel signal quality)
6. hr (heart rate in BPM)
7. spo2 (blood oxygen saturation %)
8. alpha, beta, gamma, theta, delta (5 values each: LF, OTEL, RF, OTER, AVG)

**Total**: 10 score metrics + 5 power bands

## Not Currently Saved

These are available but not being saved (design decision):
- `array__*` versions (historical buffers maintained by device)
- `start_time` / `end_time` (session timestamps - redundant with session_info.json)
- Individual `.dat` files from streamer (we save to HDF5 instead)

## Why This Matters

1. **Reproducibility**: IMU calibration ensures you can correctly interpret IMU data
2. **Analysis**: Knowing sampling rates is critical for signal processing
3. **Debugging**: Device ID helps track which device was used
4. **Validation**: Can verify data integrity using timestamps and sample counts
