#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logging utilities for Test Case Manager v2.0

This module provides centralized logging configuration and utilities
for consistent logging throughout the application.

Author: juno-kyojin
Created: 2025-06-12
"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Optional

# Define constants locally to avoid circular imports
BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / "data" / "logs"
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class ColoredConsoleHandler(logging.StreamHandler):
    """Console handler with colored output for different log levels."""
    
    # Color codes for different log levels
    COLORS = {
        logging.DEBUG: '\033[36m',    # Cyan
        logging.INFO: '\033[32m',     # Green  
        logging.WARNING: '\033[33m',  # Yellow
        logging.ERROR: '\033[31m',    # Red
        logging.CRITICAL: '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Get the original formatted message
        msg = super().format(record)
        
        # Add color if terminal supports it
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(record.levelno, '')
            if color:
                msg = f"{color}{msg}{self.RESET}"
        
        return msg


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_file_name: str = "app.log"
) -> logging.Logger:
    """
    Setup centralized logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        log_file_name: Name of the log file
        
    Returns:
        Configured root logger
        
    Raises:
        ValueError: If log_level is invalid
        OSError: If log directory cannot be created
    """
    # Validate log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add file handler if requested
    if log_to_file:
        log_file_path = LOG_DIR / log_file_name
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=MAX_LOG_FILE_SIZE,
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(numeric_level)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}")
    
    # Add console handler if requested
    if log_to_console:
        console_handler = ColoredConsoleHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)
    
    # Log initial message
    root_logger.info(f"Logging initialized - Level: {log_level}")
    
    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (defaults to caller's module name)
        
    Returns:
        Logger instance
    """
    if name is None:
        # Get caller's module name
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get('__name__', 'unknown')
    
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capability to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")