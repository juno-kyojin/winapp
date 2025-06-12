#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Constants for Test Case Manager v2.0

This module defines all application-wide constants including default values,
file paths, network settings, and configuration parameters.

Author: juno-kyojin
Created: 2025-06-12
"""

import os
from pathlib import Path

# Application Information
APP_NAME = "Test Case Manager"
APP_VERSION = "2.0.0"
APP_AUTHOR = "juno-kyojin"

# File and Directory Constants
TEMPLATE_FILE_EXTENSION = ".json"
CONFIG_FILE_EXTENSION = ".json"
LOG_FILE_EXTENSION = ".log"
DATABASE_FILE_EXTENSION = ".db"

# Default Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_DIR = DATA_DIR / "templates"
CONFIG_DIR = DATA_DIR / "config"
DATABASE_DIR = DATA_DIR / "database"
LOG_DIR = DATA_DIR / "logs"
TEMP_DIR = DATA_DIR / "temp"

# Database Constants
DATABASE_NAME = "test_manager.db"
DATABASE_PATH = DATABASE_DIR / DATABASE_NAME

# Network Constants
DEFAULT_SSH_PORT = 22
DEFAULT_HTTP_PORT = 80
DEFAULT_HTTPS_PORT = 443
DEFAULT_MIDDLEWARE_PORT = 5000
MAX_RETRY_ATTEMPTS = 3
CONNECTION_TIMEOUT = 15
COMMAND_TIMEOUT = 30
NETWORK_CHECK_INTERVAL = 5

# SSH Configuration
SSH_CONNECT_TIMEOUT = 15
SSH_BANNER_TIMEOUT = 10
SSH_AUTH_TIMEOUT = 10

# Template Categories
TEMPLATE_CATEGORIES = [
    "wan",
    "lan", 
    "network",
    "security",
    "system",
    "wireless"
]

# GUI Constants
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 600
WINDOW_DEFAULT_WIDTH = 1200
WINDOW_DEFAULT_HEIGHT = 800

# Logging Configuration
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

# Test Execution Constants
TEST_QUEUE_MAX_SIZE = 100
TEST_TIMEOUT_DEFAULT = 120
TEST_TIMEOUT_NETWORK = 300
RESULT_CHECK_INTERVAL = 3
CLEANUP_INTERVAL_HOURS = 24

# Parameter Types
PARAM_TYPE_STRING = "string"
PARAM_TYPE_INTEGER = "integer"
PARAM_TYPE_FLOAT = "float"
PARAM_TYPE_BOOLEAN = "boolean"
PARAM_TYPE_ENUM = "enum"
PARAM_TYPE_ARRAY = "array"
PARAM_TYPE_OBJECT = "object"

# Validation Constants
MAX_STRING_LENGTH = 255
MAX_INTEGER_VALUE = 2147483647
MIN_INTEGER_VALUE = -2147483648
MAX_FLOAT_VALUE = 1e308
MIN_FLOAT_VALUE = -1e308

# File Size Limits (in bytes)
MAX_TEMPLATE_FILE_SIZE = 1024 * 1024  # 1MB
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_RESULT_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Status Constants
STATUS_READY = "ready"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_TIMEOUT = "timeout"
STATUS_CANCELLED = "cancelled"

# Result Source Types
RESULT_SOURCE_SSH = "ssh"
RESULT_SOURCE_MIDDLEWARE = "middleware"
RESULT_SOURCE_LOCAL = "local"

# Default Remote Paths
DEFAULT_REMOTE_CONFIG_PATH = "/root/config"
DEFAULT_REMOTE_RESULT_PATH = "/root/result"
DEFAULT_REMOTE_SCRIPT_PATH = "/root/scripts"

# Error Messages
ERROR_TEMPLATE_NOT_FOUND = "Template not found: {template_id}"
ERROR_INVALID_PARAMETER = "Invalid parameter: {param_name}"
ERROR_CONNECTION_FAILED = "Connection failed: {host}:{port}"
ERROR_DATABASE_ERROR = "Database operation failed: {operation}"
ERROR_FILE_NOT_FOUND = "File not found: {file_path}"