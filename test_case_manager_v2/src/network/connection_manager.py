#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: connection_manager.py
# Purpose: Unified connection manager for SSH and HTTP
# Last updated: 2025-06-23 06:50:07 by juno-kyojin

import logging
import json
import time
import importlib
from typing import Dict, Any, Tuple, Optional, List

from utils.logger import get_logger
from core.config import AppConfig

class ConnectionManager:
    """Unified connection manager for both SSH and HTTP connections"""
    
    # Connection types
    SSH_MODE = "ssh"
    HTTP_MODE = "http"
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.connection_type = self.HTTP_MODE  # Default to HTTP
        
        # Initialize HTTP client - Sửa tên class để phù hợp với định nghĩa
        from network.http_client import HTTPTestClient
        self.http_client = HTTPTestClient()
        
        # SSH client will be lazy loaded when needed
        self.ssh_connection = None
        
        # Connection parameters
        self.hostname = None
        self.port = None
        
        # HTTP specific parameters
        self.http_connect_timeout = 5
        self.http_read_timeout = 40
        
        # SSH specific parameters
        self.username = None
        self.password = None
        self.config_path = None
        self.result_path = None
        
        # Timestamp for metadata
        self.timestamp = "2025-06-23 06:50:07"
        self.username = "juno-kyojin"
    
    def set_connection_type(self, conn_type: str) -> None:
        """Set connection type (ssh or http)"""
        if conn_type.lower() not in [self.SSH_MODE, self.HTTP_MODE]:
            self.logger.error(f"Invalid connection type: {conn_type}")
            return
            
        self.connection_type = conn_type.lower()
        self.logger.info(f"Connection type set to {self.connection_type}")
        
        # Initialize SSH if needed - Sửa import dựa trên tên file và class thực tế của bạn
        if conn_type.lower() == self.SSH_MODE and self.ssh_connection is None:
            try:
                # Dùng importlib để import động tránh lỗi nếu module không tồn tại
                ssh_module = importlib.import_module('network.ssh_connection')
                SSHConnection = getattr(ssh_module, 'SSHConnection')
                self.ssh_connection = SSHConnection()
            except (ImportError, AttributeError) as e:
                self.logger.error(f"Could not load SSH module: {e}")
    
    def connect(self, hostname: str, **kwargs) -> bool:
        """Connect to remote host using selected connection type"""
        self.hostname = hostname
        
        if self.connection_type == self.SSH_MODE:
            # Lazy load SSH module - Sửa tương tự như trên
            if self.ssh_connection is None:
                try:
                    ssh_module = importlib.import_module('network.ssh_connection')
                    SSHConnection = getattr(ssh_module, 'SSHConnection')
                    self.ssh_connection = SSHConnection()
                except (ImportError, AttributeError) as e:
                    self.logger.error(f"Could not load SSH module: {e}")
                    return False
            
            # SSH connection requires more parameters
            self.username = kwargs.get('username')
            self.password = kwargs.get('password')
            self.config_path = kwargs.get('config_path')
            self.result_path = kwargs.get('result_path')
            
            return self.ssh_connection.connect(
                hostname=hostname,
                username=self.username,
                password=self.password,
                timeout=kwargs.get('timeout', 10)
            )
            
        else:  # HTTP mode
            self.port = kwargs.get('port', 8080)
            self.http_connect_timeout = kwargs.get('connect_timeout', 5)
            self.http_read_timeout = kwargs.get('read_timeout', 40)
            
            return self.http_client.connect(
                host=hostname,  # Sửa tham số để phù hợp với HTTPTestClient.connect
                port=self.port,
                connect_timeout=self.http_connect_timeout,
                read_timeout=self.http_read_timeout
            )
    
    def is_connected(self) -> bool:
        """Check if connected to remote host"""
        if self.connection_type == self.SSH_MODE:
            return self.ssh_connection is not None and self.ssh_connection.is_connected()
        else:
            return self.http_client.is_connected()
    
    def disconnect(self) -> None:
        """Disconnect from remote host"""
        if self.connection_type == self.SSH_MODE and self.ssh_connection is not None:
            self.ssh_connection.disconnect()
        else:
            self.http_client.disconnect()
    
    def send_test(self, test_data: Dict[str, Any], test_file_path: Optional[str] = "", 
                affects_network: bool = False) -> Tuple[bool, Optional[Dict], str]:
        """
        Send test to remote host and wait for result
        - In SSH mode, uploads file and waits for result file
        - In HTTP mode, sends test data directly and gets result
        """
        if self.connection_type == self.SSH_MODE:
            # If SSH is needed but not initialized
            if self.ssh_connection is None:
                self.logger.warning("SSH connection requested but not initialized")
                try:
                    ssh_module = importlib.import_module('network.ssh_connection')
                    SSHConnection = getattr(ssh_module, 'SSHConnection')
                    self.ssh_connection = SSHConnection()
                except (ImportError, AttributeError) as e:
                    self.logger.error(f"Could not load SSH module: {e}")
                    return False, None, f"SSH module error: {e}"
                
            # Legacy SSH method (not fully implemented here)
            # Would need implementation if SSH fallback is required
            return False, None, "SSH result handling not implemented"
            
        else:
            # HTTP method - send test data directly
            # Adjust timeout for network-affecting tests
            original_timeout = self.http_client.read_timeout
            
            if affects_network:
                self.http_client.read_timeout = original_timeout * 2
                self.logger.info(f"Extended timeout for network-affecting test: {self.http_client.read_timeout}s")
            
            try:
                return self.http_client.send_test(test_data)
            finally:
                # Reset timeout
                if affects_network:
                    self.http_client.read_timeout = original_timeout