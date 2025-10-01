"""
FRENZ Collector module for FRENZ data collection system.

This module serves as the main orchestrator for data collection from FRENZ brainband devices.
It integrates DeviceManager, DataStorage, and EventLogger to provide a unified interface
for recording sessions with real-time data collection, processing, and storage.
"""

import os
import time
import json
import logging
import threading
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from datetime import datetime
import numpy as np

from device_manager import DeviceManager, DeviceStatus
from data_storage import DataStorage
from event_logger import EventLogger
from config import config


class FrenzCollectorError(Exception):
    """Raised when there's an error in the FrenzCollector."""
    pass


class FrenzCollector:
    """
    Main orchestrator for FRENZ data collection.

    This class integrates all system components to provide:
    - Unified session management with automatic device connection
    - Real-time data collection from streamer in worker threads
    - Processing and storage of raw sensor data and ML scores
    - Event logging with precise timestamps
    - Session statistics and monitoring
    - Thread-safe operations for concurrent data access
    - Comprehensive error handling and recovery
    """

    def __init__(self,
                 device_id: Optional[str] = None,
                 product_key: Optional[str] = None,
                 data_dir: Optional[Union[str, Path]] = None,
                 buffer_size_minutes: int = 5,
                 auto_save_interval: int = 300):
        """
        Initialize the FrenzCollector.

        Args:
            device_id: Device identifier (uses config/env if None)
            product_key: Product key for authentication (uses config/env if None)
            data_dir: Directory for data storage (uses config if None)
            buffer_size_minutes: Size of data buffer in minutes
            auto_save_interval: Automatic save interval in seconds
        """
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Store configuration
        self.device_id = device_id or config.device.get("default_device_id")
        self.product_key = product_key or config.device.get("default_product_key")
        self.data_dir = Path(data_dir) if data_dir else config.storage["data_dir"]
        self.buffer_size_minutes = buffer_size_minutes
        self.auto_save_interval = auto_save_interval

        # Initialize core components
        self.device_manager = DeviceManager(
            connection_timeout=config.device["connection_timeout"],
            reconnect_attempts=config.device["reconnect_attempts"],
            auto_connect_on_start=config.device["auto_connect_on_start"]
        )

        self.storage: Optional[DataStorage] = None
        self.event_logger: Optional[EventLogger] = None
        self.streamer = None

        # Recording state
        self.is_recording = False
        self.session_id: Optional[str] = None
        self.session_start_time: Optional[float] = None

        # Worker thread management
        self._data_worker_thread: Optional[threading.Thread] = None
        self._stop_data_collection = False
        self._data_collection_lock = threading.RLock()

        # Data collection statistics
        self._stats = {
            "samples_collected": 0,
            "errors_count": 0,
            "last_data_time": None,
            "data_types_seen": set(),
            "collection_rate": 0.0
        }

        self.logger.info("FrenzCollector initialized")

    def start_recording(self, device_id: Optional[str] = None, session_id: Optional[str] = None) -> bool:
        """
        Initialize and start a recording session.

        Args:
            device_id: Specific device to connect to (uses default if None)
            session_id: Custom session identifier (generates if None)

        Returns:
            bool: True if recording started successfully, False otherwise
        """
        try:
            if self.is_recording:
                self.logger.warning("Recording session already active")
                return False

            # Use provided device_id or fall back to instance/config defaults
            target_device_id = device_id or self.device_id
            if not target_device_id:
                self.logger.error("No device ID specified")
                return False

            self.logger.info(f"Starting recording session with device: {target_device_id}")

            # Generate session ID if not provided
            if session_id is None:
                session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            self.session_id = session_id
            self.session_start_time = time.time()

            # Connect to device (or use existing connection)
            if self.device_manager.is_connected():
                self.logger.info("Using existing device connection")
                self.streamer = self.device_manager.get_streamer()
            else:
                self.logger.info("Connecting to device")
                self.streamer = self.device_manager.connect(target_device_id, self.product_key)

            if not self.streamer:
                self.logger.error("Failed to connect to device")
                return False

            # Initialize storage
            self.storage = DataStorage(
                data_dir=self.data_dir,
                buffer_size_minutes=self.buffer_size_minutes,
                auto_save_interval=self.auto_save_interval
            )

            if not self.storage.initialize_session(self.session_id):
                self.logger.error("Failed to initialize data storage")
                self.device_manager.disconnect()
                return False

            # Initialize event logger
            self.event_logger = EventLogger(
                session_id=self.session_id,
                data_dir=self.data_dir,
                auto_save=True
            )

            # Save device configuration metadata
            self._save_device_metadata()

            # Reset statistics
            self._reset_stats()

            # Set recording flag BEFORE starting worker to avoid race condition
            self.is_recording = True

            # Start data collection worker
            self._start_data_worker()

            self.logger.info(f"Recording session started: {self.session_id}")

            # Log session start event
            self.event_logger.log_event("Recording session started", "other")

            return True

        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            # Cleanup on failure
            self._cleanup_failed_start()
            return False

    def stop_recording(self) -> Dict[str, Any]:
        """
        Stop recording and save all data.

        Returns:
            Dict containing session summary and statistics
        """
        try:
            if not self.is_recording:
                self.logger.warning("No active recording session")
                return {"error": "No active recording session"}

            self.logger.info("Stopping recording session...")

            # Log session end event
            if self.event_logger:
                try:
                    self.event_logger.log_event("Recording session ended", "other")
                except Exception as e:
                    self.logger.warning(f"Failed to log end event: {e}")

            # Stop data collection worker
            try:
                self._stop_data_worker()
            except Exception as e:
                self.logger.error(f"Error stopping data worker: {e}")

            # Finalize storage
            session_summary = {}
            if self.storage:
                try:
                    session_summary = self.storage.finalize_session()
                except Exception as e:
                    self.logger.error(f"Error finalizing storage: {e}")
                    session_summary = {"error": str(e)}

            # Don't disconnect device - keep connection alive for next recording
            # Device will be disconnected when dashboard disconnects explicitly

            # Calculate final statistics
            session_end_time = time.time()
            duration = session_end_time - (self.session_start_time or session_end_time)

            # Create comprehensive session summary
            final_summary = {
                "session_id": self.session_id,
                "start_time": self.session_start_time,
                "end_time": session_end_time,
                "duration_seconds": duration,
                "samples_collected": self._stats["samples_collected"],
                "errors_count": self._stats["errors_count"],
                "data_types_collected": list(self._stats["data_types_seen"]),
                "average_collection_rate": self._stats["collection_rate"],
                "storage_summary": session_summary,
                "event_count": self.event_logger.get_event_count() if self.event_logger else 0
            }

            # Reset state
            self.is_recording = False
            self.session_id = None
            self.session_start_time = None
            self.streamer = None
            self.storage = None
            self.event_logger = None

            self.logger.info(f"Recording session completed successfully")
            self.logger.info(f"Duration: {duration:.1f}s, Samples: {self._stats['samples_collected']}")

            return final_summary

        except Exception as e:
            self.logger.error(f"Error stopping recording: {e}", exc_info=True)

            # Try to cleanup even if there was an error
            try:
                self.is_recording = False
                if self.storage:
                    self.storage.finalize_session()
            except:
                pass

            return {"error": str(e), "traceback": str(e)}

    def collect_data_worker(self) -> None:
        """
        Main loop for data collection in worker thread.

        This method runs in a background thread and continuously collects data
        from the streamer, processes it, and stores it via the storage system.
        """
        self.logger.info("Data collection worker started")

        last_stats_update = time.time()
        stats_interval = 30  # Update stats every 30 seconds

        try:
            while not self._stop_data_collection and self.is_recording:
                try:
                    current_time = time.time()

                    # Process raw data
                    self.process_raw_data()

                    # Process ML scores
                    self.process_scores()

                    # Update statistics periodically
                    if current_time - last_stats_update >= stats_interval:
                        self._update_collection_stats()
                        last_stats_update = current_time

                    # Small sleep to prevent excessive CPU usage
                    time.sleep(0.01)  # 10ms

                except Exception as e:
                    self.logger.error(f"Error in data collection loop: {e}")
                    self._stats["errors_count"] += 1
                    time.sleep(0.1)  # Longer sleep on error

        except Exception as e:
            self.logger.error(f"Fatal error in data collection worker: {e}")

        self.logger.info("Data collection worker stopped")

    def process_raw_data(self) -> None:
        """Extract and organize raw sensor data from streamer."""
        if not self.streamer or not self.storage:
            return

        try:
            current_time = time.time()

            # Process EEG data (actual shape is [N, 7] not [N, 4])
            eeg_data = self.streamer.DATA.get("RAW", {}).get("EEG")
            if eeg_data is not None and hasattr(eeg_data, 'shape') and eeg_data.shape[0] > 0:
                if len(eeg_data.shape) == 2:
                    latest_eeg = eeg_data[-1, :]  # Get last row (all 7 channels)
                    self.storage.append_data("raw/eeg", latest_eeg, current_time)
                    self._stats["samples_collected"] += 1
                    self._stats["data_types_seen"].add("raw/eeg")

            # EOG and EMG are not available in this device/firmware version
            # Skipping as they return None

            # Process IMU data (shape is [N, 4] not [N, 3])
            imu_data = self.streamer.DATA.get("RAW", {}).get("IMU")
            if imu_data is not None and hasattr(imu_data, 'shape') and imu_data.shape[0] > 0:
                if len(imu_data.shape) == 2:
                    latest_imu = imu_data[-1, 1:]  # Skip timestamp, take x,y,z
                    self.storage.append_data("raw/imu", latest_imu, current_time)
                    self._stats["data_types_seen"].add("raw/imu")

            # Process PPG data (shape is [N, 4] not [N, 3])
            ppg_data = self.streamer.DATA.get("RAW", {}).get("PPG")
            if ppg_data is not None and hasattr(ppg_data, 'shape') and ppg_data.shape[0] > 0:
                if len(ppg_data.shape) == 2:
                    latest_ppg = ppg_data[-1, 1:]  # Skip timestamp, take G,R,IR
                    self.storage.append_data("raw/ppg", latest_ppg, current_time)
                    self._stats["data_types_seen"].add("raw/ppg")

            # Skip filtered data - format is incompatible with storage expectations
            # Filtered EEG is 1D array with variable lengths not divisible by channel count
            # Raw EEG is being collected successfully, so filtered data is not critical

            self._stats["last_data_time"] = current_time

        except Exception as e:
            self.logger.error(f"Error processing raw data: {e}")
            self._stats["errors_count"] += 1

    def process_scores(self) -> None:
        """Extract ML scores from streamer."""
        if not self.streamer or not self.storage:
            return

        try:
            current_time = time.time()

            # Process individual scores
            scores_map = {
                "focus_score": "scores/focus",
                "poas": "scores/poas",
                "posture": "scores/posture",
                "sleep_stage": "scores/sleep_stage",
                "sqc_scores": "scores/signal_quality",
                "hr": "scores/hr",  # Heart rate (BPM)
                "spo2": "scores/spo2"  # Blood oxygen saturation (%)
            }

            for score_key, dataset_name in scores_map.items():
                score_value = self.streamer.SCORES.get(score_key)
                if score_value is not None:
                    # Handle different score types
                    if score_key == "sqc_scores":
                        # Signal quality is array of 4 values
                        if hasattr(score_value, '__len__') and len(score_value) == 4:
                            self.storage.append_data(dataset_name, np.array(score_value), current_time)
                            self._stats["data_types_seen"].add(dataset_name)
                    else:
                        # Single value scores - convert to float, handle strings
                        try:
                            if isinstance(score_value, str):
                                # Map string values to numeric for posture
                                if score_key == "posture":
                                    posture_map = {"upright": 1, "slouching": 2, "unknown": 0}
                                    score_value = posture_map.get(score_value.lower(), 0)
                                else:
                                    # Skip non-numeric strings
                                    continue
                            self.storage.append_data(dataset_name, float(score_value), current_time)
                            self._stats["data_types_seen"].add(dataset_name)
                        except (ValueError, TypeError):
                            # Skip invalid values
                            pass

            # Process power band data
            power_bands = ["alpha", "beta", "gamma", "theta", "delta"]
            for band in power_bands:
                band_data = self.streamer.SCORES.get(band)
                if band_data is not None:
                    # Power bands are arrays of 5 values (LF, OTEL, RF, OTER, AVG)
                    if hasattr(band_data, '__len__') and len(band_data) == 5:
                        dataset_name = f"power_bands/{band}"
                        self.storage.append_data(dataset_name, np.array(band_data), current_time)
                        self._stats["data_types_seen"].add(dataset_name)

        except Exception as e:
            self.logger.error(f"Error processing scores: {e}")
            self._stats["errors_count"] += 1

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Return current session statistics.

        Returns:
            Dict containing comprehensive session statistics
        """
        if not self.is_recording:
            return {"status": "not_recording"}

        try:
            current_time = time.time()
            duration = current_time - (self.session_start_time or current_time)

            # Get storage stats
            storage_stats = {}
            if self.storage:
                storage_stats = self.storage.get_session_stats()

            # Get event stats
            event_stats = {}
            if self.event_logger:
                event_info = self.event_logger.get_session_info()
                event_stats = {
                    "total_events": event_info["total_events"],
                    "category_counts": event_info["category_counts"]
                }

            # Get device connection stats
            device_stats = self.device_manager.get_status_info()

            # Calculate collection rate
            collection_rate = 0.0
            if duration > 0:
                collection_rate = self._stats["samples_collected"] / duration

            return {
                "status": "recording",
                "session_id": self.session_id,
                "duration_seconds": duration,
                "start_time": self.session_start_time,
                "samples_collected": self._stats["samples_collected"],
                "collection_rate_hz": collection_rate,
                "errors_count": self._stats["errors_count"],
                "data_types_active": list(self._stats["data_types_seen"]),
                "last_data_time": self._stats["last_data_time"],
                "time_since_last_data": current_time - (self._stats["last_data_time"] or current_time),
                "device_status": device_stats,
                "storage_stats": storage_stats,
                "event_stats": event_stats
            }

        except Exception as e:
            self.logger.error(f"Error getting session stats: {e}")
            return {"error": str(e)}

    def log_event(self, description: str, category: str = "other") -> bool:
        """
        Log an event during recording.

        Args:
            description: Event description
            category: Event category (subjective, stimulus, response, other)

        Returns:
            bool: True if event logged successfully, False otherwise
        """
        try:
            if not self.event_logger:
                self.logger.warning("Event logger not initialized")
                return False

            self.event_logger.log_event(description, category)
            return True

        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
            return False

    def get_recent_data(self, data_type: str, seconds: int = 60) -> Optional[np.ndarray]:
        """
        Get recent data for visualization.

        Args:
            data_type: Type of data to retrieve (e.g., "scores/focus")
            seconds: Number of seconds of recent data to retrieve

        Returns:
            numpy array of recent data or None if not available
        """
        # This would require additional buffering for visualization
        # For now, return None as this is typically handled by the dashboard
        self.logger.warning("get_recent_data not implemented - use dashboard visualization")
        return None

    def is_connected(self) -> bool:
        """Check if device is connected and data is flowing."""
        return (self.device_manager.is_connected() and
                self.is_recording and
                self._stats["last_data_time"] is not None and
                time.time() - self._stats["last_data_time"] < 10)  # Data within last 10 seconds

    def get_device_info(self) -> Optional[Dict]:
        """Get information about the connected device."""
        return self.device_manager.get_device_info()

    def _save_device_metadata(self) -> None:
        """Save device configuration and calibration data to session folder."""
        try:
            if not self.storage or not self.storage.session_path:
                return

            metadata = {
                "device_id": self.device_manager.device_id or "Unknown",
                "session_start_time": time.time(),
                "imu_calibration": None,
                "device_configuration": {
                    "eeg_sampling_rate": 125,
                    "imu_sampling_rate": 50,
                    "ppg_sampling_rate": 25,
                    "hr_sampling_rate": 1,
                    "spo2_sampling_rate": 1,
                }
            }

            # Try to get IMU calibration from SCORES
            if self.streamer and hasattr(self.streamer, 'SCORES'):
                imu_cal = self.streamer.SCORES.get('imu_calibration')
                if imu_cal is not None:
                    metadata["imu_calibration"] = list(imu_cal)

            # Save to device_config.json
            config_path = self.storage.session_path / "device_config.json"
            with open(config_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            self.logger.info(f"Device metadata saved to {config_path}")

        except Exception as e:
            self.logger.error(f"Error saving device metadata: {e}")

    def _start_data_worker(self) -> None:
        """Start the data collection worker thread."""
        if self._data_worker_thread and self._data_worker_thread.is_alive():
            self.logger.warning("Data worker thread already running")
            return

        self._stop_data_collection = False
        self._data_worker_thread = threading.Thread(
            target=self.collect_data_worker,
            name="FrenzCollector-DataWorker",
            daemon=True
        )
        self._data_worker_thread.start()
        self.logger.info("Data collection worker thread started")

    def _stop_data_worker(self) -> None:
        """Stop the data collection worker thread."""
        self._stop_data_collection = True

        if self._data_worker_thread and self._data_worker_thread.is_alive():
            self.logger.info("Stopping data collection worker...")
            self._data_worker_thread.join(timeout=5.0)

            if self._data_worker_thread.is_alive():
                self.logger.warning("Data worker thread did not stop gracefully")
            else:
                self.logger.info("Data collection worker stopped")

    def _reset_stats(self) -> None:
        """Reset collection statistics."""
        self._stats = {
            "samples_collected": 0,
            "errors_count": 0,
            "last_data_time": None,
            "data_types_seen": set(),
            "collection_rate": 0.0
        }

    def _update_collection_stats(self) -> None:
        """Update collection statistics."""
        if self.session_start_time:
            duration = time.time() - self.session_start_time
            if duration > 0:
                self._stats["collection_rate"] = self._stats["samples_collected"] / duration

    def _cleanup_failed_start(self) -> None:
        """Cleanup after failed recording start."""
        try:
            if self.storage:
                self.storage.stop_recording()
                self.storage = None

            if self.device_manager.is_connected():
                self.device_manager.disconnect()

            self.event_logger = None
            self.streamer = None
            self.is_recording = False
            self.session_id = None
            self.session_start_time = None

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Cleanup on object destruction."""
        try:
            if self.is_recording:
                self.stop_recording()
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error in destructor: {e}")


