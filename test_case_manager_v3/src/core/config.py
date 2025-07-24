#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration management for Test Case Manager v1.0

This module handles application configuration loading, saving, and validation.
It provides a centralized configuration system with default values and
user customization support.

Author: juno-kyojin
Created: 2025-06-12
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, cast, TypeVar, Type
from dataclasses import dataclass, asdict, field

from .constants import (
    CONFIG_DIR, 
    DEFAULT_SSH_PORT,
    DEFAULT_REMOTE_CONFIG_PATH,
    DEFAULT_REMOTE_RESULT_PATH,
    CONNECTION_TIMEOUT,
    TEST_TIMEOUT_DEFAULT
)
from .exceptions import ConfigurationError, FileOperationError

# Type variable for dataclass return types
T = TypeVar('T', bound='AppConfig')


@dataclass
class NetworkConfig:
    """
    Network connection configuration.
    
    Attributes:
        connection_type: Type of connection (http/ssh)
        ssh_host: SSH server hostname or IP
        ssh_port: SSH server port
        ssh_username: SSH username
        ssh_password: SSH password
        connection_timeout: Connection timeout in seconds
        remote_config_path: Path to config files on remote server
        remote_result_path: Path to result files on remote server
        http_host: HTTP server hostname or IP
        http_port: HTTP server port
        http_connect_timeout: HTTP connection timeout in seconds
        http_read_timeout: HTTP read timeout in seconds
        middleware_url: URL to middleware server
    """
    
    # Connection type - HTTP or SSH
    connection_type: str = "http"  # Default to HTTP
    
    # SSH configuration
    ssh_host: str = "192.168.88.1"
    ssh_port: int = DEFAULT_SSH_PORT
    ssh_username: str = "root"
    ssh_password: str = ""
    connection_timeout: int = CONNECTION_TIMEOUT
    remote_config_path: str = DEFAULT_REMOTE_CONFIG_PATH
    remote_result_path: str = DEFAULT_REMOTE_RESULT_PATH
    
    # HTTP configuration
    http_host: str = "192.168.88.1"  # Default to same IP as SSH
    http_port: int = 6970            # Default HTTP port for rnd_autotest
    http_connect_timeout: int = 5    # Default connect timeout in seconds
    http_read_timeout: int = 40      # Default read timeout in seconds
    middleware_url: str = "http://192.168.88.10:5000"  # Existing setting


@dataclass
class TestConfig:
    """
    Test execution configuration.
    
    Attributes:
        default_timeout: Default timeout for test execution in seconds
        max_concurrent_tests: Maximum number of tests that can run concurrently
        auto_cleanup: Whether to automatically clean up test artifacts
        cleanup_interval_hours: Interval between cleanup runs in hours
        retry_attempts: Number of retry attempts for failed tests
        retry_delay: Delay between retry attempts in seconds
    """
    
    default_timeout: int = TEST_TIMEOUT_DEFAULT
    max_concurrent_tests: int = 1
    auto_cleanup: bool = True
    cleanup_interval_hours: int = 24
    retry_attempts: int = 3
    retry_delay: int = 5


@dataclass
class GUIConfig:
    """
    GUI appearance and behavior configuration.
    
    Attributes:
        window_width: Width of the main window in pixels
        window_height: Height of the main window in pixels
        auto_save_settings: Whether to automatically save settings on exit
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        theme: GUI theme name
        font_family: Font family name
        font_size: Font size in points
    """
    
    window_width: int = 1200
    window_height: int = 800
    auto_save_settings: bool = True
    log_level: str = "INFO"
    theme: str = "default"
    font_family: str = "Segoe UI"
    font_size: int = 9


