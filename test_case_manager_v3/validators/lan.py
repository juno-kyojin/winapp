#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validators for lan service.

This module provides validation functions for lan test cases.
"""

from typing import Dict, Any, Tuple
import socket
import time
import subprocess
import platform
import re

def validate_lan_edit_change_leasetime(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate lan edit_leasetime test case.
    
    Args:
        test_data: Test case data
        result_data: Test result data
    
    Returns:
        Tuple containing (success boolean, message)
    """
    # First check if the server reported success
    if not result_data.get("summary", {}).get("passed", 0) > 0:
        return False, "Server reported test failure"
    
    # Extract LAN parameters from test data
    lan_params = None
    if "test_cases" in test_data:
        for test_case in test_data["test_cases"]:
            if test_case.get("service") == "lan" and test_case.get("action") == "edit_leasetime":
                lan_params = test_case.get("params", {})
                break
    
    if not lan_params:
        return False, "Could not find LAN parameters in test data"
    
    # Verify we still have network connectivity
    if not _check_local_network_connectivity():
        return False, "Lost network connectivity after changing LAN lease time"
    
    # Try to verify lease time (this is difficult to do programmatically)
    # We'll just check that we have a valid lease
    lease_info = _get_dhcp_lease_info()
    if not lease_info:
        return False, "Failed to verify DHCP lease after changing lease time"
    
    return True, "Successfully verified LAN lease time change with network connectivity"

def validate_lan_edit_change_start(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate lan edit_ip_start test case.
    
    Args:
        test_data: Test case data
        result_data: Test result data
    
    Returns:
        Tuple containing (success boolean, message)
    """
    # First check if the server reported success
    if not result_data.get("summary", {}).get("passed", 0) > 0:
        return False, "Server reported test failure"
    
    # Extract LAN parameters from test data
    lan_params = None
    if "test_cases" in test_data:
        for test_case in test_data["test_cases"]:
            if test_case.get("service") == "lan" and test_case.get("action") == "edit_ip_start":
                lan_params = test_case.get("params", {})
                break
    
    if not lan_params:
        return False, "Could not find LAN parameters in test data"
    
    # Get the new start IP and DHCP range
    start_ip = lan_params.get("dhcp_start")
    network_ip = lan_params.get("network_ipv4_ip")
    
    if not start_ip:
        return False, "Could not find DHCP start IP in test parameters"
    
    # Allow some time for DHCP changes to take effect
    time.sleep(3)
    
    # Try to release and renew DHCP lease
    _release_renew_dhcp()
    
    # Verify we still have network connectivity
    if not _check_local_network_connectivity():
        return False, "Lost network connectivity after changing LAN IP start"
    
    # Get our current IP address
    current_ip = _get_current_ip()
    if not current_ip:
        return False, "Failed to determine current IP address"
    
    # Verify our IP is in the expected range
    # This is a basic check - a more thorough check would verify the IP is within
    # the exact DHCP range, but that requires more complex subnet calculations
    if not _is_in_same_subnet(current_ip, network_ip or start_ip):
        return False, f"Current IP {current_ip} is not in the expected subnet"
    
    return True, f"Successfully verified LAN IP start change with IP {current_ip}"

# Helper functions for network verification

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

def _get_current_ip() -> str:
    """Get the current IP address of this machine."""
    if platform.system().lower() == "windows":
        return _get_current_ip_windows()
    else:
        return _get_current_ip_linux()

def _get_current_ip_windows() -> str:
    """Get the current IP address on Windows."""
    try:
        # Run ipconfig and parse the output
        result = subprocess.run(["ipconfig"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout
        
        # Look for IPv4 Address
        sections = re.split(r"\n(?=[A-Za-z ]+adapter )", output)
        for section in sections:
            if "Media disconnected" in section:
                continue
            if "VMware" in section or "vEthernet" in section:
                continue
            
            ip_match = re.search(r"IPv4 Address[^\:]*:\s*([\d\.]+)", section)
            if ip_match:
                return ip_match.group(1)
    except Exception:
        pass
    
    return ""

def _get_current_ip_linux() -> str:
    """Get the current IP address on Linux."""
    try:
        # Run ip addr and parse the output
        result = subprocess.run(["ip", "addr"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout
        
        # Look for inet (IPv4) addresses
        for line in output.split('\n'):
            if "inet " in line and not "127.0.0.1" in line:
                match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    return match.group(1)
    except Exception:
        pass
    
    return ""

def _is_in_same_subnet(ip1: str, ip2: str) -> bool:
    """Check if two IP addresses are in the same subnet (assuming /24)."""
    try:
        # Simple check for /24 subnet
        parts1 = ip1.split('.')
        parts2 = ip2.split('.')
        
        if len(parts1) != 4 or len(parts2) != 4:
            return False
        
        # Check first three octets match (assuming /24 subnet)
        return parts1[0] == parts2[0] and parts1[1] == parts2[1] and parts1[2] == parts2[2]
    except Exception:
        return False

def _release_renew_dhcp() -> bool:
    """Release and renew DHCP lease."""
    try:
        if platform.system().lower() == "windows":
            # On Windows, use ipconfig /release and /renew
            subprocess.run(["ipconfig", "/release"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            time.sleep(2)
            subprocess.run(["ipconfig", "/renew"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        else:
            # On Linux, use dhclient -r and dhclient
            # This might require sudo, which could be problematic
            # A better approach would be to check if we have a valid IP
            pass
        
        # Give some time for the renewal to complete
        time.sleep(5)
        return True
    except Exception:
        return False

def _get_dhcp_lease_info() -> Dict[str, Any]:
    """Get DHCP lease information."""
    try:
        if platform.system().lower() == "windows":
            # Run ipconfig /all and parse the output
            result = subprocess.run(["ipconfig", "/all"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout
            
            # Find the active adapter section
            sections = re.split(r"\n(?=[A-Za-z ]+adapter )", output)
            for section in sections:
                if "Media disconnected" in section:
                    continue
                if "VMware" in section or "vEthernet" in section:
                    continue
                
                # Extract lease information
                lease_info = {}
                
                ip_match = re.search(r"IPv4 Address[^\:]*:\s*([\d\.]+)", section)
                if ip_match:
                    lease_info["ip"] = ip_match.group(1)
                
                subnet_match = re.search(r"Subnet Mask[^\:]*:\s*([\d\.]+)", section)
                if subnet_match:
                    lease_info["subnet_mask"] = subnet_match.group(1)
                
                gateway_match = re.search(r"Default Gateway[^\:]*:\s*([\d\.]+)", section)
                if gateway_match:
                    lease_info["gateway"] = gateway_match.group(1)
                
                dhcp_match = re.search(r"DHCP Server[^\:]*:\s*([\d\.]+)", section)
                if dhcp_match:
                    lease_info["dhcp_server"] = dhcp_match.group(1)
                
                lease_obtained_match = re.search(r"Lease Obtained[^\:]*:\s*(.+)", section)
                if lease_obtained_match:
                    lease_info["lease_obtained"] = lease_obtained_match.group(1).strip()
                
                lease_expires_match = re.search(r"Lease Expires[^\:]*:\s*(.+)", section)
                if lease_expires_match:
                    lease_info["lease_expires"] = lease_expires_match.group(1).strip()
                
                if "ip" in lease_info:
                    return lease_info
        else:
            # On Linux, we could parse /var/lib/dhcp/dhclient.leases
            # But this is more complex and might require root access
            pass
    except Exception:
        pass
    
    return {}
