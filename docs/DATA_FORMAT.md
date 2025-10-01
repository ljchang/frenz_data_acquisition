# Data Format Documentation

Complete reference for all data collected and stored by the FRENZ Data Acquisition System.

## Table of Contents
- [Session Directory Structure](#session-directory-structure)
- [HDF5 Data Format](#hdf5-data-format)
- [Raw Sensor Data](#raw-sensor-data)
- [Computed Scores](#computed-scores)
- [Event Annotations](#event-annotations)
- [Device Metadata](#device-metadata)
- [FRENZ Streamer Data](#frenz-streamer-data)

---

## Session Directory Structure

Each recording session creates a timestamped directory:

```
data/
├── session_20250930_140523/
│   ├── session_data.h5          # All sensor and ML data (HDF5)
│   ├── events.json               # Event annotations
│   ├── session_info.json         # Session statistics
│   └── device_config.json        # Device configuration & calibration
└── frenz_streamer_temp/
    └── 1759276972.509111/        # Raw streamer output (backup)
        ├── eeg.dat
        ├── imu.dat
        ├── ppg.dat
        ├── hr.dat
        ├── spo2.dat
        ├── recording_data.npz
        └── state.json
```

---

## HDF5 Data Format

**File**: `session_data.h5`

All sensor data and computed scores stored in hierarchical HDF5 format for efficient access and analysis.

### HDF5 Structure

```
/raw/
  /eeg              (N, 7)    - 7-channel EEG data
  /imu              (N, 3)    - 3-axis accelerometer (x, y, z)
  /ppg              (N, 3)    - 3-channel PPG (Green, Red, IR)

/scores/
  /focus            (N,)      - Focus score (0-100)
  /poas             (N,)      - Physical/Occupational Activity Score (0-1)
  /posture          (N,)      - Posture (1=upright, 2=slouching, 0=unknown)
  /sleep_stage      (N,)      - Sleep stage (0-5)
  /signal_quality   (N, 4)    - Per-channel signal quality (0-1)
  /hr               (N,)      - Heart rate (BPM)
  /spo2             (N,)      - Blood oxygen saturation (%)

/power_bands/
  /alpha            (N, 5)    - Alpha band power (8-12 Hz)
  /beta             (N, 5)    - Beta band power (12-30 Hz)
  /gamma            (N, 5)    - Gamma band power (30-100 Hz)
  /theta            (N, 5)    - Theta band power (4-8 Hz)
  /delta            (N, 5)    - Delta band power (0.5-4 Hz)

/timestamps         (N,)      - Unix timestamps (seconds)
```

---

## Raw Sensor Data

### EEG (Electroencephalography)
- **Path**: `/raw/eeg`
- **Shape**: (N, 7)
- **Sampling Rate**: 125 Hz
- **Channels**:
  1. Channel 1 - Left Frontal (LF)
  2. Channel 2 - Left Ear (OTEL - Over The Ear Left)
  3. Channel 3 - Right Frontal (RF)
  4. Channel 4 - Right Ear (OTER - Over The Ear Right)
  5-7. Additional EEG channels
- **Units**: Microvolts (μV)
- **Type**: float32

### IMU (Inertial Measurement Unit)
- **Path**: `/raw/imu`
- **Shape**: (N, 3)
- **Sampling Rate**: 50 Hz
- **Channels**:
  - X-axis acceleration
  - Y-axis acceleration
  - Z-axis acceleration
- **Units**: g (gravitational acceleration)
- **Type**: float32
- **Note**: Calibration parameters saved in `device_config.json`

### PPG (Photoplethysmography)
- **Path**: `/raw/ppg`
- **Shape**: (N, 3)
- **Sampling Rate**: 25 Hz
- **Channels**:
  - Green wavelength (525 nm)
  - Red wavelength (660 nm)
  - Infrared wavelength (940 nm)
- **Units**: Raw intensity values
- **Type**: float32
- **Use**: Input for HR and SpO2 computation

---

## Computed Scores

### Focus Score
- **Path**: `/scores/focus`
- **Sampling Rate**: ~0.5 Hz (every 2 seconds)
- **Range**: 0-100
- **Type**: float32
- **Description**: Real-time cognitive focus/concentration level computed from EEG power bands

### POAS (Physical and Occupational Activity Score)
- **Path**: `/scores/poas`
- **Sampling Rate**: ~0.05 Hz (every 20 seconds)
- **Range**: 0-1
- **Type**: float32
- **Description**: Activity level metric combining movement and physiological data

### Posture
- **Path**: `/scores/posture`
- **Sampling Rate**: ~0.1 Hz (every 10 seconds)
- **Values**:
  - 0 = Unknown
  - 1 = Upright
  - 2 = Slouching
- **Type**: int8
- **Description**: Body posture classification from IMU data

### Sleep Stage
- **Path**: `/scores/sleep_stage`
- **Sampling Rate**: ~0.05 Hz (every 20 seconds)
- **Values**:
  - 0 = Awake
  - 1 = Stage 1 (Light sleep)
  - 2 = Stage 2 (Light sleep)
  - 3 = Stage 3 (Deep sleep)
  - 4 = Stage 4 (Deep sleep)
  - 5 = REM sleep
- **Type**: int8
- **Description**: Sleep stage classification from EEG patterns

### Signal Quality
- **Path**: `/scores/signal_quality`
- **Shape**: (N, 4)
- **Sampling Rate**: ~1 Hz
- **Range**: 0-1 per channel
- **Channels**: [Left Frontal, Left Ear, Right Frontal, Right Ear]
- **Type**: float32
- **Description**: Real-time electrode contact quality
- **Interpretation**:
  - > 0.7 = Good (green)
  - 0.4-0.7 = Fair (orange)
  - < 0.4 = Poor (red)

### Heart Rate
- **Path**: `/scores/hr`
- **Sampling Rate**: 1 Hz
- **Range**: 40-200 BPM (typical)
- **Type**: int16
- **Description**: Heart rate computed from PPG signals

### SpO2 (Blood Oxygen Saturation)
- **Path**: `/scores/spo2`
- **Sampling Rate**: 1 Hz
- **Range**: 85-100%
- **Type**: int16
- **Description**: Peripheral oxygen saturation computed from PPG
- **Interpretation**:
  - > 95% = Normal (green)
  - 90-95% = Low (orange)
  - < 90% = Critical (red)

---

## EEG Power Bands

All power bands have the same structure:

- **Shape**: (N, 5)
- **Sampling Rate**: ~0.5 Hz (every 2 seconds)
- **Channels**:
  1. LF - Left Frontal
  2. OTEL - Over The Ear Left
  3. RF - Right Frontal
  4. OTER - Over The Ear Right
  5. AVG - Average across all channels
- **Units**: Decibels (dB)
- **Type**: float32

### Band Definitions

| Band  | Frequency Range | Path                | Associated With        |
|-------|-----------------|---------------------|------------------------|
| Delta | 0.5-4 Hz        | `/power_bands/delta`| Deep sleep, healing    |
| Theta | 4-8 Hz          | `/power_bands/theta`| Drowsiness, meditation |
| Alpha | 8-12 Hz         | `/power_bands/alpha`| Relaxed, eyes closed   |
| Beta  | 12-30 Hz        | `/power_bands/beta` | Active thinking, focus |
| Gamma | 30-100 Hz       | `/power_bands/gamma`| High-level cognition   |

---

## Event Annotations

**File**: `events.json`

User-annotated events with precise timestamps.

### Format

```json
{
  "session_id": "20250930_140523",
  "total_events": 5,
  "category_counts": {
    "other": 5
  },
  "events": [
    {
      "timestamp": 1759276983.123,
      "description": "Started reading task",
      "category": "other",
      "relative_time": 0.0
    }
  ]
}
```

### Fields

- **timestamp**: Unix timestamp (seconds.microseconds)
- **description**: Free-text event description
- **category**: Event category (currently all "other")
- **relative_time**: Seconds since session start

---

## Device Metadata

**File**: `device_config.json`

Device-specific configuration and calibration data.

### Format

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

6-element array containing device-specific calibration parameters:
- Elements 0-2: Accelerometer offsets (x, y, z)
- Elements 3-5: Gyroscope offsets or scale factors

These values are unique per device and used by firmware to calibrate raw IMU readings.

---

## Session Statistics

**File**: `session_info.json`

Session summary and statistics (created at session end).

### Format

```json
{
  "session_id": "20250930_140523",
  "start_time": 1759276983.66,
  "end_time": 1759277792.38,
  "duration_seconds": 808.72,
  "total_samples": 156789,
  "file_size_mb": 12.34,
  "data_stats": {
    "raw/eeg": 101250,
    "raw/imu": 40450,
    "raw/ppg": 20225,
    "scores/focus": 404,
    "scores/hr": 809
  }
}
```

---

## FRENZ Streamer Data

**Directory**: `data/frenz_streamer_temp/<timestamp>/`

Raw output from frenztoolkit Streamer (backup/reference).

### Files

#### `eeg.dat`
- Binary file with raw EEG data
- Can be loaded with `frenztoolkit.reader.load_experiment()`

#### `imu.dat`, `ppg.dat`, `hr.dat`, `spo2.dat`
- Binary files for respective sensor channels
- Same loading method as EEG

#### `recording_data.npz`
- NumPy archive with metadata
- Keys: `device_id`, `params`, packet timestamps, data sizes

#### `state.json`
- JSON with all SCORES and array buffers
- Contains both latest values and historical buffers (`array__*`)

### Not Saved by Our System

The following are available in streamer but NOT saved to HDF5 (design decision):

- **Array buffers** (`array__focus_score`, `array__alpha`, etc.)
  - Historical buffers maintained by device (last 25-287 samples)
  - Redundant with our HDF5 time-series storage

- **Timestamps** (`start_time`, `end_time`)
  - Saved in metadata files instead

---

## Data Access Examples

### Python - Load Session Data

```python
import h5py
import json
import numpy as np

# Load HDF5 data
with h5py.File('data/session_20250930_140523/session_data.h5', 'r') as f:
    eeg_data = f['/raw/eeg'][:]
    timestamps = f['/timestamps'][:]
    focus_scores = f['/scores/focus'][:]
    hr_data = f['/scores/hr'][:]

    # Get dataset info
    print(f"EEG shape: {eeg_data.shape}")
    print(f"Duration: {timestamps[-1] - timestamps[0]:.1f} seconds")

# Load events
with open('data/session_20250930_140523/events.json') as f:
    events = json.load(f)
    print(f"Total events: {events['total_events']}")

# Load device config
with open('data/session_20250930_140523/device_config.json') as f:
    config = json.load(f)
    print(f"Device: {config['device_id']}")
    print(f"IMU Calibration: {config['imu_calibration']}")
```

### Python - Load Streamer Data

```python
from frenztoolkit.reader import load_experiment

# Load streamer output
data = load_experiment('data/frenz_streamer_temp/1759276972.509111')

# Access data
eeg = data['DATA']['RAW']['EEG']  # Shape: (N, 7)
focus = data['SCORE']['focus_score']  # Latest value
focus_history = data['SCORE']['array__focus_score']  # Historical buffer
```

---

## Data Quality Notes

### Missing Data
- If a sensor temporarily disconnects, that dataset will have gaps
- Timestamps are always continuous - use them to identify gaps

### Signal Quality
- Monitor `/scores/signal_quality` to validate EEG data quality
- Values < 0.4 indicate poor electrode contact

### Computed Metrics
- HR and SpO2 require ~10 seconds of PPG data to stabilize
- Focus score requires ~30 seconds of EEG data for first value
- Sleep stage updates every ~20 seconds

### Synchronization
- All data synchronized via `/timestamps` dataset
- Timestamps are Unix time (seconds since epoch)
- Use timestamps to align different sampling rates

---

## File Size Estimates

**Typical 10-minute session**:
- Raw EEG (125 Hz, 7 ch): ~4 MB
- Raw IMU (50 Hz, 3 ch): ~0.9 MB
- Raw PPG (25 Hz, 3 ch): ~0.5 MB
- All scores: ~0.1 MB
- **Total HDF5**: ~5-6 MB
- Events JSON: < 1 KB
- Metadata JSON: < 1 KB

**Total per session**: ~6 MB + streamer backup (~12 MB) = ~18 MB
