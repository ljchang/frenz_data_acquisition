# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FRENZ Data Acquisition System - A comprehensive data collection system for FRENZ brainband devices with real-time visualization, continuous recording, and event annotation capabilities. Built with Python using Marimo for interactive dashboards, HDF5 for efficient storage, and the frenztoolkit library for device communication.

## Setup and Development Commands

### Environment Setup
```bash
# Install UV package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Configure device credentials (required before running)
cp .env.example .env
# Edit .env with FRENZ_ID and FRENZ_KEY
```

### Running the Application
```bash
# Start the interactive dashboard (main application)
marimo run dashboard.py

# Run programmatic data collection
python frenz_collector.py --duration 300

# Quick system verification
python scripts/quick_start.py
```

### Testing and Code Quality
```bash
# Run tests
pytest tests/test_frenz_collector.py -v

# Format code
uv run black .

# Lint code
uv run ruff check .
```

## System Architecture

### Core Components and Data Flow

The system follows a modular orchestrator pattern:

1. **FrenzCollector (frenz_collector.py)** - Main orchestrator
   - Integrates all components and manages session lifecycle
   - Runs background worker thread (`collect_data_worker`) for continuous data collection
   - Extracts data from streamer via `process_raw_data()` and `process_scores()`
   - Thread-safe with RLock for concurrent access to stats and state

2. **DeviceManager (device_manager.py)** - Device communication layer
   - Wraps frenztoolkit's Scanner and Streamer classes
   - Provides connection management with auto-reconnect capability
   - Uses environment variables for credentials (FRENZ_ID, FRENZ_KEY)
   - Connection timeout and status tracking with DeviceStatus enum

3. **DataStorage (data_storage.py)** - HDF5 persistence layer
   - Single growing file strategy (session_data.h5 per session)
   - In-memory buffering with configurable size (default: 5 minutes)
   - Background auto-save thread writes buffer to disk periodically (default: 300s)
   - Thread-safe operations with RLock protecting buffers
   - Organized HDF5 structure: /raw/, /filtered/, /scores/, /power_bands/, /timestamps

4. **EventLogger (event_logger.py)** - Event annotation system
   - Thread-safe event logging with precise timestamps
   - Supports 4 categories: subjective, stimulus, response, other
   - Auto-saves to events.json with atomic file writes

5. **Config (config.py)** - Centralized configuration
   - Loads settings from environment variables via .env file
   - Provides Config singleton with device, storage, display, and logging sections
   - Validates all configuration values on initialization

### Data Structure

**Streamer Data Access Pattern:**
- Raw data accessed via: `streamer.DATA.get("RAW", {}).get("EEG")`
- Filtered data via: `streamer.DATA.get("FILTERED", {}).get("EEG")`
- Scores via: `streamer.SCORES.get("focus_score")`
- Data is multi-dimensional numpy arrays; FrenzCollector extracts latest sample with `[-1, :]`

**HDF5 Storage Schema:**
- `/raw/eeg` (N, 4) - 4 EEG channels
- `/raw/eog` (N, 4) - 4 EOG channels
- `/raw/emg` (N, 4) - 4 EMG channels
- `/raw/imu` (N, 3) - IMU x,y,z
- `/raw/ppg` (N, 3) - PPG G,R,IR
- `/filtered/eeg`, `/filtered/eog`, `/filtered/emg` - Processed signals
- `/scores/focus`, `/scores/poas`, `/scores/posture`, `/scores/sleep_stage`
- `/scores/signal_quality` (N, 4) - Per-channel quality
- `/power_bands/alpha`, `/beta`, `/gamma`, `/theta`, `/delta` (N, 5) - LF, OTEL, RF, OTER, AVG
- `/timestamps` (N,) - Unix timestamps for synchronization

**Session Directory Structure:**
```
data/session_YYYYMMDD_HHMMSS/
├── session_data.h5      # All sensor and ML data
├── events.json          # Annotated events with timestamps
└── session_info.json    # Session metadata and statistics
```

## Critical Implementation Details

### Threading Architecture
- **FrenzCollector**: Main data collection worker thread runs `collect_data_worker()` continuously
- **DataStorage**: Auto-save worker thread flushes buffer to disk every 300s
- **DeviceManager**: Reconnect worker thread for automatic reconnection with exponential backoff
- All use daemon threads with proper stop flags and join timeouts

### Credentials and Security
- Device credentials MUST be stored in .env (gitignored)
- Never commit FRENZ_ID or FRENZ_KEY to version control
- .env.example shows required format without actual credentials

### Memory Management
- Dashboard uses rolling buffers to prevent unbounded memory growth
- DataStorage buffer flushes when duration exceeds BUFFER_SIZE_MINUTES (default: 5 min)
- HDF5 chunking optimized for time-series data (chunks: 10000 samples)

### Error Handling Pattern
- All core components use try-except with logging
- Connection failures trigger cleanup via `_cleanup_failed_start()`
- Device disconnection stops all threads and closes files properly
- Destructors (`__del__`) ensure cleanup on object destruction

## Common Development Patterns

### Adding New Sensor Data Type
1. Add dataset config to `DataStorage._get_dataset_configs()` with shape, dtype, chunks
2. Extract data in `FrenzCollector.process_raw_data()` or `process_scores()`
3. Update dashboard visualization in `dashboard.py`

### Modifying Data Collection Frequency
- Adjust `time.sleep(0.01)` in `FrenzCollector.collect_data_worker()` (currently 10ms)
- Affects CPU usage vs. data temporal resolution tradeoff

### Loading Recorded Data for Analysis
```python
import h5py
import json

with h5py.File('data/session_*/session_data.h5', 'r') as f:
    eeg_data = f['/raw/eeg'][:]
    timestamps = f['/timestamps'][:]
    focus_scores = f['/scores/focus'][:]

with open('data/session_*/events.json', 'r') as f:
    events = json.load(f)['events']
```

## Dependencies

**Core:**
- frenztoolkit>=0.2.9 - FRENZ device communication
- marimo>=0.15.5 - Interactive dashboard
- h5py>=3.0.0 - HDF5 storage
- numpy>=1.21.0 - Array operations
- plotly>=6.3.0 - Visualizations
- python-dotenv>=0.19.0 - Environment configuration
- nest-asyncio>=1.6.0 - Async compatibility

**Development:**
- pytest>=8.4.2 - Testing
- ruff>=0.13.0 - Linting
- black>=24.0.0 - Formatting