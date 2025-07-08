#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Connection Panel for Test Case Manager v1.0

This module provides a panel for managing device connections.

Author: juno-kyojin
Created: 2025-06-25
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Dict, Any, Optional, Callable

from src.core.config import AppConfig, save_config
from src.network.test_executor import TestExecutor
from src.utils.logger import get_logger


class ConnectionPanel(ttk.Frame):
    """
    Panel for managing device connections.
    
    This panel provides UI for configuring and managing connections
    to network devices.
    """
    
    def __init__(self, parent: tk.Widget, test_executor: TestExecutor,
                config: AppConfig,
                status_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Initialize the connection panel.
        
        Args:
            parent: Parent widget
            test_executor: Test executor instance
            config: Application configuration
            status_callback: Callback for status updates
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.test_executor = test_executor
        self.config = config
        self.status_callback = status_callback
        
        # Default connection settings
        default_http_port = 6262
        default_connect_timeout = 5
        default_read_timeout = 40
        default_ssh_port = 22
        default_ssh_username = "admin"
        
        # Connection variables
        self.connection_type_var = tk.StringVar(value="http")
        self.host_var = tk.StringVar(value="192.168.1.1")
        self.http_port_var = tk.StringVar(value=str(default_http_port))
        self.http_connect_timeout_var = tk.StringVar(value=str(default_connect_timeout))
        self.http_read_timeout_var = tk.StringVar(value=str(default_read_timeout))
        self.ssh_port_var = tk.StringVar(value=str(default_ssh_port))
        self.ssh_username_var = tk.StringVar(value=default_ssh_username)
        self.ssh_password_var = tk.StringVar(value="")
        self.connection_status_var = tk.StringVar(value="Not Connected")
        
        # Create UI
        self._create_ui()

        # Load settings from config
        self._load_settings_from_config()
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Connection type frame
        type_frame = ttk.LabelFrame(self, text="Connection Type")
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Radiobutton(
            type_frame,
            text="HTTP",
            variable=self.connection_type_var,
            value="http",
            command=self._toggle_connection_ui
        ).pack(side=tk.LEFT, padx=20, pady=5)
        
        ttk.Radiobutton(
            type_frame,
            text="SSH",
            variable=self.connection_type_var,
            value="ssh",
            command=self._toggle_connection_ui
        ).pack(side=tk.LEFT, padx=20, pady=5)
        
        # Connection settings frame
        self.settings_frame = ttk.LabelFrame(self, text="Connection Settings")
        self.settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Host frame
        host_frame = ttk.Frame(self.settings_frame)
        host_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            host_frame,
            text="Host:",
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        ttk.Entry(
            host_frame,
            textvariable=self.host_var,
            width=30
        ).pack(side=tk.LEFT, padx=5)
        
        # HTTP settings frame
        self.http_frame = ttk.Frame(self.settings_frame)
        
        # HTTP port
        http_port_frame = ttk.Frame(self.http_frame)
        http_port_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            http_port_frame,
            text="Port:",
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        ttk.Entry(
            http_port_frame,
            textvariable=self.http_port_var,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # HTTP connect timeout
        http_connect_frame = ttk.Frame(self.http_frame)
        http_connect_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            http_connect_frame,
            text="Connect Timeout:",
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        ttk.Entry(
            http_connect_frame,
            textvariable=self.http_connect_timeout_var,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            http_connect_frame,
            text="seconds"
        ).pack(side=tk.LEFT)
        
        # HTTP read timeout
        http_read_frame = ttk.Frame(self.http_frame)
        http_read_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            http_read_frame,
            text="Read Timeout:",
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        ttk.Entry(
            http_read_frame,
            textvariable=self.http_read_timeout_var,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            http_read_frame,
            text="seconds"
        ).pack(side=tk.LEFT)
        
        # SSH settings frame
        self.ssh_frame = ttk.Frame(self.settings_frame)
        
        # SSH port
        ssh_port_frame = ttk.Frame(self.ssh_frame)
        ssh_port_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            ssh_port_frame,
            text="Port:",
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        ttk.Entry(
            ssh_port_frame,
            textvariable=self.ssh_port_var,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # SSH username
        ssh_username_frame = ttk.Frame(self.ssh_frame)
        ssh_username_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            ssh_username_frame,
            text="Username:",
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        ttk.Entry(
            ssh_username_frame,
            textvariable=self.ssh_username_var,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        # SSH password
        ssh_password_frame = ttk.Frame(self.ssh_frame)
        ssh_password_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            ssh_password_frame,
            text="Password:",
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        ttk.Entry(
            ssh_password_frame,
            textvariable=self.ssh_password_var,
            width=20,
            show="*"
        ).pack(side=tk.LEFT, padx=5)
        
        # Show appropriate connection frame
        self._toggle_connection_ui()
        
        # Connection actions frame
        actions_frame = ttk.Frame(self)
        actions_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(
            actions_frame,
            text="Connect",
            command=self._connect
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            actions_frame,
            text="Disconnect",
            command=self._disconnect
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            actions_frame,
            text="Test Connection",
            command=self.test_connection
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            actions_frame,
            text="Save Settings",
            command=self._save_settings
        ).pack(side=tk.LEFT, padx=5)
        
        # Connection status frame
        status_frame = ttk.LabelFrame(self, text="Connection Status")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        status_label = ttk.Label(
            status_frame,
            textvariable=self.connection_status_var,
            padding=10
        )
        status_label.pack(fill=tk.X)
    
    def _toggle_connection_ui(self) -> None:
        """Toggle between HTTP and SSH connection UI."""
        connection_type = self.connection_type_var.get()

        # Update host field based on connection type
        if connection_type == "http":
            # Switch to HTTP host
            self.host_var.set(self.config.network.http_host)
            self.ssh_frame.pack_forget()
            self.http_frame.pack(fill=tk.X)
        else:
            # Switch to SSH host
            self.host_var.set(self.config.network.ssh_host)
            self.http_frame.pack_forget()
            self.ssh_frame.pack(fill=tk.X)
    
    def _connect(self) -> None:
        """Connect to the device."""
        # Get connection parameters
        host = self.host_var.get()
        connection_type = self.connection_type_var.get()
        
        if not host:
            messagebox.showerror("Connection Error", "Host cannot be empty")
            return
        
        # Update status
        self._update_status("Connecting...")
        
        # Create connection parameters
        params: Dict[str, Any] = {
            "connection_type": connection_type
        }
        
        if connection_type == "http":
            try:
                port = int(self.http_port_var.get())
                connect_timeout = int(self.http_connect_timeout_var.get())
                read_timeout = int(self.http_read_timeout_var.get())
                
                params["port"] = port
                params["connect_timeout"] = connect_timeout
                params["read_timeout"] = read_timeout
            except ValueError:
                messagebox.showerror("Connection Error", "Invalid HTTP parameters")
                self._update_status("Not Connected")
                return
        else:  # SSH
            try:
                port = int(self.ssh_port_var.get())
                params["port"] = port
                params["username"] = self.ssh_username_var.get()
                params["password"] = self.ssh_password_var.get()
            except ValueError:
                messagebox.showerror("Connection Error", "Invalid SSH parameters")
                self._update_status("Not Connected")
                return
        
        # Connect in a separate thread
        threading.Thread(
            target=self._connect_thread,
            args=(host, params),
            daemon=True
        ).start()
    
    def _connect_thread(self, host: str, params: Dict[str, Any]) -> None:
        """
        Connect to the device in a separate thread.
        
        Args:
            host: Host to connect to
            params: Connection parameters
        """
        try:
            success = self.test_executor.connect(host, **params)
            
            if success:
                self._update_status(f"Connected to {host}")
                self._update_connection_status(True)
            else:
                self._update_status("Connection failed")
                self._update_connection_status(False)
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self._update_status(f"Connection error: {str(e)}")
            self._update_connection_status(False)
    
    def _disconnect(self) -> None:
        """Disconnect from the device."""
        try:
            self.test_executor.disconnect()
            self._update_status("Disconnected")
            self._update_connection_status(False)
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
            self._update_status(f"Disconnect error: {str(e)}")
    
    def test_connection(self) -> None:
        """Test the connection to the device."""
        if not self.test_executor.connection_manager.is_connected():
            messagebox.showinfo("Connection Test", "Not connected. Please connect first.")
            return
        
        # Update status
        self._update_status("Testing connection...")
        
        # Test in a separate thread
        threading.Thread(
            target=self._test_connection_thread,
            daemon=True
        ).start()
    
    def _test_connection_thread(self) -> None:
        """Test the connection in a separate thread."""
        try:
            if self.test_executor.connection_manager.is_connected():
                self._update_status("Connection test successful")
                messagebox.showinfo("Connection Test", "Connection test successful")
            else:
                self._update_status("Connection test failed")
                messagebox.showerror("Connection Test", "Connection test failed")
                self._update_connection_status(False)
        except Exception as e:
            self.logger.error(f"Connection test error: {e}")
            self._update_status(f"Connection test error: {str(e)}")
            messagebox.showerror("Connection Test", f"Connection test error: {str(e)}")
            self._update_connection_status(False)

    def _load_settings_from_config(self) -> None:
        """Load connection settings from configuration."""
        try:
            # Load network configuration
            network_config = self.config.network

            # Set connection type
            self.connection_type_var.set(network_config.connection_type)

            # Set host based on connection type
            if network_config.connection_type == "http":
                self.host_var.set(network_config.http_host)
            else:
                self.host_var.set(network_config.ssh_host)

            # Set HTTP settings
            self.http_port_var.set(str(network_config.http_port))
            self.http_connect_timeout_var.set(str(network_config.http_connect_timeout))
            self.http_read_timeout_var.set(str(network_config.http_read_timeout))

            # Set SSH settings
            self.ssh_port_var.set(str(network_config.ssh_port))
            self.ssh_username_var.set(network_config.ssh_username)
            self.ssh_password_var.set(network_config.ssh_password)

            # Update UI to show correct connection type
            self._toggle_connection_ui()

            self.logger.info("Settings loaded from configuration")

        except Exception as e:
            self.logger.error(f"Load settings error: {e}")
            self._update_status(f"Failed to load settings: {str(e)}")

    def _save_settings(self) -> None:
        """Save connection settings to configuration."""
        try:
            # Update network configuration with current UI values
            connection_type = self.connection_type_var.get()
            host_value = self.host_var.get()

            self.config.network.connection_type = connection_type

            # Update appropriate host field based on connection type
            if connection_type == "http":
                self.config.network.http_host = host_value
            else:
                self.config.network.ssh_host = host_value

            # Update other settings
            self.config.network.http_port = int(self.http_port_var.get())
            self.config.network.http_connect_timeout = int(self.http_connect_timeout_var.get())
            self.config.network.http_read_timeout = int(self.http_read_timeout_var.get())
            self.config.network.ssh_port = int(self.ssh_port_var.get())
            self.config.network.ssh_username = self.ssh_username_var.get()
            self.config.network.ssh_password = self.ssh_password_var.get()

            # Save configuration to file
            save_config(self.config)

            messagebox.showinfo("Settings Saved", "Connection settings saved successfully")
            self._update_status("Connection settings saved")
            self.logger.info("Connection settings saved to configuration file")

        except ValueError as e:
            error_msg = f"Invalid input values: {str(e)}"
            self.logger.error(f"Save settings error: {error_msg}")
            messagebox.showerror("Save Error", error_msg)
        except Exception as e:
            error_msg = f"Failed to save settings: {str(e)}"
            self.logger.error(f"Save settings error: {error_msg}")
            messagebox.showerror("Save Error", error_msg)
    
    def _update_status(self, message: str) -> None:
        """
        Update the status message.
        
        Args:
            message: Status message
        """
        self.connection_status_var.set(message)
        
        if self.status_callback:
            self.status_callback(message)
    
    def _update_connection_status(self, connected: bool) -> None:
        """
        Update the connection status.
        
        Args:
            connected: Whether the connection is active
        """
        # This would typically update a status indicator in the main window
        pass 