#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HTTP client for Test Case Manager v2.0

This module provides client functionality for communicating with
OpenWrt test servers via HTTP.

Author: juno-kyojin
Created: 2025-06-17
"""

import requests
import json
import logging
import time
from typing import Dict, Any, Tuple, Optional

class HTTPTestClient:
    """HTTP client for communicating with OpenWrt test servers"""
    
    def __init__(self):
        """Initialize the HTTP client"""
        self.logger = logging.getLogger(__name__)
        self.url = None
        self.connected = False
        self.host = None
        self.port = 8080
        self.connect_timeout = 5
        self.read_timeout = 40
    
    def connect(self, host: str, port: int = 8080, 
                connect_timeout: int = 5, read_timeout: int = 40) -> bool:
        """
        Initialize connection parameters and test connectivity
        
        Args:
            host: Router hostname or IP address
            port: HTTP server port
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            
        Returns:
            bool: True if connection parameters are valid
        """
        try:
            self.host = host
            self.port = port
            self.connect_timeout = connect_timeout
            self.read_timeout = read_timeout
            self.url = f"http://{host}:{port}"
            
            # Test simple connection (just to verify host:port is reachable)
            # The server might not have a /ping endpoint, so we accept 404
            response = requests.get(
                f"{self.url}/ping",
                timeout=self.connect_timeout
            )
            
            # Success if we get any response (200 OK or 404 Not Found)
            self.connected = response.status_code in [200, 404]
            
            # Log success or failure
            if self.connected:
                self.logger.info(f"HTTP client successfully connected to {self.url}")
            else:
                self.logger.error(f"Failed to connect to {self.url}: Status {response.status_code}")
                
            return self.connected
            
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
    
    def is_connected(self) -> bool:
        """Check if client is initialized and connected"""
        if not self.url:
            return False
            
        try:
            # Simple check if server is reachable
            response = requests.get(
                f"{self.url}/ping", 
                timeout=self.connect_timeout
            )
            
            # Accept 200 OK or 404 Not Found
            return response.status_code in [200, 404]
            
        except:
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """Reset connection state"""
        self.connected = False
        self.url = None
            
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to server using GET request
        
        Returns:
            Tuple[bool, str]: Success flag and message
        """
        try:
            if not self.url:
                return False, "No URL configured"
            
            # Sử dụng GET request để tránh tạo file trên server
            response = requests.get(
                self.url,
                timeout=self.connect_timeout
            )
            
            # Chỉ kiểm tra kết nối thành công, không quan tâm đến nội dung
            self.connected = True
            return True, f"Connection successful (Status: {response.status_code})"
                    
        except requests.exceptions.ConnectTimeout:
            self.connected = False
            return False, f"Connection timeout ({self.connect_timeout}s)"
                
        except requests.exceptions.ConnectionError:
            self.connected = False
            return False, "Connection refused"
                
        except Exception as e:
            self.connected = False
            return False, f"Error: {str(e)}"
    
    def send_test(self, test_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict], str]:
        """
        Send test data to server for execution
        
        Args:
            test_data: Test data to send (must have test_cases array)
            
        Returns:
            Tuple[bool, Optional[Dict], str]: 
                - Success flag
                - Response data (if successful)
                - Error message (if failed)
        """
        if not self.connected:
            return False, None, "Not connected to server"
        
        if not self.url:
            return False, None, "URL not configured"
        
        try:
            self.logger.info(f"Sending test case to {self.url}")
            
            # Validate test structure
            if "test_cases" not in test_data:
                # Wrap single test case in proper structure if needed
                if "service" in test_data:
                    test_data = {"test_cases": [test_data]}
                else:
                    return False, None, "Invalid test case format - missing 'test_cases' array"
            
            # Optional: log test case content for debugging
            self.logger.debug(f"Test case content: {json.dumps(test_data, indent=2)}")
            
            # Send POST request with test case JSON in body
            response = requests.post(
                self.url,  # Use the root URL as endpoint
                json=test_data,  # This will be serialized to JSON
                headers={"Content-Type": "application/json"},
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
                return True, response_data, ""
            except json.JSONDecodeError:
                error_msg = "Server returned invalid JSON response"
                self.logger.error(error_msg)
                return False, None, error_msg
                
        except Exception as e:
            error_msg = f"Error sending test case: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg