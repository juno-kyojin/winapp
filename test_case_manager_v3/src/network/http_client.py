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
        self.max_retries = 3
        self.retry_delay = 2
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
    
    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"
    
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
                f"{self.url}/status/{safe_transaction_id}",
                timeout=self.connect_timeout
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    status = data.get("status", "unknown")
                    return status, f"Transaction status: {status}"
                except json.JSONDecodeError:
                    return "error", "Invalid JSON response from server"
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
                timeout=self.connect_timeout
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
                                        max_retries: int = 10, 
                                        retry_delay: int = 2) -> Tuple[bool, Optional[Dict[str, Any]], str]:
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
            error_msg = f"Error sending test case: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg
    
    def execute_test_with_retries(self, test_data: Dict[str, Any], 
                                  max_retries: int = 3,
                                  is_important: bool = False) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Execute a test with automatic retries on failure.
        
        Args:
            test_data: Test data to send
            max_retries: Maximum number of retry attempts
            is_important: Whether this is an important test (affects retry behavior)
            
        Returns:
            Tuple containing (success flag, response data, error message)
        """
        # Add transaction ID if not present
        if "metadata" not in test_data:
            test_data["metadata"] = {}
            
        if "transaction_id" not in test_data["metadata"]:
            transaction_id = self._generate_transaction_id()
            test_data["metadata"]["transaction_id"] = transaction_id
        
        # Store the original transaction ID
        original_transaction_id = test_data["metadata"]["transaction_id"]
        
        # Implement exponential backoff for retries
        retry_delay = 2 if not is_important else 5
        
        for attempt in range(max_retries):
            if attempt > 0:
                # For retries, generate a new transaction ID based on the original
                retry_transaction_id = f"{original_transaction_id}_retry{attempt}"
                test_data["metadata"]["transaction_id"] = retry_transaction_id
                test_data["metadata"]["retry_count"] = attempt
                test_data["metadata"]["original_transaction_id"] = original_transaction_id
                
                self.logger.info(f"Retry attempt {attempt}/{max_retries} with transaction ID: {retry_transaction_id}")
                
                # Wait before retry with exponential backoff
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # Cap at 30 seconds
            
            # Send the test
            success, response, error = self.send_test(test_data)
            
            if success:
                return success, response, error
                
            # Check if error is retryable
            if not self._is_retryable_error(error):
                self.logger.warning(f"Non-retryable error: {error}")
                return success, response, error
                
            self.logger.warning(f"Retryable error: {error}")
        
        # If we've exhausted all retries
        return False, None, f"Failed after {max_retries} attempts"
    
    def _is_retryable_error(self, error: str) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: Error message to check
            
        Returns:
            True if error is retryable, False otherwise
        """
        retryable_patterns = [
            "timeout", 
            "empty file", 
            "file not found",
            "connection refused",
            "connection reset",
            "empty response",
            "no result",
            "invalid json"
        ]
        
        error_lower = error.lower()
        for pattern in retryable_patterns:
            if pattern in error_lower:
                return True
                
        return False
    
    def is_connected(self) -> bool:
        """
        Check if client is connected to server.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected
