#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LAN Checker for Test Case Manager v3.0

This module provides functions to verify LAN configuration and
network connectivity after test case execution.

Author: juno-kyojin
Created: 2025-06-25
"""

import re
import subprocess
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union, List, Tuple

from ..utils.logger import get_logger

# Core IP and lease time verification functions
def ip_to_int(ip: str) -> int:
    """
    Convert an IP address to its integer representation.
    
    Args:
        ip: IP address in dotted decimal format
        
    Returns:
        Integer representation of the IP address
    """
    parts = [int(x) for x in ip.strip().split('.')]
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]

def check_ip(ip: str, start: str, limit: int) -> bool:
    """
    Check if an IP address is within a specified range.
    
    Args:
        ip: IP address to check
        start: Start IP address of the range
        limit: Number of addresses in the range
        
    Returns:
        True if the IP is within the range, False otherwise
    """
    try:
        ip_int = ip_to_int(ip)
        start_int = ip_to_int(start)
        limit = int(limit)
    except Exception:
        return False
    return start_int <= ip_int <= start_int + limit

def parse_leasetime(leasetime: str) -> Optional[datetime]:
    """
    Parse a lease time string into a datetime object.
    
    Args:
        leasetime: Lease time string in various formats
        
    Returns:
        Datetime object if parsing successful, None otherwise
    """
    formats = [
        "%A, %B %d, %Y %I:%M:%S %p",   # Thursday, June 26, 2025 8:06:09 AM
        "%d %B %Y %H:%M:%S",           # 25 June 2025 12:01:27
        "%d/%m/%Y %H:%M:%S",           # 25/06/2025 12:01:27
        "%Y-%m-%d %H:%M:%S",           # 2025-06-25 12:01:27
    ]
    for fmt in formats:
        try:
            return datetime.strptime(leasetime, fmt)
        except Exception:
            continue
    return None

def check_leasetime(leasetime: str, leasetime_config: int) -> bool:
    """
    Check if a lease time is valid according to configuration.
    
    Args:
        leasetime: Lease time string
        leasetime_config: Configured lease time in seconds
        
    Returns:
        True if lease time is valid, False otherwise
    """
    dt = parse_leasetime(leasetime)
    if not dt:
        return False
    lease_ts = int(dt.timestamp())
    now_ts = int(datetime.now().timestamp())
    diff = lease_ts - now_ts
    return diff < leasetime_config

def get_ip_start(ipconfig_output: str) -> Optional[str]:
    """
    Extract the IP address from ipconfig output.
    
    Args:
        ipconfig_output: Output from ipconfig command
        
    Returns:
        IP address if found, None otherwise
    """
    sections = re.split(r"\n(?=[A-Za-z ]+adapter )", ipconfig_output)
    for section in sections:
        if "Media disconnected" in section:
            continue
        if "VMware" in section or "vEthernet" in section:
            continue
        ip_match = re.search(r"IPv4 Address[^\:]*:\s*([\d\.]+)", section)
        if not ip_match:
            ip_match = re.search(r"IPv4[\s\.]*:\s*([\d\.]+)", section)
        if ip_match:
            return ip_match.group(1)
    return None

def get_leasetime(ipconfig_output: str) -> Optional[str]:
    """
    Extract the lease time from ipconfig output.
    
    Args:
        ipconfig_output: Output from ipconfig command
        
    Returns:
        Lease time string if found, None otherwise
    """
    sections = re.split(r"\n(?=[A-Za-z ]+adapter )", ipconfig_output)
    for section in sections:
        if "Media disconnected" in section:
            continue
        if "VMware" in section or "vEthernet" in section:
            continue
        lease_match = re.search(r"Lease Expires[^\:]*:\s*(.+)", section)
        if lease_match:
            return lease_match.group(1).strip()
    return None

# Simple helpers for test case manager integration
def get_current_network_info() -> Dict[str, Any]:
    """
    Get current network information without making any changes.
    
    Returns:
        Dictionary containing network information:
            - output: Raw ipconfig output
            - ip: Current IP address
            - leasetime: Current lease time
    """
    try:
        result = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, encoding='utf-8')
        output = result.stdout
        return {
            "output": output,
            "ip": get_ip_start(output),
            "leasetime": get_leasetime(output)
        }
    except Exception:
        return {"output": "", "ip": None, "leasetime": None}

def refresh_network_config() -> None:
    """
    Refresh network configuration using ipconfig /renew.
    
    This function runs ipconfig /renew to refresh DHCP configuration
    and waits for the command to complete.
    """
    logger = get_logger(__name__)
    logger.info("Refreshing network configuration (ipconfig /renew)")
    try:
        subprocess.run(["ipconfig", "/renew"], capture_output=True, text=True, timeout=60)
        logger.info("IP renewal request completed")
    except subprocess.TimeoutExpired:
        # Ignore timeout warning, just continue
        pass
    except Exception as e:
        logger.warning(f"DHCP renew error: {e}")

def verify_lan_test(test_data: Dict[str, Any], 
                   result_data: Optional[Dict[str, Any]], 
                   logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """
    Verify LAN test results by checking network connectivity.
    
    This function checks if the network is still connected after
    a LAN test and updates the result data with verification status.
    
    Args:
        test_data: Test data that was sent
        result_data: Result data received from the device
        logger: Logger instance to use (optional)
        
    Returns:
        Updated result data with client verification
    """
    if logger is None:
        logger = get_logger(__name__)
    
    # Ensure result_data is a dict
    if result_data is None:
        result_data = {}
    
    # Check if result from router was successful
    if result_data and "summary" in result_data and result_data["summary"].get("passed", 0) > 0:
        # Refresh network to get latest information
        refresh_network_config()
        network_info = get_current_network_info()
        
        # Simple check: is network connected?
        if network_info["ip"]:
            logger.info(f"Network connection verified: IP={network_info['ip']}")
            result_data["client_verification"] = {
                "status": True,
                "message": f"Network connection verified with IP {network_info['ip']}"
            }
            
            # If test case info is available, log additional information
            if test_data and "test_cases" in test_data and test_data["test_cases"]:
                test_case = test_data["test_cases"][0]
                action = test_case.get("action", "").lower()
                
                # Log lease time information if relevant
                if action == "edit_leasetime" and network_info["leasetime"]:
                    logger.info(f"Current lease time: {network_info['leasetime']}")
                    
                # Print current IP for IP-related tests
                if "ip" in action and network_info["ip"]:
                    logger.info(f"Current IP: {network_info['ip']}")
            
            # Report success for client verification
            if "client_verification" in result_data:
                logger.info(f"Client verification passed: {result_data['client_verification']['message']}")
        else:
            logger.error("Failed to verify network connection")
            result_data["client_verification"] = {
                "status": False,
                "message": "Failed to verify network connection"
            }
    
    return result_data 
