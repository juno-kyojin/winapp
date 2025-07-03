#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Connection Manager for Test Case Manager v3.0

This module provides a unified interface for connecting to devices
via either SSH or HTTP, sending test commands, and retrieving results.

Author: juno-kyojin
Created: 2025-06-12
"""

import json
import logging
import os
import time
import uuid
import socket
import importlib
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from src.network.http_client import HTTPTestClient
# from src.network.ssh_connection import SSHConnection
from src.utils.file_utils import ensure_directory
from src.utils.file_lock_utils import read_file_with_lock, write_file_with_lock
from src.utils.logger import get_logger
from src.utils.error_types import ErrorType, should_retry_error, get_retry_reason

class ConnectionManager:
    """
    Unified connection manager for both SSH and HTTP connections.
    
    This class provides a common interface for connecting to devices
    via either SSH or HTTP, sending test commands, and retrieving results.
    It handles automatic switching between connection types and manages
    connection parameters.
    """
    
    # Connection types
    SSH_MODE = "ssh"
    HTTP_MODE = "http"
    
    def __init__(self) -> None:
        """
        Initialize connection manager.
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize connection components
        self.http_client: HTTPTestClient = HTTPTestClient()
        # self.ssh_client = SSHConnection()  # Hiện chưa có SSHConnection
        
        # Default to HTTP mode
        self._connection_type = self.HTTP_MODE
        
        # Connection status
        self._connected = False
        self._hostname: Optional[str] = None
        
        # Add timestamp for metadata
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.username = "juno-kyojin"
        
        # Test execution settings
        self.default_timeout = 60
        self.network_timeout = 500  # Longer timeout for network-affecting tests - increased to match client.py
        self.between_tests_delay = 2  # Seconds to wait between tests
        self.network_test_delay = 5  # Seconds to wait after network-affecting tests
        

            

            
        # Basic timeout settings
        self.default_timeout = 60
    
    def set_connection_type(self, conn_type: str) -> None:
        """
        Set the connection type to use.
        
        Args:
            conn_type: Connection type ('ssh' or 'http')
        """
        if conn_type.lower() not in [self.SSH_MODE, self.HTTP_MODE]:
            self.logger.error(f"Invalid connection type: {conn_type}")
            return
            
        self._connection_type = conn_type.lower()
        self.logger.info(f"Connection type set to {self._connection_type}")
        
        # Initialize SSH if needed
        if conn_type.lower() == self.SSH_MODE and self.ssh_connection is None:
            try:
                # Use importlib for dynamic import to avoid errors if module doesn't exist
                ssh_module = importlib.import_module('network.ssh_connection')
                SSHConnection = getattr(ssh_module, 'SSHConnection')
                self.ssh_connection = SSHConnection()
            except (ImportError, AttributeError) as e:
                self.logger.error(f"Could not load SSH module: {e}")
    
    def connect(self, hostname: str, **kwargs) -> bool:
        """
        Connect to remote host using selected connection type.
        
        Args:
            hostname: Target host name or IP address
            **kwargs: Additional connection parameters:
                - port: Port number (for HTTP)
                - username: SSH username
                - password: SSH password
                - config_path: Remote config path (for SSH)
                - result_path: Remote result path (for SSH)
                - timeout: Connection timeout
                - connect_timeout: HTTP connection timeout
                - read_timeout: HTTP read timeout
                
        Returns:
            True if connection successful, False otherwise
        """
        self._hostname = hostname
        
        if self._connection_type == self.SSH_MODE:
            # Lazy load SSH module
            if self.ssh_connection is None:
                try:
                    ssh_module = importlib.import_module('network.ssh_connection')
                    SSHConnection = getattr(ssh_module, 'SSHConnection')
                    self.ssh_connection = SSHConnection()
                except (ImportError, AttributeError) as e:
                    self.logger.error(f"Could not load SSH module: {e}")
                    return False
            
            # SSH connection requires more parameters
            self.username = kwargs.get('username')
            self.password = kwargs.get('password')
            self.config_path = kwargs.get('config_path')
            self.result_path = kwargs.get('result_path')
            
            return self.ssh_connection.connect(
                hostname=hostname,
                username=self.username,
                password=self.password,
                timeout=kwargs.get('timeout', 10)
            )
            
        else:  # HTTP mode
            self.port = kwargs.get('port', 6262)
            self.http_connect_timeout = kwargs.get('connect_timeout', 5)  # Default to 5s like client.py
            self.http_read_timeout = kwargs.get('read_timeout', 500)  # Default to 500s like client.py
            
            # Ensure port is an integer
            port = int(self.port) if self.port is not None else 6262
            
            return self.http_client.connect(
                host=hostname,
                port=port,
                connect_timeout=self.http_connect_timeout,
                read_timeout=self.http_read_timeout
            )
    
    def is_connected(self) -> bool:
        """
        Check if connected to remote host.
        
        Returns:
            True if connected, False otherwise
        """
        if self._connection_type == self.SSH_MODE:
            return self.ssh_connection is not None and self.ssh_connection.is_connected()
        else:
            return self.http_client.is_connected()
    
    def disconnect(self) -> None:
        """Disconnect from remote host."""
        if self._connection_type == self.SSH_MODE and self.ssh_connection is not None:
            self.ssh_connection.disconnect()
        else:
            self.http_client.disconnect()
        
    def send_test(self, test_data: Dict[str, Any],
                affects_network: bool = False) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Send test case to the device for execution.
        
        Args:
            test_data: Test case data to send
            test_file_path: Path to test case file (optional)
            affects_network: Whether the test affects network connectivity
            
        Returns:
            Tuple containing (success flag, response data, error message)
        """
        # Kiểm tra và đảm bảo kết nối trước khi gửi test
        if not self.ensure_connection_before_test():
            return False, None, "Failed to ensure connection to device"
            
        # Validate test data
        if not test_data:
            return False, None, "Test data is empty"
            
        try:
            self.logger.info("Sending test case to device")
            self.logger.debug(f"Test data: {json.dumps(test_data, indent=2)}")
            
            # Add transaction ID if not present
            if "metadata" not in test_data:
                test_data["metadata"] = {}
                
            if "transaction_id" not in test_data["metadata"]:
                # Generate unique transaction ID
                transaction_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
                test_data["metadata"]["transaction_id"] = transaction_id
                
            # Send test based on connection type
            if self._connection_type == self.SSH_MODE:
                # Implement SSH-based test execution when SSH connection is available
                self.logger.error("SSH test execution not implemented yet")
                return False, None, "SSH test execution not implemented yet"
                
            elif self._connection_type == self.HTTP_MODE:
                # Use HTTP client to send test
                http_client = self.http_client
                
                # Adjust timeout for network-affecting tests
                original_timeout = http_client.read_timeout
                
                if affects_network:
                    http_client.read_timeout = original_timeout * 2
                    self.logger.info(f"Extended timeout for network-affecting test: {http_client.read_timeout}s")
                
                try:
                    # Send test directly without complex retry mechanisms
                    success, response_data, error_message, error_type = http_client.send_test(test_data)

                    # Không kiểm tra lại kết quả từ http_client.py
                    return success, response_data, error_message
                finally:
                    # Reset timeout
                    if affects_network:
                        http_client.read_timeout = original_timeout
                
            else:
                return False, None, f"Unknown connection type: {self._connection_type}"
                
        except Exception as e:
            error_msg = f"Error sending test case: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def ensure_device_ready(self, affects_network: bool = False) -> bool:
        """
        Kiểm tra đơn giản xem device có sẵn sàng không.

        Args:
            affects_network: Whether the upcoming test affects network connectivity

        Returns:
            True if device is ready, False otherwise
        """
        if not self.is_connected():
            self.logger.error("Not connected to device")
            return False

        try:
            # Ping đơn giản để kiểm tra device
            response = requests.get(
                f"{self.http_client.url}/ping",
                timeout=5
            )

            if response.status_code == 200:
                self.logger.info("Device is ready")
                # Chờ ngắn nếu test ảnh hưởng network
                if affects_network:
                    time.sleep(2)
                return True
            else:
                self.logger.warning(f"Device ping returned status {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Error checking device readiness: {e}")
            return False

    def ping_server(self) -> bool:
        """
        Send a ping request to the server to check if it's ready.
        This helps ensure the server is in a clean state before sending a test.
        
        Returns:
            True if server is responsive, False otherwise
        """
        if not self.is_connected():
            self.logger.error("Not connected to server")
            return False
            
        try:
            # Send a ping request
            if self.http_client and self.http_client.url:
                try:
                    response = requests.get(
                        f"{self.http_client.url}/ping",
                        timeout=self.http_client.connect_timeout
                    )
                    
                    # Check if response is successful
                    if response.status_code == 200:
                        self.logger.debug("Server ping successful")
                        return True
                    else:
                        self.logger.warning(f"Server ping returned status code {response.status_code}")
                        # Try a simple GET to the base URL as fallback
                        try:
                            response = requests.get(
                                self.http_client.url, 
                                timeout=self.http_client.connect_timeout
                            )
                            if response.status_code == 200 or response.status_code == 404:
                                self.logger.debug("Base URL connection successful")
                                return True
                        except Exception:
                            pass
                        return False
                except Exception as e:
                    self.logger.warning(f"Ping request failed: {e}, but continuing")
                    # Ping failed, but we should still continue with the test
                    return True
            else:
                self.logger.error("HTTP client not properly initialized")
                return False
                
        except Exception as e:
            self.logger.error(f"Error pinging server: {e}")
            return False

    def prepare_server_for_test(self) -> bool:
        """
        Prepare the server for a test by sending a dummy request.
        This helps prevent the empty file issue by ensuring the server
        has processed any previous requests and cleared the config file.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected() or not self.http_client or not self.http_client.url:
            self.logger.error("Not connected to server")
            return False
            
        try:
            # Send a ping request to check if server is responsive
            self.logger.info("Sending ping request to prepare server...")
            response = requests.get(
                f"{self.http_client.url}/ping",
                timeout=self.http_client.connect_timeout
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Server ping returned status code {response.status_code}")
                time.sleep(2)  # Wait a moment if ping failed
                return False
                
            # Send a dummy request to clear any existing config file
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
                    "purpose": "clear_config_file"
                }
            }
            
            self.logger.info("Sending dummy request to clear config file...")
            
            # Send the dummy request with a short timeout
            try:
                requests.post(
                    self.http_client.url,
                    json=dummy_data,
                    headers={"Content-Type": "application/json"},
                    timeout=2  # Short timeout as we don't care about the response
                )
            except requests.exceptions.Timeout:
                # Timeout is expected and not a problem
                self.logger.debug("Dummy request timed out as expected")
            except Exception as e:
                self.logger.debug(f"Dummy request exception (can be ignored): {e}")
                
            # Wait to ensure server has processed the dummy request
            time.sleep(2)
            
            # Send another ping to verify server is still responsive
            try:
                response = requests.get(
                    f"{self.http_client.url}/ping",
                    timeout=self.http_client.connect_timeout
                )
                
                if response.status_code == 200:
                    self.logger.info("Server is ready for test")
                    return True
                else:
                    self.logger.warning(f"Server returned status code {response.status_code} after dummy request")
                    return False
            except Exception as e:
                self.logger.error(f"Error checking server after dummy request: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error preparing server for test: {e}")
            return False

    def _verify_server_with_multiple_pings(self) -> bool:
        """
        Verify server is ready by sending multiple ping requests with increasing delays.
        This helps ensure the server is in a stable state before sending important tests.
        
        Returns:
            True if server is responsive, False otherwise
        """
        self.logger.info("Performing multiple ping verification...")
        success_count = 0
        
        # Try multiple pings with increasing delays
        for i in range(4):
            try:
                response = requests.get(
                    f"{self.http_client.url}/ping",
                    timeout=self.http_client.connect_timeout
                )
                
                if response.status_code == 200:
                    success_count += 1
                    self.logger.debug(f"Ping {i+1} successful")
                else:
                    self.logger.debug(f"Ping {i+1} returned status {response.status_code}")
                
                # Increasing delay between pings
                time.sleep(i + 1)
            except Exception as e:
                self.logger.debug(f"Ping {i+1} failed: {e}")
                time.sleep(i + 2)  # Longer delay after failure
        
        if success_count >= 3:
            self.logger.info("Server verified responsive")
            return True
        else:
            self.logger.warning(f"Server responsiveness check: {success_count}/4 successful")
            # Wait longer if server doesn't seem fully responsive
            time.sleep(5)
            return False

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

    def ensure_connection_before_test(self) -> bool:
        """
        Kiểm tra kết nối đơn giản trước khi chạy test.

        Returns:
            True nếu kết nối hoạt động, False nếu không thể kết nối
        """
        if self.is_connected():
            # Kiểm tra kết nối bằng ping đơn giản
            if self.ping_server():
                return True
            else:
                self.logger.warning("Connection check failed")
                return False
        else:
            self.logger.warning("Not connected")
            return False

    def send_test_with_retry(self, test_data: Dict[str, Any],
                       affects_network: bool = False, max_retries: int = 3) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Send test case with intelligent retry mechanism.
        Only retries network/transport errors, not application errors.

        Args:
            test_data: Test case data to send
            affects_network: Whether the test affects network connectivity
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            Tuple containing (success flag, response data, error message)
        """
        last_error = ""
        last_error_type = ErrorType.UNKNOWN_ERROR

        for attempt in range(max_retries):
            try:
                # Send test and get error classification
                success, response, error = self.send_test(
                    test_data=test_data,
                    affects_network=affects_network
                )

                # For now, classify errors manually since send_test doesn't return error_type
                # This will be improved when we update send_test method signature
                if not success:
                    from ..utils.error_types import classify_error
                    error_type = classify_error(error)
                else:
                    error_type = ErrorType.NETWORK_ERROR  # Success case, not used

                if success:
                    if attempt > 0:
                        self.logger.info(f"Test succeeded on retry {attempt}")
                    return success, response, error

                # Store error details
                last_error = error
                last_error_type = error_type

                # Check if we should retry this error type
                if not should_retry_error(error_type):
                    retry_reason = get_retry_reason(error_type, error)
                    self.logger.warning(f"Application error detected, skipping retry: {retry_reason}")
                    break  # Exit retry loop immediately for application errors

                # Log retry attempt for network errors
                retry_reason = get_retry_reason(error_type, error)
                self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {retry_reason}")

                # Wait before retrying (only for network errors)
                if attempt < max_retries - 1:  # Don't wait on last attempt
                    self.logger.info(f"Waiting 2 seconds before retry {attempt + 2}")
                    time.sleep(2)

            except Exception as e:
                last_error = str(e)
                last_error_type = ErrorType.UNKNOWN_ERROR
                self.logger.error(f"Exception on attempt {attempt + 1}: {last_error}")

                # Wait before retrying exceptions (treat as network errors)
                if attempt < max_retries - 1:
                    time.sleep(2)

        # All attempts failed or application error encountered
        if last_error_type == ErrorType.APPLICATION_ERROR:
            self.logger.error(f"Test failed due to application error (no retry): {last_error}")
        else:
            self.logger.error(f"Test failed after {max_retries} attempts: {last_error}")
        return False, None, f"Failed after {max_retries} attempts: {last_error}"
