"""
Configuration module for FRENZ data collection system.

This module provides centralized configuration management for all system components
including device settings, storage settings, display settings, and logging settings.
It supports environment variable overrides, validation, and provides sensible defaults.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when there's an error in configuration."""
    pass


class Config:
    """
    Centralized configuration management for FRENZ data collection system.

    This class manages all configuration settings with support for:
    - Loading from environment variables via .env file
    - Configuration validation
    - Override capabilities
    - Default fallback values
    - Type checking and conversion
    """

    def __init__(self, env_file: Optional[Union[str, Path]] = None, validate: bool = True):
        """
        Initialize configuration.

        Args:
            env_file: Path to .env file. If None, looks for .env in current directory
            validate: Whether to validate configuration values
        """
        # Load environment variables
        if env_file is None:
            env_file = Path.cwd() / ".env"
        if Path(env_file).exists():
            load_dotenv(env_file)

        # Initialize configuration sections
        self._device_settings = self._load_device_settings()
        self._storage_settings = self._load_storage_settings()
        self._display_settings = self._load_display_settings()
        self._logging_settings = self._load_logging_settings()

        if validate:
            self._validate_config()

    def _load_device_settings(self) -> Dict[str, Any]:
        """Load device-related configuration settings."""
        return {
            "default_device_id": os.getenv("FRENZ_ID"),
            "default_product_key": os.getenv("FRENZ_KEY"),
            "connection_timeout": int(os.getenv("CONNECTION_TIMEOUT", "30")),
            "reconnect_attempts": int(os.getenv("RECONNECT_ATTEMPTS", "3")),
            "auto_connect_on_start": os.getenv("AUTO_CONNECT_ON_START", "True").lower() == "true",
            "scan_timeout": int(os.getenv("SCAN_TIMEOUT", "10")),
            "reconnect_delay": float(os.getenv("RECONNECT_DELAY", "1.0")),
            "max_reconnect_delay": float(os.getenv("MAX_RECONNECT_DELAY", "60.0")),
        }

    def _load_storage_settings(self) -> Dict[str, Any]:
        """Load storage-related configuration settings."""
        data_dir = Path(os.getenv("DATA_DIR", "./data"))
        return {
            "data_dir": data_dir,
            "buffer_size_minutes": int(os.getenv("BUFFER_SIZE_MINUTES", "5")),
            "auto_save_interval": int(os.getenv("AUTO_SAVE_INTERVAL", "300")),
            "file_rotation_hours": int(os.getenv("FILE_ROTATION_HOURS", "24")),
            "compression": os.getenv("COMPRESSION", "gzip"),
            "compression_level": int(os.getenv("COMPRESSION_LEVEL", "4")),
            "chunk_size": int(os.getenv("HDF5_CHUNK_SIZE", "10000")),
            "max_file_size_gb": float(os.getenv("MAX_FILE_SIZE_GB", "10.0")),
            "backup_enabled": os.getenv("BACKUP_ENABLED", "False").lower() == "true",
            "backup_dir": Path(os.getenv("BACKUP_DIR", data_dir / "backups")),
        }

    def _load_display_settings(self) -> Dict[str, Any]:
        """Load display-related configuration settings."""
        return {
            "default_display_window": int(os.getenv("DEFAULT_DISPLAY_WINDOW", "600")),
            "max_display_points": int(os.getenv("MAX_DISPLAY_POINTS", "1000")),
            "downsample_threshold": int(os.getenv("DOWNSAMPLE_THRESHOLD", "5000")),
            "memory_limit_mb": int(os.getenv("MEMORY_LIMIT_MB", "500")),
            "auto_scroll": os.getenv("AUTO_SCROLL", "True").lower() == "true",
            "update_intervals": {
                "focus": int(os.getenv("UPDATE_INTERVAL_FOCUS", "2")),
                "poas": int(os.getenv("UPDATE_INTERVAL_POAS", "30")),
                "power_bands": int(os.getenv("UPDATE_INTERVAL_POWER_BANDS", "2")),
                "signal_quality": int(os.getenv("UPDATE_INTERVAL_SIGNAL_QUALITY", "5")),
                "posture": int(os.getenv("UPDATE_INTERVAL_POSTURE", "5")),
                "sleep_stage": int(os.getenv("UPDATE_INTERVAL_SLEEP_STAGE", "30")),
            },
            "plot_settings": {
                "theme": os.getenv("PLOT_THEME", "plotly_white"),
                "height": int(os.getenv("PLOT_HEIGHT", "400")),
                "show_legend": os.getenv("SHOW_LEGEND", "True").lower() == "true",
                "animate_transitions": os.getenv("ANIMATE_TRANSITIONS", "False").lower() == "true",
            },
            "color_schemes": {
                "focus": os.getenv("COLOR_FOCUS", "#1f77b4"),
                "poas": os.getenv("COLOR_POAS", "#ff7f0e"),
                "signal_quality_good": os.getenv("COLOR_SQ_GOOD", "#2ca02c"),
                "signal_quality_poor": os.getenv("COLOR_SQ_POOR", "#d62728"),
            }
        }

    def _load_logging_settings(self) -> Dict[str, Any]:
        """Load logging-related configuration settings."""
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

        return {
            "log_level": log_level,
            "log_file": os.getenv("LOG_FILE", "frenz_collector.log"),
            "log_dir": Path(os.getenv("LOG_DIR", "./logs")),
            "log_rotation": os.getenv("LOG_ROTATION", "True").lower() == "true",
            "max_log_size_mb": int(os.getenv("MAX_LOG_SIZE_MB", "10")),
            "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
            "console_logging": os.getenv("CONSOLE_LOGGING", "True").lower() == "true",
            "debug_mode": os.getenv("DEBUG_MODE", "False").lower() == "true",
            "log_format": os.getenv("LOG_FORMAT",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            "date_format": os.getenv("DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
        }

    def _validate_config(self) -> None:
        """Validate configuration values."""
        # Validate device settings
        if self._device_settings["connection_timeout"] <= 0:
            raise ConfigurationError("Connection timeout must be positive")

        if self._device_settings["reconnect_attempts"] < 0:
            raise ConfigurationError("Reconnect attempts must be non-negative")

        if self._device_settings["scan_timeout"] <= 0:
            raise ConfigurationError("Scan timeout must be positive")

        if self._device_settings["reconnect_delay"] <= 0:
            raise ConfigurationError("Reconnect delay must be positive")

        if self._device_settings["max_reconnect_delay"] <= 0:
            raise ConfigurationError("Max reconnect delay must be positive")

        # Validate storage settings
        if self._storage_settings["buffer_size_minutes"] <= 0:
            raise ConfigurationError("Buffer size must be positive")

        if self._storage_settings["auto_save_interval"] <= 0:
            raise ConfigurationError("Auto-save interval must be positive")

        if self._storage_settings["file_rotation_hours"] <= 0:
            raise ConfigurationError("File rotation hours must be positive")

        if not 0 <= self._storage_settings["compression_level"] <= 9:
            raise ConfigurationError("Compression level must be between 0 and 9")

        if self._storage_settings["chunk_size"] <= 0:
            raise ConfigurationError("HDF5 chunk size must be positive")

        if self._storage_settings["max_file_size_gb"] <= 0:
            raise ConfigurationError("Max file size must be positive")

        # Validate display settings
        if self._display_settings["default_display_window"] <= 0:
            raise ConfigurationError("Display window must be positive")

        if self._display_settings["max_display_points"] <= 0:
            raise ConfigurationError("Max display points must be positive")

        if self._display_settings["downsample_threshold"] <= 0:
            raise ConfigurationError("Downsample threshold must be positive")

        if self._display_settings["memory_limit_mb"] <= 0:
            raise ConfigurationError("Memory limit must be positive")

        # Validate update intervals
        for metric, interval in self._display_settings["update_intervals"].items():
            if interval <= 0:
                raise ConfigurationError(f"Update interval for {metric} must be positive")

        # Validate plot settings
        if self._display_settings["plot_settings"]["height"] <= 0:
            raise ConfigurationError("Plot height must be positive")

        # Validate logging settings
        if self._logging_settings["max_log_size_mb"] <= 0:
            raise ConfigurationError("Max log size must be positive")

        if self._logging_settings["backup_count"] < 0:
            raise ConfigurationError("Backup count must be non-negative")

    def create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self._storage_settings["data_dir"],
            self._storage_settings["backup_dir"],
            self._logging_settings["log_dir"],
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def override(self, section: str, key: str, value: Any, validate: bool = True) -> None:
        """
        Override a configuration value.

        Args:
            section: Configuration section (device, storage, display, logging)
            key: Configuration key
            value: New value
            validate: Whether to validate after setting the value
        """
        section_map = {
            "device": self._device_settings,
            "storage": self._storage_settings,
            "display": self._display_settings,
            "logging": self._logging_settings,
        }

        if section not in section_map:
            raise ConfigurationError(f"Unknown configuration section: {section}")

        if key not in section_map[section]:
            raise ConfigurationError(f"Unknown configuration key: {key} in section {section}")

        # Store old value in case validation fails
        old_value = section_map[section][key]
        section_map[section][key] = value

        if validate:
            try:
                self._validate_config()
            except ConfigurationError:
                # Restore old value and re-raise
                section_map[section][key] = old_value
                raise

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        section_map = {
            "device": self._device_settings,
            "storage": self._storage_settings,
            "display": self._display_settings,
            "logging": self._logging_settings,
        }

        if section not in section_map:
            return default

        return section_map[section].get(key, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section: Configuration section name

        Returns:
            Dictionary containing section configuration
        """
        section_map = {
            "device": self._device_settings,
            "storage": self._storage_settings,
            "display": self._display_settings,
            "logging": self._logging_settings,
        }

        if section not in section_map:
            raise ConfigurationError(f"Unknown configuration section: {section}")

        return section_map[section].copy()

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Export all configuration as a dictionary.

        Returns:
            Dictionary containing all configuration sections
        """
        return {
            "device": self._device_settings.copy(),
            "storage": self._storage_settings.copy(),
            "display": self._display_settings.copy(),
            "logging": self._logging_settings.copy(),
        }

    @property
    def device(self) -> Dict[str, Any]:
        """Device configuration settings."""
        return self._device_settings.copy()

    @property
    def storage(self) -> Dict[str, Any]:
        """Storage configuration settings."""
        return self._storage_settings.copy()

    @property
    def display(self) -> Dict[str, Any]:
        """Display configuration settings."""
        return self._display_settings.copy()

    @property
    def logging(self) -> Dict[str, Any]:
        """Logging configuration settings."""
        return self._logging_settings.copy()


# Global configuration instance
config = Config()

# Convenience constants for backwards compatibility and easy access
# Device Settings
DEFAULT_DEVICE_ID = config.device.get("default_device_id")
DEFAULT_PRODUCT_KEY = config.device.get("default_product_key")
CONNECTION_TIMEOUT = config.device["connection_timeout"]
RECONNECT_ATTEMPTS = config.device["reconnect_attempts"]
AUTO_CONNECT_ON_START = config.device["auto_connect_on_start"]

# Storage Settings
DATA_DIR = config.storage["data_dir"]
BUFFER_SIZE_MINUTES = config.storage["buffer_size_minutes"]
AUTO_SAVE_INTERVAL = config.storage["auto_save_interval"]
FILE_ROTATION_HOURS = config.storage["file_rotation_hours"]
COMPRESSION = config.storage["compression"]
COMPRESSION_LEVEL = config.storage["compression_level"]

# Display Settings
DEFAULT_DISPLAY_WINDOW = config.display["default_display_window"]
MAX_DISPLAY_POINTS = config.display["max_display_points"]
UPDATE_INTERVALS = config.display["update_intervals"]

# Logging Settings
LOG_LEVEL = config.logging["log_level"]
LOG_FILE = config.logging["log_file"]


def setup_logging() -> None:
    """Setup logging configuration based on config settings."""
    log_config = config.logging

    # Create log directory
    log_dir = log_config["log_dir"]
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure logging
    log_file_path = log_dir / log_config["log_file"]

    handlers = []

    # File handler
    if log_config["log_rotation"]:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=log_config["max_log_size_mb"] * 1024 * 1024,
            backupCount=log_config["backup_count"]
        )
    else:
        file_handler = logging.FileHandler(log_file_path)

    file_handler.setLevel(log_config["log_level"])
    file_handler.setFormatter(logging.Formatter(
        log_config["log_format"],
        datefmt=log_config["date_format"]
    ))
    handlers.append(file_handler)

    # Console handler
    if log_config["console_logging"]:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_config["log_level"])
        console_handler.setFormatter(logging.Formatter(
            log_config["log_format"],
            datefmt=log_config["date_format"]
        ))
        handlers.append(console_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_config["log_level"],
        handlers=handlers,
        force=True
    )

    # Set specific logger levels for debug mode
    if log_config["debug_mode"]:
        logging.getLogger("frenz").setLevel(logging.DEBUG)
        logging.getLogger("h5py").setLevel(logging.INFO)  # Reduce h5py noise


def initialize_config(env_file: Optional[Union[str, Path]] = None) -> Config:
    """
    Initialize configuration and create necessary directories.

    Args:
        env_file: Path to environment file

    Returns:
        Configured Config instance
    """
    global config
    config = Config(env_file=env_file)
    config.create_directories()
    setup_logging()
    return config


# Initialize on import
config.create_directories()