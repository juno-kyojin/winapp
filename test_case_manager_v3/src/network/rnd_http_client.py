#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple HTTP Client for rnd_autotest Communication

This module provides a simplified HTTP client specifically designed for
communicating with rnd_autotest HTTP server. It uses synchronous HTTP
communication without ping or polling mechanisms.

Author: juno-kyojin
Created: 2025-07-22
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.error_types import ErrorType, classify_error


class RndHTTPClient:
    """
    Simple HTTP client for rnd_autotest communication.
    
    This client sends test cases to rnd_autotest HTTP server and receives
    immediate synchronous responses. No ping or polling mechanisms.
    """
    
    def __init__(self):
        """Initialize the HTTP client."""
        self.logger = logging.getLogger(__name__)
        
        # Connection parameters
        self.url: Optional[str] = None
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.connect_timeout: int = 5
        self.read_timeout: int = 180  # Increased for wireless tests
        
        # Connection state
        self.connected: bool = False
        
        # HTTP session
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Setup HTTP session with retry strategy and minimal connection pooling."""
        # Simple retry strategy for connection issues only
        retry_strategy = Retry(
            total=2,  # Reduced retries to avoid long delays
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=0.5,  # Faster backoff
            allowed_methods=["POST"]
        )

        # Minimal connection pooling to avoid ConnectionResetError
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1,  # Single connection pool
            pool_maxsize=1       # Force fresh connections
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers with cache-busting and connection control
        self.session.headers.update({
            "User-Agent": "TestCaseManager/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close"  # Force connection close like curl
        })
    
    def connect(self, host: str, port: int = 6969,
                connect_timeout: int = 5, read_timeout: int = 120) -> bool:
        """
        Initialize connection parameters for rnd_autotest server.
        
        Args:
            host: Target host name or IP address
            port: Target port number (default: 6969 for rnd_autotest)
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            
        Returns:
            True if connection parameters set successfully
        """
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.url = f"http://{host}:{port}"

        # Test actual connection to server
        try:
            self.logger.info(f"Testing connection to {self.url}")
            response = requests.get(
                self.url,
                timeout=(connect_timeout, 5),  # Short timeout for connection test
                headers={"User-Agent": "TestCaseManager-ConnectionTest/1.0"}
            )

            # Accept any HTTP response (200, 404, 405, etc.) as "server is reachable"
            if response.status_code:
                self.connected = True
                self.logger.info(f"HTTP client connected to rnd_autotest at {self.url} (status: {response.status_code})")
                return True
            else:
                self.connected = False
                self.logger.error(f"Server at {self.url} returned no status code")
                return False

        except requests.exceptions.RequestException as e:
            self.connected = False
            self.logger.error(f"Failed to connect to {self.url}: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from server."""
        if self.session:
            self.session.close()
        self.connected = False
        self.url = None
        self.logger.info("Disconnected from rnd_autotest server")
    
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self.connected and self.url is not None
    
    def send_test(self, test_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], str, ErrorType]:
        """
        Send test data to rnd_autotest server for immediate execution.

        Args:
            test_data: Test case data to send

        Returns:
            Tuple containing (success flag, response data, error message, error type)
        """
        if not self.is_connected() or not self.url:
            return False, None, "Not connected to server", ErrorType.NETWORK_ERROR
        
        try:
            # Check if this is a script result (different validation)
            is_script_result = test_data.get("type") == "script" and "script_result" in test_data

            if not is_script_result:
                # Validate test case format (only for regular test cases)
                if "test_cases" not in test_data or not test_data["test_cases"]:
                    return False, None, "Invalid test case format - missing 'test_cases' array", ErrorType.APPLICATION_ERROR

                # Simple metadata for device compatibility (only for test cases)
                if "metadata" not in test_data:
                    test_data["metadata"] = {}

            if not is_script_result:
                # Add minimal metadata with unique cache-busting element (only for test cases)
                current_time = time.time()
                test_data["metadata"].update({
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "request_id": str(uuid.uuid4()),
                    "cache_bust": int(current_time * 1000000)  # Microsecond precision
                })

                # Log test case for debugging
                self.logger.info(f"Sending fresh request with ID: {test_data['metadata']['request_id']}")
                self.logger.info(f"Request timestamp: {test_data['metadata']['timestamp']}")
                self.logger.info(f"Cache bust value: {test_data['metadata']['cache_bust']}")
                self.logger.debug(f"Sending test case: {json.dumps(test_data, indent=2)}")
            else:
                # Log script result for debugging
                self.logger.info(f"Sending script result: {test_data}")
                self.logger.debug(f"Script result data: {json.dumps(test_data, indent=2)}")

            # Force connection reset to prevent cached responses and connection issues
            if self.session:
                try:
                    # Close all connections in the session pool
                    self.session.close()
                except:
                    pass

            # Create completely fresh session for each request to avoid ConnectionResetError
            self.session = requests.Session()
            self._setup_session()

            # Preserve current timeout settings (may have been extended for network tests)
            current_connect_timeout = getattr(self, 'connect_timeout', 5)
            current_read_timeout = getattr(self, 'read_timeout', 120)

            self.logger.info(f"Created fresh session with timeouts: connect={current_connect_timeout}s, read={current_read_timeout}s")
            self.logger.info(f"Timeout settings preserved from previous session")

            # Send POST request to rnd_autotest root URL (no cache-busting parameters)
            # Device may not expect query parameters
            # Minimal request like curl

            # CRITICAL: Force server cache clear before sending actual test
            self.logger.info("Sending cache clear requests to force server refresh")
            self._send_cache_clear_request()

            # Add delay to ensure server processes fresh request
            time.sleep(3)  # 3 second delay after cache clear

            self.logger.info(f"Sending simple request to root URL: {self.url}")
            self.logger.info(f"Using timeouts: connect={current_connect_timeout}s, read={current_read_timeout}s for device test execution")

            # Use direct requests.post() with curl-like headers to avoid caching
            curl_headers = {
                "Content-Type": "application/json",
                "User-Agent": f"curl/7.68.0-{uuid.uuid4()}",  # Unique user-agent like curl
                "Accept": "*/*",
                "Connection": "close"  # Force connection close
            }

            response = requests.post(
                self.url,  # Use root URL only (rnd_autotest requirement)
                json=test_data,
                headers=curl_headers,
                timeout=(current_connect_timeout, current_read_timeout)
            )

            # Log raw response for debugging
            self.logger.info(f"HTTP Response Status: {response.status_code}")
            self.logger.info(f"HTTP Response Headers: {dict(response.headers)}")

            # Debug response content
            response_text = response.text
            self.logger.info(f"Raw Response Length: {len(response_text)} bytes")
            self.logger.info(f"Raw Response Text: '{response_text}'")  # With quotes to see exact content

            # Process immediate response
            if response.status_code == 200:
                try:
                    if not response_text.strip():
                        self.logger.error("Empty response text received")
                        return False, None, "Empty response from server", ErrorType.NETWORK_ERROR

                    response_data = response.json()

                    # Log actual response for debugging
                    self.logger.info(f"Received response from rnd_autotest: {json.dumps(response_data, indent=2)}")

                    # Analyze response timing to understand server behavior (only for test cases, not script results)
                    if "failed_by_service" in response_data and "metadata" in test_data:
                        for _, failures in response_data["failed_by_service"].items():
                            for failure in failures:
                                if "timestamp" in failure:
                                    response_timestamp = failure["timestamp"]
                                    request_timestamp = test_data["metadata"]["timestamp"]
                                    execution_time_ms = failure.get("execution_time_ms", 0)

                                    self.logger.warning(f"Response timestamp: {response_timestamp}")
                                    self.logger.warning(f"Request timestamp: {request_timestamp}")
                                    self.logger.warning(f"Server reported execution time: {execution_time_ms}ms")

                                    if response_timestamp != request_timestamp:
                                        # This might not be caching - could be server using test execution time for timestamp
                                        self.logger.error(f"TIMESTAMP MISMATCH: Response timestamp is {response_timestamp}, but request was at {request_timestamp}")
                                        self.logger.error(f"This suggests server uses test execution start time, not request time for timestamps")

                                        if execution_time_ms < 5000:  # Less than 5 seconds
                                            self.logger.error(f"Fast failure detected: {execution_time_ms}ms - likely configuration issue, not caching")

                    # Enhanced response format validation for multiple rnd_autotest response types
                    if "summary" in response_data:
                        # Standard test execution response
                        self.logger.info("Test executed successfully - found 'summary' field")
                        return True, response_data, "", ErrorType.NETWORK_ERROR  # Success case
                    elif "script" in response_data and "script_params" in response_data:
                        # Script verification response - treat as success
                        self.logger.info("Test executed successfully - found 'script' verification response")
                        return True, response_data, "", ErrorType.NETWORK_ERROR  # Success case
                    elif "status" in response_data and response_data["status"] == "error":
                        # Error response from rnd_autotest
                        error_msg = response_data.get("message", "Unknown error")
                        self.logger.error(f"rnd_autotest returned error: {error_msg}")
                        return False, response_data, f"Server error: {error_msg}", ErrorType.APPLICATION_ERROR
                    else:
                        # Unknown response format
                        available_fields = list(response_data.keys()) if isinstance(response_data, dict) else "Not a dict"
                        self.logger.error(f"Unknown response format. Available fields: {available_fields}")
                        self.logger.error(f"Full response data: {response_data}")
                        return False, response_data, f"Unknown response format. Available: {available_fields}", ErrorType.APPLICATION_ERROR
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error: {e}")
                    self.logger.error(f"Response text that failed to parse: '{response_text}'")
                    return False, None, f"Invalid JSON response: {str(e)}", ErrorType.APPLICATION_ERROR
            else:
                error_msg = f"Server returned status code {response.status_code}"
                self.logger.error(error_msg)
                return False, None, error_msg, ErrorType.NETWORK_ERROR
                
        except requests.exceptions.Timeout:
            return False, None, "Request timeout", ErrorType.NETWORK_ERROR
        except requests.exceptions.ConnectionError as e:
            detailed_error = f"Connection error: {str(e)}"
            self.logger.error(f"Connection failed to {self.url}: {e}")
            return False, None, detailed_error, ErrorType.NETWORK_ERROR
        except Exception as e:
            error_msg = f"Error sending test: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg, classify_error(error_msg)

    def _send_cache_clear_request(self) -> None:
        """Send a special request to clear server-side cache."""
        try:
            # Send multiple cache clear requests with different data to force server refresh
            for i in range(3):
                cache_clear_data = {
                    "test_cases": [],
                    "metadata": {
                        "cache_clear": True,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "clear_id": str(uuid.uuid4()),
                        "iteration": i,
                        "force_refresh": True
                    }
                }

                # Quick request with short timeout
                if self.url:
                    requests.post(
                        self.url,
                        json=cache_clear_data,
                        timeout=(2, 3),  # Very short timeout
                        headers={
                            "Cache-Control": "no-cache, no-store, must-revalidate",
                            "Pragma": "no-cache",
                            "Expires": "0",
                            "Connection": "close"
                        }
                    )
                time.sleep(0.5)  # Small delay between requests

            self.logger.info("Multiple cache clear requests sent to force server refresh")

        except Exception as e:
            self.logger.debug(f"Cache clear requests failed (expected): {e}")
            # Ignore errors - this is just to force cache refresh
