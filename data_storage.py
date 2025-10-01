"""
Data Storage module for FRENZ data collection system.

This module manages HDF5 file storage with buffering and auto-save functionality.
It provides efficient data storage for continuous recording sessions with proper
HDF5 dataset structure, background saving, and session metadata management.
"""

import os
import time
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import numpy as np

try:
    import h5py
except ImportError:
    raise ImportError(
        "h5py is required for data storage. Install with: pip install h5py>=3.0.0"
    )


class DataStorage:
    """
    Manages HDF5 file storage with buffering and auto-save for FRENZ data collection.

    This class provides efficient data storage for continuous recording sessions with:
    - HDF5 file management with single growing file strategy
    - Efficient buffering system with configurable buffer size
    - Automatic periodic saves with background threading
    - Proper HDF5 dataset structure with optimal chunking
    - Thread-safe operations for concurrent access
    - Session metadata management and summary generation
    - Comprehensive error handling and logging
    """

    def __init__(self,
                 data_dir: Union[str, Path] = "./data",
                 buffer_size_minutes: int = 5,
                 auto_save_interval: int = 300,
                 compression: str = "gzip",
                 compression_level: int = 4):
        """
        Initialize the DataStorage instance.

        Args:
            data_dir: Directory for storing data files
            buffer_size_minutes: Size of in-memory buffer in minutes (default: 5)
            auto_save_interval: Automatic save interval in seconds (default: 300)
            compression: HDF5 compression method (default: "gzip")
            compression_level: Compression level 0-9 (default: 4)
        """
        self.data_dir = Path(data_dir)
        self.buffer_size_minutes = buffer_size_minutes
        self.auto_save_interval = auto_save_interval
        self.compression = compression
        self.compression_level = compression_level

        # Set up logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Initialize state
        self.session_path: Optional[Path] = None
        self.h5_file: Optional[h5py.File] = None
        self.session_id: Optional[str] = None
        self.session_start_time: Optional[float] = None
        self.is_recording = False

        # Threading and buffer management
        self._buffer_lock = threading.RLock()
        self._auto_save_thread: Optional[threading.Thread] = None
        self._stop_auto_save = False
        self._data_buffers: Dict[str, List] = {}
        self._timestamp_buffers: Dict[str, List] = {}
        self._last_save_time = 0

        # Dataset configuration
        self._dataset_configs = self._get_dataset_configs()

        # Create data directory
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("DataStorage initialized")

    def _get_dataset_configs(self) -> Dict[str, Dict]:
        """Get HDF5 dataset configurations with shapes, dtypes, and chunk sizes."""
        return {
            # Raw data - actual shapes from FRENZ device
            "raw/eeg": {"shape": (0, 7), "dtype": np.float32, "chunks": (10000, 7)},  # 7 channels
            "raw/imu": {"shape": (0, 3), "dtype": np.float32, "chunks": (10000, 3)},  # x,y,z (skip timestamp)
            "raw/ppg": {"shape": (0, 3), "dtype": np.float32, "chunks": (10000, 3)},  # G,R,IR (skip timestamp)

            # Filtered data (7 channels like raw)
            "filtered/eeg": {"shape": (0, 7), "dtype": np.float32, "chunks": (10000, 7)},

            # Scores - single values
            "scores/poas": {"shape": (0,), "dtype": np.float32, "chunks": (10000,)},
            "scores/focus": {"shape": (0,), "dtype": np.float32, "chunks": (10000,)},
            "scores/posture": {"shape": (0,), "dtype": np.int8, "chunks": (10000,)},
            "scores/sleep_stage": {"shape": (0,), "dtype": np.int8, "chunks": (10000,)},
            "scores/signal_quality": {"shape": (0, 4), "dtype": np.float32, "chunks": (10000, 4)},
            "scores/hr": {"shape": (0,), "dtype": np.int16, "chunks": (10000,)},  # Heart rate (BPM)
            "scores/spo2": {"shape": (0,), "dtype": np.int16, "chunks": (10000,)},  # Blood oxygen (%)

            # Power bands - 5 channels (LF, OTEL, RF, OTER, AVG)
            "power_bands/alpha": {"shape": (0, 5), "dtype": np.float32, "chunks": (10000, 5)},
            "power_bands/beta": {"shape": (0, 5), "dtype": np.float32, "chunks": (10000, 5)},
            "power_bands/gamma": {"shape": (0, 5), "dtype": np.float32, "chunks": (10000, 5)},
            "power_bands/theta": {"shape": (0, 5), "dtype": np.float32, "chunks": (10000, 5)},
            "power_bands/delta": {"shape": (0, 5), "dtype": np.float32, "chunks": (10000, 5)},

            # Timestamps
            "timestamps": {"shape": (0,), "dtype": np.float64, "chunks": (10000,)}
        }

    def initialize_session(self, session_id: Optional[str] = None) -> bool:
        """
        Create session directory and HDF5 file.

        Args:
            session_id: Unique session identifier. If None, generates timestamp-based ID

        Returns:
            bool: True if session initialized successfully, False otherwise
        """
        try:
            # Generate session ID if not provided
            if session_id is None:
                session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            self.session_id = session_id
            self.session_start_time = time.time()

            # Create session directory
            self.session_path = self.data_dir / session_id
            self.session_path.mkdir(parents=True, exist_ok=True)

            # Initialize HDF5 file
            h5_path = self.session_path / "session_data.h5"
            self.h5_file = h5py.File(h5_path, "w")

            # Create datasets
            success = self.create_datasets()
            if not success:
                self.logger.error("Failed to create datasets")
                return False

            # Initialize buffers
            self._initialize_buffers()

            # Start auto-save worker
            self._start_auto_save_worker()

            self.is_recording = True
            self.logger.info(f"Session initialized: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize session: {e}")
            return False

    def create_datasets(self) -> bool:
        """
        Initialize all HDF5 datasets with appropriate chunking and compression.

        Returns:
            bool: True if datasets created successfully, False otherwise
        """
        try:
            if self.h5_file is None:
                self.logger.error("HDF5 file not initialized")
                return False

            for dataset_name, config in self._dataset_configs.items():
                try:
                    # Skip if dataset already exists
                    if dataset_name in self.h5_file:
                        self.logger.debug(f"Dataset {dataset_name} already exists, skipping")
                        continue

                    # Create group if needed (only for datasets with groups)
                    if '/' in dataset_name:
                        group_name = dataset_name.split('/')[0]
                        if group_name not in self.h5_file:
                            self.h5_file.create_group(group_name)
                            self.logger.debug(f"Created group: {group_name}")

                    # Create dataset with proper configuration
                    self.h5_file.create_dataset(
                        dataset_name,
                        shape=config["shape"],
                        maxshape=(None,) + config["shape"][1:] if len(config["shape"]) > 1 else (None,),
                        dtype=config["dtype"],
                        chunks=config["chunks"],
                        compression=self.compression,
                        compression_opts=self.compression_level,
                        shuffle=True,  # Improves compression
                        fletcher32=True  # Error detection
                    )
                    self.logger.debug(f"Created dataset: {dataset_name}")

                except Exception as e:
                    self.logger.error(f"Failed to create dataset {dataset_name}: {e}")
                    raise

            self.logger.info("HDF5 datasets created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create datasets: {e}")
            return False

    def _initialize_buffers(self) -> None:
        """Initialize data buffers for all datasets."""
        with self._buffer_lock:
            self._data_buffers.clear()
            self._timestamp_buffers.clear()

            for dataset_name in self._dataset_configs.keys():
                self._data_buffers[dataset_name] = []
                if dataset_name != "timestamps":
                    self._timestamp_buffers[dataset_name] = []

    def append_data(self, data_type: str, data: Union[np.ndarray, float, int],
                   timestamp: Optional[float] = None) -> bool:
        """
        Add data to buffer with timestamp.

        Args:
            data_type: Type of data (e.g., "raw/eeg", "scores/focus")
            data: Data array or single value
            timestamp: Unix timestamp. If None, uses current time

        Returns:
            bool: True if data appended successfully, False otherwise
        """
        try:
            if not self.is_recording:
                self.logger.warning("Not recording, data not saved")
                return False

            if timestamp is None:
                timestamp = time.time()

            # Validate data type
            if data_type not in self._dataset_configs:
                self.logger.error(f"Unknown data type: {data_type}")
                return False

            # Convert data to numpy array if needed
            if not isinstance(data, np.ndarray):
                data = np.array(data, dtype=self._dataset_configs[data_type]["dtype"])
            else:
                data = data.astype(self._dataset_configs[data_type]["dtype"])

            # Validate data shape
            expected_shape = self._dataset_configs[data_type]["shape"][1:]
            if len(expected_shape) > 0 and data.shape != expected_shape:
                self.logger.error(f"Data shape mismatch for {data_type}: {data.shape} != {expected_shape}")
                return False

            # Add to buffer
            with self._buffer_lock:
                self._data_buffers[data_type].append(data)
                if data_type != "timestamps":
                    self._timestamp_buffers[data_type].append(timestamp)

                # Also add timestamp to timestamp buffer
                if data_type != "timestamps":
                    self._data_buffers["timestamps"].append(timestamp)

            # Check if buffer needs flushing
            self._check_buffer_size()

            return True

        except Exception as e:
            self.logger.error(f"Failed to append data: {e}")
            return False

    def _check_buffer_size(self) -> None:
        """Check if buffer size exceeds limit and flush if needed."""
        try:
            with self._buffer_lock:
                # Calculate buffer duration based on timestamps
                if len(self._data_buffers.get("timestamps", [])) < 2:
                    return

                timestamps = self._data_buffers["timestamps"]
                duration_minutes = (timestamps[-1] - timestamps[0]) / 60.0

                if duration_minutes >= self.buffer_size_minutes:
                    self.logger.info(f"Buffer full ({duration_minutes:.1f} min), flushing...")
                    self.flush_buffer()

        except Exception as e:
            self.logger.error(f"Error checking buffer size: {e}")

    def flush_buffer(self) -> bool:
        """
        Write buffer to disk efficiently.

        Returns:
            bool: True if buffer flushed successfully, False otherwise
        """
        try:
            if self.h5_file is None:
                self.logger.error("HDF5 file not initialized")
                return False

            with self._buffer_lock:
                # Check if there's data to write
                total_samples = 0
                for dataset_name, buffer in self._data_buffers.items():
                    if len(buffer) > 0:
                        total_samples += len(buffer)

                if total_samples == 0:
                    return True  # Nothing to flush

                # Write data to HDF5 file
                for dataset_name, buffer in self._data_buffers.items():
                    if len(buffer) == 0:
                        continue

                    dataset = self.h5_file[dataset_name]
                    old_size = dataset.shape[0]
                    new_size = old_size + len(buffer)

                    # Resize dataset
                    dataset.resize((new_size,) + dataset.shape[1:])

                    # Write data
                    if len(dataset.shape) == 1:
                        dataset[old_size:new_size] = buffer
                    else:
                        dataset[old_size:new_size, :] = np.array(buffer)

                # Clear buffers
                self._initialize_buffers()

                # Force write to disk
                self.h5_file.flush()
                self._last_save_time = time.time()

                self.logger.info(f"Buffer flushed: {total_samples} samples written")
                return True

        except Exception as e:
            self.logger.error(f"Failed to flush buffer: {e}")
            return False

    def _start_auto_save_worker(self) -> None:
        """Start background thread for periodic saves."""
        if self._auto_save_thread is not None and self._auto_save_thread.is_alive():
            self.logger.warning("Auto-save thread already running")
            return

        self._stop_auto_save = False
        self._auto_save_thread = threading.Thread(
            target=self.auto_save_worker,
            name="DataStorage-AutoSave",
            daemon=True
        )
        self._auto_save_thread.start()
        self.logger.info("Auto-save worker started")

    def auto_save_worker(self) -> None:
        """Background thread for periodic saves."""
        self.logger.info("Auto-save worker thread started")

        while not self._stop_auto_save and self.is_recording:
            try:
                time.sleep(1)  # Check every second

                current_time = time.time()
                time_since_save = current_time - self._last_save_time

                if time_since_save >= self.auto_save_interval:
                    self.logger.info("Auto-save triggered")
                    self.flush_buffer()

            except Exception as e:
                self.logger.error(f"Error in auto-save worker: {e}")

        self.logger.info("Auto-save worker thread stopped")

    def stop_recording(self) -> bool:
        """
        Stop recording and flush final data.

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        try:
            self.is_recording = False

            # Stop auto-save worker
            self._stop_auto_save = True
            if self._auto_save_thread and self._auto_save_thread.is_alive():
                self._auto_save_thread.join(timeout=5)

            # Final buffer flush
            success = self.flush_buffer()

            self.logger.info("Recording stopped")
            return success

        except Exception as e:
            self.logger.error(f"Error stopping recording: {e}")
            return False

    def finalize_session(self) -> Dict[str, Any]:
        """
        Close file and generate session summary.

        Returns:
            Dict containing session summary and statistics
        """
        try:
            # Stop recording if still active
            if self.is_recording:
                self.stop_recording()

            # Calculate session statistics
            session_end_time = time.time()
            duration = session_end_time - (self.session_start_time or session_end_time)

            # Collect data statistics
            data_stats = {}
            total_samples = 0

            if self.h5_file:
                for dataset_name in self._dataset_configs.keys():
                    if dataset_name in self.h5_file:
                        dataset = self.h5_file[dataset_name]
                        samples = dataset.shape[0]
                        data_stats[dataset_name] = samples
                        if dataset_name != "timestamps":
                            total_samples += samples

                # Get file size
                file_size_mb = os.path.getsize(self.h5_file.filename) / (1024 * 1024)

                # Close HDF5 file
                self.h5_file.close()
                self.h5_file = None
            else:
                file_size_mb = 0

            # Create session metadata
            session_metadata = {
                "session_id": self.session_id,
                "start_time": self.session_start_time,
                "end_time": session_end_time,
                "duration_seconds": duration,
                "data_stats": {
                    "total_samples": total_samples,
                    "file_size_mb": file_size_mb,
                    "datasets": data_stats
                },
                "files": {
                    "data": "session_data.h5"
                },
                "buffer_config": {
                    "buffer_size_minutes": self.buffer_size_minutes,
                    "auto_save_interval": self.auto_save_interval,
                    "compression": self.compression,
                    "compression_level": self.compression_level
                }
            }

            # Save metadata to JSON file
            if self.session_path:
                metadata_path = self.session_path / "session_info.json"
                with open(metadata_path, 'w') as f:
                    json.dump(session_metadata, f, indent=2)

                self.logger.info(f"Session finalized: {self.session_id}")
                self.logger.info(f"Duration: {duration:.1f}s, Samples: {total_samples}, Size: {file_size_mb:.1f}MB")

            return session_metadata

        except Exception as e:
            self.logger.error(f"Error finalizing session: {e}")
            return {"error": str(e)}

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get current session statistics.

        Returns:
            Dict containing current session statistics
        """
        try:
            if not self.is_recording or self.h5_file is None:
                return {"status": "not_recording"}

            current_time = time.time()
            duration = current_time - (self.session_start_time or current_time)

            # Count buffered samples
            buffered_samples = 0
            with self._buffer_lock:
                for dataset_name, buffer in self._data_buffers.items():
                    if dataset_name != "timestamps":
                        buffered_samples += len(buffer)

            # Count saved samples
            saved_samples = 0
            for dataset_name in self._dataset_configs.keys():
                if dataset_name != "timestamps" and dataset_name in self.h5_file:
                    saved_samples += self.h5_file[dataset_name].shape[0]

            return {
                "status": "recording",
                "session_id": self.session_id,
                "duration_seconds": duration,
                "saved_samples": saved_samples,
                "buffered_samples": buffered_samples,
                "total_samples": saved_samples + buffered_samples,
                "last_save_time": self._last_save_time,
                "time_since_save": current_time - self._last_save_time
            }

        except Exception as e:
            self.logger.error(f"Error getting session stats: {e}")
            return {"error": str(e)}

    def __del__(self):
        """Cleanup on object destruction."""
        try:
            if self.is_recording:
                self.stop_recording()

            if self.h5_file:
                self.h5_file.close()

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error in destructor: {e}")


# Example usage
if __name__ == "__main__":
    """
    Example usage of the DataStorage class.
    """
    import numpy as np
    import time

    # Initialize storage
    storage = DataStorage(
        data_dir="./data",
        buffer_size_minutes=5,
        auto_save_interval=300
    )

    try:
        # Start a session
        storage.initialize_session("example_session")

        # Add some sample data
        for i in range(100):
            # Simulate EEG data (4 channels)
            eeg_data = np.random.randn(4).astype(np.float32)
            storage.append_data("raw/eeg", eeg_data)

            # Simulate focus score
            focus_score = np.random.rand()
            storage.append_data("scores/focus", focus_score)

            # Simulate power band data
            alpha_data = np.random.randn(5).astype(np.float32)
            storage.append_data("power_bands/alpha", alpha_data)

            time.sleep(0.01)  # 100 Hz simulation

        # Get session statistics
        stats = storage.get_session_stats()
        print(f"Session stats: {stats}")

        # Finalize the session
        summary = storage.finalize_session()
        print(f"Session completed: {summary['session_id']}")
        print(f"Duration: {summary['duration_seconds']:.1f}s")
        print(f"Total samples: {summary['data_stats']['total_samples']}")
        print(f"File size: {summary['data_stats']['file_size_mb']:.2f} MB")

    except Exception as e:
        print(f"Error: {e}")
        if storage.is_recording:
            storage.stop_recording()