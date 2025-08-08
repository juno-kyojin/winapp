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
import time
import importlib
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from src.network.rnd_http_client import RndHTTPClient
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

def is_complex_test(test_data: Dict[str, Any]) -> bool:
    """
    Check if test contains multiple test cases or complex operations.

    Args:
        test_data: Test data to check

    Returns:
        True if test is complex and may cause extended processing time
    """
    if "test_cases" in test_data and test_data["test_cases"]:
        test_cases = test_data["test_cases"]

        # Multiple test cases = complex
        if len(test_cases) > 1:
            return True

        # Single test case but complex operations
        for test_case in test_cases:
            service = test_case.get("service", "").lower()
            action = test_case.get("action", "").lower()

            # WAN operations are inherently complex
            if service == "wan" and action in ["create", "delete", "edit"]:
                return True

            # Backup operations can be time-consuming
            if service == "backup":
                return True

    return False

class ConnectionManager:
    """
    HTTP connection manager for Test Case Manager v1.0.

    This class provides HTTP connection interface for connecting to devices
    and sending test commands to rnd_autotest server.
    """
    
    def __init__(self) -> None:
        """
        Initialize HTTP connection manager.
        """
        self.logger = logging.getLogger(__name__)

        # Initialize HTTP client only
        self.http_client: RndHTTPClient = RndHTTPClient()

        # Connection type is always HTTP
        self._connection_type = "http"

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
        self.network_test_delay = 30  # Seconds to wait after network-affecting tests (increased for WAN operations)

    # def _initialize_ssh_connection(self) -> bool:
    #     """
    #     Initialize SSH connection if not already initialized.
    #
    #     Returns:
    #         True if SSH connection is available, False otherwise
    #     """
    #     if self.ssh_connection is None:
    #         try:
    #             # Use importlib for dynamic import to avoid errors if module doesn't exist
    #             ssh_module = importlib.import_module('network.ssh_connection')
    #             SSHConnection = getattr(ssh_module, 'SSHConnection')
    #             self.ssh_connection = SSHConnection()
    #             return True
    #         except (ImportError, AttributeError) as e:
    #             self.logger.error(f"Could not load SSH module: {e}")
    #             return False
    #     return True

    def set_connection_type(self, conn_type: str) -> None:
        """
        Set the connection type (HTTP only).

        Args:
            conn_type: Connection type (must be 'http')
        """
        if conn_type.lower() != "http":
            self.logger.error(f"Invalid connection type: {conn_type}. Only HTTP is supported.")
            return

        self._connection_type = "http"
        self.logger.info(f"Connection type set to {self._connection_type}")
    
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

        # HTTP connection only
        self.port = kwargs.get('port', 6969)
        self.http_connect_timeout = kwargs.get('connect_timeout', 5)  # Default to 5s like client.py
        self.http_read_timeout = kwargs.get('read_timeout', 180)  # Increased to 180s for complex multi-test operations

        # Ensure port is an integer
        port = int(self.port) if self.port is not None else 6969

        return self.http_client.connect(
            host=hostname,
            port=port,
            connect_timeout=self.http_connect_timeout,
            read_timeout=self.http_read_timeout
        )
    
    def is_connected(self) -> bool:
        """
        Check if connected to remote host via HTTP.

        Returns:
            True if connected, False otherwise
        """
        return self.http_client.is_connected()
    
    def disconnect(self) -> None:
        """Disconnect from remote HTTP host."""
        self.http_client.disconnect()

        self._connected = False
        self._hostname = None
        self.logger.info("Disconnected from remote host")

    def send_script_result(self, script_result_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Send script verification result to the device and wait for final test result.

        Args:
            script_result_data: Script result data to send (format: {"type": "script", "script_result": [...]})

        Returns:
            Tuple containing (success flag, final response data, error message)
        """
        if not self.is_connected():
            return False, None, "Not connected to device"

        # Validate script result data
        if not script_result_data or "type" not in script_result_data:
            return False, None, "Invalid script result data format"

        self.logger.info("Sending script result to device and waiting for final test result")

        # For script results, use retry mechanism to handle connection issues
        max_retries = 2  # Fewer retries for script results
        last_error = ""

        for attempt in range(max_retries):
            try:
                # Ensure fresh connection for script results to avoid ConnectionResetError
                if attempt > 0:
                    self.logger.info(f"Script result retry attempt {attempt + 1}")
                    # Force reconnection on retry
                    if hasattr(self.http_client, 'session') and self.http_client.session:
                        self.http_client.session.close()

                # Use HTTP client directly for script results (no test case validation needed)
                success, response_data, error_msg, error_type = self.http_client.send_test(script_result_data)

                if success:
                    if attempt > 0:
                        self.logger.info(f"Script result sent successfully on retry {attempt + 1}")
                    else:
                        self.logger.info("Script result sent successfully")

                    # Check if response contains final test result or another script request
                    if response_data and "script" in response_data:
                        # Device sent another script request - this shouldn't happen for LAN tests
                        self.logger.warning("Device sent another script request after script result")
                        return True, response_data, ""
                    elif response_data and ("summary" in response_data or "status" in response_data):
                        # Device sent final test result
                        self.logger.info("Received final test result from device")
                        return True, response_data, ""
                    else:
                        # Device acknowledged script result but didn't send final result yet
                        # This is the current behavior - device processes script result internally
                        self.logger.info("Device acknowledged script result")
                        return True, response_data, ""
                else:
                    last_error = error_msg
                    # Check if this is a connection error that should be retried
                    if "connection" in error_msg.lower() or "reset" in error_msg.lower():
                        if attempt < max_retries - 1:
                            self.logger.warning(f"Connection error on attempt {attempt + 1}, retrying: {error_msg}")
                            time.sleep(1)  # Short delay before retry
                            continue
                    else:
                        # Non-connection error, don't retry
                        break

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Exception sending script result on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue

        self.logger.error(f"Failed to send script result after {max_retries} attempts: {last_error}")
        return False, None, last_error

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
            
            # Add metadata if not present (no transaction ID needed for rnd_autotest)
            if "metadata" not in test_data:
                test_data["metadata"] = {
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
            # Send test via HTTP
            http_client = self.http_client

            # Adjust timeout for network-affecting and complex tests
            original_timeout = http_client.read_timeout
            is_complex = is_complex_test(test_data)

            if affects_network and is_complex:
                # Extra long timeout for complex network operations
                extended_timeout = original_timeout * 3
                http_client.read_timeout = extended_timeout
                self.logger.info(f"Extended timeout for complex network-affecting test: {original_timeout}s → {extended_timeout}s")
            elif affects_network:
                extended_timeout = original_timeout * 2
                http_client.read_timeout = extended_timeout
                self.logger.info(f"Extended timeout for network-affecting test: {original_timeout}s → {extended_timeout}s")
            elif is_complex:
                extended_timeout = int(original_timeout * 1.5)
                http_client.read_timeout = extended_timeout
                self.logger.info(f"Extended timeout for complex test: {original_timeout}s → {extended_timeout}s")
            else:
                self.logger.info(f"Using standard timeout for simple test: {original_timeout}s")

            try:
                # Send test directly without complex retry mechanisms
                success, response_data, error_message, _ = http_client.send_test(test_data)

                # Không kiểm tra lại kết quả từ http_client.py
                return success, response_data, error_message
            finally:
                # Reset timeout
                if affects_network:
                    http_client.read_timeout = original_timeout
                
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

        # For rnd_autotest synchronous HTTP, device readiness is verified through actual test execution
        self.logger.info("Device ready (synchronous HTTP communication)")
        if affects_network:
            time.sleep(2)  # Brief delay for network-affecting tests
        return True

    # Removed ping_server() - rnd_autotest uses synchronous HTTP communication

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
            # For rnd_autotest synchronous HTTP, no ping needed
            self.logger.info("Preparing server for test (synchronous HTTP)...")
                
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
            
            # For rnd_autotest synchronous HTTP, server is ready after dummy request
            self.logger.info("Server is ready for test")
            return True
                
        except Exception as e:
            self.logger.error(f"Error preparing server for test: {e}")
            return False

    # Removed _verify_server_with_multiple_pings() - rnd_autotest uses synchronous HTTP communication



    def ensure_connection_before_test(self) -> bool:
        """
        Kiểm tra kết nối đơn giản trước khi chạy test.
        Tự động thử kết nối lại nếu kết nối bị mất.

        Returns:
            True nếu kết nối hoạt động, False nếu không thể kết nối
        """
        # Kiểm tra kết nối hiện tại
        if self.is_connected():
            # For rnd_autotest synchronous HTTP, connection is verified through actual test execution
            return True
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
                        # For rnd_autotest synchronous HTTP, connection success means ready
                        self.logger.info(f"Reconnection successful on attempt {attempt + 1}")
                        return True
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
            self.logger.error(f"Test failed due to appliation error (no retry): {last_error}")
        else:
            self.logger.error(f"Test failed after {max_retries} attempts: {last_error}")
        return False, None, f"Failed after {max_retries} attempts: {last_error}"

    def send_cancellation_signal(self) -> bool:
        """
        Send cancellation signal to device to reset its state.

        Returns:
            True if cancellation signal sent successfully, False otherwise
        """
        try:
            self.logger.info("Sending cancellation signal to device")

            cancellation_data = {
                "type": "cancel",
                "message": "Test execution cancelled by user"
            }

            # Use shorter timeout for cancellation signal
            success, response, error_msg = self.http_client.send_test(cancellation_data, timeout=10)

            if success:
                self.logger.info("Cancellation signal sent successfully to device")
                return True
            else:
                self.logger.warning(f"Failed to send cancellation signal: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending cancellation signal: {e}")
            return False
