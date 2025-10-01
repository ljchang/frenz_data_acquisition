"""
Event Logger module for FRENZ data collection system.

This module provides event logging functionality with precise timestamps,
category support, thread-safe operations, and export capabilities for
manual event annotation during data collection sessions.
"""

import os
import csv
import json
import time
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime


class EventLogger:
    """
    Manages event logging with timestamps for FRENZ data collection.

    This class provides:
    - Event logging with precise timestamps (unix and ISO format)
    - Category support (subjective, stimulus, response, other)
    - Thread-safe operations for concurrent access
    - Save to JSON file with proper formatting
    - Export capabilities (CSV format)
    - Filtering by time range
    - Session management and metadata tracking
    """

    def __init__(self,
                 session_id: Optional[str] = None,
                 data_dir: Union[str, Path] = "./data",
                 auto_save: bool = True):
        """
        Initialize the EventLogger instance.

        Args:
            session_id: Unique session identifier. If None, generates one based on current time
            data_dir: Directory to store event files
            auto_save: Whether to automatically save events to file after each log
        """
        self.data_dir = Path(data_dir)
        self.auto_save = auto_save
        self.session_id = session_id or self._generate_session_id()

        # Thread-safe event storage
        self._events: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

        # Valid event categories
        self.valid_categories = {"subjective", "stimulus", "response", "other"}

        # Session metadata
        self.session_start_time = time.time()

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Set up session directory
        self.session_dir = self.data_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.events_file = self.session_dir / "events.json"

        # Configure logging
        self.logger = logging.getLogger(__name__)

        # Load existing events if file exists
        self._load_existing_events()

    def _generate_session_id(self) -> str:
        """Generate a session ID based on current timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _load_existing_events(self) -> None:
        """Load existing events from file if it exists."""
        if self.events_file.exists():
            try:
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'events' in data:
                        self._events = data['events']
                    elif isinstance(data, list):
                        self._events = data
                    else:
                        self.logger.warning(f"Invalid events file format: {self.events_file}")
                        self._events = []
                self.logger.info(f"Loaded {len(self._events)} existing events")
            except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
                self.logger.error(f"Error loading existing events: {e}")
                self._events = []

    def log_event(self,
                  description: str,
                  category: str = "other") -> Dict[str, Any]:
        """
        Log an event with timestamp and description.

        Args:
            description: Description of the event
            category: Category of the event (subjective, stimulus, response, other)

        Returns:
            Dict containing the logged event data

        Raises:
            ValueError: If category is not valid
            TypeError: If description is not a string
        """
        if not isinstance(description, str):
            raise TypeError("Description must be a string")

        if description.strip() == "":
            raise ValueError("Description cannot be empty")

        if category not in self.valid_categories:
            raise ValueError(f"Category must be one of: {self.valid_categories}")

        # Generate precise timestamp
        timestamp = time.time()
        iso_time = datetime.fromtimestamp(timestamp).isoformat() + "Z"

        # Create event record
        event = {
            "timestamp": timestamp,
            "iso_time": iso_time,
            "description": description.strip(),
            "category": category,
            "session_id": self.session_id
        }

        # Thread-safe addition to events list
        with self._lock:
            self._events.append(event)
            event_count = len(self._events)

        # Auto-save if enabled
        if self.auto_save:
            try:
                self.save_events()
            except Exception as e:
                self.logger.error(f"Auto-save failed: {e}")

        self.logger.info(f"Event logged: {description} [{category}] (Total: {event_count})")
        return event.copy()

    def get_events(self,
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None,
                   category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve events with optional time and category filtering.

        Args:
            start_time: Unix timestamp for start of time range (inclusive)
            end_time: Unix timestamp for end of time range (inclusive)
            category: Filter by event category

        Returns:
            List of event dictionaries matching the filters
        """
        with self._lock:
            events = self._events.copy()

        # Apply time filtering
        if start_time is not None:
            events = [e for e in events if e["timestamp"] >= start_time]

        if end_time is not None:
            events = [e for e in events if e["timestamp"] <= end_time]

        # Apply category filtering
        if category is not None:
            if category not in self.valid_categories:
                raise ValueError(f"Category must be one of: {self.valid_categories}")
            events = [e for e in events if e["category"] == category]

        return events

    def save_events(self) -> bool:
        """
        Write events to JSON file.

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                events_data = {
                    "session_info": {
                        "session_id": self.session_id,
                        "session_start_time": self.session_start_time,
                        "session_start_iso": datetime.fromtimestamp(self.session_start_time).isoformat() + "Z",
                        "total_events": len(self._events),
                        "last_updated": time.time(),
                        "last_updated_iso": datetime.now().isoformat() + "Z"
                    },
                    "events": self._events.copy()
                }

            # Write to temporary file first, then move (atomic operation)
            temp_file = self.events_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, indent=2, ensure_ascii=False)

            # Atomic move
            temp_file.replace(self.events_file)

            self.logger.debug(f"Events saved to {self.events_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save events: {e}")
            return False

    def export_events(self,
                      format: str = "csv",
                      output_path: Optional[Union[str, Path]] = None,
                      start_time: Optional[float] = None,
                      end_time: Optional[float] = None,
                      category: Optional[str] = None) -> Path:
        """
        Export events in specified format.

        Args:
            format: Export format ("csv" or "json")
            output_path: Custom output file path. If None, generates default
            start_time: Unix timestamp for start of time range (inclusive)
            end_time: Unix timestamp for end of time range (inclusive)
            category: Filter by event category

        Returns:
            Path to the exported file

        Raises:
            ValueError: If format is not supported
            IOError: If export fails
        """
        if format not in ["csv", "json"]:
            raise ValueError("Format must be 'csv' or 'json'")

        # Get filtered events
        events = self.get_events(start_time, end_time, category)

        # Generate output path if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"events_export_{timestamp}.{format}"
            output_path = self.session_dir / filename
        else:
            output_path = Path(output_path)

        try:
            if format == "csv":
                self._export_csv(events, output_path)
            elif format == "json":
                self._export_json(events, output_path)

            self.logger.info(f"Exported {len(events)} events to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            raise IOError(f"Failed to export events: {e}")

    def _export_csv(self, events: List[Dict[str, Any]], output_path: Path) -> None:
        """Export events to CSV format."""
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'iso_time', 'description', 'category', 'session_id']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for event in events:
                writer.writerow(event)

    def _export_json(self, events: List[Dict[str, Any]], output_path: Path) -> None:
        """Export events to JSON format."""
        export_data = {
            "export_info": {
                "export_time": time.time(),
                "export_time_iso": datetime.now().isoformat() + "Z",
                "session_id": self.session_id,
                "event_count": len(events)
            },
            "events": events
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

    def clear_events(self, confirm: bool = False) -> bool:
        """
        Clear event buffer.

        Args:
            confirm: Must be True to actually clear events (safety check)

        Returns:
            True if events were cleared, False otherwise
        """
        if not confirm:
            self.logger.warning("clear_events() called without confirmation")
            return False

        with self._lock:
            event_count = len(self._events)
            self._events.clear()

        # Save empty state if auto-save is enabled
        if self.auto_save:
            self.save_events()

        self.logger.info(f"Cleared {event_count} events")
        return True

    def get_event_count(self) -> int:
        """Get the current number of logged events."""
        with self._lock:
            return len(self._events)

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get session information and statistics.

        Returns:
            Dictionary containing session metadata and statistics
        """
        with self._lock:
            event_count = len(self._events)
            if event_count > 0:
                first_event_time = self._events[0]["timestamp"]
                last_event_time = self._events[-1]["timestamp"]
                event_duration = last_event_time - first_event_time
            else:
                first_event_time = None
                last_event_time = None
                event_duration = 0

            # Count events by category
            category_counts = {}
            for category in self.valid_categories:
                category_counts[category] = sum(1 for e in self._events if e["category"] == category)

        return {
            "session_id": self.session_id,
            "session_start_time": self.session_start_time,
            "session_start_iso": datetime.fromtimestamp(self.session_start_time).isoformat() + "Z",
            "current_time": time.time(),
            "session_duration": time.time() - self.session_start_time,
            "total_events": event_count,
            "first_event_time": first_event_time,
            "last_event_time": last_event_time,
            "event_duration": event_duration,
            "category_counts": category_counts,
            "events_file": str(self.events_file),
            "auto_save": self.auto_save
        }

    def get_recent_events(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent events.

        Args:
            count: Number of recent events to return

        Returns:
            List of recent event dictionaries
        """
        with self._lock:
            return self._events[-count:] if self._events else []

    def validate_event_integrity(self) -> Dict[str, Any]:
        """
        Validate the integrity of stored events.

        Returns:
            Dictionary containing validation results
        """
        issues = []

        with self._lock:
            events = self._events.copy()

        # Check for required fields
        required_fields = {"timestamp", "iso_time", "description", "category", "session_id"}
        for i, event in enumerate(events):
            missing_fields = required_fields - set(event.keys())
            if missing_fields:
                issues.append(f"Event {i}: Missing fields {missing_fields}")

            # Check timestamp validity
            if "timestamp" in event:
                try:
                    float(event["timestamp"])
                except (ValueError, TypeError):
                    issues.append(f"Event {i}: Invalid timestamp")

            # Check category validity
            if "category" in event and event["category"] not in self.valid_categories:
                issues.append(f"Event {i}: Invalid category '{event['category']}'")

        # Check chronological order
        timestamps = [e.get("timestamp", 0) for e in events if "timestamp" in e]
        if timestamps != sorted(timestamps):
            issues.append("Events are not in chronological order")

        return {
            "is_valid": len(issues) == 0,
            "event_count": len(events),
            "issues": issues,
            "validation_time": time.time()
        }


# Convenience function for quick event logging
def log_quick_event(description: str, category: str = "other", session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick utility function to log an event without maintaining an EventLogger instance.

    Args:
        description: Description of the event
        category: Category of the event
        session_id: Session ID (will be generated if None)

    Returns:
        The logged event dictionary
    """
    logger = EventLogger(session_id=session_id, auto_save=True)
    return logger.log_event(description, category)


if __name__ == "__main__":
    # Example usage and testing
    print("EventLogger Example Usage")
    print("=" * 40)

    # Create event logger
    logger = EventLogger(auto_save=True)
    print(f"Session ID: {logger.session_id}")

    # Log some example events
    events = [
        ("Experiment started", "other"),
        ("Baseline recording initiated", "other"),
        ("Subject reported feeling alert", "subjective"),
        ("Visual stimulus presented", "stimulus"),
        ("Subject pressed response button", "response"),
        ("Subject reported drowsiness", "subjective"),
        ("End of session", "other")
    ]

    for desc, cat in events:
        event = logger.log_event(desc, cat)
        print(f"Logged: {event['description']} [{event['category']}]")
        time.sleep(0.1)  # Small delay for demonstration

    # Get session info
    info = logger.get_session_info()
    print(f"\nSession Info:")
    print(f"Total events: {info['total_events']}")
    print(f"Category counts: {info['category_counts']}")

    # Export events
    csv_path = logger.export_events("csv")
    print(f"\nEvents exported to: {csv_path}")

    # Validate integrity
    validation = logger.validate_event_integrity()
    print(f"\nValidation: {'PASSED' if validation['is_valid'] else 'FAILED'}")
    if validation['issues']:
        for issue in validation['issues']:
            print(f"  - {issue}")