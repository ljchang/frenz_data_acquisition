#!/usr/bin/env python3
"""
Test script for FrenzCollector module.

This script validates the FrenzCollector API and ensures compatibility
with dashboard requirements without requiring an actual device connection.
"""

import sys
import time
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from frenz_collector import FrenzCollector, quick_recording_session


def test_collector_api():
    """Test the FrenzCollector API without device connection."""
    print("Testing FrenzCollector API...")

    # Test instantiation
    collector = FrenzCollector(
        device_id="test_device",
        data_dir="./test_data",
        buffer_size_minutes=1,
        auto_save_interval=30
    )

    # Test initial state
    assert not collector.is_recording, "Should not be recording initially"
    assert not collector.is_connected(), "Should not be connected initially"

    stats = collector.get_session_stats()
    assert stats["status"] == "not_recording", "Should show not recording status"

    # Test event logging when not recording
    success = collector.log_event("Test event", "other")
    assert not success, "Should fail to log event when not recording"

    print("✓ Basic API tests passed")


def test_dashboard_compatibility():
    """Test methods required for Marimo dashboard integration."""
    print("Testing dashboard compatibility...")

    collector = FrenzCollector()

    # Test methods that dashboard will use
    methods_to_test = [
        'get_session_stats',
        'is_connected',
        'get_device_info',
        'log_event'
    ]

    for method_name in methods_to_test:
        method = getattr(collector, method_name, None)
        assert method is not None, f"Method {method_name} should exist"
        assert callable(method), f"Method {method_name} should be callable"

    # Test return types for dashboard
    stats = collector.get_session_stats()
    assert isinstance(stats, dict), "get_session_stats should return dict"

    connected = collector.is_connected()
    assert isinstance(connected, bool), "is_connected should return bool"

    device_info = collector.get_device_info()
    assert device_info is None or isinstance(device_info, dict), "get_device_info should return dict or None"

    print("✓ Dashboard compatibility tests passed")


def test_configuration_integration():
    """Test integration with config module."""
    print("Testing configuration integration...")

    from config import config

    # Test that collector uses config values
    collector = FrenzCollector()

    # These should match config defaults
    expected_data_dir = config.storage["data_dir"]
    assert collector.data_dir == expected_data_dir, f"Data dir should match config: {collector.data_dir} vs {expected_data_dir}"

    print("✓ Configuration integration tests passed")


def test_thread_safety():
    """Test thread safety for concurrent operations."""
    print("Testing thread safety...")

    collector = FrenzCollector()

    # Test that we can call methods concurrently without errors
    import threading

    results = []
    errors = []

    def worker():
        try:
            for i in range(10):
                stats = collector.get_session_stats()
                results.append(stats)
                time.sleep(0.01)
        except Exception as e:
            errors.append(e)

    # Start multiple threads
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    # Wait for completion
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Should have no errors in concurrent access: {errors}"
    assert len(results) == 30, f"Should have 30 results from 3 threads: {len(results)}"

    print("✓ Thread safety tests passed")


def test_error_handling():
    """Test error handling scenarios."""
    print("Testing error handling...")

    collector = FrenzCollector()

    # Test invalid session start (no device)
    success = collector.start_recording(device_id="nonexistent_device")
    assert not success, "Should fail to start recording with invalid device"

    # Test stop when not recording
    result = collector.stop_recording()
    assert "error" in result, "Should return error when stopping non-active recording"

    # Test invalid event category
    try:
        from event_logger import EventLogger
        logger = EventLogger()
        logger.log_event("test", "invalid_category")
        assert False, "Should raise ValueError for invalid category"
    except ValueError:
        pass  # Expected

    print("✓ Error handling tests passed")


def test_data_structure_compatibility():
    """Test compatibility with expected data structures."""
    print("Testing data structure compatibility...")

    collector = FrenzCollector()

    # Test session stats structure
    stats = collector.get_session_stats()
    required_keys = ["status"]
    for key in required_keys:
        assert key in stats, f"Session stats should contain {key}"

    # Test that we can handle the expected data types from specs
    from data_storage import DataStorage
    storage = DataStorage()

    # Test dataset configs match specs
    configs = storage._get_dataset_configs()
    expected_datasets = [
        "raw/eeg", "raw/eog", "raw/emg", "raw/imu", "raw/ppg",
        "filtered/eeg", "filtered/eog", "filtered/emg",
        "scores/poas", "scores/focus", "scores/posture", "scores/sleep_stage", "scores/signal_quality",
        "power_bands/alpha", "power_bands/beta", "power_bands/gamma", "power_bands/theta", "power_bands/delta",
        "timestamps"
    ]

    for dataset in expected_datasets:
        assert dataset in configs, f"Dataset {dataset} should be configured"

    print("✓ Data structure compatibility tests passed")


def main():
    """Run all tests."""
    print("FRENZ Collector Test Suite")
    print("=" * 40)

    try:
        test_collector_api()
        test_dashboard_compatibility()
        test_configuration_integration()
        test_thread_safety()
        test_error_handling()
        test_data_structure_compatibility()

        print("\n" + "=" * 40)
        print("✅ All tests passed successfully!")
        print("FrenzCollector is ready for use with the dashboard.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()