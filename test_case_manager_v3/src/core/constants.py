#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Constants for Test Case Manager v1.0

This module defines all application-wide constants including default values,
file paths, network settings, and configuration parameters.

Author: juno-kyojin
Created: 2025-06-12
"""

import os
from pathlib import Path
from typing import Dict, List, Final, Set, Tuple, Union

# ------------------------------------------------------------------
# Application Information
# ------------------------------------------------------------------
APP_NAME: Final[str] = "Test Case Manager"
APP_VERSION: Final[str] = "1.0.0"
APP_AUTHOR: Final[str] = "juno-kyojin"

# ------------------------------------------------------------------
# File and Directory Constants
# ------------------------------------------------------------------
TEMPLATE_FILE_EXTENSION: Final[str] = ".json"
CONFIG_FILE_EXTENSION: Final[str] = ".json"
LOG_FILE_EXTENSION: Final[str] = ".log"
DATABASE_FILE_EXTENSION: Final[str] = ".db"

# Base Directories - Handle both development and executable environments
def _get_base_dir() -> Path:
    """
    Get the base directory for the application.

    When running from source: returns project root directory
    When running from executable: returns directory containing the .exe file
    """
    import sys

    if getattr(sys, 'frozen', False):
        # Running from PyInstaller executable
        # sys.executable points to the .exe file
        return Path(sys.executable).parent
    else:
        # Running from source code
        return Path(__file__).parent.parent.parent

BASE_DIR: Final[Path] = _get_base_dir()
DATA_DIR: Final[Path] = BASE_DIR / "data"
TEMPLATE_DIR: Final[Path] = DATA_DIR / "templates"
CONFIG_DIR: Final[Path] = DATA_DIR / "config"
DATABASE_DIR: Final[Path] = DATA_DIR / "database"
LOG_DIR: Final[Path] = DATA_DIR / "logs"
TEMP_DIR: Final[Path] = DATA_DIR / "temp"

# File Size Limits (in bytes)
MAX_TEMPLATE_FILE_SIZE: Final[int] = 1024 * 1024  # 1MB
MAX_LOG_FILE_SIZE: Final[int] = 10 * 1024 * 1024  # 10MB
MAX_RESULT_FILE_SIZE: Final[int] = 5 * 1024 * 1024  # 5MB

# ------------------------------------------------------------------
# Database Constants
# ------------------------------------------------------------------
DATABASE_NAME: Final[str] = "test_manager.db"
DATABASE_PATH: Final[Path] = DATABASE_DIR / DATABASE_NAME

# ------------------------------------------------------------------
# Network Constants
# ------------------------------------------------------------------

# Connection Types
CONNECTION_TYPE_HTTP: Final[str] = "http"     # Sử dụng HTTP API only

# HTTP Client-Server Constants
DEFAULT_HTTP_API_PORT: Final[int] = 6970      # Port mặc định cho rnd_autotest server
HTTP_CONNECT_TIMEOUT: Final[int] = 5          # Thời gian timeout khi kết nối HTTP (giây)
HTTP_READ_TIMEOUT: Final[int] = 40            # Thời gian timeout khi đọc response HTTP (giây)
HTTP_API_VERSION: Final[str] = "v1"           # API version
DEFAULT_HTTP_ENDPOINT: Final[str] = "/api"    # Endpoint mặc định
HTTP_RETRY_ATTEMPTS: Final[int] = 2           # Số lần thử lại kết nối HTTP
HTTP_RETRY_DELAY: Final[int] = 2              # Thời gian giữa các lần thử lại (giây)

# HTTP Status Codes
HTTP_STATUS_SUCCESS: Final[int] = 200
HTTP_STATUS_BAD_REQUEST: Final[int] = 400
HTTP_STATUS_UNAUTHORIZED: Final[int] = 401
HTTP_STATUS_NOT_FOUND: Final[int] = 404
HTTP_STATUS_TIMEOUT: Final[int] = 408
HTTP_STATUS_SERVER_ERROR: Final[int] = 500

# Port defaults
DEFAULT_HTTP_PORT: Final[int] = 80
DEFAULT_HTTPS_PORT: Final[int] = 443
DEFAULT_MIDDLEWARE_PORT: Final[int] = 5000

# Connection parameters
MAX_RETRY_ATTEMPTS: Final[int] = 3
CONNECTION_TIMEOUT: Final[int] = 15
COMMAND_TIMEOUT: Final[int] = 30
NETWORK_CHECK_INTERVAL: Final[int] = 5

# ------------------------------------------------------------------
# Template Configuration
# ------------------------------------------------------------------

# Available template categories
TEMPLATE_CATEGORIES: Final[List[str]] = [
    "wan",
    "lan", 
    "network",
    "security",
    "system",
    "wireless"
]

# Parameter Types
PARAM_TYPE_STRING: Final[str] = "string"
PARAM_TYPE_INTEGER: Final[str] = "integer"
PARAM_TYPE_FLOAT: Final[str] = "float"
PARAM_TYPE_BOOLEAN: Final[str] = "boolean"
PARAM_TYPE_ENUM: Final[str] = "enum"
PARAM_TYPE_ARRAY: Final[str] = "array"
PARAM_TYPE_OBJECT: Final[str] = "object"

# Parameter type mapping for validation
PARAM_TYPES: Final[Dict[str, str]] = {
    "string": "str",
    "integer": "int",
    "float": "float",
    "boolean": "bool",
    "enum": "str", 
    "array": "list",
    "object": "dict"
}

# ------------------------------------------------------------------
# GUI Constants
# ------------------------------------------------------------------
WINDOW_MIN_WIDTH: Final[int] = 1000
WINDOW_MIN_HEIGHT: Final[int] = 700
WINDOW_DEFAULT_WIDTH: Final[int] = 1400
WINDOW_DEFAULT_HEIGHT: Final[int] = 900

# ------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------
LOG_FORMAT: Final[str] = "[%(asctime)s] %(levelname)s - %(name)s: %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL_DEBUG: Final[str] = "DEBUG"
LOG_LEVEL_INFO: Final[str] = "INFO"
LOG_LEVEL_WARNING: Final[str] = "WARNING"
LOG_LEVEL_ERROR: Final[str] = "ERROR"
LOG_LEVEL_CRITICAL: Final[str] = "CRITICAL"

# All valid log levels for validation
VALID_LOG_LEVELS: Final[Set[str]] = {
    LOG_LEVEL_DEBUG, 
    LOG_LEVEL_INFO, 
    LOG_LEVEL_WARNING, 
    LOG_LEVEL_ERROR, 
    LOG_LEVEL_CRITICAL
}

# ------------------------------------------------------------------
# Test Execution Constants
# ------------------------------------------------------------------
TEST_QUEUE_MAX_SIZE: Final[int] = 100
TEST_TIMEOUT_DEFAULT: Final[int] = 120
TEST_TIMEOUT_NETWORK: Final[int] = 300
RESULT_CHECK_INTERVAL: Final[int] = 3
CLEANUP_INTERVAL_HOURS: Final[int] = 24

# ------------------------------------------------------------------
# Validation Constants
# ------------------------------------------------------------------
MAX_STRING_LENGTH: Final[int] = 255
MAX_INTEGER_VALUE: Final[int] = 2147483647
MIN_INTEGER_VALUE: Final[int] = -2147483648
MAX_FLOAT_VALUE: Final[float] = 1e308
MIN_FLOAT_VALUE: Final[float] = -1e308

# ------------------------------------------------------------------
# Status Constants
# ------------------------------------------------------------------
STATUS_READY: Final[str] = "ready"
STATUS_RUNNING: Final[str] = "running"
STATUS_SUCCESS: Final[str] = "success"
STATUS_FAILED: Final[str] = "failed"
STATUS_TIMEOUT: Final[str] = "timeout"
STATUS_CANCELLED: Final[str] = "cancelled"

# All valid statuses for validation
VALID_STATUSES: Final[Set[str]] = {
    STATUS_READY,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_TIMEOUT,
    STATUS_CANCELLED
}

# ------------------------------------------------------------------
# Result Types
# ------------------------------------------------------------------
RESULT_SOURCE_HTTP: Final[str] = "http"
RESULT_SOURCE_MIDDLEWARE: Final[str] = "middleware"
RESULT_SOURCE_LOCAL: Final[str] = "local"

# ------------------------------------------------------------------
# Error Message Templates
# ------------------------------------------------------------------
ERROR_TEMPLATE_NOT_FOUND: Final[str] = "Template not found: {template_id}"
ERROR_INVALID_PARAMETER: Final[str] = "Invalid parameter: {param_name}"
ERROR_CONNECTION_FAILED: Final[str] = "Connection failed: {host}:{port}"
ERROR_DATABASE_ERROR: Final[str] = "Database operation failed: {operation}"
ERROR_FILE_NOT_FOUND: Final[str] = "File not found: {file_path}"

# New directory paths
TEMPLATES_DIR: Final[Path] = DATA_DIR / "templates"
BACKUP_DIR: Final[Path] = DATA_DIR / "backup"
RESULTS_DIR: Final[Path] = TEMP_DIR / "results"

# Default configuration
DEFAULT_CONFIG: Final[Dict[str, Dict[str, Union[int, str, bool]]]] = {
    "connection": {
        "http_port": 6969,
        "connect_timeout": 5,
        "read_timeout": 40
    },
    "gui": {
        "theme": "default",
        "window_width": 1024,
        "window_height": 768,
        "font_size": 10
    },
    "logging": {
        "level": "INFO",
        "max_size_mb": 10,
        "backup_count": 3
    },
    "execution": {
        "retry_count": 2,
        "retry_delay": 5,
        "verify_network": True
    },
    "paths": {
        "templates_dir": str(TEMPLATES_DIR),
        "results_dir": str(RESULTS_DIR),
        "logs_dir": str(LOG_DIR),
        "backup_dir": str(BACKUP_DIR)
    }
}

# Create directories if they don't exist
for directory in [DATA_DIR, CONFIG_DIR, TEMPLATES_DIR, BACKUP_DIR, TEMP_DIR, LOG_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True) 