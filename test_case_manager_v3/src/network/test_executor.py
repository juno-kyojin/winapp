#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Executor for Test Case Manager v3.0

This module provides specialized test execution functionality with
enhanced error handling and retry mechanisms, particularly for dealing
with the "empty file" issue on the server.

Author: juno-kyojin
Created: 2025-07-01
"""

import json
import logging
import time
import uuid
import socket
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Union, cast

from .connection_manager import ConnectionManager
from ..utils.logger import get_logger
from ..utils.file_lock_utils import read_file_with_lock, write_file_with_lock

class TestExecutor:
    """
    Test executor with enhanced error handling.
    
    This class provides specialized test execution functionality with
    improved error handling and retry mechanisms for common server issues.
    """
    
    def __init__(self, connection_manager: Optional[ConnectionManager] = None) -> None:
        """
        Initialize the test executor.
        
        Args:
            connection_manager: Connection manager to use for test execution.
                              If None, a new ConnectionManager will be created.
        """
        self.logger = get_logger(__name__)
        
        # Create connection manager if not provided
        if connection_manager is None:
            self.connection_manager = ConnectionManager()
        else:
            self.connection_manager = connection_manager
        
        # Default retry parameters
        self.max_retries = 5
        self.base_retry_delay = 3
        self.empty_file_max_retries = 8
        
        # Track last execution stats
        self.last_test_time: Optional[float] = None
        self.last_test_duration: Optional[float] = None
        self.last_transaction_id: Optional[str] = None
        self.last_test_type: Optional[str] = None
        self.last_test_affected_network: bool = False
        self.error_history: List[str] = []
        self.consecutive_errors = 0
        self.execution_count = 0
        self.successful_count = 0
        
    def connect(self, host: str, **kwargs) -> bool:
        """
        Connect to a device.
        
        Args:
            host: Host to connect to
            **kwargs: Additional connection parameters
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            return self.connection_manager.connect(host, **kwargs)
        except Exception as e:
            self.logger.error(f"Error connecting to device: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the current device."""
        try:
            self.connection_manager.disconnect()
        except Exception as e:
            self.logger.error(f"Error disconnecting from device: {e}")
            
    def is_connected(self) -> bool:
        """
        Check if connected to a device.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connection_manager.is_connected()
        
    def execute_test(self, test_data: Dict[str, Any], 
                   affects_network: bool = False) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Execute a test case on the connected device.
        
        Args:
            test_data: Test data to send
            affects_network: Whether the test affects network connectivity
            
        Returns:
            Tuple containing (success flag, response data, error message)
        """
        if not self.is_connected():
            self.logger.error("Not connected to device")
            return False, None, "Not connected to device"
            
        # Validate test data
        if not test_data:
            self.logger.error("Test data is empty")
            return False, None, "Test data is empty"
            
        try:
            self.logger.info("Executing test case")
            self.logger.debug(f"Test data: {json.dumps(test_data, indent=2)}")
            
            # Simple server preparation
            self._prepare_server_for_test()
                
            # Add transaction ID if not present
            if "metadata" not in test_data:
                test_data["metadata"] = {}
                
            if "transaction_id" not in test_data["metadata"]:
                # Generate unique transaction ID
                transaction_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
                test_data["metadata"]["transaction_id"] = transaction_id
                
            # Store transaction ID for checking result later
            transaction_id = test_data["metadata"]["transaction_id"]

            # Send test case to device (simplified - no complex retry logic)
            success, response, error = self.connection_manager.send_test(
                test_data,
                affects_network=affects_network
            )

            return success, response, error
            
        except Exception as e:
            error_msg = f"Error executing test: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg
    

    
    def _is_important_test(self, test_data: Dict[str, Any]) -> bool:
        """
        Check if test is important (affects network or system configuration).
        
        Args:
            test_data: Test data to check
            
        Returns:
            True if test is important, False otherwise
        """
        if "test_cases" in test_data and len(test_data["test_cases"]) > 0:
            for test_case in test_data["test_cases"]:
                service = test_case.get("service", "").lower()
                action = test_case.get("action", "").lower()
                
                # Network-affecting services
                if service in ["wan", "lan", "wireless", "firewall", "network"]:
                    return True
                    
                # System-affecting actions
                if action in ["create", "delete", "edit", "update", "restart", "reboot"]:
                    return True
        
        return False
    
    def _prepare_server_for_test(self) -> None:
        """
        Simple server preparation for test execution.
        """
        self.logger.info("Preparing server for test...")

        # Basic ping verification
        self._ping_server()

        # Short delay
        time.sleep(1)
    

    
    def _verify_server_with_multiple_pings(self, extra_delay: bool = False) -> bool:
        """
        Verify server is ready by sending multiple ping requests with increasing delays.
        
        Args:
            extra_delay: Whether to add extra delay between pings
            
        Returns:
            True if server is responsive, False otherwise
        """
        self.logger.info("Performing multiple ping verification...")
        success_count = 0
        
        # Try multiple pings with increasing delays
        for i in range(4):
            try:
                # Check if the HTTP client is initialized
                if not hasattr(self.connection_manager, 'http_client') or not self.connection_manager.http_client:
                    self.logger.warning("HTTP client not initialized, skipping ping verification")
                    return False
                    
                if not hasattr(self.connection_manager.http_client, 'url'):
                    self.logger.warning("HTTP client URL not set, skipping ping verification")
                    return False
                    
                response = requests.get(
                    f"{self.connection_manager.http_client.url}/ping",
                    timeout=5  # Use default timeout if http_client doesn't have connect_timeout
                )
                
                if response.status_code == 200:
                    success_count += 1
                    self.logger.debug(f"Ping {i+1} successful")
                else:
                    self.logger.debug(f"Ping {i+1} returned status {response.status_code}")
                
                # Increasing delay between pings
                delay = (i + 1) * 2 if extra_delay else (i + 1)
                time.sleep(delay)
            except Exception as e:
                self.logger.debug(f"Ping {i+1} failed: {e}")
                delay = (i + 2) * 2 if extra_delay else (i + 2)
                time.sleep(delay)
        
        if success_count >= 3:
            self.logger.info("Server verified responsive")
            return True
        else:
            self.logger.warning(f"Server responsiveness check: {success_count}/4 successful")
            # Wait longer if server doesn't seem fully responsive
            time.sleep(5)
            return False
    
    def _ping_server(self) -> bool:
        """
        Send a simple ping request to the server.
        
        Returns:
            True if ping successful, False otherwise
        """
        try:
            # Check if the HTTP client is initialized
            if not hasattr(self.connection_manager, 'http_client') or not self.connection_manager.http_client:
                self.logger.warning("HTTP client not initialized, skipping ping")
                return False
                
            if not hasattr(self.connection_manager.http_client, 'url'):
                self.logger.warning("HTTP client URL not set, skipping ping")
                return False
                
            response = requests.get(
                f"{self.connection_manager.http_client.url}/ping",
                timeout=5  # Use default timeout if http_client doesn't have connect_timeout
            )
            
            return response.status_code == 200
        except Exception as e:
            self.logger.debug(f"Ping failed: {e}")
            return False
    
    def _send_dummy_request(self) -> None:
        """
        Send a dummy request to clear any pending operations on the server.
        """
        try:
            # Check if the HTTP client is initialized
            if not hasattr(self.connection_manager, 'http_client') or not self.connection_manager.http_client:
                self.logger.warning("HTTP client not initialized, skipping dummy request")
                return
                
            if not hasattr(self.connection_manager.http_client, 'url'):
                self.logger.warning("HTTP client URL not set, skipping dummy request")
                return
                
            # Check if URL is None before using it
            if self.connection_manager.http_client.url is None:
                self.logger.warning("HTTP client URL is None, skipping dummy request")
                return
                
            dummy_data = {
                "test_cases": [
                    {
                        "service": "dummy",
                        "action": "prepare",
                        "params": {}
                    }
                ],
                "metadata": {
                    "transaction_id": f"dummy-{str(uuid.uuid4())[:8]}",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "purpose": "prepare_server"
                }
            }
            
            self.logger.info("Sending dummy request to prepare server...")
            
            try:
                requests.post(
                    url=self.connection_manager.http_client.url,
                    json=dummy_data,
                    headers={"Content-Type": "application/json"},
                    timeout=2
                )
            except requests.exceptions.Timeout:
                # Timeout is expected and not a problem
                self.logger.debug("Dummy request timed out as expected")
            except Exception as e:
                self.logger.debug(f"Dummy request exception (can be ignored): {e}")
            
            # Wait to ensure server has processed the dummy request
            time.sleep(2)
        except Exception as e:
            self.logger.debug(f"Error sending dummy request: {e}")
    

