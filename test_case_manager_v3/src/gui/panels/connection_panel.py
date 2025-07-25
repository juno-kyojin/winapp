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
                status_callback: Optional[Callable[[str], None]] = None,
                tab_switch_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Initialize the connection panel.

        Args:
            parent: Parent widget
            test_executor: Test executor instance
            config: Application configuration
            status_callback: Callback for status updates
            tab_switch_callback: Callback for switching tabs
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.test_executor = test_executor
        self.config = config
        self.status_callback = status_callback
        self.tab_switch_callback = tab_switch_callback

        # Connection state
        self.is_connected = False

        # Default HTTP connection settings
        default_http_port = 6969  # Updated to match actual config
        default_connect_timeout = 5
        default_read_timeout = 40

        # HTTP Connection variables only
        self.host_var = tk.StringVar(value="192.168.1.1")
        self.http_port_var = tk.StringVar(value=str(default_http_port))
        self.http_connect_timeout_var = tk.StringVar(value=str(default_connect_timeout))
        self.http_read_timeout_var = tk.StringVar(value=str(default_read_timeout))
        self.connection_status_var = tk.StringVar(value="Not Connected")

        # UI components that need state management
        self.connect_button: Optional[ttk.Button] = None
        self.disconnect_button: Optional[ttk.Button] = None
        self.status_label: Optional[ttk.Label] = None

        # Create UI
        self._create_ui()

        # Load HTTP settings from config
        self._load_settings_from_config()
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # HTTP Connection header (no more connection type selection)
        header_frame = ttk.LabelFrame(self, text="🌐 HTTP Connection", padding=(15, 10))
        header_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        # HTTP Connection settings frame
        self.settings_frame = ttk.LabelFrame(self, text="📋 Connection Settings", padding=(15, 10))
        self.settings_frame.pack(fill=tk.X, padx=15, pady=5)

        # Host frame
        host_frame = ttk.Frame(self.settings_frame)
        host_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            host_frame,
            text="Host:",
            width=15,
            anchor=tk.W,
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT)

        ttk.Entry(
            host_frame,
            textvariable=self.host_var,
            width=30,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=5)

        # HTTP settings frame (directly in settings_frame, no separate frame needed)
        self.http_frame = self.settings_frame

        # HTTP port
        http_port_frame = ttk.Frame(self.http_frame)
        http_port_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            http_port_frame,
            text="Port:",
            width=15,
            anchor=tk.W,
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT)

        ttk.Entry(
            http_port_frame,
            textvariable=self.http_port_var,
            width=10,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=5)

        # HTTP connect timeout
        http_connect_frame = ttk.Frame(self.http_frame)
        http_connect_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            http_connect_frame,
            text="Connect Timeout:",
            width=15,
            anchor=tk.W,
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT)

        ttk.Entry(
            http_connect_frame,
            textvariable=self.http_connect_timeout_var,
            width=10,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            http_connect_frame,
            text="seconds",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)

        # HTTP read timeout
        http_read_frame = ttk.Frame(self.http_frame)
        http_read_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            http_read_frame,
            text="Read Timeout:",
            width=15,
            anchor=tk.W,
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT)

        ttk.Entry(
            http_read_frame,
            textvariable=self.http_read_timeout_var,
            width=10,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            http_read_frame,
            text="seconds",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)


        # Connection actions frame
        actions_frame = ttk.Frame(self)
        actions_frame.pack(fill=tk.X, padx=15, pady=10)

        # Primary action buttons with state management
        self.connect_button = ttk.Button(
            actions_frame,
            text="🔗 Connect",
            command=self._connect,
            style="Accent.TButton"
        )
        self.connect_button.pack(side=tk.LEFT, padx=(0, 10))

        self.disconnect_button = ttk.Button(
            actions_frame,
            text="🔌 Disconnect",
            command=self._disconnect,
            state="disabled"  # Initially disabled
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=(0, 10))

        # Remove Test Connection button - redundant with Connect

        ttk.Button(
            actions_frame,
            text="💾 Save Settings",
            command=self._save_settings
        ).pack(side=tk.RIGHT)

        # Connection status frame with visual indicator
        status_frame = ttk.LabelFrame(self, text="📊 Connection Status", padding=(15, 10))
        status_frame.pack(fill=tk.X, padx=15, pady=5)

        # Status with visual indicator
        status_container = ttk.Frame(status_frame)
        status_container.pack(fill=tk.X)

        # Status indicator (colored circle)
        self.status_indicator = ttk.Label(
            status_container,
            text="🔴",  # Red circle for disconnected
            font=("Segoe UI", 12)
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 10))

        self.status_label = ttk.Label(
            status_container,
            textvariable=self.connection_status_var,
            font=("Segoe UI", 9, "bold")
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _load_http_settings(self) -> None:
        """Load HTTP settings from config."""
        # Set HTTP host from config
        self.host_var.set(self.config.network.http_host)
    
    def _connect(self) -> None:
        """Connect to the HTTP device."""
        # Get connection parameters
        host = self.host_var.get()

        if not host:
            messagebox.showerror("Connection Error", "Host cannot be empty")
            return

        # Update status
        self._update_status("Connecting...")

        # Create HTTP connection parameters
        params: Dict[str, Any] = {
            "connection_type": "http"
        }

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
                self._update_status(f"✅ Connected to {host}")
                self._update_connection_status(True)

                # Auto-switch to Templates tab after successful connection
                if self.tab_switch_callback:
                    # Use root's after_idle to ensure UI updates happen on main thread
                    root = self.winfo_toplevel()
                    if root and hasattr(root, 'after_idle'):
                        root.after_idle(lambda: self.tab_switch_callback("Templates") if self.tab_switch_callback else None)
            else:
                self._update_status("❌ Connection failed")
                self._update_connection_status(False)
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self._update_status(f"❌ Connection error: {str(e)}")
            self._update_connection_status(False)
    
    def _disconnect(self) -> None:
        """Disconnect from the device."""
        try:
            self.test_executor.disconnect()
            self._update_status("🔌 Disconnected")
            self._update_connection_status(False)
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
            self._update_status(f"❌ Disconnect error: {str(e)}")
            self._update_connection_status(False)
    


    def _load_settings_from_config(self) -> None:
        """Load HTTP connection settings from configuration."""
        try:
            # Load network configuration
            network_config = self.config.network

            # Set HTTP host and settings
            self.host_var.set(network_config.http_host)
            self.http_port_var.set(str(network_config.http_port))
            self.http_connect_timeout_var.set(str(network_config.http_connect_timeout))
            self.http_read_timeout_var.set(str(network_config.http_read_timeout))

            self.logger.info("HTTP settings loaded from configuration")

        except Exception as e:
            self.logger.error(f"Load settings error: {e}")
            self._update_status(f"Failed to load settings: {str(e)}")

    def _save_settings(self) -> None:
        """Save HTTP connection settings to configuration."""
        try:
            # Update network configuration with current HTTP UI values
            host_value = self.host_var.get()

            # Set connection type to HTTP only
            self.config.network.connection_type = "http"
            self.config.network.http_host = host_value

            # Update HTTP settings
            self.config.network.http_port = int(self.http_port_var.get())
            self.config.network.http_connect_timeout = int(self.http_connect_timeout_var.get())
            self.config.network.http_read_timeout = int(self.http_read_timeout_var.get())

            # Save configuration to file
            save_config(self.config)

            messagebox.showinfo("Settings Saved", "HTTP connection settings saved successfully")
            self._update_status("HTTP connection settings saved")
            self.logger.info("HTTP connection settings saved to configuration file")

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
        Update the connection status and UI elements.

        Args:
            connected: Whether the connection is active
        """
        self.is_connected = connected

        if connected:
            # Connection successful - update UI
            if self.connect_button:
                self.connect_button.config(state="disabled")
            if self.disconnect_button:
                self.disconnect_button.config(state="normal")
            if self.status_indicator:
                self.status_indicator.config(text="🟢")  # Green circle
        else:
            # Connection failed/disconnected - update UI
            if self.connect_button:
                self.connect_button.config(state="normal")
            if self.disconnect_button:
                self.disconnect_button.config(state="disabled")
            if self.status_indicator:
                self.status_indicator.config(text="🔴")  # Red circle

    def get_connection_status(self) -> bool:
        """
        Get the current connection status.

        Returns:
            bool: True if connected, False otherwise
        """
        return self.is_connected    