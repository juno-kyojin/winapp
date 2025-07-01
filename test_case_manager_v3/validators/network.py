#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validators for network service.

This module provides validation functions for network test cases.
"""

from typing import Dict, Any, Tuple
import socket
import time
import subprocess
import platform
import re
import logging

def validate_network_ping(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate network ping test case.
    
    Args:
        test_data: Test case data
        result_data: Test result data
    
    Returns:
        Tuple containing (success boolean, message)
    """
    # First check if the server reported success
    if not result_data.get("summary", {}).get("passed", 0) > 0:
        return False, "Server reported test failure"
    
    # Extract ping parameters from test data
    ping_params = None
    if "test_cases" in test_data:
        for test_case in test_data["test_cases"]:
            if test_case.get("service") == "network" and test_case.get("action") == "ping":
                ping_params = test_case.get("params", {})
                break
    
    if not ping_params:
        return False, "Could not find ping parameters in test data"
    
    # Get the target host to ping
    target_host = ping_params.get("target")
    if not target_host:
        return False, "No target host specified for ping test"
    
    # Perform our own ping test to verify
    ping_success = _ping_host(target_host)
    
    if not ping_success:
        return False, f"Client-side ping to {target_host} failed"
    
    return True, f"Successfully verified ping to {target_host} from both server and client"

def validate_ping(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate ping service test case.
    
    Args:
        test_data: Test case data
        result_data: Test result data
    
    Returns:
        Tuple containing (success boolean, message)
    """
    logging.debug("Starting ping validation")
    
    # First check if the server reported success
    if not result_data.get("summary", {}).get("passed", 0) > 0:
        return False, "Server reported test failure"
    
    # Extract ping parameters from test data
    ping_params = None
    if "test_cases" in test_data:
        for test_case in test_data["test_cases"]:
            if test_case.get("service") == "ping":
                ping_params = test_case.get("params", {})
                break
    
    if not ping_params:
        return False, "Could not find ping parameters in test data"
    
    # Get the target hosts to ping
    hosts = []
    if "host1" in ping_params:
        hosts.append(ping_params["host1"])
    if "host2" in ping_params:
        hosts.append(ping_params["host2"])
    
    if not hosts:
        return False, "No hosts specified for ping test"
    
    logging.debug(f"Found hosts to ping: {hosts}")
    
    # Perform our own ping test to verify
    success_count = 0
    for host in hosts:
        logging.debug(f"Pinging host: {host}")
        if _ping_host(host):
            success_count += 1
            logging.debug(f"Successfully pinged {host}")
        else:
            logging.debug(f"Failed to ping {host}")
    
    if success_count == 0:
        return False, f"Client-side ping to all hosts failed"
    elif success_count < len(hosts):
        return True, f"Client-side ping succeeded for {success_count}/{len(hosts)} hosts"
    
    return True, f"Successfully verified ping to all hosts from both server and client"

# Helper functions for network verification

def _ping_host(host: str, count: int = 4) -> bool:
    """Ping a host and return True if successful."""
    try:
        # Different ping command parameters based on OS
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, str(count), host]
        
        logging.debug(f"Running ping command: {' '.join(command)}")
        
        # Run the ping command
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        success = result.returncode == 0
        
        logging.debug(f"Ping result: {'success' if success else 'failure'}")
        return success
    except Exception as e:
        logging.error(f"Error during ping: {e}")
        return False
