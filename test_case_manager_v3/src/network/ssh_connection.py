# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# """
# SSH Connection Manager for Test Case Manager v3.0

# This module provides SSH connection functionality for communicating with
# network devices via SSH.

# Author: juno-kyojin
# Created: 2025-06-17
# """

# import os
# import time
# import logging
# from typing import Dict, Any, Tuple, Optional, List, Union

# try:
#     import paramiko
#     SSH_AVAILABLE = True
# except ImportError:
#     SSH_AVAILABLE = False

# from utils.logger import get_logger


# class SSHConnection:
#     """
#     SSH connection manager for network devices.
    
#     This class handles SSH connections to network devices, including
#     command execution, file transfers, and connection management.
#     """
    
#     def __init__(self) -> None:
#         """Initialize the SSH connection manager."""
#         self.logger = get_logger(__name__)
#         self.client: Optional['paramiko.SSHClient'] = None
#         self.sftp: Optional['paramiko.SFTPClient'] = None
#         self.hostname: Optional[str] = None
#         self.username: Optional[str] = None
#         self.password: Optional[str] = None
#         self.connected: bool = False
        
#         if not SSH_AVAILABLE:
#             self.logger.warning("Paramiko not available. SSH functionality disabled.")
    
#     def connect(self, hostname: str, username: str, password: str, 
#                 timeout: int = 10) -> bool:
#         """
#         Connect to a remote host via SSH.
        
#         Args:
#             hostname: Target host name or IP address
#             username: SSH username
#             password: SSH password
#             timeout: Connection timeout in seconds
            
#         Returns:
#             True if connection successful, False otherwise
#         """
#         if not SSH_AVAILABLE:
#             self.logger.error("Cannot connect: Paramiko not available")
#             return False
            
#         try:
#             self.hostname = hostname
#             self.username = username
#             self.password = password
            
#             self.client = paramiko.SSHClient()
#             self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#             self.client.connect(
#                 hostname=hostname,
#                 username=username,
#                 password=password,
#                 timeout=timeout
#             )
            
#             # Initialize SFTP
#             self.sftp = self.client.open_sftp()
            
#             self.connected = True
#             self.logger.info(f"SSH connection established to {hostname}")
#             return True
            
#         except Exception as e:
#             self.logger.error(f"SSH connection failed: {str(e)}")
#             self.client = None
#             self.sftp = None
#             self.connected = False
#             return False
    
#     def is_connected(self) -> bool:
#         """
#         Check if SSH connection is active.
        
#         Returns:
#             True if connected, False otherwise
#         """
#         if not self.client or not self.connected:
#             return False
            
#         try:
#             # Try a simple command to check connection
#             _, stdout, _ = self.client.exec_command("echo 1")
#             result = stdout.read().decode().strip()
#             return result == "1"
#         except:
#             self.connected = False
#             return False
    
#     def disconnect(self) -> None:
#         """Close SSH connection and clean up resources."""
#         if self.sftp:
#             try:
#                 self.sftp.close()
#             except:
#                 pass
#             self.sftp = None
            
#         if self.client:
#             try:
#                 self.client.close()
#             except:
#                 pass
#             self.client = None
            
#         self.connected = False
#         self.logger.info("SSH connection closed")
    
#     def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
#         """
#         Execute a command on the remote host.
        
#         Args:
#             command: Command to execute
#             timeout: Command timeout in seconds
            
#         Returns:
#             Tuple containing (success flag, stdout, stderr)
#         """
#         if not self.is_connected():
#             return False, "", "Not connected"
            
#         try:
#             self.logger.debug(f"Executing command: {command}")
#             _, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            
#             stdout_data = stdout.read().decode()
#             stderr_data = stderr.read().decode()
#             exit_code = stdout.channel.recv_exit_status()
            
#             success = exit_code == 0
#             if not success:
#                 self.logger.error(f"Command failed with exit code {exit_code}")
#                 self.logger.error(f"stderr: {stderr_data}")
            
#             return success, stdout_data, stderr_data
            
#         except Exception as e:
#             self.logger.error(f"Command execution failed: {str(e)}")
#             return False, "", str(e)
    
#     def upload_file(self, local_path: str, remote_path: str) -> bool:
#         """
#         Upload a file to the remote host.
        
#         Args:
#             local_path: Path to local file
#             remote_path: Path on remote host
            
#         Returns:
#             True if successful, False otherwise
#         """
#         if not self.is_connected() or not self.sftp:
#             return False
            
#         try:
#             self.logger.debug(f"Uploading {local_path} to {remote_path}")
#             self.sftp.put(local_path, remote_path)
#             return True
#         except Exception as e:
#             self.logger.error(f"File upload failed: {str(e)}")
#             return False
    
#     def download_file(self, remote_path: str, local_path: str) -> bool:
#         """
#         Download a file from the remote host.
        
#         Args:
#             remote_path: Path on remote host
#             local_path: Path to local file
            
#         Returns:
#             True if successful, False otherwise
#         """
#         if not self.is_connected() or not self.sftp:
#             return False
            
#         try:
#             self.logger.debug(f"Downloading {remote_path} to {local_path}")
#             self.sftp.get(remote_path, local_path)
#             return True
#         except Exception as e:
#             self.logger.error(f"File download failed: {str(e)}")
#             return False 