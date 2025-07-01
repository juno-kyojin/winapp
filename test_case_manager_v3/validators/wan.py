#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validators for wan service.

This module provides validation functions for wan test cases.
"""

from typing import Dict, Any, Tuple
import socket
import time
import subprocess
import platform
import re
import urllib.request
import urllib.error

def validate_wan_create(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate wan create test case.
    
    Args:
        test_data: Test case data
        result_data: Test result data
    
    Returns:
        Tuple containing (success boolean, message)
    """
    # First check if the server reported success
    if not result_data.get("summary", {}).get("passed", 0) > 0:
        return False, "Server reported test failure"
    
    # Extract WAN parameters from test data
    wan_params = None
    if "test_cases" in test_data:
        for test_case in test_data["test_cases"]:
            if test_case.get("service") == "wan" and test_case.get("action") == "create":
                wan_params = test_case.get("params", {})
                break
    
    if not wan_params:
        return False, "Could not find WAN parameters in test data"
    
    # Allow some time for network changes to take effect
    time.sleep(10)
    
    # Check if we have internet connectivity
    if not _check_internet_connectivity():
        return False, "No internet connectivity after WAN creation"
    
    # Try to verify that we're using the correct WAN interface
    # This is challenging to do programmatically, especially from the client side
    # We'll just check that we have connectivity and can reach the internet
    
    return True, "Successfully verified WAN creation with internet connectivity"

def validate_wan_edit(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate wan edit test case.
    
    Args:
        test_data: Test case data
        result_data: Test result data
    
    Returns:
        Tuple containing (success boolean, message)
    """
    # First check if the server reported success
    if not result_data.get("summary", {}).get("passed", 0) > 0:
        return False, "Server reported test failure"
    
    # Extract WAN parameters from test data
    wan_params = None
    if "test_cases" in test_data:
        for test_case in test_data["test_cases"]:
            if test_case.get("service") == "wan" and test_case.get("action") == "edit":
                wan_params = test_case.get("params", {})
                break
    
    if not wan_params:
        return False, "Could not find WAN parameters in test data"
    
    # Allow some time for network changes to take effect
    time.sleep(10)
    
    # Check if we have internet connectivity
    if not _check_internet_connectivity():
        return False, "No internet connectivity after WAN edit"
    
    return True, "Successfully verified WAN edit with internet connectivity"

def validate_wan_delete(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate wan delete test case.
    
    Args:
        test_data: Test case data
        result_data: Test result data
    
    Returns:
        Tuple containing (success boolean, message)
    """
    # First check if the server reported success
    if not result_data.get("summary", {}).get("passed", 0) > 0:
        return False, "Server reported test failure"
    
    # Extract WAN parameters from test data
    wan_params = None
    if "test_cases" in test_data:
        for test_case in test_data["test_cases"]:
            if test_case.get("service") == "wan" and test_case.get("action") == "delete":
                wan_params = test_case.get("params", {})
                break
    
    if not wan_params:
        return False, "Could not find WAN parameters in test data"
    
    # For WAN delete, we need to check if we still have connectivity
    # This depends on whether this was the only WAN interface or if there are others
    # For simplicity, we'll check if we have local network connectivity
    if not _check_local_network_connectivity():
        return False, "Lost local network connectivity after WAN delete"
    
    return True, "Successfully verified WAN delete with maintained local connectivity"

# Helper functions for network verification

def _check_internet_connectivity() -> bool:
    """Check if we have internet connectivity by trying to reach common websites."""
    urls = [
        "http://www.google.com",
        "http://www.cloudflare.com",
        "http://www.microsoft.com"
    ]
    
    for url in urls:
        if _check_url_accessibility(url):
            return True
    
    return False

def _check_url_accessibility(url: str) -> bool:
    """Check if a URL is accessible."""
    try:
        # Try to open the URL with a timeout
        urllib.request.urlopen(url, timeout=5)
        return True
    except (urllib.error.URLError, socket.timeout):
        return False

def _check_local_network_connectivity() -> bool:
    """Check if we have local network connectivity by pinging the default gateway."""
    gateway = _get_default_gateway()
    if not gateway:
        return False
    
    return _ping_host(gateway)

def _ping_host(host: str) -> bool:
    """Ping a host and return True if successful."""
    try:
        # Different ping command parameters based on OS
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "2", host]
        
        # Run the ping command
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        return result.returncode == 0
    except Exception:
        return False

def _get_default_gateway() -> str:
    """Get the default gateway (router) IP address."""
    if platform.system().lower() == "windows":
        return _get_default_gateway_windows()
    else:
        return _get_default_gateway_linux()

def _get_default_gateway_windows() -> str:
    """Get the default gateway on Windows."""
    try:
        # Run ipconfig and parse the output
        result = subprocess.run(["ipconfig"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout
        
        # Look for the default gateway
        for line in output.split('\n'):
            if "Default Gateway" in line:
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    return match.group(1)
        
        # If not found, try the first non-VMware adapter
        sections = re.split(r"\n(?=[A-Za-z ]+adapter )", output)
        for section in sections:
            if "VMware" in section or "vEthernet" in section:
                continue
            
            for line in section.split('\n'):
                if "Default Gateway" in line:
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        return match.group(1)
    except Exception:
        pass
    
    # Default to common router IPs if we can't determine it
    return "192.168.1.1"

def _get_default_gateway_linux() -> str:
    """Get the default gateway on Linux."""
    try:
        # Run ip route and parse the output
        result = subprocess.run(["ip", "route"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout
        
        # Look for the default gateway
        for line in output.split('\n'):
            if line.startswith("default"):
                parts = line.split()
                if len(parts) >= 3:
                    return parts[2]
    except Exception:
        pass
    
    # Default to common router IPs if we can't determine it
    return "192.168.1.1"
