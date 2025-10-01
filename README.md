# FRENZ Data Acquisition System

A comprehensive data collection system for FRENZ brainband devices with real-time visualization, continuous recording, and event annotation capabilities.

## Overview

This system provides a complete solution for collecting, visualizing, and storing data from FRENZ brainband devices. It features a Marimo-based interactive dashboard for real-time monitoring and control, with efficient HDF5 storage for long-duration recording sessions.

### Key Features

- Real-time streaming of EEG, IMU, PPG, HR, and SpO2 signals
- Live machine learning scores: Focus, POAS, Posture, Sleep Stage
- Frequency band analysis: Alpha, Beta, Gamma, Theta, Delta power bands
- Heart rate and blood oxygen saturation monitoring
- Continuous recording with automatic periodic saves
- Event annotation with precise timestamps
- Memory-safe visualization with rolling buffers
- Automatic device discovery and connection management
- Session-based data organization with metadata
- Device calibration and configuration tracking

📊 **[Complete Data Format Documentation](docs/DATA_FORMAT.md)**

## System Architecture

The system consists of several modular components:

- **Device Manager**: Handles FRENZ device discovery and connection
- **Data Storage**: Manages HDF5 file I/O with efficient buffering
- **Event Logger**: Records timestamped annotations during sessions
- **FRENZ Collector**: Main orchestrator for data collection
- **Dashboard**: Marimo-based interactive user interface
- **Config**: Centralized configuration management

## Installation

### Prerequisites

- Python 3.9 or higher
- FRENZ brainband device with valid credentials
- macOS, Linux, or Windows operating system

### Quick Setup with UV

1. Clone the repository:
```bash
git clone https://github.com/yourusername/frenz_data_acquisition.git
cd frenz_data_acquisition
```

2. Run the setup script:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

3. Configure your device credentials:
```bash
cp .env.example .env
# Edit .env with your FRENZ_ID and FRENZ_KEY
```

### Manual Installation

1. Install UV package manager:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Create virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

3. Create required directories:
```bash
mkdir -p data logs
```

## Usage

### Starting the Dashboard

Launch the Marimo dashboard:
```bash
marimo run dashboard.py
```

The dashboard will open in your browser at `http://localhost:2718`

### Dashboard Workflow

1. **Device Connection**
   - Click "Scan for Devices" to discover available FRENZ devices
   - Select your device from the list
   - Click "Connect" to establish connection

2. **Recording Session**
   - Click "Start Recording" to begin data collection
   - Monitor real-time visualizations across different tabs
   - Add event annotations as needed
   - Click "Stop Recording" to save and finalize the session

3. **Data Visualization**
   - Focus Score: Updated every 2 seconds
   - POAS: Updated every 30 seconds
   - Power Bands: Real-time frequency analysis
   - Signal Quality: Channel quality indicators

### Programmatic Usage

```python
from frenz_collector import FrenzCollector

# Initialize collector
collector = FrenzCollector()

# Start recording (auto-connects using .env credentials)
collector.start_recording()

# Log an event
collector.log_event("Task started", category="stimulus")

# Get session statistics
stats = collector.get_session_stats()
print(f"Duration: {stats['duration_seconds']} seconds")

# Stop and save
summary = collector.stop_recording()
print(f"Data saved to: {summary['session_path']}")
```

## Data Storage

### Session Organization

Each recording session creates a timestamped directory:
```
data/
└── session_20240928_143022/
    ├── session_data.h5      # All sensor and ML data (HDF5)
    ├── events.json          # Event annotations
    ├── session_info.json    # Session statistics
    └── device_config.json   # Device configuration & calibration
```

### HDF5 Data Structure

The main data file (`session_data.h5`) contains:
- `/raw/` - Raw sensor data (EEG, IMU, PPG)
- `/scores/` - ML model outputs (focus, POAS, HR, SpO2, etc.)
- `/power_bands/` - Frequency band analysis (alpha, beta, gamma, theta, delta)
- `/timestamps` - Unix timestamps for synchronization

**See [DATA_FORMAT.md](docs/DATA_FORMAT.md) for complete reference including:**
- All data types and their formats
- Sampling rates and data shapes
- Score metric definitions
- Device metadata structure
- Data access examples