@dataclass
class AppConfig:
    """
    Main application configuration.
    
    This class combines all configuration sections into a single entity.
    It also provides methods for validation and conversion between
    Python objects and dictionaries for serialization.
    
    Attributes:
        network: Network configuration
        test: Test execution configuration
        gui: GUI configuration
    """
    
    network: NetworkConfig = field(default_factory=NetworkConfig)
    test: TestConfig = field(default_factory=TestConfig)
    gui: GUIConfig = field(default_factory=GUIConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "network": asdict(self.network),
            "test": asdict(self.test),
            "gui": asdict(self.gui)
        }
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create configuration from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            
        Returns:
            AppConfig instance initialized with values from data
        """
        config = cls()
        
        if "network" in data:
            # Create new instance since NetworkConfig is immutable
            config.network = NetworkConfig(**data["network"])
        if "test" in data:
            config.test = TestConfig(**data["test"])
        if "gui" in data:
            config.gui = GUIConfig(**data["gui"])
            
        return config
    
    def validate(self) -> None:
        """
        Validate configuration values.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate network config
        if not self.network.ssh_host:
            raise ConfigurationError("SSH host cannot be empty")
        
        if not (1 <= self.network.ssh_port <= 65535):
            raise ConfigurationError("SSH port must be between 1 and 65535")
        
        if not self.network.ssh_username:
            raise ConfigurationError("SSH username cannot be empty")
        
        # Validate test config
        if self.test.default_timeout <= 0:
            raise ConfigurationError("Default timeout must be positive")
        
        if self.test.max_concurrent_tests <= 0:
            raise ConfigurationError("Max concurrent tests must be positive")
        
        # Validate GUI config
        if self.gui.window_width < 800:
            raise ConfigurationError("Window width must be at least 800 pixels")
        
        if self.gui.window_height < 600:
            raise ConfigurationError("Window height must be at least 600 pixels")
        
        # Validate log level
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.gui.log_level not in valid_log_levels:
            raise ConfigurationError(
                f"Invalid log level: {self.gui.log_level}. "
                f"Must be one of {', '.join(valid_log_levels)}"
            )


class ConfigManager:
    """
    Manages application configuration loading and saving.
    
    This class handles reading and writing configuration to disk,
    as well as ensuring the configuration directory exists.
    """
    
    def __init__(self, config_file: str = "app_config.json") -> None:
        """
        Initialize configuration manager.
        
        Args:
            config_file: Name of the configuration file
        """
        self.config_file = CONFIG_DIR / config_file
        self.logger = logging.getLogger(__name__)
        self._ensure_config_dir()
    
    def _ensure_config_dir(self) -> None:
        """
        Ensure configuration directory exists.
        
        Raises:
            FileOperationError: If directory cannot be created
        """
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise FileOperationError(
                f"Failed to create config directory: {e}",
                str(CONFIG_DIR),
                "mkdir"
            )
    
    def load_config(self) -> AppConfig:
        """
        Load configuration from file.
        
        Returns:
            Loaded configuration or default configuration if file doesn't exist
            
        Raises:
            ConfigurationError: If configuration file is corrupted
            FileOperationError: If file cannot be read
        """
        if not self.config_file.exists():
            self.logger.info("Config file not found, using defaults")
            return AppConfig()
        
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            config = AppConfig.from_dict(data)
            config.validate()
            
            self.logger.info("Configuration loaded successfully")
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in config file: {e}",
                config_key="file_format"
            )
        except OSError as e:
            raise FileOperationError(
                f"Failed to read config file: {e}",
                str(self.config_file),
                "read"
            )
    
    def save_config(self, config: AppConfig) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            
        Raises:
            ConfigurationError: If configuration is invalid
            FileOperationError: If file cannot be written
        """
        try:
            config.validate()
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info("Configuration saved successfully")
            
        except OSError as e:
            raise FileOperationError(
                f"Failed to write config file: {e}",
                str(self.config_file),
                "write"
            )


# Global configuration instance
_config_manager: ConfigManager = ConfigManager()
_current_config: Optional[AppConfig] = None


def load_config() -> AppConfig:
    """
    Load application configuration.
    
    Returns:
        Current application configuration
    """
    global _current_config
    if _current_config is None:
        _current_config = _config_manager.load_config()
    # Đảm bảo không trả về None
    assert _current_config is not None
    return _current_config


def save_config(config: AppConfig) -> None:
    """
    Save application configuration.
    
    Args:
        config: Configuration to save
        
    Raises:
        ConfigurationError: If configuration is invalid
        FileOperationError: If file cannot be written
    """
    global _current_config
    _config_manager.save_config(config)
    _current_config = config


def get_config() -> AppConfig:
    """
    Get current configuration, loading if necessary.
    
    Returns:
        Current application configuration
    """
    return load_config() 
