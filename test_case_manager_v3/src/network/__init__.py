#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Network module for Test Case Manager v1.0

This module provides networking functionality for the Test Case Manager.

Author: juno-kyojin
Created: 2025-06-12
"""

# Sửa relative imports thành absolute imports
import src.network.http_client
import src.network.connection_manager
import src.network.test_executor

# Expose key classes
from src.network.connection_manager import ConnectionManager
from src.network.http_client import HTTPTestClient
from src.network.test_executor import TestExecutor

__all__ = [
    'ConnectionManager',
    'HTTPTestClient',
    'TestExecutor'
] 
