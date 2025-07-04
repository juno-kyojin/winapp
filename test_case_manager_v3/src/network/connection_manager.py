#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Connection Manager for Test Case Manager v1.0

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


def affects_network_connectivity(test_data: Dict[str, Any]) -> bool:
    """
    Check if a test affects network connectivity.

    This function detects tests that may disrupt network connectivity,
    requiring special handling for connection recovery and extended timeouts.

    Args:
        test_data: Test data to check

    Returns:
        True if test affects network connectivity, False otherwise
    """
    # Check test_cases array format
    if "test_cases" in test_data and test_data["test_cases"]:
        for test_case in test_data["test_cases"]:
            service = test_case.get("service", "").lower()
            action = test_case.get("action", "").lower()
            if service in ["network", "lan", "wan", "wireless"] and action in ["edit", "create", "delete"]:
                return True

    # Check direct service format
    elif "service" in test_data:
        service = test_data.get("service", "").lower()
        action = test_data.get("action", "").lower()
        if service in ["network", "lan", "wan", "wireless"] and action in ["edit", "create", "delete"]:
            return True

    return False

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



    def ensure_connection_before_test(self) -> bool:
        """
        Kiểm tra kết nối đơn giản trước khi chạy test.
        Tự động thử kết nối lại nếu kết nối bị mất.

        Returns:
            True nếu kết nối hoạt động, False nếu không thể kết nối
        """
        # Kiểm tra kết nối hiện tại
        if self.is_connected():
            # Kiểm tra kết nối bằng ping đơn giản
            if self.ping_server():
                return True
            else:
                self.logger.warning("Connection check failed, attempting to reconnect...")
                # Thử kết nối lại
                return self._attempt_reconnection()
        else:
            self.logger.warning("Not connected, attempting to reconnect...")
            # Thử kết nối lại
            return self._attempt_reconnection()

    def _attempt_reconnection(self, max_attempts: int = 3) -> bool:
        """
        Thử kết nối lại với thiết bị.

        Args:
            max_attempts: Số lần thử tối đa

        Returns:
            True nếu kết nối thành công, False nếu thất bại
        """
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Reconnection attempt {attempt + 1}/{max_attempts}")

                # Đóng kết nối cũ nếu có
                if self.http_client:
                    self.http_client.disconnect()

                # Thử kết nối lại với thông số đã lưu
                if hasattr(self, '_hostname') and self._hostname:
                    # Sử dụng thông số kết nối đã lưu
                    connection_params = {}
                    if hasattr(self, 'port') and self.port:
                        connection_params['port'] = self.port
                    if hasattr(self, 'http_connect_timeout') and self.http_connect_timeout:
                        connection_params['connect_timeout'] = self.http_connect_timeout
                    if hasattr(self, 'http_read_timeout') and self.http_read_timeout:
                        connection_params['read_timeout'] = self.http_read_timeout

                    if self.connect(self._hostname, **connection_params):
                        # Kiểm tra kết nối bằng ping
                        if self.ping_server():
                            self.logger.info(f"Reconnection successful on attempt {attempt + 1}")
                            return True
                        else:
                            self.logger.warning(f"Reconnection attempt {attempt + 1} failed ping test")
                    else:
                        self.logger.warning(f"Reconnection attempt {attempt + 1} failed to establish connection")
                else:
                    self.logger.error("No hostname stored for reconnection")
                    return False

                # Chờ trước khi thử lại
                if attempt < max_attempts - 1:
                    wait_time = 2 * (attempt + 1)  # Tăng dần thời gian chờ: 2s, 4s, 6s
                    self.logger.info(f"Waiting {wait_time}s before next reconnection attempt")
                    time.sleep(wait_time)

            except Exception as e:
                self.logger.error(f"Exception during reconnection attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(2)

        self.logger.error(f"Failed to reconnect after {max_attempts} attempts")
        return False



    def send_test_with_retry(self, test_data: Dict[str, Any],
                       affects_network: bool = False, max_retries: int = 3) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Send test case with intelligent retry mechanism.
        Only retries network/transport errors, not application errors.
        Enhanced handling for network-affecting tests that may disrupt connectivity.

        Args:
            test_data: Test case data to send
            affects_network: Whether the test affects network connectivity
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            Tuple containing (success flag, response data, error message)
        """
        last_error = ""
        last_error_type = ErrorType.UNKNOWN_ERROR

        if affects_network:
            self.logger.info("Detected network-affecting test - using enhanced connectivity handling")

        for attempt in range(max_retries):
            try:
                # For network-affecting tests, add extra connection validation before sending
                if affects_network and attempt > 0:
                    self.logger.info("Network-affecting test retry - performing enhanced connection validation")
                    if not self.ensure_connection_before_test():
                        self.logger.warning("Connection validation failed for network-affecting test retry")
                        last_error = "Failed to ensure connection to device"
                        last_error_type = ErrorType.NETWORK_ERROR
                        continue

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
                # For network-affecting tests, be more aggressive about retrying connection failures
                if affects_network and "connection" in error.lower():
                    self.logger.info("Network-affecting test connection failure - treating as network error for retry")
                    error_type = ErrorType.NETWORK_ERROR

                if not should_retry_error(error_type):
                    retry_reason = get_retry_reason(error_type, error)
                    self.logger.warning(f"Application error detected, skipping retry: {retry_reason}")
                    break  # Exit retry loop immediately for application errors

                # Log retry attempt for network errors
                retry_reason = get_retry_reason(error_type, error)
                self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {retry_reason}")

                # Wait before retrying (only for network errors)
                if attempt < max_retries - 1:  # Don't wait on last attempt
                    # Use longer wait time for network-affecting tests that may disrupt connectivity
                    wait_time = 10 if affects_network else 2
                    self.logger.info(f"Waiting {wait_time} seconds before retry {attempt + 2}")
                    time.sleep(wait_time)

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