### Quick Data Access

```python
import h5py
import json

# Load sensor data
with h5py.File('data/session_20240928_143022/session_data.h5', 'r') as f:
    eeg_data = f['/raw/eeg'][:]           # Shape: (N, 7)
    hr_data = f['/scores/hr'][:]          # Heart rate
    spo2_data = f['/scores/spo2'][:]      # Blood oxygen
    focus_scores = f['/scores/focus'][:]  # Focus scores
    timestamps = f['/timestamps'][:]

# Load device config
with open('data/session_20240928_143022/device_config.json') as f:
    config = json.load(f)
    print(f"Device: {config['device_id']}")
    print(f"IMU Calibration: {config['imu_calibration']}")
```

## Configuration

Edit `config.py` to customize system behavior:

```python
# Device settings
CONNECTION_TIMEOUT = 30  # seconds
RECONNECT_ATTEMPTS = 3

# Storage settings
BUFFER_SIZE_MINUTES = 5
AUTO_SAVE_INTERVAL = 300  # seconds

# Display settings
DEFAULT_DISPLAY_WINDOW = 600  # seconds
UPDATE_INTERVALS = {
    "focus": 2,
    "poas": 30,
    "power_bands": 2
}
```

## Project Structure

```
frenz_data_acquisition/
├── dashboard.py           # Marimo interactive dashboard
├── frenz_collector.py     # Main data collection orchestrator
├── device_manager.py      # Device connection management
├── data_storage.py        # HDF5 storage handler
├── event_logger.py        # Event annotation system
├── config.py             # Configuration settings
├── docs/                 # Documentation
│   ├── FRENZ_SPEC.md    # Technical specification
│   └── SYSTEM_OVERVIEW.md # System overview
├── scripts/              # Utility scripts
│   ├── quick_start.py   # System verification
│   └── setup.sh         # Installation script
├── tests/                # Test suite
│   └── test_frenz_collector.py
├── data/                 # Data storage (gitignored)
├── logs/                 # Log files (gitignored)
├── pyproject.toml        # UV package configuration
├── uv.toml              # UV workspace settings
├── .marimo.toml         # Marimo app configuration
├── .env.example         # Environment template
└── .gitignore           # Git ignore rules
```

## Development

### Running Tests

```bash
pytest test_frenz_collector.py -v
```

### Code Quality

```bash
# Format code
uv run black .

# Lint code
uv run ruff check .
```

### Adding New Visualizations

1. Add data buffer in `dashboard.py` initialization
2. Create visualization function
3. Add to dashboard tabs
4. Set appropriate refresh interval

## Troubleshooting

### Connection Issues
- Ensure FRENZ device is powered on and in range
- Verify credentials in `.env` file
- Check Bluetooth is enabled on your system

### Performance Optimization
- Reduce display window for better performance
- Disable auto-scroll during active monitoring
- Check available disk space for data storage

### Common Issues

| Issue | Solution |
|-------|----------|
| Device not found | Check device is on and in pairing mode |
| Connection timeout | Increase `CONNECTION_TIMEOUT` in config |
| Memory usage high | Reduce `DEFAULT_DISPLAY_WINDOW` |
| Plots not updating | Check data is being received from device |

## API Reference

### FrenzCollector

Main class for data collection orchestration.

```python
collector = FrenzCollector()
collector.start_recording(device_id=None)  # Uses .env if device_id not provided
collector.log_event(description, category)
collector.get_session_stats()
collector.stop_recording()
```

### DeviceManager

Handles device discovery and connection.

```python
manager = DeviceManager()
devices = manager.scan_devices()
manager.connect(device_id, product_key)
manager.disconnect()
manager.get_status()
```

### DataStorage

Manages HDF5 file operations.

```python
storage = DataStorage(session_id)
storage.initialize_session()
storage.append_data(data_type, data, timestamp)
storage.flush_buffer()
storage.finalize_session()
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the FRENZ_SPEC.md for technical details

## Acknowledgments

Built using:
- [Marimo](https://marimo.io/) for interactive dashboards
- [UV](https://github.com/astral-sh/uv) for Python package management
- [HDF5](https://www.hdfgroup.org/) for efficient data storage
- [Plotly](https://plotly.com/) for interactive visualizations