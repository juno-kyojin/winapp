#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Formatting utilities for Test Case Manager v2.0

This module provides formatting functions for timestamps, file sizes,
durations, and other display data.

Author: juno-kyojin
Created: 2025-06-12
"""

import datetime
from typing import Optional, Union


def format_timestamp(
    timestamp: Optional[Union[datetime.datetime, float, str]] = None,
    format_str: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format timestamp for display.
    
    Args:
        timestamp: Timestamp to format (datetime, unix timestamp, or None for now)
        format_str: Format string for datetime formatting
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        dt = datetime.datetime.now()
    elif isinstance(timestamp, datetime.datetime):
        dt = timestamp
    elif isinstance(timestamp, (int, float)):
        dt = datetime.datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        # Try to parse ISO format
        try:
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return timestamp  # Return as-is if can't parse
    else:
        return str(timestamp)
    
    return dt.strftime(format_str)


def format_file_size(size_bytes: Union[int, float]) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string (e.g., "1.5 KB", "2.3 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_bytes = float(size_bytes)
    
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    if i == 0:
        return f"{int(size_bytes)} {size_names[i]}"
    else:
        return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: Union[int, float]) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "2m 30s", "1h 15m")
    """
    if seconds < 0:
        return "0s"
    
    seconds = int(seconds)
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes}m"
        else:
            return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {remaining_minutes}m"


def format_test_status(status: str) -> str:
    """
    Format test status for display with appropriate icons.
    
    Args:
        status: Test status string
        
    Returns:
        Formatted status with emoji icon
    """
    status_icons = {
        'ready': '⏳ Ready',
        'running': '🔄 Running',
        'success': '✅ Success',
        'failed': '❌ Failed',
        'timeout': '⏰ Timeout',
        'cancelled': '🚫 Cancelled',
        'unknown': '❓ Unknown'
    }
    
    status_lower = status.lower()
    return status_icons.get(status_lower, f"❓ {status}")


def format_connection_status(connected: bool, host: Optional[str] = None) -> str:
    """
    Format connection status for display.
    
    Args:
        connected: Whether connection is established
        host: Optional host information
        
    Returns:
        Formatted connection status string
    """
    if connected:
        if host:
            return f"🟢 Connected to {host}"
        else:
            return "🟢 Connected"
    else:
        if host:
            return f"🔴 Disconnected from {host}"
        else:
            return "🔴 Disconnected"