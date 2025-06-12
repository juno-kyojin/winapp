#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core module for Test Case Manager v2.0

This module contains the core functionality, configuration management,
constants, and custom exceptions for the application.
"""

from .config import AppConfig, load_config, save_config
from .constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_SSH_PORT,
    MAX_RETRY_ATTEMPTS,
    TEMPLATE_FILE_EXTENSION,
    LOG_FORMAT,
    DATABASE_NAME
)
from .exceptions import (
    TestCaseManagerError,
    TemplateError,
    NetworkError,
    DatabaseError
)

__all__ = [
    # Configuration
    "AppConfig",
    "load_config", 
    "save_config",
    
    # Constants
    "APP_NAME",
    "APP_VERSION",
    "DEFAULT_SSH_PORT",
    "MAX_RETRY_ATTEMPTS", 
    "TEMPLATE_FILE_EXTENSION",
    "LOG_FORMAT",
    "DATABASE_NAME",
    
    # Exceptions
    "TestCaseManagerError",
    "TemplateError",
    "NetworkError", 
    "DatabaseError"
]