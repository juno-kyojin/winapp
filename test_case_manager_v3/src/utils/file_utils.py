#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File utilities for Test Case Manager v3.0

This module provides utility functions for file operations.

Author: juno-kyojin
Created: 2025-06-14
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from .logger import get_logger
from .file_lock_utils import read_file_with_lock, write_file_with_lock

logger = get_logger(__name__)

def ensure_directory(path: Path) -> None:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure
    """
    try:
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {path}")
    except Exception as e:
        logger.error(f"Error ensuring directory {path}: {e}")
        raise

def read_json_file(file_path: Path) -> Dict[str, Any]:
    """
    Read JSON file with error handling and file locking.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary containing file contents
        
    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file is not valid JSON
    """
    try:
        file_path = Path(file_path)
        
        # Use file locking to read file
        data = read_file_with_lock(file_path)
        
        if data is None:
            # If read_file_with_lock returns None, it means the file doesn't exist
            # or is empty after retries, so we raise an appropriate exception
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            else:
                raise ValueError(f"File is empty: {file_path}")
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise

def write_json_file(file_path: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """
    Write data to JSON file with error handling and file locking.
    
    Args:
        file_path: Path to JSON file
        data: Dictionary to write
        indent: JSON indentation level
        
    Raises:
        IOError: If file cannot be written
    """
    try:
        file_path = Path(file_path)
        
        # Ensure parent directory exists
        ensure_directory(file_path.parent)
        
        # Use file locking to write file
        success = write_file_with_lock(file_path, data)
        
        if not success:
            raise IOError(f"Failed to write file: {file_path}")
            
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        raise

def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
        
    Raises:
        FileNotFoundError: If file does not exist
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return file_path.stat().st_size
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        raise 