#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File utilities for Test Case Manager v2.0

This module provides file operation utilities including directory creation,
JSON file handling, and file system operations.

Author: juno-kyojin
Created: 2025-06-12
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def ensure_directory(path: Path) -> None:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        path: Path to the directory
        
    Raises:
        OSError: If directory cannot be created
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create directory {path}: {e}")


def read_json_file(file_path: Path) -> Dict[str, Any]:
    """
    Read and parse a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Parsed JSON data as dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
        OSError: If file cannot be read
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in {file_path}: {e}", e.doc, e.pos)
    except OSError as e:
        raise OSError(f"Failed to read JSON file {file_path}: {e}")


def write_json_file(file_path: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """
    Write data to a JSON file.
    
    Args:
        file_path: Path to the JSON file
        data: Data to write
        indent: JSON indentation level
        
    Raises:
        OSError: If file cannot be written
        TypeError: If data is not JSON serializable
    """
    try:
        # Ensure parent directory exists
        ensure_directory(file_path.parent)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    except OSError as e:
        raise OSError(f"Failed to write JSON file {file_path}: {e}")
    except TypeError as e:
        raise TypeError(f"Data is not JSON serializable: {e}")


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
        
    Raises:
        FileNotFoundError: If file doesn't exist
        OSError: If file cannot be accessed
    """
    try:
        return file_path.stat().st_size
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except OSError as e:
        raise OSError(f"Failed to get file size for {file_path}: {e}")