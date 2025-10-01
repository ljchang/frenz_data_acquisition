"""
Device Manager module for FRENZ data collection system.

This module handles device discovery, connection, and management for FRENZ brainband devices.
It provides functionality for scanning devices, loading devices from environment files,
connection management with proper error handling, status tracking, and auto-reconnect capability.
"""

import os
import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Union
from pathlib import Path
from dotenv import load_dotenv
import threading
import asyncio

import nest_asyncio
nest_asyncio.apply()

from frenztoolkit import Scanner, Streamer


class DeviceStatus(Enum):
    """Device connection status enumeration."""
    DISCONNECTED = "disconnected"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class DeviceManager:
    """
    Manages FRENZ device discovery, connection, and lifecycle.

    This class provides a unified interface for device management including:
    - Device scanning and discovery
    - Loading devices from environment configuration
    - Connection establishment and management
    - Status tracking and monitoring
    - Auto-reconnect functionality with exponential backoff
    - Comprehensive error handling and logging
    """

    def __init__(self,
                 connection_timeout: int = 30,
                 reconnect_attempts: int = 3,
                 auto_connect_on_start: bool = True,
                 env_path: Optional[Path] = None):
        """
        Initialize the DeviceManager.

        Args:
            connection_timeout: Maximum time in seconds to wait for connection
            reconnect_attempts: Number of automatic reconnection attempts
            auto_connect_on_start: Whether to automatically connect on startup
            env_path: Path to environment file (defaults to project root .env)
        """
        self.connection_timeout = connection_timeout
        self.reconnect_attempts = reconnect_attempts
        self.auto_connect_on_start = auto_connect_on_start
        self.light_off = True  # Default to light off

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
        self._status = DeviceStatus.DISCONNECTED
        self._scanner = None
        self._streamer = None
        self._connected_device = None
        self._reconnect_thread = None
        self._stop_reconnect = False
        self._last_connection_error = None

        # Load environment variables
        self._load_env_variables(env_path)

        self.logger.info("DeviceManager initialized")

    def _load_env_variables(self, env_path: Optional[Path] = None) -> None:
        """Load environment variables from file."""
        try:
            if env_path is None:
                # Try multiple common locations
                possible_paths = [
                    Path(".env"),
                    Path.home() / '.config' / 'my_api_keys' / 'keys.env',
                    Path(__file__).parent / ".env"
                ]

                for path in possible_paths:
                    if path.exists():
                        env_path = path
                        break

            if env_path and env_path.exists():
                load_dotenv(env_path)
                self.logger.info(f"Loaded environment variables from {env_path}")
            else:
                self.logger.warning("No .env file found, using system environment variables")

        except Exception as e:
            self.logger.error(f"Error loading environment variables: {e}")

    def scan_devices(self) -> List[Dict]:
        """
        Scan for available FRENZ devices.

        Returns:
            List of discovered devices with format:
            [{"id": "FRENZ-001", "name": "FRENZ Band", "rssi": -45}]
        """
        self.logger.info("Starting device scan...")
        self._status = DeviceStatus.SCANNING

        try:
            if self._scanner is None:
                self._scanner = Scanner()

            # Perform scan
            devices = self._scanner.scan()
            self.logger.info(f"Found {len(devices)} devices")

            # Filter for FRENZ devices only (devices containing "FRENZ" in the name)
            formatted_devices = []
            for device in devices:
                device_str = str(device)
                # Only include devices that contain "FRENZ" in their name
                if "FRENZ" in device_str.upper():
                    formatted_devices.append({
                        "id": device_str,
                        "name": "FRENZ Band",
                        "rssi": -50  # Default RSSI since scanner doesn't provide it
                    })

            self.logger.info(f"Found {len(formatted_devices)} FRENZ devices")

            self._status = DeviceStatus.DISCONNECTED
            return formatted_devices

        except Exception as e:
            self.logger.error(f"Error scanning devices: {e}")
            self._status = DeviceStatus.ERROR
            self._last_connection_error = str(e)
            return []

    def load_env_devices(self) -> Dict:
        """
        Load device configuration from environment variables.

        Returns:
            Dictionary containing device configuration from .env file
        """
        try:
            device_config = {
                "device_id": os.getenv("FRENZ_ID"),
                "product_key": os.getenv("FRENZ_KEY"),
                "available": False
            }

            # Check if required variables are present
            if device_config["device_id"] and device_config["product_key"]:
                device_config["available"] = True
                self.logger.info(f"Loaded device config for {device_config['device_id']}")
            else:
                self.logger.warning("FRENZ_ID or FRENZ_KEY not found in environment")

            return device_config

        except Exception as e:
            self.logger.error(f"Error loading environment devices: {e}")
            return {"available": False, "error": str(e)}

    def connect(self, device_id: Optional[str] = None, product_key: Optional[str] = None) -> Optional[Streamer]:
        """
        Establish connection to a FRENZ device.

        Args:
            device_id: Device identifier (uses env var if None)
            product_key: Product key for authentication (uses env var if None)

        Returns:
            Streamer instance if successful, None otherwise
        """
        self.logger.info(f"Attempting to connect to device: {device_id}")
        self._status = DeviceStatus.CONNECTING
        self._last_connection_error = None

        try:
            # Use environment variables if not provided
            if device_id is None:
                device_id = os.getenv("FRENZ_ID")
            if product_key is None:
                product_key = os.getenv("FRENZ_KEY")

            if not device_id or not product_key:
                raise ValueError("Device ID and product key are required")

            # Clean up existing connection
            if self._streamer:
                self.disconnect()

            # Create new streamer instance
            # Store Streamer's internal data in data/frenz_streamer_temp to keep it organized
            from pathlib import Path
            streamer_temp_dir = Path("./data/frenz_streamer_temp")
            streamer_temp_dir.mkdir(parents=True, exist_ok=True)

            self._streamer = Streamer(
                device_id=device_id,
                product_key=product_key,
                data_folder=str(streamer_temp_dir),
                turn_off_light=self.light_off
            )

            # Start connection with timeout
            start_time = time.time()
            self._streamer.start()

            # Wait for connection to establish
            while time.time() - start_time < self.connection_timeout:
                # Check if we have data flowing (indicates successful connection)
                if hasattr(self._streamer, 'DATA') and self._streamer.DATA:
                    self._status = DeviceStatus.CONNECTED
                    self._connected_device = {
                        "id": device_id,
                        "product_key": product_key,
                        "connected_at": time.time()
                    }
                    self.logger.info(f"Successfully connected to device {device_id}")
                    return self._streamer

                time.sleep(0.5)

            # Connection timeout
            raise TimeoutError(f"Connection timeout after {self.connection_timeout} seconds")

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self._status = DeviceStatus.ERROR
            self._last_connection_error = str(e)

            # Clean up failed connection
            if self._streamer:
                try:
                    self._streamer.stop()
                except:
                    pass
                self._streamer = None

            return None

    def disconnect(self) -> bool:
        """
        Cleanly disconnect from the current device.

        Returns:
            True if disconnection successful, False otherwise
        """
        try:
            self.logger.info("Starting disconnect process...")

            # Stop reconnect thread first
            self._stop_reconnect = True
            if self._reconnect_thread and self._reconnect_thread.is_alive():
                self.logger.info("Waiting for reconnect thread to stop...")
                self._reconnect_thread.join(timeout=2.0)

            # Stop the streamer
            if self._streamer:
                self.logger.info("Stopping streamer...")
                try:
                    self._streamer.stop()
                except Exception as e:
                    self.logger.warning(f"Error stopping streamer (non-fatal): {e}")
                finally:
                    self._streamer = None

            # Clear state
            self._connected_device = None
            self._status = DeviceStatus.DISCONNECTED

            self.logger.info("Device disconnected successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error during disconnection: {e}", exc_info=True)
            # Force cleanup even on error
            self._streamer = None
            self._connected_device = None
            self._status = DeviceStatus.ERROR
            return False

    def get_status(self) -> DeviceStatus:
        """
        Get current device connection status.

        Returns:
            Current DeviceStatus enum value
        """
        return self._status

    def get_status_info(self) -> Dict:
        """
        Get detailed status information.

        Returns:
            Dictionary with detailed status information
        """
        info = {
            "status": self._status.value,
            "connected_device": self._connected_device,
            "last_error": self._last_connection_error,
            "has_streamer": self._streamer is not None
        }

        if self._connected_device:
            info["connection_duration"] = time.time() - self._connected_device["connected_at"]

        return info

    def auto_reconnect(self) -> bool:
        """
        Attempt to reconnect to the last known device.

        Uses exponential backoff strategy for reconnection attempts.

        Returns:
            True if reconnection successful, False otherwise
        """
        if not self._connected_device:
            self.logger.warning("No previous device to reconnect to")
            return False

        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self.logger.info("Reconnection already in progress")
            return False

        self._stop_reconnect = False
        self._reconnect_thread = threading.Thread(target=self._reconnect_worker)
        self._reconnect_thread.daemon = True
        self._reconnect_thread.start()

        return True

    def _reconnect_worker(self) -> None:
        """Background worker for automatic reconnection with exponential backoff."""
        device_id = self._connected_device["id"]
        product_key = self._connected_device["product_key"]

        for attempt in range(self.reconnect_attempts):
            if self._stop_reconnect:
                break

            self.logger.info(f"Reconnection attempt {attempt + 1}/{self.reconnect_attempts}")

            # Exponential backoff: 2^attempt seconds
            wait_time = min(2 ** attempt, 30)  # Cap at 30 seconds

            if attempt > 0:  # Don't wait on first attempt
                for _ in range(wait_time):
                    if self._stop_reconnect:
                        return
                    time.sleep(1)

            # Attempt reconnection
            if self.connect(device_id, product_key):
                self.logger.info("Reconnection successful")
                return

        self.logger.error(f"Failed to reconnect after {self.reconnect_attempts} attempts")
        self._status = DeviceStatus.ERROR

    def is_connected(self) -> bool:
        """Check if device is currently connected."""
        return self._status == DeviceStatus.CONNECTED and self._streamer is not None

    def get_streamer(self) -> Optional[Streamer]:
        """Get the current Streamer instance if connected."""
        return self._streamer if self.is_connected() else None

    def get_device_info(self) -> Optional[Dict]:
        """Get information about the currently connected device."""
        return self._connected_device.copy() if self._connected_device else None

    def check_connection_health(self) -> bool:
        """
        Check if the current connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            # Try to access data to verify connection is working
            if hasattr(self._streamer, 'DATA') and self._streamer.DATA:
                # Check if we're getting recent data
                eeg_data = self._streamer.DATA.get("RAW", {}).get("EEG")
                if eeg_data is not None and len(eeg_data) > 0:
                    return True

            # If we can't verify data flow, consider connection unhealthy
            self.logger.warning("Connection appears unhealthy - no data flow detected")
            return False

        except Exception as e:
            self.logger.error(f"Error checking connection health: {e}")
            return False

    def toggle_light(self, light_on: bool) -> Dict:
        """
        Toggle device light setting.

        Note: Light setting is applied at connection time. If already connected,
        you'll need to reconnect for the change to take effect.

        Args:
            light_on: True to turn light on, False to turn it off

        Returns:
            Dictionary with status information
        """
        self.light_off = not light_on
        self.logger.info(f"Light setting changed to: {'ON' if light_on else 'OFF'}")

        result = {
            "light_on": light_on,
            "light_off": self.light_off,
            "requires_reconnect": self.is_connected()
        }

        if self.is_connected():
            result["message"] = "Light setting updated. Reconnect device for changes to take effect."
        else:
            result["message"] = f"Light will be {'ON' if light_on else 'OFF'} on next connection."

        return result

    def __del__(self):
        """Cleanup on object destruction."""
        try:
            if self._streamer:
                try:
                    self._streamer.stop()
                except:
                    pass
                self._streamer = None
            self._connected_device = None
            self._status = DeviceStatus.DISCONNECTED
        except:
            pass