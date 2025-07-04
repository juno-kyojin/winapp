#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Run script for Test Case Manager v1.0

This script is the entry point for the Test Case Manager application.
It sets up the Python path and launches the application.

Author: juno-kyojin
Created: 2025-06-12
"""

import os
import sys
import logging
from datetime import datetime

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now import from src
from src.main import main

if __name__ == "__main__":
    # Configure logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)
    
    # Start the application
    try:
        main()
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 