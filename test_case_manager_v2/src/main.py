#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for Test Case Manager v2.0

This module provides the main application entry point and handles
application initialization, configuration loading, and GUI startup.

Author: juno-kyojin
Created: 2025-06-12
"""

import sys
import logging
import os
from pathlib import Path
from typing import Optional

# Add src directory to Python path for imports
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

# Now import modules
from core.config import load_config, AppConfig
from core.exceptions import TestCaseManagerError, ConfigurationError
from utils.logger import setup_logging
from gui.main_window import MainWindow


def initialize_application() -> AppConfig:
    """
    Initialize the application.
    
    Returns:
        Loaded application configuration
        
    Raises:
        ConfigurationError: If configuration is invalid
        TestCaseManagerError: If initialization fails
    """
    try:
        # Load configuration
        config = load_config()
        
        # Setup logging
        setup_logging(
            log_level=config.gui.log_level,
            log_to_file=True,
            log_to_console=True
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Test Case Manager v2.0 starting up...")
        logger.info(f"Configuration loaded successfully")
        
        return config
        
    except Exception as e:
        # Fallback logging to console if setup failed
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Failed to initialize application: {e}")
        raise TestCaseManagerError(f"Application initialization failed: {e}")


def main() -> int:
    """
    Main application entry point.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Initialize application
        config = initialize_application()
        logger = logging.getLogger(__name__)
        
        # Start GUI
        logger.info("Starting GUI...")
        app = MainWindow(config)
        
        # Run application
        logger.info("Application ready")
        app.run()
        
        logger.info("Application shutdown complete")
        return 0
        
    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
        return 1
        
    except TestCaseManagerError as e:
        logging.error(f"Application error: {e}")
        return 2
        
    except Exception as e:
        logging.critical(f"Unexpected error: {e}", exc_info=True)
        return 3


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run application
    exit_code = main()
    sys.exit(exit_code)