# Convenience function for quick recording sessions
def quick_recording_session(duration_seconds: int = 300,
                          device_id: Optional[str] = None,
                          session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Start a quick recording session for a specified duration.

    Args:
        duration_seconds: Recording duration in seconds (default: 5 minutes)
        device_id: Device to connect to (uses default if None)
        session_id: Session identifier (generates if None)

    Returns:
        Dictionary containing session summary
    """
    collector = FrenzCollector()

    try:
        # Start recording
        if not collector.start_recording(device_id=device_id, session_id=session_id):
            return {"error": "Failed to start recording"}

        print(f"Recording started for {duration_seconds} seconds...")

        # Record for specified duration
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            time.sleep(1)

            # Print progress every 30 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 30 == 0:
                stats = collector.get_session_stats()
                print(f"Recording... {elapsed:.0f}s elapsed, "
                      f"{stats.get('samples_collected', 0)} samples collected")

        # Stop recording
        summary = collector.stop_recording()
        print(f"Recording completed: {summary.get('session_id', 'unknown')}")

        return summary

    except KeyboardInterrupt:
        print("\nRecording interrupted by user")
        return collector.stop_recording()
    except Exception as e:
        print(f"Error during recording: {e}")
        return collector.stop_recording()


if __name__ == "__main__":
    """
    Example usage of the FrenzCollector class.
    """
    import argparse

    parser = argparse.ArgumentParser(description="FRENZ Data Collector")
    parser.add_argument("--duration", type=int, default=300,
                       help="Recording duration in seconds (default: 300)")
    parser.add_argument("--device-id", type=str,
                       help="Device ID to connect to")
    parser.add_argument("--session-id", type=str,
                       help="Custom session ID")

    args = parser.parse_args()

    print("FRENZ Data Collector")
    print("=" * 40)

    # Run quick recording session
    summary = quick_recording_session(
        duration_seconds=args.duration,
        device_id=args.device_id,
        session_id=args.session_id
    )

    if "error" in summary:
        print(f"Error: {summary['error']}")
    else:
        print("\nRecording Summary:")
        print(f"Session ID: {summary.get('session_id', 'N/A')}")
        print(f"Duration: {summary.get('duration_seconds', 0):.1f} seconds")
        print(f"Samples collected: {summary.get('samples_collected', 0)}")
        print(f"Data types: {summary.get('data_types_collected', [])}")
        print(f"Events logged: {summary.get('event_count', 0)}")

        if summary.get('storage_summary'):
            storage = summary['storage_summary']
            if 'data_stats' in storage:
                print(f"File size: {storage['data_stats'].get('file_size_mb', 0):.2f} MB")