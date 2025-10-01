# FRENZ Data Collection System Specification

## Overview
A comprehensive data collection system for FRENZ brainband devices with real-time visualization, continuous recording, and event annotation capabilities. Built with Marimo for interactive dashboards and HDF5 for efficient data storage.

## System Architecture

### Core Components

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Device Manager    │────▶│  FRENZ Collector │────▶│  Data Storage   │
│  - Scan devices     │     │  - Stream data   │     │  - HDF5 writer  │
│  - Connect/disconnect│     │  - Buffer mgmt   │     │  - Auto-save    │
└─────────────────────┘     └──────────────────┘     └─────────────────┘
           │                          │                        │
           ▼                          ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Marimo Dashboard                              │
│  - Device selection    - Real-time plots    - Event annotation       │
│  - Recording controls  - Memory-safe display - Session management    │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Device Connection**: Scanner → Device Selection → Streamer Initialization
2. **Data Collection**: FRENZ Device → Streamer → Buffer → Periodic Save to HDF5
3. **Visualization**: Buffer → Rolling Display Buffer → Marimo Plots
4. **Event Logging**: User Input → Timestamp → JSON File

## Module Specifications

### 1. Device Manager (`device_manager.py`)

**Purpose**: Handle device discovery, connection, and management

**Class: DeviceManager**
```python
Methods:
- scan_devices() -> List[Dict]
  # Returns: [{"id": "FRENZ-001", "name": "FRENZ Band", "rssi": -45}]

- load_env_devices() -> Dict
  # Returns devices from .env file

- connect(device_id: str, product_key: str) -> Streamer
  # Establishes connection and returns Streamer instance

- disconnect() -> bool
  # Cleanly disconnects current device

- get_status() -> DeviceStatus
  # Returns: DISCONNECTED, SCANNING, CONNECTING, CONNECTED, ERROR

- auto_reconnect() -> bool
  # Attempts to reconnect on connection loss
```

**Error Handling**:
- Device not found
- Connection timeout
- Invalid credentials
- Connection drops

### 2. Data Storage (`data_storage.py`)

**Purpose**: Manage HDF5 file storage with buffering and auto-save

**Class: DataStorage**
```python
Attributes:
- session_path: Path
- buffer_size: int (default: 5 minutes of data)
- auto_save_interval: int (seconds, default: 300)

Methods:
- initialize_session(session_id: str) -> bool
  # Creates session directory and HDF5 file

- create_datasets() -> bool
  # Initializes HDF5 structure with appropriate chunk sizes

- append_data(data_type: str, data: np.array, timestamp: float)
  # Adds data to buffer with timestamp

- flush_buffer() -> bool
  # Writes buffer to disk

- auto_save_worker() -> None
  # Background thread for periodic saves

- finalize_session() -> Dict
  # Closes file and returns session summary
```

**HDF5 Structure**:
```
/session_data.h5
├── /raw
│   ├── /eeg            [N, 4] float32, chunks=(10000, 4)
│   ├── /eog            [N, 4] float32
│   ├── /emg            [N, 4] float32
│   ├── /imu            [N, 3] float32
│   └── /ppg            [N, 3] float32
├── /filtered
│   ├── /eeg            [N, 4] float32
│   ├── /eog            [N, 4] float32
│   └── /emg            [N, 4] float32
├── /scores
│   ├── /poas           [N] float32
│   ├── /focus          [N] float32
│   ├── /posture        [N] int8
│   ├── /sleep_stage    [N] int8
│   └── /signal_quality [N, 4] float32
├── /power_bands
│   ├── /alpha          [N, 5] float32 (LF, OTEL, RF, OTER, AVG)
│   ├── /beta           [N, 5] float32
│   ├── /gamma          [N, 5] float32
│   ├── /theta          [N, 5] float32
│   └── /delta          [N, 5] float32
└── /timestamps         [N] float64 (unix timestamps)
```

### 3. Event Logger (`event_logger.py`)

**Purpose**: Log manual events with timestamps

**Class: EventLogger**
```python
Methods:
- log_event(description: str, category: str = None) -> Dict
  # Returns: {"timestamp": unix_time, "description": str, "category": str}

- get_events(start_time: float = None, end_time: float = None) -> List[Dict]
  # Returns filtered list of events

- save_events() -> bool
  # Writes events to JSON file

- export_events(format: str = "csv") -> Path
  # Export events in specified format
```

