#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validation utilities for Test Case Manager v2.0

This module provides input validation functions for IP addresses,
ports, filenames, and other data types.

Author: juno-kyojin
Created: 2025-06-12
"""

import re
import json
import ipaddress
from pathlib import Path
from typing import Union


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address (IPv4 or IPv6).
    
    Args:
        ip: IP address string to validate
        
    Returns:
        True if valid IP address, False otherwise
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_port(port: Union[str, int]) -> bool:
    """
    Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid port (1-65535), False otherwise
    """
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False


def validate_filename(filename: str) -> bool:
    """
    Validate filename for illegal characters.
    
    Args:
        filename: Filename to validate
        
    Returns:
        True if valid filename, False otherwise
    """
    if not filename or not isinstance(filename, str):
        return False
    
    # Check for illegal characters (Windows)
    illegal_chars = r'[<>:"/\\|?*]'
    if re.search(illegal_chars, filename):
        return False
    
    # Check for reserved names (Windows)
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in reserved_names:
        return False
    
    return True


def validate_template_id(template_id: str) -> bool:
    """
    Validate template ID format.
    
    Args:
        template_id: Template ID to validate
        
    Returns:
        True if valid template ID, False otherwise
    """
    if not template_id or not isinstance(template_id, str):
        return False
    
    # Template ID should be alphanumeric with underscores, no spaces
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]*$'
    return bool(re.match(pattern, template_id))


def validate_json_string(json_str: str) -> bool:
    """
    Validate JSON string format.
    
    Args:
        json_str: JSON string to validate
        
    Returns:
        True if valid JSON, False otherwise
    """
    try:
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def validate_hostname(hostname: str) -> bool:
    """
    Validate hostname format.
    
    Args:
        hostname: Hostname to validate
        
    Returns:
        True if valid hostname, False otherwise
    """
    if not hostname or not isinstance(hostname, str):
        return False
    
    # Check length
    if len(hostname) > 253:
        return False
    
    # Check if it's an IP address first
    if validate_ip_address(hostname):
        return True
    
    # Check hostname format
    hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(hostname_pattern, hostname))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic URL pattern
    url_pattern = r'^https?://[a-zA-Z0-9\-._~:/?#[\]@!$&\'()*+,;=%]+$'
    return bool(re.match(url_pattern, url))


def validate_ssh_config(host: str, port: Union[str, int], username: str) -> tuple[bool, str]:
    """
    Validate SSH connection configuration.
    
    Args:
        host: SSH host (IP or hostname)
        port: SSH port number
        username: SSH username
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate host
    if not validate_hostname(host):
        return False, f"Invalid hostname or IP address: {host}"
    
    # Validate port
    if not validate_port(port):
        return False, f"Invalid port number: {port}"
    
    # Validate username
    if not username or not isinstance(username, str):
        return False, "Username cannot be empty"
    
    if len(username) > 32:
        return False, "Username too long (max 32 characters)"
    
    # Username should contain only alphanumeric characters and underscores
    username_pattern = r'^[a-zA-Z0-9_]+$'
    if not re.match(username_pattern, username):
        return False, "Username contains invalid characters"
    
    return True, ""


def validate_template_parameter(param_name: str, param_value: str, param_type: str, required: bool = False) -> tuple[bool, str]:
    """
    Validate template parameter value.
    
    Args:
        param_name: Parameter name
        param_value: Parameter value to validate
        param_type: Expected parameter type
        required: Whether parameter is required
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if required parameter is provided
    if required and (not param_value or param_value.strip() == ""):
        return False, f"Required parameter '{param_name}' is missing"
    
    # If not required and empty, it's valid
    if not required and (not param_value or param_value.strip() == ""):
        return True, ""
    
    # Validate based on type
    if param_type == "string":
        return True, ""
    
    elif param_type == "integer":
        try:
            int(param_value)
            return True, ""
        except ValueError:
            return False, f"Parameter '{param_name}' must be an integer"
    
    elif param_type == "float":
        try:
            float(param_value)
            return True, ""
        except ValueError:
            return False, f"Parameter '{param_name}' must be a number"
    
    elif param_type == "boolean":
        if param_value.lower() in ["true", "false", "1", "0", "yes", "no"]:
            return True, ""
        else:
            return False, f"Parameter '{param_name}' must be a boolean (true/false)"
    
    elif param_type == "json":
        if validate_json_string(param_value):
            return True, ""
        else:
            return False, f"Parameter '{param_name}' must be valid JSON"
    
    else:
        return True, ""  # Unknown type, assume valid