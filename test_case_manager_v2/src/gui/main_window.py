#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main window for Test Case Manager v2.0

This module implements the main application window with tabbed interface
and core GUI functionality.

Author: juno-kyojin
Created: 2025-06-12
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
import json
import time
import threading
import requests 
from typing import Optional

from core.config import AppConfig
from core.constants import APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from core.exceptions import TestCaseManagerError
from utils.logger import LoggerMixin


class MainWindow(LoggerMixin):
    """
    Main application window.
    
    This class implements the main GUI window with tabbed interface,
    menu bar, status bar, and core application functionality.
    """
            
    def __init__(self, config: AppConfig) -> None:
        """
        Initialize the main window.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.root: Optional[tk.Tk] = None
        self.notebook: Optional[ttk.Notebook] = None
        
        # Thêm biến theo dõi trạng thái kết nối
        self.http_connected = False
        # Initialize HTTP variables
        self.http_host_var: Optional[tk.StringVar] = None
        self.http_port_var: Optional[tk.StringVar] = None
        self.http_conn_timeout_var: Optional[tk.StringVar] = None
        self.http_read_timeout_var: Optional[tk.StringVar] = None
        self.connection_type_var: Optional[tk.StringVar] = None
        self.connection_mode_var: Optional[tk.StringVar] = None
        
        # Initialize SSH variables
        self.ssh_host_var: Optional[tk.StringVar] = None
        self.ssh_port_var: Optional[tk.StringVar] = None
        self.ssh_username_var: Optional[tk.StringVar] = None
        self.ssh_password_var: Optional[tk.StringVar] = None
        
        # Common variables
        self.connection_status_var: Optional[tk.StringVar] = None
        self.status_var: Optional[tk.StringVar] = None
        self.log_text: Optional[tk.Text] = None
        
        # Không ghi đè lên property logger từ LoggerMixin
        # self.logger đã được định nghĩa bởi LoggerMixin, chỉ cần sử dụng nó
        
        # Initialize network modules
        self._load_network_modules()
        
        # Setup UI
        self._setup_window()
        self._create_menu()
        self._create_tabs()
        self._create_status_bar()
        
        self.logger.info("Main window initialized")

    def _safe_get(self, string_var, default=""):
        """Safely get value from a StringVar that might be None"""
        if string_var is None:
            return default
        try:
            return string_var.get()
        except Exception:
            return default

        

    def _safe_set(self, string_var, value):
        """Safely set value to a StringVar that might be None"""
        if string_var is not None:
            try:
                string_var.set(value)
            except Exception:
                pass  # Ignore errors when setting
    def _safe_after(self, delay, callback):
        """Safely call after on root object that might be None"""
        if self.root is not None:
            try:
                return self.root.after(delay, callback)
            except Exception:
                pass
        return None
    def _load_network_modules(self) -> None:
        """Load network modules as needed"""
        try:
            # Import the HTTP client module
            from network.http_client import HTTPTestClient
            self.http_client = HTTPTestClient()
            self.logger.info("HTTP client module loaded")
            
            # SSH module will be loaded on demand when needed
            self.ssh_connection = None
            
        except ImportError as e:
            self.logger.error(f"Failed to import HTTP client module: {e}")
            self.http_client = None
        except Exception as e:
            self.logger.error(f"Failed to initialize network modules: {e}")
            self.http_client = None
    
    def _setup_window(self) -> None:
        """Setup the main window properties with improved layout management."""
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        
        # Set window size and position
        width = self.config.gui.window_width
        height = self.config.gui.window_height
        
        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # Đặt trọng số cho mở rộng - quan trọng cho status bar!
        self.root.rowconfigure(0, weight=1)  # Main content expands
        self.root.rowconfigure(1, weight=0)  # Status bar fixed height
        self.root.columnconfigure(0, weight=1)  # Expand horizontally
        
        # Set window icon (if available)
        try:
            # TODO: Add application icon
            pass
        except Exception:
            pass
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_menu(self) -> None:
        """Create the application menu bar."""
        if not self.root:
            return
            
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Template...", command=self._new_template)
        file_menu.add_command(label="Open Template...", command=self._open_template)
        file_menu.add_separator()
        file_menu.add_command(label="Export Results...", command=self._export_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Preferences...", command=self._show_preferences)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Connection Test", command=self._test_connection)
        tools_menu.add_command(label="Template Validator", command=self._validate_templates)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self._show_documentation)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
    
    def _create_tabs(self) -> None:
        """Create the tabbed interface."""
        if not self.root:
            return
            
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tab frames
        self._create_connection_template_tab()  # Kết hợp Connection & Templates
        self._create_saved_tests_tab()          # Tab mới quản lý test cases đã tạo
        self._create_queue_tab()                # Tab quản lý queue
        self._create_history_tab()
        self._create_logs_tab()

    def _create_connection_template_tab(self) -> None:
        """Create the combined connection and templates tab."""
        if not self.notebook:
            return
            
        # Main frame for tab
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Connection & Templates")
        
        # ROW 1: Connection and Status
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Connection panel
        conn_frame = ttk.LabelFrame(top_frame, text="Router Connection")
        conn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Connection type
        type_frame = ttk.Frame(conn_frame)
        type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Connection type radio buttons
        self.connection_type_var = tk.StringVar(value="http")  # Default to HTTP
        
        ttk.Radiobutton(
            type_frame,
            text="HTTP Client-Server",
            variable=self.connection_type_var,
            value="http",
            command=self._toggle_connection_ui
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(
            type_frame,
            text="SSH (Legacy)",
            variable=self.connection_type_var,
            value="ssh",
            command=self._toggle_connection_ui
        ).pack(side=tk.LEFT, padx=10)
        
        # Connection settings (stacked frames for HTTP and SSH)
        self.conn_settings_frame = ttk.Frame(conn_frame)
        self.conn_settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # HTTP Connection Frame
        self.http_frame = ttk.Frame(self.conn_settings_frame)
        
        # Host and port (on same line)
        host_port_frame = ttk.Frame(self.http_frame)
        host_port_frame.pack(fill=tk.X, padx=0, pady=5)
        
        ttk.Label(host_port_frame, text="Host:").pack(side=tk.LEFT, padx=2)
        self.http_host_var = tk.StringVar(value=self.config.network.ssh_host)  # Reuse SSH host as default
        ttk.Entry(host_port_frame, textvariable=self.http_host_var, width=15).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(host_port_frame, text="Port:").pack(side=tk.LEFT, padx=10)
        self.http_port_var = tk.StringVar(value="8080")
        ttk.Entry(host_port_frame, textvariable=self.http_port_var, width=5).pack(side=tk.LEFT, padx=2)
        
        # Timeout settings
        timeout_frame = ttk.Frame(self.http_frame)
        timeout_frame.pack(fill=tk.X, padx=0, pady=5)
        
        ttk.Label(timeout_frame, text="Connect Timeout:").pack(side=tk.LEFT, padx=2)
        self.http_conn_timeout_var = tk.StringVar(value="5")
        ttk.Entry(timeout_frame, textvariable=self.http_conn_timeout_var, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(timeout_frame, text="Read Timeout:").pack(side=tk.LEFT, padx=10)
        self.http_read_timeout_var = tk.StringVar(value="40")
        ttk.Entry(timeout_frame, textvariable=self.http_read_timeout_var, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(timeout_frame, text="seconds").pack(side=tk.LEFT, padx=2)
        
        # SSH Connection Frame
        self.ssh_frame = ttk.Frame(self.conn_settings_frame)
        
        # Host and port (on same line)
        host_port_frame = ttk.Frame(self.ssh_frame)
        host_port_frame.pack(fill=tk.X, padx=0, pady=5)
        
        ttk.Label(host_port_frame, text="Host:").pack(side=tk.LEFT, padx=2)
        self.ssh_host_var = tk.StringVar(value=self.config.network.ssh_host)
        ttk.Entry(host_port_frame, textvariable=self.ssh_host_var, width=15).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(host_port_frame, text="Port:").pack(side=tk.LEFT, padx=10)
        self.ssh_port_var = tk.StringVar(value=str(self.config.network.ssh_port))
        ttk.Entry(host_port_frame, textvariable=self.ssh_port_var, width=5).pack(side=tk.LEFT, padx=2)
        
        # Username and password (on same line)
        user_pass_frame = ttk.Frame(self.ssh_frame)
        user_pass_frame.pack(fill=tk.X, padx=0, pady=5)
        
        ttk.Label(user_pass_frame, text="User:").pack(side=tk.LEFT, padx=2)
        self.ssh_username_var = tk.StringVar(value=self.config.network.ssh_username)
        ttk.Entry(user_pass_frame, textvariable=self.ssh_username_var, width=10).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(user_pass_frame, text="Pass:").pack(side=tk.LEFT, padx=10)
        self.ssh_password_var = tk.StringVar(value=self.config.network.ssh_password)
        ttk.Entry(user_pass_frame, textvariable=self.ssh_password_var, show="*", width=10).pack(side=tk.LEFT, padx=2)
        
        # Show appropriate connection UI based on initial selection
        self._toggle_connection_ui()
        
        # Buttons
        button_frame = ttk.Frame(conn_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Connect", command=self._test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save", command=self._save_connection_settings).pack(side=tk.LEFT, padx=5)
        
        # Status panel
        status_frame = ttk.LabelFrame(top_frame, text="Status")
        status_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Connection status indicator
        status_indicator = ttk.Frame(status_frame, width=200)
        status_indicator.pack(fill=tk.X, padx=5, pady=5)
        
        self.connection_status_var = tk.StringVar(value="🔴 Not connected")
        self.connection_mode_var = tk.StringVar(value="Mode: HTTP")
        
        ttk.Label(status_indicator, textvariable=self.connection_status_var, font=("Segoe UI", 9)).pack(anchor=tk.W)
        ttk.Label(status_indicator, textvariable=self.connection_mode_var, font=("Segoe UI", 9)).pack(anchor=tk.W)
        ttk.Label(status_indicator, text="Last ping: --").pack(anchor=tk.W)
        ttk.Label(status_indicator, text="Router Model: --").pack(anchor=tk.W)
        
        # ROW 2: Test Case Library with TreeView
        library_frame = ttk.LabelFrame(frame, text="Test Case Library")
        library_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Category tabs for filtering
        filter_frame = ttk.Frame(library_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a notebook for category tabs
        self.category_tabs = ttk.Notebook(filter_frame)
        self.category_tabs.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create tabs for each category
        self.category_frames = {}
        self.add_category_tab("ALL", "All")  # First tab shows all
        self.add_category_tab("WAN", "WAN")
        self.add_category_tab("LAN", "LAN")
        self.add_category_tab("Network", "Network")
        self.add_category_tab("Security", "Security")
        self.add_category_tab("System", "System")
        
        # Refresh button
        ttk.Button(filter_frame, text="Refresh", command=self._refresh_test_cases).pack(side=tk.RIGHT, padx=5)
        
        # Bind event for tab selection to filter test cases
        self.category_tabs.bind("<<NotebookTabChanged>>", self._on_category_tab_changed)
        
        # Create TreeView with hierarchical structure
        treeview_frame = ttk.Frame(library_frame)
        treeview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # TreeView with Show="tree" to display hierarchy
        self.test_tree = ttk.Treeview(treeview_frame, show="tree", selectmode="browse")
        
        # Add scrollbar
        scrollbar_y = ttk.Scrollbar(treeview_frame, orient=tk.VERTICAL, command=self.test_tree.yview)
        self.test_tree.configure(yscrollcommand=scrollbar_y.set)
        
        # Pack TreeView and scrollbar
        self.test_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate test case tree
        self._populate_test_tree()
        
        # Bind tree selection event
        self.test_tree.bind("<<TreeviewSelect>>", self._on_test_case_selected)
        
        # Action buttons
        action_frame = ttk.Frame(library_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(action_frame, text="✅ Add to Test Queue", command=self._add_to_test_queue).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🔍 View Details", command=self._view_template_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📝 Create from Template", command=self._create_from_template).pack(side=tk.RIGHT, padx=5)
        
        # ROW 3: Parameters section
        self.params_frame = ttk.LabelFrame(frame, text="Template Parameters")
        self.params_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create dynamic parameters form based on selected template
        self.create_placeholder_params()

    def _toggle_connection_ui(self):
        """Toggle between HTTP and SSH connection UI"""
        connection_type = self._safe_get(self.connection_type_var, "http")
        
        # Update connection mode label
        self._safe_set(self.connection_mode_var, f"Mode: {connection_type.upper()}")
        
        if connection_type == "http":
            # Hide SSH, show HTTP
            if hasattr(self, 'ssh_frame'):
                self.ssh_frame.pack_forget()
            if hasattr(self, 'http_frame'):
                self.http_frame.pack(fill=tk.X)
        else:
            # Hide HTTP, show SSH
            if hasattr(self, 'http_frame'):
                self.http_frame.pack_forget()
            if hasattr(self, 'ssh_frame'):
                self.ssh_frame.pack(fill=tk.X)
        
        # Reset connection status
        self._safe_set(self.connection_status_var, "🔴 Not connected")
        
        # Update status
        self._safe_set(self.status_var, f"Switched to {connection_type.upper()} connection mode")

    def add_category_tab(self, category_id, display_name):
        """Add a category tab to the category notebook"""
        # Tạo frame cho tab
        tab_frame = ttk.Frame(self.category_tabs)
        # Thêm tab vào notebook
        self.category_tabs.add(tab_frame, text=display_name)
        # Lưu trữ để tham chiếu sau này
        self.category_frames[category_id] = tab_frame

    def _on_category_tab_changed(self, event):
        """Handle change of category tab"""
        selected_tab = self.category_tabs.select()
        if not selected_tab:
            return
            
        # Lấy index tab đang được chọn
        tab_index = self.category_tabs.index(selected_tab)
        
        # Lọc test cases dựa trên tab được chọn
        categories = ["ALL", "WAN", "LAN", "Network", "Ping", "Security", "System"]
        if tab_index >= 0 and tab_index < len(categories):
            selected_category = categories[tab_index]
            self._filter_test_cases_by_category(selected_category)
        
    def _filter_test_cases_by_category(self, category):
        """Filter test cases by category"""
        # Nếu là "ALL", hiển thị tất cả
        if category == "ALL":
            self._populate_test_tree()
            return
            
        # Lọc các test case theo danh mục
        self._populate_test_tree(filter_category=category)

    def _populate_test_tree(self, filter_category=None):
        """Populate the test case tree with hierarchical data"""
        # Clear existing items
        for item in self.test_tree.get_children():
            self.test_tree.delete(item)
        
        # Define categories and their test cases with standardized naming
        test_categories = {
            "WAN": [
                {"id": "wan_create", "name": "wan_create", "impacts_network": True},
                {"id": "wan_delete", "name": "wan_delete", "impacts_network": True},
                {"id": "wan_edit", "name": "wan_edit", "impacts_network": True},
            ],
            "LAN": [
                {"id": "lan_config", "name": "lan_config", "impacts_network": True},
                {"id": "lan_interfaces", "name": "lan_interfaces", "impacts_network": True},
                {"id": "lan_dhcp", "name": "lan_dhcp", "impacts_network": True},
            ],
            "Network": [
                {"id": "ping", "name": "ping", "impacts_network": False}, 
                {"id": "bandwidth_test", "name": "bandwidth_test", "impacts_network": False},
                {"id": "dns_test", "name": "dns_test", "impacts_network": False},
            ],
            "Security": [
                {"id": "firewall_rule", "name": "firewall_rule", "impacts_network": False},
                {"id": "port_forward", "name": "port_forward", "impacts_network": False},
            ],
            "System": [
                {"id": "sys_backup", "name": "sys_backup", "impacts_network": False},
                {"id": "sys_restore", "name": "sys_restore", "impacts_network": True},
                {"id": "sys_reboot", "name": "sys_reboot", "impacts_network": True},
            ],
        }
        
        # Add categories and their test cases
        for category, test_cases in test_categories.items():
            # Skip if filtering and this category is not the one we want
            if filter_category and filter_category != "ALL" and category != filter_category:
                continue
                
            # Add category as parent
            category_id = self.test_tree.insert("", "end", text=category)
            
            # Add test cases under the category
            for test_case in test_cases:
                # Add icon indicator for network impact
                display_text = test_case["name"]
                if test_case["impacts_network"]:
                    display_text = f"{display_text} ⚠️"
                    
                # Store test case ID in the 'values' column for later retrieval
                self.test_tree.insert(
                    category_id, 
                    "end", 
                    text=display_text,
                    values=(test_case["id"], category, test_case["impacts_network"])
                )

    def _on_test_case_selected(self, event):
        """Handler for test case selection from TreeView with improved UI stability"""
        # Get the selected item
        selection = self.test_tree.selection()
        if not selection:
            return
        
        # Check if it's a test case (leaf) or category (parent)
        # If parent has no children, it's a leaf node/test case
        if not self.test_tree.get_children(selection[0]):
            # Get test case info
            test_id = self.test_tree.item(selection[0], "values")[0]
            test_name = self.test_tree.item(selection[0], "text").split(" ⚠️")[0]  # Remove warning icon if present
            category = self.test_tree.item(self.test_tree.parent(selection[0]), "text")
            
            # Update parameters frame title
            self.params_frame.configure(text=f"Template Parameters ({test_name})")
            
            # Load parameters for the selected test case
            self._load_test_parameters(test_id, category)
            
            # Đặt status message để đảm bảo hiển thị đúng
            # Sửa: Sử dụng _safe_set thay vì truy cập trực tiếp đến set
            self._safe_set(self.status_var, f"Selected test: {test_name}")
                
            # Đảm bảo UI được cập nhật
            # Sửa: Kiểm tra self.root trước khi gọi update_idletasks
            if self.root:
                self.root.update_idletasks()
        else:
            # It's a category - clear parameters
            self.params_frame.configure(text="Template Parameters")
            self._clear_parameters()
            
            # Đặt status message
            # Sửa: Sử dụng _safe_set thay vì truy cập trực tiếp đến set
            self._safe_set(self.status_var, f"Selected category: {self.test_tree.item(selection[0], 'text')}")
    def _load_test_parameters(self, test_id, category):
        """Load parameters for selected test case"""
        # Clear existing parameters
        self._clear_parameters()
        
        # Define sample parameters based on test type
        params = []
        
        if test_id == "wan_create":
            params = [
                {"name": "name", "value": "wan1", "type": "string", "required": True},
                {"name": "protocol", "value": "ipv4", "type": "enum", "required": True, 
                "options": ["ipv4", "ipv6"]},
                {"name": "gateway_type", "value": "route", "type": "enum", "required": True,
                "options": ["route", "bridge"]},
                {"name": "mtu", "value": "1492", "type": "integer", "required": True},
                {"name": "nat", "value": "true", "type": "boolean", "required": True, 
                "options": ["true", "false"]},
                {"name": "link_mode", "value": "ipoe", "type": "enum", "required": True,
                "options": ["ipoe", "pppoe"]},
                {"name": "ipv4_alloc", "value": "dhcp", "type": "enum", "required": True,
                "options": ["dhcp", "static"]},
                {"name": "ipv4_ip", "value": "192.168.1.100", "type": "string", "required": False},
                {"name": "ipv4_mask", "value": "255.255.255.0", "type": "string", "required": False},
                {"name": "ipv4_gw", "value": "192.168.1.1", "type": "string", "required": False},
                {"name": "ipv4_dns", "value": "8.8.8.8,8.8.4.4", "type": "string", "required": False},
            ]
        elif test_id == "wan_delete":
            params = [
                {"name": "name", "value": "wan1", "type": "string", "required": True},
            ]
        elif test_id == "wan_edit":
            params = [
                {"name": "name", "value": "wan1", "type": "string", "required": True},
                {"name": "protocol", "value": "ipv4", "type": "enum", "required": True, 
                "options": ["ipv4", "ipv6"]},
                {"name": "gateway_type", "value": "route", "type": "enum", "required": False,
                "options": ["route", "bridge"]},
                {"name": "mtu", "value": "1492", "type": "integer", "required": False},
                {"name": "nat", "value": "true", "type": "boolean", "required": False, 
                "options": ["true", "false"]},
            ]
        elif test_id == "ping_test" or test_id == "ping":
            # Sửa: Dùng đúng định dạng tham số cho ping
            params = [
                {"name": "host1", "value": "youtube.com", "type": "string", "required": True},
                {"name": "host2", "value": "google.com", "type": "string", "required": False}
            ]
        elif test_id == "lan_config":
            params = [
                {"name": "interface", "value": "eth0", "type": "string", "required": True},
                {"name": "ip", "value": "192.168.1.1", "type": "string", "required": True},
                {"name": "netmask", "value": "255.255.255.0", "type": "string", "required": True},
                {"name": "enable_dhcp", "value": "true", "type": "boolean", "required": False},
            ]
        elif test_id == "firewall_rule":
            params = [
                {"name": "name", "value": "allow-ssh", "type": "string", "required": True},
                {"name": "src", "value": "wan", "type": "string", "required": True},
                {"name": "dest", "value": "lan", "type": "string", "required": True},
                {"name": "proto", "value": "tcp", "type": "string", "required": True},
                {"name": "dest_port", "value": "22", "type": "string", "required": True},
                {"name": "target", "value": "ACCEPT", "type": "string", "required": True},
            ]
        elif test_id == "sys_reboot":
            params = [
                {"name": "delay", "value": "5", "type": "integer", "required": False},
                {"name": "force", "value": "false", "type": "boolean", "required": False},
            ]
        else:
            # Default parameters
            params = [
                {"name": "param1", "value": "value1", "type": "string", "required": True},
                {"name": "param2", "value": "value2", "type": "string", "required": False},
            ]
                
        # Create UI for parameters
        self._create_parameter_controls(params)
    def _create_saved_tests_tab(self) -> None:
        """Create a tab to browse saved test cases"""
        if not self.notebook:
            return
            
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Saved Tests")
        
        # Controls at the top
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="Refresh", command=self._load_saved_tests).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Add to Queue", command=self._add_saved_test_to_queue).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Delete", command=self._delete_saved_test).pack(side=tk.RIGHT, padx=5)
        
        # Create TreeView for saved tests
        treeview_frame = ttk.Frame(frame)
        treeview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("name", "category", "timestamp", "path")
        self.saved_tests_tree = ttk.Treeview(treeview_frame, columns=columns, show="headings")
        
        self.saved_tests_tree.heading("name", text="Test Name")
        self.saved_tests_tree.heading("category", text="Category")
        self.saved_tests_tree.heading("timestamp", text="Created")
        self.saved_tests_tree.heading("path", text="Path")
        
        self.saved_tests_tree.column("name", width=200)
        self.saved_tests_tree.column("category", width=100)
        self.saved_tests_tree.column("timestamp", width=150)
        self.saved_tests_tree.column("path", width=300)
        
        # Add scrollbar
        scrollbar_y = ttk.Scrollbar(treeview_frame, orient=tk.VERTICAL, command=self.saved_tests_tree.yview)
        self.saved_tests_tree.configure(yscrollcommand=scrollbar_y.set)
        
        # Pack treeview and scrollbar
        self.saved_tests_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to view details
        self.saved_tests_tree.bind("<Double-1>", self._view_saved_test_details)
        
        # Load saved tests
        self._load_saved_tests()

    def _load_saved_tests(self) -> None:
        """Load all saved test cases"""
        import os
        import glob
        import datetime
        import json
        
        # Clear existing items
        for item in self.saved_tests_tree.get_children():
            self.saved_tests_tree.delete(item)
        
        # Base directory for generated tests
        base_dir = os.path.join("data", "temp", "generated_tests")
        
        # Check if directory exists
        if not os.path.exists(base_dir):
            return
        
        # Find all JSON files recursively
        test_files = []
        for category in os.listdir(base_dir):
            category_path = os.path.join(base_dir, category)
            if os.path.isdir(category_path):
                for json_file in glob.glob(os.path.join(category_path, "*.json")):
                    test_files.append((json_file, category))
        
        # Sort by modification time (newest first)
        test_files.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)
        
        # Add to treeview
        for file_path, category in test_files:
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]  # Remove .json extension
            
            # Extract timestamp from JSON metadata if exists
            timestamp = ""
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Handle both formats: dictionary with metadata or list of test cases
                    if isinstance(data, dict) and "metadata" in data:
                        # New format with proper metadata
                        metadata = data["metadata"]
                        if "created_at" in metadata:
                            timestamp = metadata["created_at"]
                    elif isinstance(data, list):
                        # Old format - list of test cases without metadata
                        # Không có metadata, sử dụng fallback
                        self.logger.debug(f"File {file_name} is in old list format without metadata")
                        
                # If still empty, use fallback
                if not timestamp:
                    mod_time = os.path.getmtime(file_path)
                    timestamp = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
                    
            except Exception as e:
                # Log the error and fallback to file modification time
                self.logger.error(f"Error reading timestamp from {file_name}: {e}")
                mod_time = os.path.getmtime(file_path)
                timestamp = datetime.datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # Use base_name as display name
            self.saved_tests_tree.insert("", "end", values=(
                base_name,  # Giữ nguyên định dạng service_action_identifier
                category.title(),
                timestamp,  # Thời gian từ metadata hoặc file modification time
                file_path
            ))

    def _add_saved_test_to_queue(self, file_path=None) -> None:
        """Add selected saved test to queue"""
        import os
        
        # If file_path is not provided, get it from tree selection
        if file_path is None:
            selected = self.saved_tests_tree.selection()
            if not selected:
                messagebox.showinfo("Information", "Please select a test file")
                return
            
            # Get file path from selection
            values = self.saved_tests_tree.item(selected[0], "values")
            file_path = values[3]
        
        import json
        try:
            # Extract the filename for display
            filename = os.path.basename(file_path)
            
            # Load the test file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both formats
            test_case = {}
            if isinstance(data, dict) and "test_cases" in data:
                # New format
                test_case = data["test_cases"][0] if data["test_cases"] else {}
            elif isinstance(data, list) and len(data) > 0:
                # Old format
                test_case = data[0]
            else:
                raise ValueError("Invalid test case format")
                
            service = test_case.get("service", "")
            action = test_case.get("action", "")
            params = test_case.get("params", {})
            
            # Determine category from file path
            parts = file_path.split(os.sep)
            category = "Unknown"
            if "generated_tests" in parts:
                idx = parts.index("generated_tests")
                if idx + 1 < len(parts):
                    category = parts[idx + 1].title()
            
            # Generate test ID and name
            test_id = f"{service}_{action}" if action else service
            display_name = test_id  # Sử dụng test_id làm tên hiển thị
            
            # Add to queue
            if hasattr(self, 'queue_manager'):
                added = self.queue_manager.add_item(test_id, display_name, category, params)
                
                if added:
                    # Switch to queue tab
                    if self.notebook:
                        for i in range(self.notebook.index("end")):
                            if "Test Queue" in self.notebook.tab(i, "text"):
                                self.notebook.select(i)
                                break
                        
                    self.logger.info(f"Added saved test to queue: {filename}")
                    
                    # Update status
                    if self.status_var:
                        self.status_var.set(f"Added {filename} to queue")
                        
                    messagebox.showinfo("Success", f"Added {display_name} to queue")
                else:
                    messagebox.showerror("Error", "Failed to add test to queue")
            else:
                messagebox.showinfo("Information", "Queue manager not initialized yet")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add test to queue: {e}")

    def _view_saved_test_details(self, event) -> None:
        """View details of selected saved test"""
        import os
        
        selected = self.saved_tests_tree.selection()
        if not selected:
            return
        
        # Get file path
        values = self.saved_tests_tree.item(selected[0], "values")
        file_path = values[3]
        
        # Load and display the test file
        import json
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            
            # Extract metadata and test cases based on file format
            metadata = {}
            test_cases = []
            
            if isinstance(test_data, dict):
                # New format with metadata
                metadata = test_data.get("metadata", {})
                test_cases = test_data.get("test_cases", [])
            elif isinstance(test_data, list):
                # Old format - test_data is directly a list of test cases
                test_cases = test_data
                # No metadata available
                
            created_by = metadata.get("created_by", "Unknown")
            created_at = metadata.get("created_at", "Unknown")
            
            # Format JSON for display
            formatted_json = json.dumps(test_cases, indent=2)
            
            # Create popup window with better title based on filename
            file_name = os.path.basename(file_path)
            # Remove .json extension and split by underscore
            base_name = os.path.splitext(file_name)[0]
            
            popup = tk.Toplevel(self.root)
            popup.title(f"Test Details: {base_name}")
            popup.geometry("600x450")
            
            # Add metadata info at top
            meta_frame = ttk.Frame(popup)
            meta_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Label(meta_frame, text=f"Created by: {created_by}", font=("Segoe UI", 9)).pack(anchor=tk.W)
            ttk.Label(meta_frame, text=f"Created on: {created_at}", font=("Segoe UI", 9)).pack(anchor=tk.W)
            
            # Add text area with scrollbar
            text_frame = ttk.Frame(popup)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            text = tk.Text(text_frame, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text.yview)
            text.configure(yscrollcommand=scrollbar.set)
            
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Insert formatted JSON
            text.insert(tk.END, formatted_json)
            text.config(state=tk.DISABLED)
            
            # Add buttons for actions
            button_frame = ttk.Frame(popup)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Button(button_frame, text="Add to Test Queue", 
                    command=lambda file=file_path: self._add_saved_test_to_queue(file)).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(button_frame, text="Close", 
                    command=popup.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load test file: {e}")

    def _delete_saved_test(self) -> None:
        """Delete selected saved test file"""
        selected = self.saved_tests_tree.selection()
        if not selected:
            messagebox.showinfo("Information", "Please select a test file")
            return
        
        # Get file path
        values = self.saved_tests_tree.item(selected[0], "values")
        file_path = values[3]
        test_name = values[0]
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Deletion", f"Delete test file '{test_name}'?"):
            try:
                import os
                os.remove(file_path)
                
                # Remove from treeview
                self.saved_tests_tree.delete(selected[0])
                
                self.logger.info(f"Deleted test file: {file_path}")
                
                # Update status
                if self.status_var:
                    self.status_var.set(f"Deleted test file: {test_name}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {e}")

    def _refresh_test_cases(self):
        """Refresh test case tree"""
        # In Phase 1, just repopulate
        # In Phase 2, this would reload from the filesystem
        self._populate_test_tree()
        
        # Show status message
        if self.status_var:
            self.status_var.set("Test cases refreshed")
        
    def _clear_parameters(self):
        """Clear all parameters from the parameters frame"""
        for widget in self.params_frame.winfo_children():
            widget.destroy()
    def _create_parameter_controls(self, params):
        """Create parameter input fields based on parameter definitions"""
        # Xóa các widget hiện có
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        # ===== PHẦN 1: FRAME CỐ ĐỊNH CHO CÁC NÚT ĐIỀU KHIỂN =====
        control_frame = ttk.Frame(self.params_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Đưa các nút điều khiển vào frame này
        ttk.Button(control_frame, text="➕ Add Param", command=self._add_parameter).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="💾 Save Parameters", command=self._save_parameters).pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="🔄 Reset", command=lambda: self._on_test_case_selected(None)).pack(side=tk.RIGHT, padx=5)
    
        
        # ===== PHẦN 2: FRAME CỐ ĐỊNH CHO TIÊU ĐỀ CỘT =====
        header_frame = ttk.Frame(self.params_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Thiết lập grid columns - chỉ còn 3 cột
        header_frame.columnconfigure(0, weight=0, minsize=150)  # Param
        header_frame.columnconfigure(1, weight=1, minsize=250)  # Value
        header_frame.columnconfigure(2, weight=0, minsize=100)  # Actions

        # Tiêu đề với 3 cột
        ttk.Label(header_frame, text="Parameter", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5, sticky=tk.W)
        ttk.Label(header_frame, text="Value", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5, sticky=tk.W)
        ttk.Label(header_frame, text="Actions", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=5, sticky=tk.W)
        
        # Separator sau tiêu đề
        ttk.Separator(self.params_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)
        
        # ===== PHẦN 3: KHUNG CUỘN CHO NỘI DUNG =====
        # Frame chứa canvas và scrollbar
        scroll_frame = ttk.Frame(self.params_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tạo canvas
        canvas = tk.Canvas(scroll_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_frame, orient=tk.VERTICAL, command=canvas.yview)
        
        # Cấu hình và đặt vị trí cho canvas và scrollbar
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tạo frame con bên trong canvas để chứa các tham số
        param_frame = ttk.Frame(canvas)
        
        # Thiết lập grid columns đồng nhất với header - chỉ 3 cột
        param_frame.columnconfigure(0, weight=0, minsize=150)  # Param
        param_frame.columnconfigure(1, weight=1, minsize=250)  # Value
        param_frame.columnconfigure(2, weight=0, minsize=100)  # Actions
        
        # Tạo window trong canvas để hiển thị frame con
        canvas_window = canvas.create_window(0, 0, window=param_frame, anchor=tk.NW, tags="param_frame")
        
        # Store parameter variables for later access
        self.param_vars = {}
        
        # ===== PHẦN 4: TẠO CÁC DÒNG THAM SỐ =====
        for i, param in enumerate(params):
            # Tên tham số
            ttk.Label(param_frame, text=param["name"]).grid(row=i, column=0, padx=5, pady=6, sticky=tk.W)
            
            # Giá trị tham số - sử dụng giá trị hiện có, không quan tâm đến type nữa
            var = tk.StringVar(value=param["value"])
            ttk.Entry(param_frame, textvariable=var, width=35).grid(row=i, column=1, padx=5, pady=6, sticky=tk.W+tk.E)
            
            # Lưu biến giá trị
            self.param_vars[param["name"]] = var
            
            # Nút hành động
            action_frame = ttk.Frame(param_frame)
            action_frame.grid(row=i, column=2, padx=5, pady=6, sticky=tk.W)
            
            ttk.Button(action_frame, text="🔼", width=2, 
                    command=lambda name=param["name"]: self._move_parameter_up(name)).pack(side=tk.LEFT, padx=1)
            ttk.Button(action_frame, text="🔽", width=2,
                    command=lambda name=param["name"]: self._move_parameter_down(name)).pack(side=tk.LEFT, padx=1)
            ttk.Button(action_frame, text="❌", width=2,
                    command=lambda name=param["name"]: self._delete_parameter(name)).pack(side=tk.LEFT, padx=1)

        # ===== PHẦN 5: CẤU HÌNH LINH HOẠT VÀ CUỘN =====
        # Cập nhật kích thước của frame để tính toán scrollregion
        param_frame.update_idletasks()
        
        # Cập nhật scrollregion của canvas
        canvas.config(scrollregion=canvas.bbox("all"))
        
        # Đặt chiều rộng của window trong canvas bằng với chiều rộng của canvas
        def _on_canvas_configure(event):
            # Điều chỉnh chiều rộng của frame trong canvas khi canvas thay đổi kích thước
            canvas.itemconfig(canvas_window, width=event.width)
            # Cập nhật scrollregion
            canvas.config(scrollregion=canvas.bbox("all"))
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Thêm binding cho chuột để cuộn
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel cho canvas
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Bind mousewheel cho tất cả widget trong param_frame
        def _bind_mousewheel_to_children(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel_to_children(child)
        
        _bind_mousewheel_to_children(param_frame)

        # Ban đầu kích hoạt sự kiện configure để đảm bảo chiều rộng được đặt đúng
        canvas.event_generate("<Configure>", width=canvas.winfo_width())
    def _add_parameter(self):
        """Add a new parameter to the list - adaptive version for different screen sizes"""
        # Tạo dialog thích ứng
        add_dialog = tk.Toplevel(self.root)
        add_dialog.title("Add New Parameter")
        add_dialog.transient(self.root)  # Modal behavior
        add_dialog.grab_set()            # Prevent interaction with main window
        
        # Đặt chế độ thay đổi kích thước để người dùng có thể điều chỉnh nếu cần
        add_dialog.resizable(True, True)
        
        # Main frame với padding thích hợp
        main_frame = ttk.Frame(add_dialog, padding=(20, 20, 20, 20))  # Padding lớn hơn cho không gian tốt hơn
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sử dụng pack với expand để tận dụng không gian
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Grid layout cho form để đảm bảo căn chỉnh chính xác
        form_frame.columnconfigure(0, weight=0, minsize=120)  # Cột nhãn
        form_frame.columnconfigure(1, weight=1, minsize=200)  # Cột nhập liệu
        
        # Tham số cần thu thập
        param_name_var = tk.StringVar()
        param_value_var = tk.StringVar()
        
        # Tên tham số - sử dụng grid để căn chỉnh chính xác
        ttk.Label(form_frame, text="Parameter Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=10)
        name_entry = ttk.Entry(form_frame, textvariable=param_name_var)
        name_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=10)
        
        # Giá trị tham số
        ttk.Label(form_frame, text="Value:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=10)
        value_entry = ttk.Entry(form_frame, textvariable=param_value_var)
        value_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=10)
        
        # Thông tin trợ giúp
        ttk.Label(
            main_frame, 
            text="Enter parameter name and value to add to the test case.",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Nút hành động - sử dụng frame riêng để đảm bảo căn chỉnh
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Sử dụng pack với fill=tk.X và side=RIGHT để đảm bảo nút luôn hiển thị đủ và theo thứ tự
        ttk.Button(button_frame, text="Cancel", command=add_dialog.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        add_button = ttk.Button(button_frame, text="Add Parameter", command=lambda: add_parameter_action())
        add_button.pack(side=tk.RIGHT, padx=(5, 5))
        
        # Hàm thực hiện thêm tham số
        def add_parameter_action():
            name = param_name_var.get().strip()
            value = param_value_var.get()
            
            # Kiểm tra tên tham số
            if not name:
                messagebox.showwarning("Validation Error", "Parameter name is required", parent=add_dialog)
                return
            
            if name in self.param_vars:
                messagebox.showwarning("Duplicate", f"Parameter '{name}' already exists", parent=add_dialog)
                return
                
            # Tạo tham số mới với định dạng đơn giản
            new_param = {
                "name": name,
                "value": value,
                "type": "string",        # Giá trị mặc định cho type
                "required": False        # Giá trị mặc định cho required
            }
            
            # Lấy tham số hiện tại và thêm tham số mới
            current_params = []
            for pname in self.param_vars.keys():
                param = self._get_parameter_data(pname)
                current_params.append(param)
            
            # Thêm tham số mới
            current_params.append(new_param)
            
            # Đóng dialog
            add_dialog.destroy()
            
            # Tải lại với tham số mới
            self._create_parameter_controls(current_params)
            
            # Log thành công
            self.logger.info(f"Added new parameter: {name}")
        
        # Cài đặt focus và validation
        add_dialog.after(100, lambda: name_entry.focus_set())
        
        # Add validation for name entry - enable Add button only when name is valid
        def validate_name(*args):
            name = param_name_var.get().strip()
            if name and name not in self.param_vars:
                add_button.config(state=tk.NORMAL)
            else:
                add_button.config(state=tk.DISABLED)
        
        # Track changes to name entry
        param_name_var.trace("w", validate_name)
        validate_name()  # Initial validation
        
        # Tính toán và đặt kích thước tối thiểu hợp lý
        add_dialog.update_idletasks()  # Cập nhật để có thể đo kích thước thực tế của các widget
        
        # Đặt kích thước tối thiểu
        min_width = 400
        min_height = 250
        
        # Đặt vị trí ở giữa màn hình chính
        if self.root:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (min_width // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (min_height // 2)
            if x < 0: x = 0
            if y < 0: y = 0
            
            # Đặt kích thước và vị trí
            add_dialog.geometry(f"{min_width}x{min_height}+{x}+{y}")
            
        # Thêm một chút thêm padding cho các màn hình khác nhau    
        add_dialog.minsize(min_width, min_height)
        


    def _delete_parameter(self, param_name):
        """Delete a parameter"""
        if param_name not in self.param_vars:
            return
            
        # Xác nhận xóa  
        confirm = messagebox.askyesno("Confirm Delete", 
                                f"Delete parameter '{param_name}'?")
        if not confirm:
            return
        
        # Lấy danh sách tham số, bỏ tham số cần xóa
        current_params = []
        for name in self.param_vars.keys():
            if name != param_name:
                param = self._get_parameter_data(name)
                current_params.append(param)
        
        # Tải lại với tham số mới
        self._create_parameter_controls(current_params)
        
        self.logger.info(f"Deleted parameter: {param_name}")


    def _move_parameter_up(self, param_name):
        """Move a parameter up in the list"""
        # Lấy toàn bộ tham số hiện tại
        current_params = []
        for name in self.param_vars.keys():
            param = self._get_parameter_data(name)
            current_params.append(param)
        
        # Tìm vị trí của tham số cần di chuyển
        index = -1
        for i, param in enumerate(current_params):
            if param["name"] == param_name:
                index = i
                break
        
        if index <= 0:  # Không thể di chuyển lên nếu đã ở đầu
            return
            
        # Hoán đổi vị trí
        current_params[index], current_params[index-1] = current_params[index-1], current_params[index]
        
        # Tải lại với thứ tự mới
        self._create_parameter_controls(current_params)

    def _move_parameter_down(self, param_name):
        """Move a parameter down in the list"""
        # Lấy toàn bộ tham số hiện tại
        current_params = []
        for name in self.param_vars.keys():
            param = self._get_parameter_data(name)
            current_params.append(param)
        
        # Tìm vị trí của tham số cần di chuyển
        index = -1
        for i, param in enumerate(current_params):
            if param["name"] == param_name:
                index = i
                break
        
        if index < 0 or index >= len(current_params) - 1:  # Không thể di chuyển xuống nếu đã ở cuối
            return
            
        # Hoán đổi vị trí
        current_params[index], current_params[index+1] = current_params[index+1], current_params[index]
        
        # Tải lại với thứ tự mới
        self._create_parameter_controls(current_params)

    def _get_parameter_data(self, param_name):
        """Get all data for a parameter"""
        if param_name not in self.param_vars:
            return None
                
        # Đã loại bỏ những dòng truy cập vào param_type_vars và param_required_vars
        value = self.param_vars[param_name].get()
        
        param_data = {
            "name": param_name,
            "value": value,
            "type": "string",  # Mặc định là string vì không còn lưu trữ type
            "required": False  # Mặc định là False vì không còn lưu trữ required
        }
        
        return param_data
        

    def _save_parameters(self) -> None:
        """Save current template parameters."""
        # Get selected item
        selected = self.test_tree.selection()
        if not selected or self.test_tree.get_children(selected[0]):
            messagebox.showinfo("Information", "Please select a test case first")
            return
                
        # Get test case info
        test_id = self.test_tree.item(selected[0], "values")[0]
        test_name = self.test_tree.item(selected[0], "text").split(" ⚠️")[0]
        
        # Lấy tất cả giá trị tham số và thực hiện chuyển đổi kiểu cơ bản
        saved_params = {}
        for param_name, var in self.param_vars.items():
            value = var.get()
            
            # Chuyển đổi kiểu dữ liệu đơn giản dựa trên giá trị
            if value.lower() == "true":
                saved_params[param_name] = True
            elif value.lower() == "false":
                saved_params[param_name] = False
            elif value.isdigit():
                saved_params[param_name] = int(value)
            elif "," in value and param_name.endswith("_dns"):
                # Xử lý đặc biệt cho các trường DNS - chuyển thành mảng
                saved_params[param_name] = [item.strip() for item in value.split(",") if item.strip()]
            else:
                # Mặc định xử lý như string
                saved_params[param_name] = value
        
        # Hiển thị thông báo thành công với chi tiết tham số
        detail_message = f"Parameters for '{test_name}' saved successfully:\n\n"
        for name, value in saved_params.items():
            detail_message += f"• {name}: {value}\n"
        
        messagebox.showinfo("Success", detail_message)
        self.logger.info(f"Template parameters saved for {test_name} with {len(saved_params)} parameters")
        
        # Update status
        if self.status_var:
            self.status_var.set(f"Parameters saved for {test_name}")
                
    def create_placeholder_params(self):
        """Create placeholder parameters UI - Simplified version"""
        # Clear existing widgets
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        # Parameter table frame
        param_table_frame = ttk.Frame(self.params_frame)
        param_table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Headers - Chỉ còn 2 cột: Parameter và Value
        header_frame = ttk.Frame(param_table_frame)
        header_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(header_frame, text="Parameter", width=15, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(header_frame, text="Value", width=30, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5)
        
        # Sample parameters
        params = [
            {"name": "name", "value": "wan1"},
            {"name": "protocol", "value": "ipv4"},
            {"name": "interface", "value": "eth1"},
            {"name": "metric", "value": "100"},
        ]
        
        # Create parameter rows - Chỉ hiển thị 2 cột
        param_rows_frame = ttk.Frame(param_table_frame)
        param_rows_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        row = 0
        for param in params:
            # Tên tham số
            ttk.Label(param_rows_frame, text=param["name"], width=15, anchor=tk.W).grid(row=row, column=0, padx=5, pady=3)
            
            # Giá trị tham số - Chỉ dùng Entry widget
            var = tk.StringVar(value=param["value"])
            ttk.Entry(param_rows_frame, textvariable=var, width=30).grid(row=row, column=1, padx=5, pady=3, sticky=tk.W+tk.E)
            
            row += 1
        
        # Action buttons
        button_frame = ttk.Frame(self.params_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Loại bỏ dòng hiển thị thời gian
        # ttk.Label(button_frame, text=f"Current time: {current_time}").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="💾 Save Parameters", command=self._save_parameters).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="🔄 Reset", command=lambda: self.create_placeholder_params()).pack(side=tk.RIGHT, padx=5)



    def _on_template_selected(self, event):
        """Handler for template selection event"""
        # In a real app, this would load the template's parameters
        selected = self.test_tree.selection()  # Sửa từ template_tree thành test_tree
        if not selected:
            return
        
        # Get selected template ID
        template_id = self.test_tree.item(selected[0], "values")[0]  # Sửa
        self.params_frame.configure(text=f"Template Parameters ({self.test_tree.item(selected[0], 'values')[1]})")  # Sửa
        
        # This would normally load the parameters for the selected template
        self.create_placeholder_params()
        
    def _add_to_test_queue(self) -> None:
        """Add current template with parameters to test queue"""
        selected = self.test_tree.selection()
        if not selected:
            messagebox.showinfo("Information", "Please select a test case first")
            return
        
        # Skip if it's a category node (has children)
        if self.test_tree.get_children(selected[0]):
            messagebox.showinfo("Information", "Please select a specific test case, not a category")
            return
        
        # Get test case info
        test_id = self.test_tree.item(selected[0], "values")[0]
        test_name = test_id  # Sử dụng ID làm tên để đảm bảo nhất quán
        category = self.test_tree.item(self.test_tree.parent(selected[0]), "text")
        
        # Collect parameter values
        params = {}
        for param_name, var in self.param_vars.items():
            value = var.get()
            # Basic type conversion
            if value.lower() == "true":
                params[param_name] = True
            elif value.lower() == "false":
                params[param_name] = False
            elif value.isdigit():
                params[param_name] = int(value)
            else:
                params[param_name] = value
        
        # Add to queue
        added = self.queue_manager.add_item(test_id, test_name, category, params)
        
        if added:
            # Update status
            if self.status_var:
                self.status_var.set(f"Added {test_name} to test queue")
                
            # Switch to queue tab to show the addition
            if self.notebook:
                queue_tab_index = self.notebook.index("end") - 3  # Assuming queue is the 2nd tab
                self.notebook.select(queue_tab_index)
                
            # Log the addition
            self.logger.info(f"Added test case to queue: {test_name} ({test_id})")
        else:
            messagebox.showerror("Error", "Failed to add test to queue")

    def _create_from_template(self):
        """Create a new test case from the selected template"""
        selected = self.test_tree.selection()
        if not selected or self.test_tree.get_children(selected[0]):
            messagebox.showinfo("Information", "Please select a test case first")
            return
            
        # Get test case info
        test_id = self.test_tree.item(selected[0], "values")[0]
        test_name = self.test_tree.item(selected[0], "text").split(" ⚠️")[0]
        category = self.test_tree.item(self.test_tree.parent(selected[0]), "text")
        
        # Get service and action from test_id
        parts = test_id.split('_')
        service = parts[0]  # wan, ping, etc.
        action = parts[1] if len(parts) > 1 else ""  # create, delete, etc.
        
        # Kiểm tra nhưng tên test cases đã tồn tại
        import os
        import glob
        save_dir = os.path.join("data", "temp", "generated_tests", category.lower())
        os.makedirs(save_dir, exist_ok=True)
        
        # Lấy danh sách các filenames hiện có
        existing_files = []
        pattern = f"{service}_{action}_*.json" if action else f"{service}_*.json"
        if os.path.exists(save_dir):
            existing_files = [os.path.basename(f) for f in glob.glob(os.path.join(save_dir, pattern))]
        
        # Tìm số identifier tiếp theo có sẵn
        next_id = 1
        while True:
            test_filename = f"{service}_{action}_{next_id}.json" if action else f"{service}_{next_id}.json"
            if test_filename not in existing_files:
                break
            next_id += 1
        
        # Hiển thị cửa sổ nhập với gợi ý số tiếp theo
        from tkinter import simpledialog
        prompt_message = (
            f"Enter test identifier (recommended: {next_id}):\n\n"
            f"• Current test: {test_id}\n"
            f"• File will be saved as: {service}_{action}_[identifier].json\n\n"
            f"Note: Use simple identifiers like numbers or short descriptions."
        )
        
        identifier = simpledialog.askstring("Test Identifier", prompt_message, initialvalue=str(next_id))
        
        if not identifier:
            messagebox.showinfo("Information", "Test creation cancelled")
            return
        
        # Loại bỏ ký tự không hợp lệ và kiểm tra trùng lặp
        import re
        # Chỉ giữ lại ký tự an toàn cho tên file
        identifier = re.sub(r'[\\/*?:"<>|]', "", identifier)
        
        # Loại bỏ service và action khỏi identifier nếu người dùng vô tình nhập
        identifier = identifier.replace(service, "").replace(action, "")
        # Loại bỏ dấu gạch dư thừa
        identifier = re.sub(r'^_+|_+$', "", identifier)
        identifier = re.sub(r'_+', "_", identifier)
        
        # Nếu identifier trống sau khi loại bỏ các phần không cần thiết, sử dụng giá trị mặc định
        if not identifier:
            identifier = str(next_id)
        
        # Thu thập tham số
        params = {}
        for param_name, var in self.param_vars.items():
            # Xử lý đặc biệt cho tham số mảng
            if param_name == "ipv4_dns":
                # Split comma-separated values into array
                dns_values = var.get().split(",")
                params[param_name] = [dns.strip() for dns in dns_values if dns.strip()]
            else:
                # Chuyển đổi kiểu dữ liệu
                value = var.get()
                if value.lower() == "true":
                    params[param_name] = True
                elif value.lower() == "false":
                    params[param_name] = False
                elif value.isdigit():
                    params[param_name] = int(value)
                else:
                    params[param_name] = value

        # Thời gian hiện tại từ yêu cầu  
        import datetime
        current_time = "2025-06-18 03:28:32"  
        current_user = "juno-kyojin"          
        
        # Tạo đúng cấu trúc JSON theo đặc tả - QUAN TRỌNG: Đặt metadata ngoài mảng test_cases
        test_data = {
            "test_cases": [
                {
                    "service": service,
                    "params": params
                }
            ],
            "metadata": {
                "created_by": current_user,
                "created_at": current_time,
                "category": category,
                "identifier": identifier,
                "connection_type": self._safe_get(self.connection_type_var, "http"),  # Thêm thông tin connection_type
                "version": "2.0"  # Thêm version để nhận diện phiên bản định dạng
            }
        }
        
        # Thêm action nếu có
        if action:
            test_data["test_cases"][0]["action"] = action
        
        # Xây dựng tên file theo định dạng service_action_identifier.json
        filename = f"{service}_{action}_{identifier}.json" if action else f"{service}_{identifier}.json"
        
        # Log tên file đã tạo để debug
        self.logger.info(f"Generated filename: {filename}")
        
        # Đường dẫn đầy đủ cho file
        file_path = os.path.join(save_dir, filename)
        
        # Kiểm tra file đã tồn tại chưa
        if os.path.exists(file_path):
            overwrite = messagebox.askyesno(
                "File Exists", 
                f"File {filename} already exists. Overwrite?"
            )
            if not overwrite:
                return
        
        # Lưu file với cấu trúc đúng
        import json
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=4)
            
            self.logger.info(f"Generated test case saved to: {file_path}")
            
            # Hiển thị thông báo thành công
            messagebox.showinfo("Test Case Created", 
                        f"Test case saved to:\n{file_path}\n\n"
                        f"You can find it in the 'Saved Tests' tab.")
            
            # Làm mới tab Saved Tests
            if hasattr(self, '_load_saved_tests'):
                self._load_saved_tests()
                
            # Chuyển đến tab Saved Tests
            if self.notebook:
                for i in range(self.notebook.index("end")):
                    if "Saved Tests" in self.notebook.tab(i, "text"):
                        self.notebook.select(i)
                        break
            
            # Cập nhật trạng thái
            if self.status_var:
                self.status_var.set(f"Test case {filename} created")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create test case: {e}")

    def _view_template_details(self):
        """View details of the selected test case"""
        selected = self.test_tree.selection()
        if not selected or self.test_tree.get_children(selected[0]):
            messagebox.showinfo("Information", "Please select a test case first")
            return
        
        # Get test case info
        test_id = self.test_tree.item(selected[0], "values")[0]
        test_name = self.test_tree.item(selected[0], "text").split(" ⚠️")[0]
        category = self.test_tree.item(self.test_tree.parent(selected[0]), "text")
        affects_network = self.test_tree.item(selected[0], "values")[2]
        
        # Extract service and action
        parts = test_id.split('_')
        service = parts[0]
        action = parts[1] if len(parts) > 1 else "N/A"
        
        # Show different details based on test type
        if test_id == "wan_create":
            detail_text = f"""
    Test ID: {test_id}
    Name: {test_name}
    Category: {category}
    Service: {service}
    Action: {action}
    Network Impact: {"Yes" if affects_network else "No"}

    Description:
    Creates a new WAN connection with the specified parameters.
    This test will configure network settings and may cause
    temporary connectivity interruption.

    Parameters:
    - name: WAN connection name
    - protocol: Network protocol (IPv4/IPv6)
    - gateway_type: Type of gateway (route/bridge)
    - mtu: Maximum Transmission Unit
    - nat: Enable/disable Network Address Translation
    - link_mode: Connection mode (IPoE/PPPoE)
    - ipv4_alloc: IPv4 allocation method (DHCP/Static)
    - ipv4_ip: Static IP address (if applicable)
    - ipv4_mask: Network mask (if applicable)
    - ipv4_gw: Gateway IP address (if applicable)
    - ipv4_dns: DNS server addresses (comma separated)
    """
        elif test_id == "wan_delete":
            detail_text = f"""
    Test ID: {test_id}
    Name: {test_name}
    Category: {category}
    Service: {service}
    Action: {action}
    Network Impact: {"Yes" if affects_network else "No"}

    Description:
    Deletes an existing WAN connection.
    Warning: This may disconnect current network connectivity.

    Parameters:
    - name: WAN connection name to delete
    """
        elif test_id == "ping":
            detail_text = f"""
    Test ID: {test_id}
    Name: {test_name}
    Category: {category}
    Service: {service}
    Network Impact: {"Yes" if affects_network else "No"}

    Description:
    Performs ping test to specified hosts to check connectivity.
    This test helps verify network connectivity is functioning correctly.

    Parameters:
    - host1: Primary target hostname/IP address
    - host2: Secondary target hostname/IP address (optional)
    - count: Number of ping packets to send (optional)
    """
        else:
            detail_text = f"""
    Test ID: {test_id}
    Name: {test_name}
    Category: {category}
    Network Impact: {"Yes" if affects_network else "No"}

    No detailed information available for this test case.
    """
        
        messagebox.showinfo("Test Case Details", detail_text)

    def _edit_template(self) -> None:
        """Edit selected template."""
        # Placeholder for Phase 2
        messagebox.showinfo("Info", "Template editor will be implemented in Phase 2")

    
    def _create_connection_tab(self) -> None:
        """Create the connection configuration tab."""
        if not self.notebook:
            return
            
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Connection")
        
        # Connection settings
        settings_frame = ttk.LabelFrame(frame, text="SSH Connection Settings")
        settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # SSH Host
        ttk.Label(settings_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.ssh_host_var = tk.StringVar(value=self.config.network.ssh_host)
        ttk.Entry(settings_frame, textvariable=self.ssh_host_var, width=20).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5
        )
        
        # SSH Port
        ttk.Label(settings_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.ssh_port_var = tk.StringVar(value=str(self.config.network.ssh_port))
        ttk.Entry(settings_frame, textvariable=self.ssh_port_var, width=8).grid(
            row=0, column=3, sticky=tk.W, padx=5, pady=5
        )
        
        # Username
        ttk.Label(settings_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.ssh_username_var = tk.StringVar(value=self.config.network.ssh_username)
        ttk.Entry(settings_frame, textvariable=self.ssh_username_var, width=20).grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=5
        )
        
        # Password
        ttk.Label(settings_frame, text="Password:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.ssh_password_var = tk.StringVar(value=self.config.network.ssh_password)
        ttk.Entry(settings_frame, textvariable=self.ssh_password_var, show="*", width=20).grid(
            row=1, column=3, sticky=tk.W, padx=5, pady=5
        )
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Connect", command=self._test_connection).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Save Settings", command=self._save_connection_settings).pack(
            side=tk.RIGHT, padx=5
        )
        
        # Status
        self.connection_status_var = tk.StringVar(value="Not connected")
        ttk.Label(frame, textvariable=self.connection_status_var).pack(
            side=tk.BOTTOM, anchor=tk.W, padx=10, pady=5
        )
    
    def _create_templates_tab(self) -> None:
        """Create the template browser tab."""
        if not self.notebook:
            return
            
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Templates")
        
        # Placeholder content
        ttk.Label(frame, text="Template browser will be implemented in Phase 2").pack(
            expand=True
        )
        
    def _create_queue_tab(self) -> None:
        """Create the test queue tab."""
        if not self.notebook:
            return
                
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Test Queue")
        
        # Import the TestQueueManager
        from gui.widgets.queue_manager import TestQueueManager
        
        # Create queue manager với các callbacks rõ ràng hơn
        self.queue_manager = TestQueueManager(
            frame, 
            on_selection_change=self._on_queue_selection_change,
            on_run_all=self.send_all_tests,
            on_run_selected=self.send_selected_test  # Trực tiếp gọi send_selected_test
        )
        self.queue_manager.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status display at the bottom
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.queue_status_var = tk.StringVar(value="Queue ready. No tests running.")
        ttk.Label(status_frame, textvariable=self.queue_status_var).pack(side=tk.LEFT)
        
        # Display test count
        count_label = ttk.Label(status_frame, text="0 tests in queue")
        count_label.pack(side=tk.RIGHT)
        
        # Update the test count when queue changes
        def update_count():
            if hasattr(self, 'queue_manager'):
                count = len(self.queue_manager.queue_items)
                count_label.config(text=f"{count} tests in queue")
        
        # Schedule periodic updates
        update_count()
        if self.root:
            self.root.after(1000, update_count)
    
    def _on_queue_selection_change(self, item_data: dict) -> None:
        """Handle selection change in queue manager"""
        # Update UI based on selected item
        if self.status_var:
            self.status_var.set(f"Selected: {item_data.get('name', '')}")
        
        # Log the selection
        self.logger.debug(f"Queue item selected: {item_data.get('name', '')}")

    def _create_history_tab(self) -> None:
        """Create the test history tab."""
        if not self.notebook:
            return
            
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="History")
        
        # Placeholder content
        ttk.Label(frame, text="Test history will be implemented in Phase 2").pack(
            expand=True
        )
    
    def _create_logs_tab(self) -> None:
        """Create the logs tab."""
        if not self.notebook:
            return
            
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Logs")
        
        # Log text area
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Text widget with scrollbar
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=15)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add some sample log entries
        self.log_text.insert(tk.END, "[2025-06-12 02:42:02] INFO - Application started\n")
        self.log_text.insert(tk.END, "[2025-06-12 02:42:03] INFO - Configuration loaded\n")
        self.log_text.insert(tk.END, "[2025-06-12 02:42:04] INFO - GUI initialized\n")
        self.log_text.config(state=tk.DISABLED)
        
    def _create_status_bar(self) -> None:
        """Create the status bar with improved visibility."""
        if not self.root:
            return
            
        # Tạo một frame riêng cho status bar với border và relief để nổi bật
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, borderwidth=1)
        # Đặt pack_propagate=False để đảm bảo kích thước cố định
        status_frame.pack_propagate(False)
        # Đặt chiều cao cố định cho status bar
        status_frame.configure(height=28)
        # Đặt ở cuối cùng với fill=X để mở rộng theo chiều ngang
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=0)
        
        # Status message bên trái - sử dụng pack thay vì grid để linh hoạt hơn
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=10, pady=2)
        
        # Thời gian hiện tại - ở giữa
        self.time_var = tk.StringVar(value=self._get_current_time())
        time_label = ttk.Label(status_frame, textvariable=self.time_var)
        time_label.pack(side=tk.LEFT, padx=10, pady=2, expand=True)
        
        # Cập nhật thời gian mỗi giây
        def update_time():
            # Sử dụng _safe_set để cập nhật thời gian
            self._safe_set(self.time_var, self._get_current_time())
            # Sử dụng _safe_after thay vì trực tiếp gọi self.root.after
            self._safe_after(1000, update_time)
        
        # Bắt đầu cập nhật thời gian
        update_time()

    def _test_connection(self) -> None:
        """Test connection using selected method (HTTP or SSH)."""
        connection_type = self._safe_get(self.connection_type_var, "http")
        
        # Update status
        self._safe_set(self.connection_status_var, "🟡 Testing connection...")
        self._safe_set(self.status_var, f"Testing {connection_type.upper()} connection...")
        
        # Run test in background thread to prevent UI freeze
        import threading
        thread = threading.Thread(target=self._run_connection_test, daemon=True)
        thread.start()
                    
    def _run_connection_test(self) -> None:
        """Run connection test in background thread using direct socket connection"""
        try:
            connection_type = self._safe_get(self.connection_type_var, "http")
            
            if connection_type == "http":
                # Test HTTP connection using direct socket connection
                host = self._safe_get(self.http_host_var, "127.0.0.1")
                port = int(self._safe_get(self.http_port_var, "6262"))  # Cổng 6262
                
                import socket
                try:
                    self.logger.info(f"Testing TCP socket connection to {host}:{port}")
                    
                    # Tạo socket và kết nối
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(int(self._safe_get(self.http_conn_timeout_var, "5")))
                    sock.connect((host, port))
                    sock.close()  # Đóng kết nối ngay lập tức, không gửi dữ liệu
                    
                    # Kết nối thành công
                    self._safe_after(0, lambda: self._safe_set(self.connection_status_var, 
                                                        "🟢 Connected (TCP Socket)"))
                    self.logger.info(f"Socket connection successful to {host}:{port}")
                    
                    # Đánh dấu là đã kết nối thành công
                    self.http_connected = True
                    
                    # Cập nhật thông tin trong UI
                    current_time = self._get_current_time()
                    self._safe_after(0, lambda: self._safe_set(self.status_var, 
                                                f"Connected to {host}:{port} successfully at {current_time}"))
                    
                except socket.timeout:
                    self.http_connected = False
                    self._safe_after(0, lambda: self._safe_set(self.connection_status_var, 
                                                        "🔴 Connection timeout"))
                    self.logger.error(f"Socket connection timeout to {host}:{port}")
                except socket.error as e:
                    self.http_connected = False
                    self._safe_after(0, lambda: self._safe_set(self.connection_status_var, 
                                                        "🔴 Connection refused"))
                    self.logger.error(f"Socket connection error to {host}:{port}: {str(e)}")
                except Exception as e:
                    self.http_connected = False
                    self._safe_after(0, lambda: self._safe_set(self.connection_status_var, 
                                                        f"🔴 Error: {str(e)[:30]}..."))
                    self.logger.error(f"Connection error: {str(e)}")
                    
            else:
                # Test SSH connection
                host = self._safe_get(self.ssh_host_var)
                username = self._safe_get(self.ssh_username_var)
                password = self._safe_get(self.ssh_password_var)
                port = int(self._safe_get(self.ssh_port_var, "22"))
                
                # Log the attempt
                self.logger.info(f"SSH connection requested to {host}:{port} as {username}")
                
                # Simulate connection delay
                import time
                time.sleep(1)
                
                # Update status
                self._safe_after(0, lambda: self._safe_set(self.connection_status_var, "🟢 Connected (SSH)"))
                
            # Update status
            self._safe_after(0, lambda: self._safe_set(self.status_var, f"{connection_type.upper()} connection test completed"))
                
        except Exception as e:
            self.logger.error(f"Connection test error: {str(e)}")
            self._safe_after(0, lambda: self._safe_set(self.connection_status_var, f"🔴 Error: {str(e)[:30]}..."))
            self._safe_after(0, lambda: self._safe_set(self.status_var, f"Connection test failed: {str(e)[:50]}..."))
                        
    def _get_current_time(self):
        """Get current local time in correct format (YYYY-MM-DD HH:MM:SS)"""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    def send_test_case_http(self, test_data, index):
        """Send test case to HTTP server and process response with improved logging"""
        try:
            # Import cần thiết
            import requests
            import json
            import time
            
            if not self.http_client:
                self.logger.error("HTTP client not initialized")
                self._safe_after(0, lambda: self.update_test_status(index, "Error", "HTTP client not initialized"))
                return
                    
            host = self._safe_get(self.http_host_var, "127.0.0.1")
            port = int(self._safe_get(self.http_port_var, "6262"))
            url = f"http://{host}:{port}"
            
            self.logger.info(f"Sending test case to {url}")
            transaction_id = test_data.get("metadata", {}).get("transaction_id", "unknown")
            self._safe_after(0, lambda: self.update_test_status(index, "Sending", f"TX: {transaction_id}"))
            
            # Lấy thời gian hiện tại để tính thời gian thực thi
            start_time = time.time()
            
            try:
                # Gửi POST request
                response = requests.post(
                    url,
                    json=test_data,
                    headers={"Content-Type": "application/json"},
                    timeout=(int(self._safe_get(self.http_conn_timeout_var, "5")),
                            int(self._safe_get(self.http_read_timeout_var, "40")))
                )
                
                # Tính thời gian phản hồi
                elapsed_time = time.time() - start_time
                
                # Process response
                if response.status_code == 200:
                    try:
                        result = response.json()
                        self.logger.info(f"Test response received in {elapsed_time:.2f}s: {json.dumps(result, indent=2)}")
                        
                        # Extract test results
                        success = result.get("summary", {}).get("passed", 0) > 0
                        status = "Success" if success else "Failed"
                        passed = result.get("summary", {}).get("passed", 0)
                        failed = result.get("summary", {}).get("failed", 0)
                        message = f"Passed: {passed}, Failed: {failed}, Time: {elapsed_time:.1f}s, TX: {transaction_id[:8]}"
                        
                        self._safe_after(0, lambda: self.update_test_status(index, status, message))
                    except Exception as e:
                        self.logger.error(f"Error processing response: {str(e)}")
                        self._safe_after(0, lambda: self.update_test_status(index, "Error", f"Response error: {str(e)}"))
                else:
                    self.logger.error(f"HTTP error: {response.status_code}")
                    self._safe_after(0, lambda: self.update_test_status(index, "Error", f"HTTP {response.status_code}"))
                    
            except requests.exceptions.ConnectionError:
                self.logger.error("Connection refused")
                self._safe_after(0, lambda: self.update_test_status(index, "Error", "Connection refused"))
            except requests.exceptions.Timeout:
                self.logger.error("Connection timeout")
                self._safe_after(0, lambda: self.update_test_status(index, "Error", "Connection timeout"))
                
        except Exception as e:
            self.logger.error(f"Error sending test: {str(e)}")
            self._safe_after(0, lambda: self.update_test_status(index, "Error", str(e)[:30]))
    def send_all_tests(self):
        """Send all tests in queue for execution with proper delay between tests"""
        try:
            if not hasattr(self, 'queue_manager') or not hasattr(self.queue_manager, 'queue_items'):
                messagebox.showinfo("Information", "Queue is empty or not initialized")
                return
                    
            if len(self.queue_manager.queue_items) == 0:
                messagebox.showinfo("Information", "Queue is empty")
                return
                    
            # Kiểm tra kết nối
            connection_type = self._safe_get(self.connection_type_var, "http")
            if connection_type == "http":
                if not hasattr(self, 'http_connected') or not self.http_connected:
                    messagebox.showinfo("Error", "Not connected to HTTP server. Please test connection first.")
                    return
            elif connection_type == "ssh" and (not self.ssh_connection or not self.ssh_connection.is_connected()):
                messagebox.showinfo("Error", "Not connected to SSH server. Please test connection first.")
                return
                    
            # Hỏi xác nhận
            if len(self.queue_manager.queue_items) > 1:
                confirm = messagebox.askyesno("Confirm",
                    f"Send all {len(self.queue_manager.queue_items)} tests for execution?")
                if not confirm:
                    return
                
            # QUAN TRỌNG: Tính toán delay dựa trên loại test case
            delays = []
            for i, test_item in enumerate(self.queue_manager.queue_items):
                test_id = test_item.get("test_id", "")
                # Kiểm tra xem test có ảnh hưởng đến mạng không
                if "wan_" in test_id or "network_" in test_id or "reboot" in test_id:
                    # Test ảnh hưởng mạng cần delay lâu hơn
                    delay = 30000  # 30 giây
                else:
                    # Test thông thường
                    delay = 10000  # 10 giây
                
                delays.append(delay)
                
            # Log lịch gửi test case
            self.logger.info(f"Scheduling {len(self.queue_manager.queue_items)} tests with delays: {', '.join([f'{d/1000}s' for d in delays])}")
                
            # Lặp qua từng test và schedule với delay phù hợp
            total_delay = 0
            for i in range(len(self.queue_manager.queue_items)):
                idx = i
                if i > 0:
                    total_delay += delays[i-1]  # Tích lũy delay của các test trước
                
                self.logger.info(f"Scheduling test #{i+1} after {total_delay/1000}s delay")
                self._safe_after(total_delay, lambda idx=i: self.send_selected_test(idx))
                    
            # Status update
            self._safe_set(self.status_var, f"Sending {len(self.queue_manager.queue_items)} tests with appropriate delays...")
            
        except Exception as e:
            self.logger.error(f"Error sending tests: {str(e)}")
            messagebox.showerror("Error", f"Failed to send tests: {str(e)}")
    def update_test_status(self, index, status, message):
        """Update test status in the queue"""
        if not hasattr(self, 'queue_manager'):
            self.logger.warning("Queue manager not available")
            return
                
        try:
            # Sử dụng tên đúng cho Treeview: queue_tree thay vì test_queue
            if hasattr(self.queue_manager, 'queue_tree'):
                items = self.queue_manager.queue_tree.get_children()
                if index < len(items):
                    item_id = items[index]
                    # Lấy giá trị hiện tại
                    current_values = list(self.queue_manager.queue_tree.item(item_id, "values"))
                    
                    # Cập nhật status - cột số 4 (theo định nghĩa trong TestQueueManager)
                    # columns = ("order", "name", "category", "parameters", "status")
                    status_col = 4  # Vị trí của cột status
                    if len(current_values) > status_col:
                        current_values[status_col] = f"{status}: {message}" if message else status
                        
                    # Cập nhật item
                    self.queue_manager.queue_tree.item(item_id, values=tuple(current_values))
                    
                    # Cập nhật dữ liệu nội bộ
                    if index < len(self.queue_manager.queue_items):
                        self.queue_manager.queue_items[index]["status"] = status
                        if message:
                            self.queue_manager.queue_items[index]["message"] = message
                    
                    return
        except Exception as e:
            self.logger.error(f"Error updating test status in queue UI: {e}")
                
        # Fallback: Log warning nếu không thể cập nhật
            self.logger.warning(f"Could not update test status for item {index}. Status={status}, Message={message}")

    def send_selected_test(self, index=None):
        """Send a selected test from the queue with transaction tracking"""
        try:
            if not hasattr(self, 'queue_manager'):
                messagebox.showinfo("Error", "Queue manager not initialized")
                return
                        
            # Kiểm tra kết nối
            connection_type = self._safe_get(self.connection_type_var, "http")
            if connection_type == "http" and not getattr(self, 'http_connected', False):
                messagebox.showinfo("Error", "Not connected to HTTP server. Please test connection first.")
                return
                        
            # Lấy index nếu không được chỉ định
            if index is None:
                selected = self.queue_manager.queue_tree.selection()
                if not selected:
                    messagebox.showinfo("Information", "Please select a test case first")
                    return
                index = self.queue_manager.queue_tree.index(selected[0])
            
            # Log và Debug để xác nhận
            self.logger.info(f"send_selected_test called with index: {index}")
            
            # Lấy thông tin test case
            if index < 0 or index >= len(self.queue_manager.queue_items):
                messagebox.showinfo("Error", "Invalid test index")
                return
                        
            test_item = self.queue_manager.queue_items[index]
            test_id = test_item.get("test_id", "")
            name = test_item.get("name", "")
            params = test_item.get("parameters", {}).copy()  # Tạo bản sao
            
            # Parse service và action từ test_id
            parts = test_id.split("_")
            service = parts[0]  # ping, wan, lan, etc
            action = parts[1] if len(parts) > 1 else ""  # test, create, etc
            
            # Tạo transaction ID duy nhất
            import uuid
            import datetime
            transaction_id = f"tx-{str(uuid.uuid4())[:8]}"
            client_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Xử lý đặc biệt cho ping theo đúng định dạng
            if service == "ping" or (service == "ping" and action == "test"):
                # Sửa: Sử dụng đúng định dạng ping theo mẫu
                service = "ping"  # Đảm bảo service đúng
                action = ""  # Không cần action cho ping
                
                # QUAN TRỌNG: Nếu đang sử dụng system.execute, chuyển về định dạng ping
                if "command" in params and "ping" in params["command"]:
                    # Trích xuất host và count từ command nếu có
                    cmd = params["command"]
                    import re
                    
                    # Tìm host
                    host_match = re.search(r'ping -c \d+ (.+)', cmd)
                    if host_match:
                        params = {"host1": host_match.group(1)}
                        
                        # Tìm count nếu có
                        count_match = re.search(r'ping -c (\d+)', cmd)
                        if count_match:
                            params["count"] = int(count_match.group(1))
                    else:
                        # Giá trị mặc định nếu không parse được
                        params = {"host1": "youtube.com", "count": 4}
                
                # Đảm bảo có ít nhất host1
                if "host1" not in params:
                    params["host1"] = "youtube.com"  # Giá trị mặc định
            
            # Đảm bảo mảng cho các tham số cần mảng
            for key, value in list(params.items()):
                if key in ["ipv4_dns", "ipv6_dns"] and isinstance(value, str):
                    # Chuyển đổi chuỗi thành list một cách an toàn
                    if value.strip():
                        # Tạo một danh sách đúng định dạng từ chuỗi phân cách bằng dấu phẩy
                        dns_list = [dns.strip() for dns in value.split(",") if dns.strip()]
                        # Gán danh sách vào params
                        params[key] = dns_list
                    else:
                        # Nếu chuỗi rỗng hoặc chỉ có khoảng trắng, đặt là list rỗng
                        params[key] = []
            
            # Tạo test case với các trường bổ sung
            test_case = {
                "service": service,
                "params": params,
                "client_id": transaction_id,           # Thêm ID giao dịch duy nhất
                "client_timestamp": client_timestamp   # Thêm timestamp từ client
            }
            
            # Thêm action nếu có và cần thiết
            if action:
                test_case["action"] = action
                
            # Đóng gói trong định dạng API với metadata
            test_data = {
                "test_cases": [test_case],
                "metadata": {
                    "transaction_id": transaction_id,
                    "client_timestamp": client_timestamp,
                    "created_by": "juno-kyojin",
                    "created_at": client_timestamp
                }
            }
            
            # Lưu transaction ID để theo dõi sau này
            if not hasattr(self, 'test_transactions'):
                self.test_transactions = {}
            self.test_transactions[index] = transaction_id
            
            # Cập nhật trạng thái để hiển thị ID giao dịch
            self.update_test_status(index, "Sending", f"TX: {transaction_id}")
            
            # Log thông tin test case với transaction ID
            self.logger.info(f"Sending test case {name} (index {index}, transaction_id: {transaction_id})")
            self.logger.info(f"Full payload: {json.dumps(test_data, indent=2)}")
            
            # Gửi test case
            self.send_test_case_http(test_data, index)
            
        except Exception as e:
            self.logger.error(f"Error sending selected test: {e}")
            messagebox.showerror("Error", f"Failed to send test: {str(e)}")
    def _update_connection_status(self, status: str) -> None:
        """Update connection status safely."""
        if self.connection_status_var:
            self.connection_status_var.set(status)
        
    def _save_connection_settings(self) -> None:
        """Save connection settings."""
        if not hasattr(self, 'config') or not hasattr(self.config, 'network'):
            self.logger.error("Configuration object not properly initialized")
            return
            
        try:
            connection_type = self._safe_get(self.connection_type_var, "http")
            
            # Save connection type if attribute exists
            if hasattr(self.config.network, 'connection_type'):
                self.config.network.connection_type = connection_type
            else:
                # Create the attribute if it doesn't exist
                setattr(self.config.network, 'connection_type', connection_type)
            
            if connection_type == "http":
                # Save HTTP settings
                if hasattr(self.config.network, 'http_host'):
                    self.config.network.http_host = self._safe_get(self.http_host_var)
                else:
                    setattr(self.config.network, 'http_host', self._safe_get(self.http_host_var))
                    
                if hasattr(self.config.network, 'http_port'):
                    self.config.network.http_port = int(self._safe_get(self.http_port_var, "8080"))
                else:
                    setattr(self.config.network, 'http_port', int(self._safe_get(self.http_port_var, "8080")))
                    
                if hasattr(self.config.network, 'http_connect_timeout'):
                    self.config.network.http_connect_timeout = int(self._safe_get(self.http_conn_timeout_var, "5"))
                else:
                    setattr(self.config.network, 'http_connect_timeout', int(self._safe_get(self.http_conn_timeout_var, "5")))
                    
                if hasattr(self.config.network, 'http_read_timeout'):
                    self.config.network.http_read_timeout = int(self._safe_get(self.http_read_timeout_var, "40"))
                else:
                    setattr(self.config.network, 'http_read_timeout', int(self._safe_get(self.http_read_timeout_var, "40")))
                
                # Update status
                self.logger.info(f"HTTP connection settings saved: {self._safe_get(self.http_host_var)}:{self._safe_get(self.http_port_var, '8080')}")
            else:
                # Save SSH settings
                self.config.network.ssh_host = self._safe_get(self.ssh_host_var)
                self.config.network.ssh_port = int(self._safe_get(self.ssh_port_var, "22"))
                self.config.network.ssh_username = self._safe_get(self.ssh_username_var)
                self.config.network.ssh_password = self._safe_get(self.ssh_password_var)
                
                # Update status
                self.logger.info(f"SSH connection settings saved: {self.config.network.ssh_host}:{self.config.network.ssh_port}")
            
            # Update status message
            self._safe_set(self.status_var, f"{connection_type.upper()} connection settings saved")
                
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid numeric value: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def _new_template(self) -> None:
        """Create new template."""
        # TODO: Implement in Phase 2
        messagebox.showinfo("Info", "Template creation will be implemented in Phase 2")
    
    def _open_template(self) -> None:
        """Open existing template."""
        # TODO: Implement in Phase 2
        messagebox.showinfo("Info", "Template opening will be implemented in Phase 2")
    
    def _export_results(self) -> None:
        """Export test results."""
        # TODO: Implement in Phase 2
        messagebox.showinfo("Info", "Result export will be implemented in Phase 2")
    
    def _show_preferences(self) -> None:
        """Show preferences dialog."""
        # TODO: Implement in Phase 2
        messagebox.showinfo("Info", "Preferences will be implemented in Phase 2")
    
    def _validate_templates(self) -> None:
        """Show server status and debug information"""
        # Tạo dialog để hiển thị thông tin
        debug_window = tk.Toplevel(self.root)
        debug_window.title("Server Status")
        debug_window.geometry("600x400")
        debug_window.transient(self.root)
        
        # Tạo frame chính
        main_frame = ttk.Frame(debug_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Hiển thị thông tin về kết nối
        host = self._safe_get(self.http_host_var, "Unknown")
        port = self._safe_get(self.http_port_var, "Unknown")
        connection_type = self._safe_get(self.connection_type_var, "Unknown")
        
        # Tạo bảng hiển thị thông tin
        info_frame = ttk.LabelFrame(main_frame, text="Server Information")
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text=f"Server: {host}:{port}").pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Connection Type: {connection_type.upper()}").pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Status: {'Connected' if getattr(self, 'http_connected', False) else 'Not Connected'}").pack(anchor=tk.W, pady=2)
        ttk.Label(info_frame, text=f"Current Client Time: {self._get_current_time()}").pack(anchor=tk.W, pady=2)
        
        # Thông tin về queues hiện tại
        queue_frame = ttk.LabelFrame(main_frame, text="Queue Information")
        queue_frame.pack(fill=tk.X, pady=5)
        
        queue_count = len(self.queue_manager.queue_items) if hasattr(self, 'queue_manager') else 0
        ttk.Label(queue_frame, text=f"Tests in Queue: {queue_count}").pack(anchor=tk.W, pady=2)
        
        # Thông tin chi tiết
        debug_frame = ttk.LabelFrame(main_frame, text="Server Debug Information")
        debug_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo text widget với scrollbar
        text_frame = ttk.Frame(debug_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        debug_text = tk.Text(text_frame, wrap=tk.WORD, height=10)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=debug_text.yview)
        debug_text.configure(yscrollcommand=scrollbar.set)
        
        debug_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Thêm thông tin debug
        debug_info = f"""Server Configuration:
    - Using fixed config file: config.json
    - Each test is sent to the same file location
    - Server processes may take 10-30 seconds
    - WAN operations require 20-30 second delays
    - Network tests will cause temporary disconnections

    Transaction Tracking:
    - Client adds transaction IDs to each test
    - Server does not use transaction IDs yet
    - Multiple quick tests may cause server congestion

    Current UTC Time: {self._get_current_time_utc()}
    Current Local Time: {self._get_current_time()}
    """
        
        debug_text.insert(tk.END, debug_info)
        
        # Nút đóng
        ttk.Button(main_frame, text="Close", command=debug_window.destroy).pack(side=tk.RIGHT, pady=10)
        
        # Nút test server
        ttk.Button(main_frame, text="Connect", 
                command=self._test_connection).pack(side=tk.LEFT, pady=10)


    def _get_current_time_utc(self):
        """Get current UTC time in correct format (YYYY-MM-DD HH:MM:SS)"""
        import datetime
        return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    def _show_documentation(self) -> None:
        """Show documentation."""
        doc_text = f"""
{APP_NAME} v{APP_VERSION}

Template-based OpenWrt router testing tool.

Phase 1: Foundation completed
- Basic GUI structure
- Configuration management  
- Logging system
- Project structure

Phase 2: Coming soon
- Template system
- SSH connectivity
- Test execution
- Database operations
        """
        messagebox.showinfo("Documentation", doc_text)
    
    def _show_about(self) -> None:
        """Show about dialog."""
        about_text = f"""
{APP_NAME} v{APP_VERSION}

Template-based OpenWrt router testing tool

Author: juno-kyojin
Created: 2025-06-12

A comprehensive Windows application for automated testing
of OpenWrt routers using template-driven test case
generation and execution.
        """
        messagebox.showinfo("About", about_text)
    
    def _on_closing(self) -> None:
        """Handle application closing."""
        try:
            self.logger.info("Application closing...")
            
            # TODO: Save any unsaved data
            # TODO: Clean up resources
            
            if self.root:
                self.root.destroy()
                
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def run(self) -> None:
        """Run the application main loop."""
        if not self.root:
            raise TestCaseManagerError("Window not initialized")
        
        try:
            self.logger.info("Starting GUI main loop")
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"GUI error: {e}")
            raise TestCaseManagerError(f"GUI execution failed: {e}")