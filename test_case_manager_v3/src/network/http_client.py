#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HTTP client for Test Case Manager v3.0

This module provides client functionality for communicating with
OpenWrt test servers via HTTP.

Author: juno-kyojin
Created: 2025-06-17
"""

import requests
import json
import logging
import time
import os
from typing import Dict, Any, Tuple, Optional, Union, List
import uuid
from urllib.parse import urljoin
from pathlib import Path
import re

import src.utils.logger as logger_module
from src.utils.file_lock_utils import read_file_with_lock, write_file_with_lock

class HTTPTestClient:
    """
    HTTP client for communicating with OpenWrt test servers.
    
    This class handles HTTP communication with test servers, including
    connection management, test case submission, and response handling.
    """
    
    def __init__(self) -> None:
        """Initialize the HTTP client with default settings."""
        self.logger = logging.getLogger(__name__)
        self.url: Optional[str] = None
        self.connected: bool = False
        self.host: Optional[str] = None
        self.port: int = 8080
        self.connect_timeout: int = 5
        self.read_timeout: int = 500

        self.session = requests.Session()
        self.last_transaction_id: Optional[str] = None
        self.last_test_data: Optional[Dict[str, Any]] = None
        
        # Khởi tạo session với retry adapter
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Configure requests session with retry adapter."""
        # Đơn giản hóa cơ chế retry để tránh lỗi import
        self.session = requests.Session()
        # Các cài đặt retry sẽ được xử lý thủ công trong các phương thức gửi request

    def _health_check(self) -> bool:
        """
        Perform a quick health check on the server.

        Returns:
            True if server is healthy, False otherwise
        """
        if not self.url:
            return False

        try:
            response = self.session.get(
                f"{self.url}/ping",
                timeout=3  # Quick timeout for health check
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.debug(f"Health check failed: {e}")
            return False

    def _reconnect(self) -> bool:
        """
        Attempt to reconnect to the server.

        Returns:
            True if reconnection successful, False otherwise
        """
        if not self.host or not self.port:
            return False

        try:
            return self.connect(
                host=self.host,
                port=self.port,
                connect_timeout=self.connect_timeout,
                read_timeout=self.read_timeout
            )
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
            return False
    
    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID."""
        from datetime import datetime
        import time

        # Use microseconds for better uniqueness
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        microseconds = str(int(time.time() * 1000000) % 1000000)  # Last 6 digits of microseconds
        unique_id = str(uuid.uuid4())[:8]

        transaction_id = f"{timestamp}_{microseconds}_{unique_id}"

        # Ensure we don't reuse the same transaction ID
        if transaction_id == self.last_transaction_id:
            time.sleep(0.001)  # Wait 1ms and regenerate
            return self._generate_transaction_id()

        return transaction_id
    
    def _sanitize_transaction_id(self, transaction_id: str) -> str:
        """Sanitize transaction ID to be safe for file operations."""
        # Replace any characters that might cause issues with file paths
        return re.sub(r'[/\\:*?"<>|]', '_', transaction_id)
    
    def connect(self, host: str, port: int = 8080, 
                connect_timeout: int = 10, read_timeout: int = 60) -> bool:
        """
        Initialize connection parameters and test connectivity.
        
        Args:
            host: Router hostname or IP
            port: HTTP server port
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            
        Returns:
            True if connection parameters are valid
        """
        try:
            self.host = host
            self.port = port
            self.connect_timeout = connect_timeout
            self.read_timeout = read_timeout
            self.url = f"http://{host}:{port}"
            
            # Test connection with ping endpoint
            return self.ping_server()
                
        except requests.exceptions.ConnectTimeout:
            self.logger.error(f"Connection timeout when connecting to {self.url}")
            self.connected = False
            return False
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Connection refused when connecting to {self.url}")
            self.connected = False
            return False
        except Exception as e:
            self.logger.error(f"Error connecting to HTTP server: {str(e)}")
            self.connected = False
            return False
    
    def ping_server(self) -> bool:
        """
        Ping the server to check connectivity.
        
        Returns:
            True if server is reachable, False otherwise
        """
        if not self.url:
            return False
            
        try:
            # Try ping endpoint first
            response = self.session.get(
                f"{self.url}/ping",
                timeout=self.connect_timeout
            )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully pinged server at {self.url}/ping")
                self.connected = True
                return True
                
            # If ping fails, try base URL
            response = self.session.get(
                self.url,
                timeout=self.connect_timeout
            )
            
            # Accept any response from base URL
            self.connected = True
            self.logger.info(f"Connected to server at {self.url} (status: {response.status_code})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to ping server: {str(e)}")
            self.connected = False
            return False
    
    def check_transaction_status(self, transaction_id: str) -> Tuple[str, str]:
        """
        Check the status of a transaction.
        
        Args:
            transaction_id: Transaction ID to check
            
        Returns:
            Tuple containing (status, message)
        """
        if not self.url:
            return "error", "No URL configured"
            
        try:
            # Sanitize transaction ID
            safe_transaction_id = self._sanitize_transaction_id(transaction_id)
            
            # Send request to status endpoint
            response = self.session.get(
                f"{self.url}/check_result/{safe_transaction_id}",
                timeout=(self.connect_timeout, 15)  # Use longer read timeout for status check
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # If we get valid test result data, transaction is completed
                    if "test_name" in data or "result" in data or "status" in data:
                        return "completed", "Transaction completed successfully"
                    else:
                        return "unknown", "Response received but no valid result data"
                except json.JSONDecodeError:
                    return "error", "Invalid JSON response from server"
            elif response.status_code == 404:
                # Result file not found yet - transaction still processing
                return "processing", "Transaction still processing"
            else:
                return "error", f"Server returned status code {response.status_code}"
                
        except Exception as e:
            return "error", f"Error checking transaction status: {str(e)}"
    
    def check_result(self, transaction_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Check the result of a transaction.
        
        Args:
            transaction_id: Transaction ID to check
            
        Returns:
            Tuple containing (success flag, response data, error message)
        """
        if not self.url:
            return False, None, "No URL configured"
            
        try:
            # Sanitize transaction ID
            safe_transaction_id = self._sanitize_transaction_id(transaction_id)
            
            # Send request to check_result endpoint
            response = self.session.get(
                f"{self.url}/check_result/{safe_transaction_id}",
                timeout=(self.connect_timeout, 15)  # Use longer read timeout for result check
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check if response contains error
                    if "error" in data:
                        return False, data, data["error"]
                    
                    # Check if response contains result
                    if "summary" in data:
                        return True, data, ""
                    
                    return True, data, ""
                    
                except json.JSONDecodeError:
                    return False, None, "Invalid JSON response from server"
            else:
                return False, None, f"Server returned status code {response.status_code}"
                
        except Exception as e:
            return False, None, f"Error checking result: {str(e)}"
    
    def wait_for_transaction_completion(self, transaction_id: str,
                                        max_retries: int = 15,
                                        retry_delay: int = 1) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Wait for a transaction to complete.
        
        Args:
            transaction_id: Transaction ID to check
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            
        Returns:
            Tuple containing (success flag, response data, error message)
        """
        if not transaction_id:
            return False, None, "No transaction ID provided"
            
        self.logger.info(f"Waiting for transaction {transaction_id} to complete")
        
        # Initial delay to allow server to process
        time.sleep(retry_delay)
        
        # Implement exponential backoff
        current_delay = retry_delay
        
        for attempt in range(max_retries):
            # Check transaction status
            status, message = self.check_transaction_status(transaction_id)
            
            if status == "completed":
                self.logger.info(f"Transaction {transaction_id} completed")
                return self.check_result(transaction_id)
                
            elif status == "error":
                self.logger.error(f"Transaction {transaction_id} failed: {message}")
                return False, None, f"Transaction failed: {message}"
                
            elif status == "processing":
                self.logger.debug(f"Transaction {transaction_id} still processing (attempt {attempt+1}/{max_retries})")
                
            elif status == "received":
                self.logger.debug(f"Transaction {transaction_id} received but not yet processing (attempt {attempt+1}/{max_retries})")
                
            else:
                self.logger.warning(f"Unknown status for transaction {transaction_id}: {status}")
                
            # Wait before next attempt with exponential backoff
            time.sleep(current_delay)
            current_delay = min(current_delay * 1.5, 10)  # Cap at 10 seconds
        
        # If we've exhausted all retries, try to get the result directly
        self.logger.warning(f"Transaction {transaction_id} did not complete after {max_retries} attempts")
        return self.check_result(transaction_id)
    
    def send_test(self, test_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Send test data to server for execution.
        
        Args:
            test_data: Test data to send (must have test_cases array)
            
        Returns:
            Tuple containing (success flag, response data, error message)
        """
        if not self.connected:
            return False, None, "Not connected to server"
        
        if not self.url:
            return False, None, "URL not configured"
        
        # Validate test data is not empty
        if not test_data:
            return False, None, "Test data is empty"
            
        try:
            # Health check before sending test
            if not self._health_check():
                self.logger.warning("Server health check failed, attempting to reconnect...")
                if not self._reconnect():
                    return False, None, "Server is not responding and reconnection failed"

            self.logger.info(f"Preparing to send test case to {self.url}")

            # Validate test structure
            if "test_cases" not in test_data:
                # Wrap single test case in proper structure if needed
                if "service" in test_data:
                    test_data = {"test_cases": [test_data]}
                else:
                    return False, None, "Invalid test case format - missing 'test_cases' array"
            
            # Add transaction ID if not present
            if "metadata" not in test_data:
                transaction_id = self._generate_transaction_id()
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                
                test_data["metadata"] = {
                    "transaction_id": transaction_id,
                    "client_timestamp": timestamp,
                    "created_at": timestamp,
                    "created_by": "test_case_manager_v3",
                    "client_version": "3.0.0"
                }
            elif "transaction_id" not in test_data["metadata"]:
                transaction_id = self._generate_transaction_id()
                test_data["metadata"]["transaction_id"] = transaction_id
            
            # Store transaction ID and test data for reference
            self.last_transaction_id = test_data["metadata"].get("transaction_id", "")
            self.last_test_data = test_data
            
            # Log test case content for debugging
            self.logger.debug(f"Test case content: {json.dumps(test_data, indent=2)}")
            
            # Prepare headers with transaction ID
            headers = {
                "Content-Type": "application/json",
                "X-Transaction-ID": self.last_transaction_id
            }
            
            # Send POST request with test case JSON in body
            self.logger.info(f"Sending test data to server with transaction ID: {self.last_transaction_id}")
            response = self.session.post(
                self.url,  # Use the root URL as endpoint
                json=test_data,  # This will be serialized to JSON
                headers=headers,
                timeout=(self.connect_timeout, self.read_timeout)
            )
            
            # Check response status
            if response.status_code != 200:
                error_msg = f"Server returned status code {response.status_code}"
                self.logger.error(f"{error_msg}: {response.text}")
                return False, None, error_msg
            
            # Try to parse response JSON
            try:
                response_data = response.json()
                self.logger.info("Received response from server")
                self.logger.debug(f"Response: {json.dumps(response_data, indent=2)}")
                
                # Check for error in response
                if "error" in response_data:
                    error_msg = response_data.get("error", "Unknown error")
                    self.logger.warning(f"Server reported error: {error_msg}")
                    
                    # Check if we have a transaction ID
                    if self.last_transaction_id and "timeout" in error_msg.lower():
                        self.logger.info(f"Server reported timeout, checking transaction status for {self.last_transaction_id}")
                        return self.wait_for_transaction_completion(self.last_transaction_id)
                    
                    return False, response_data, error_msg
                
                # Check for successful response by examining the content
                # Check if response indicates test failure
                if "summary" in response_data:
                    summary = response_data["summary"]
                    if "failed" in summary and summary["failed"] > 0:
                        # Test failed - extract failure message
                        failed_count = summary["failed"]
                        total_count = summary.get("total_test_cases", 0)
                        error_msg = f"Test execution failed: {failed_count}/{total_count} test cases failed"

                        # Try to get more specific error message
                        if "failed_by_service" in response_data:
                            failed_services = list(response_data["failed_by_service"].keys())
                            if failed_services:
                                first_service = failed_services[0]
                                failed_tests = response_data["failed_by_service"][first_service]
                                if failed_tests and len(failed_tests) > 0:
                                    first_failure = failed_tests[0]
                                    if "message" in first_failure:
                                        error_msg = f"Test failed: {first_failure['message']}"

                        self.logger.warning(f"Device reported test failure: {error_msg}")
                        return False, response_data, error_msg

                # Check for successful response
                return True, response_data, ""
                
            except json.JSONDecodeError:
                error_msg = "Server returned invalid JSON response"
                self.logger.error(error_msg)
                return False, None, error_msg
                
        except requests.exceptions.ConnectTimeout:
            error_msg = f"Connection timeout ({self.connect_timeout}s)"
            self.logger.error(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.ReadTimeout:
            error_msg = f"Read timeout ({self.read_timeout}s)"
            self.logger.error(error_msg)
            
            # When read timeout occurs, check if the server processed the request
            if self.last_transaction_id:
                self.logger.info(f"Read timeout occurred, checking transaction status for {self.last_transaction_id}")
                return self.wait_for_transaction_completion(self.last_transaction_id)
            
            return False, None, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = "Connection refused or lost"
            self.logger.error(error_msg)
            self.connected = False
            return False, None, error_msg
            
        except Exception as e:
            error_str = str(e)
            self.logger.error(f"Exception during test send: {error_str}")

            # Check for connection reset errors
            connection_reset_indicators = [
                "connection was forcibly closed",
                "forcibly closed",
                "connection reset by peer",
                "connection reset",
                "broken pipe",
                "ConnectionResetError",
                "Connection broken",
                "10054"  # Windows error code for connection reset
            ]

            is_connection_reset = any(indicator.lower() in error_str.lower()
                                    for indicator in connection_reset_indicators)

            if is_connection_reset:
                self.logger.warning("Detected connection reset error, marking as disconnected")
                self.connected = False
                error_msg = f"Connection reset by server: {error_str}"
            else:
                error_msg = f"Error sending test case: {error_str}"

            return False, None, error_msg


    
    def is_connected(self) -> bool:
        """
        Check if client is connected to server.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected
