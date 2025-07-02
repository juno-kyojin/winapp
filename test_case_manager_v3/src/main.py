#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Case Manager v3.0

Main entry point for the application.

Author: juno-kyojin
Created: 2025-06-12
"""

import os
import sys
import logging
import argparse
from typing import List, Optional

from src.core.config import AppConfig
from src.core.constants import APP_NAME, APP_VERSION

def setup_logger(level: int = logging.INFO, log_file: Optional[str] = None, max_size_mb: int = 10) -> None:
    """
    Setup logging configuration.
    """
    # Configure root logger
    root_logger = logging.getLogger()

    # Clear existing handlers to prevent duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()

    root_logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler (if log_file is provided)
    if log_file:
        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_format)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}", file=sys.stderr)

def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION}")
    
    parser.add_argument("--config", help="Path to configuration file", default=None)
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Set logging level"
    )
    
    return parser.parse_args(args)

def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the application.
    """
    # Parse command line arguments
    parsed_args = parse_arguments(args)
    
    try:
        # Load configuration
        config = AppConfig(parsed_args.config)
        
        # Setup logging
        log_level = logging.DEBUG if parsed_args.debug else logging.INFO
        if parsed_args.log_level:
            log_level = getattr(logging, parsed_args.log_level)
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(__file__), "..", "data", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Setup logging
        setup_logger(
            level=log_level,
            log_file=os.path.join(logs_dir, "app.log"),
            max_size_mb=10
        )
        
        # Get logger
        logger = logging.getLogger(__name__)
        logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
        
        # Import MainWindow only after configuring logging to avoid circular imports
        from src.gui.main_window import MainWindow
        
        # Create and run main window
        app = MainWindow(config)
        app.run()  # Assuming run is the correct method, based on API
        
        logger.info(f"Exiting {APP_NAME} v{APP_VERSION}")
        return 0
        
    except Exception as e:
        # If logger is not yet set up, print to stderr
        print(f"Error starting application: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
