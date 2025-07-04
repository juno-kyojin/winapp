#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Case Manager v1.0

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
from src.core.constants import APP_NAME, APP_VERSION, LOG_DIR
from src.utils.logger import setup_logging

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
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Setup centralized logging with GUI support
        setup_logging(
            log_level=logging.getLevelName(log_level),
            log_to_file=True,
            log_to_console=True,
            log_to_gui=True,
            log_file_name=str(LOG_DIR / "app.log")
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
