#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for real device communication in Test Case Manager v3.0

This script tests the communication with a real device using the Test Case Manager.
It sends a simple ping test to the device and verifies the response.

Author: juno-kyojin
Created: 2025-06-12
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now import from src
from src.network.test_executor import TestExecutor

def setup_logging():
    """Set up logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] %(levelname)s - %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger()
    logger.info("Logging initialized - Level: DEBUG")
    return logger

def main():
    """Main function to test communication with a real device"""
    logger = setup_logging()
    
    # Device connection parameters
    device_ip = "192.168.99.1"
    device_port = 6262
    
    logger.info(f"Testing communication with device at {device_ip}:{device_port}")
    
    # Create test executor
    executor = TestExecutor()
    
    # Connect to device
    logger.info("Connecting to device...")
    connected = executor.connect(device_ip, port=device_port)
    
    if not connected:
        logger.error("Failed to connect to device")
        return
        
    logger.info("Successfully connected to device")
    
    # Create test data
    test_data = {
        "test_cases": [
            {
                "service": "ping",
                "client_validation": True,
                "params": {
                    "host1": "google.com",
                    "host2": "youtube.com"
                }
            }
        ],
        "metadata": {
            "name": "Network Ping Test",
            "description": "Tests network connectivity by pinging a target",
            "version": "1.0.0",
            "tags": ["network", "connectivity", "ping"],
            "category": "network"
        }
    }
    
    # Send test to device
    logger.info("Sending test to device...")
    success, response, error = executor.execute_test(test_data)
    
    # Check result
    if success:
        logger.info("Test executed successfully!")
        logger.info(f"Response: {json.dumps(response, indent=2)}")
    else:
        logger.error(f"Test execution failed: {error}")
        
    # Disconnect from device
    executor.disconnect()

if __name__ == "__main__":
    main() 