**Event Schema**:
```json
{
  "timestamp": 1696012345.678,
  "iso_time": "2024-09-28T14:30:45.678Z",
  "description": "Subject reported feeling drowsy",
  "category": "subjective",
  "session_id": "20240928_143022"
}
```

### 4. FRENZ Collector (`frenz_collector.py`)

**Purpose**: Main orchestrator for data collection

**Class: FrenzCollector**
```python
Attributes:
- device_manager: DeviceManager
- storage: DataStorage
- event_logger: EventLogger
- streamer: Streamer (from frenztoolkit)
- is_recording: bool
- session_start_time: float

Methods:
- start_recording(device_id: str = None) -> bool
  # Initiates recording session

- stop_recording() -> Dict
  # Stops recording and returns session summary

- collect_data_worker() -> None
  # Main loop for data collection

- process_raw_data() -> None
  # Extract and organize streamer data

- process_scores() -> None
  # Extract ML scores from streamer

- get_session_stats() -> Dict
  # Returns current session statistics
```

**Data Collection Logic**:
```python
# Pseudo-code for main collection loop
while is_recording:
    # Collect raw data
    raw_eeg = streamer.DATA["RAW"]["EEG"]
    storage.append_data("raw/eeg", raw_eeg, time.time())

    # Collect ML scores
    focus = streamer.SCORES.get("focus_score")
    storage.append_data("scores/focus", focus, time.time())

    # Check buffer and auto-save
    if buffer_full or time_elapsed > auto_save_interval:
        storage.flush_buffer()
```

### 5. Dashboard (`dashboard.py`)

**Purpose**: Marimo interactive dashboard

**UI Components**:

```python
# Device Connection Panel
@app.cell
def device_panel():
    - scan_button: mo.ui.button("Scan for Devices")
    - device_selector: mo.ui.radio(options=discovered_devices)
    - connect_button: mo.ui.button("Connect")
    - status_indicator: mo.md(f"Status: {connection_status}")

# Recording Controls
@app.cell
def recording_controls():
    - start_button: mo.ui.button("Start Recording", disabled=not_connected)
    - stop_button: mo.ui.button("Stop Recording", disabled=not_recording)
    - duration_display: mo.md(f"Duration: {format_time(elapsed)}")
    - size_display: mo.md(f"Data Size: {format_size(data_size)}")

# Event Annotation
@app.cell
def event_annotation():
    - event_input: mo.ui.text("Enter event description...")
    - category_select: mo.ui.dropdown(["subjective", "stimulus", "response", "other"])
    - add_button: mo.ui.button("Add Event")
    - event_list: mo.ui.table(recent_events)

# Visualization Tabs
@app.cell
def visualizations():
    - tabs: mo.ui.tabs({
        "Focus": focus_plot(),
        "POAS": poas_plot(),
        "Power Bands": power_bands_plot(),
        "Signal Quality": signal_quality_plot()
    })

# Display Buffer Management
@app.cell
def display_settings():
    - window_selector: mo.ui.dropdown(["5 min", "10 min", "30 min", "1 hour"])
    - auto_scroll: mo.ui.checkbox("Auto-scroll")
    - pause_display: mo.ui.checkbox("Pause display")
```

**Visualization Specifications**:

1. **Focus Score Plot**
   - Line chart, 0-100 scale
   - 2-second update interval
   - Rolling buffer: 300 points (10 minutes)

2. **POAS Plot**
   - Line chart, 0-1 scale
   - 30-second update interval
   - Rolling buffer: 60 points (30 minutes)

3. **Power Bands Plot**
   - Multi-line chart for α, β, γ, θ, δ
   - 2-second update interval
   - Y-axis: dB scale

4. **Signal Quality**
   - Bar chart for 4 channels
   - Color coding: green (good), red (poor)
   - 5-second update interval

### 6. Configuration (`config.py`)

