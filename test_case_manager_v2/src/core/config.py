#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration management for Test Case Manager v2.0

This module handles application configuration loading, saving, and validation.
It provides a centralized configuration system with default values and
user customization support.

Author: juno-kyojin
Created: 2025-06-12
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from .constants import (
    CONFIG_DIR, 
    DEFAULT_SSH_PORT,
    DEFAULT_REMOTE_CONFIG_PATH,
    DEFAULT_REMOTE_RESULT_PATH,
    CONNECTION_TIMEOUT,
    TEST_TIMEOUT_DEFAULT
)
from .exceptions import ConfigurationError, FileOperationError


@dataclass
class NetworkConfig:
    """Network connection configuration."""
    
    ssh_host: str = "192.168.88.1"
    ssh_port: int = DEFAULT_SSH_PORT
    ssh_username: str = "root"
    ssh_password: str = ""
    connection_timeout: int = CONNECTION_TIMEOUT
    remote_config_path: str = DEFAULT_REMOTE_CONFIG_PATH
    remote_result_path: str = DEFAULT_REMOTE_RESULT_PATH
    middleware_url: str = "http://192.168.88.10:5000"


@dataclass  
class TestConfig:
    """Test execution configuration."""
    
    default_timeout: int = TEST_TIMEOUT_DEFAULT
    max_concurrent_tests: int = 1
    auto_cleanup: bool = True
    cleanup_interval_hours: int = 24
    retry_attempts: int = 3
    retry_delay: int = 5


@dataclass
class GUIConfig:
    """GUI appearance and behavior configuration."""
    
    window_width: int = 1200
    window_height: int = 800
    auto_save_settings: bool = True
    log_level: str = "INFO"
    theme: str = "default"
    font_family: str = "Segoe UI"
    font_size: int = 9


@dataclass
class AppConfig:
    """Main application configuration."""
    
    network: NetworkConfig
    test: TestConfig
    gui: GUIConfig
    
    def __init__(self) -> None:
        """Initialize with default values."""
        self.network = NetworkConfig()
        self.test = TestConfig()
        self.gui = GUIConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "network": asdict(self.network),
            "test": asdict(self.test),
            "gui": asdict(self.gui)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create configuration from dictionary."""
        config = cls()
        
        if "network" in data:
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


class ConfigManager:
    """Manages application configuration loading and saving."""
    
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
        """Ensure configuration directory exists."""
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
            raise ConfigurationError(f"Invalid JSON in config file: {e}")
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
_config_manager = ConfigManager()
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
    return _current_config


def save_config(config: AppConfig) -> None:
    """
    Save application configuration.
    
    Args:
        config: Configuration to save
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