```python
# Device Settings
DEFAULT_DEVICE_ID = None  # From .env if available
DEFAULT_PRODUCT_KEY = None  # From .env if available
CONNECTION_TIMEOUT = 30  # seconds
RECONNECT_ATTEMPTS = 3
AUTO_CONNECT_ON_START = True

# Storage Settings
DATA_DIR = Path("./data")
BUFFER_SIZE_MINUTES = 5
AUTO_SAVE_INTERVAL = 300  # seconds
FILE_ROTATION_HOURS = 24  # for very long sessions
COMPRESSION = "gzip"
COMPRESSION_LEVEL = 4

# Display Settings
DEFAULT_DISPLAY_WINDOW = 600  # seconds (10 minutes)
MAX_DISPLAY_POINTS = 1000  # downsample if exceeded
UPDATE_INTERVALS = {
    "focus": 2,
    "poas": 30,
    "power_bands": 2,
    "signal_quality": 5,
    "posture": 5
}

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FILE = "frenz_collector.log"
```

## Data Schemas

### Session Metadata (`session_info.json`)
```json
{
  "session_id": "20240928_143022",
  "start_time": 1696012345.678,
  "end_time": 1696023456.789,
  "duration_seconds": 11111.111,
  "device": {
    "id": "FRENZ-001",
    "product_key": "XXX-XXX",
    "firmware": "1.2.3"
  },
  "data_stats": {
    "raw_samples": 1234567,
    "score_samples": 5555,
    "events_logged": 23,
    "file_size_mb": 234.5
  },
  "files": {
    "data": "session_data.h5",
    "events": "events.json"
  }
}
```

## Error Handling

### Connection Errors
- Device not found → Show available devices
- Authentication failed → Check .env credentials
- Connection lost → Auto-reconnect with exponential backoff

### Storage Errors
- Disk full → Alert user, pause recording
- Write error → Retry with backup location
- Corrupt file → Create new file, log error

### Display Errors
- Memory limit → Reduce buffer size
- Plot error → Show error message, continue recording

## Testing Requirements

### Unit Tests
- Device connection/disconnection
- Buffer management
- File writing/reading
- Event logging
- Timestamp accuracy

### Integration Tests
- Full recording session
- Long duration recording (>1 hour)
- Connection recovery
- Data integrity verification

### Performance Tests
- Memory usage over time
- CPU usage during recording
- File size growth rate
- UI responsiveness

## Usage Examples

### Basic Usage
```python
# Start dashboard
marimo run dashboard.py

# In dashboard:
1. Click "Scan for Devices"
2. Select device
3. Click "Connect"
4. Click "Start Recording"
5. Add events as needed
6. Click "Stop Recording"
```

### Programmatic Usage
```python
from frenz_collector import FrenzCollector

collector = FrenzCollector()
collector.start_recording(device_id="FRENZ-001")

# Log event
collector.event_logger.log_event("Stimulus presented")

# Get stats
stats = collector.get_session_stats()
print(f"Recording for {stats['duration']} seconds")

# Stop and save
summary = collector.stop_recording()
print(f"Session saved to {summary['path']}")
```

## Dependencies

- Python 3.9+
- frenztoolkit>=0.2.8
- marimo>=0.15.5
- h5py>=3.0.0
- numpy>=1.21.0
- plotly>=6.3.0
- python-dotenv>=0.19.0
- nest-asyncio>=1.6.0

## Installation

```bash
cd frenz-testing
pip install -r requirements.txt
```

## File Structure

```
frenz-testing/
├── device_manager.py      # Device discovery and connection
├── data_storage.py        # HDF5 storage management
├── event_logger.py        # Event annotation system
├── frenz_collector.py     # Main collection orchestrator
├── config.py              # Configuration settings
├── dashboard.py           # Marimo interactive dashboard
├── tests/                 # Test suite
│   ├── test_device.py
│   ├── test_storage.py
│   └── test_collector.py
├── data/                  # Data storage directory
│   └── session_*/         # Individual session folders
├── .env                   # Environment variables
├── requirements.txt       # Dependencies
└── README.md             # Usage documentation
```

## Future Enhancements

1. Cloud backup integration
2. Multi-device simultaneous recording
3. Real-time data streaming to external services
4. Machine learning model training interface
5. Advanced signal processing options
6. Export to standard formats (EDF, BIDS)
7. Collaborative session annotations
8. Automated quality control checks