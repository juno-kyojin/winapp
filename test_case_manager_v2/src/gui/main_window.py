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
        
        # Initialize tkinter variables
        self.ssh_host_var: Optional[tk.StringVar] = None
        self.ssh_port_var: Optional[tk.StringVar] = None
        self.ssh_username_var: Optional[tk.StringVar] = None
        self.ssh_password_var: Optional[tk.StringVar] = None
        self.connection_status_var: Optional[tk.StringVar] = None
        self.status_var: Optional[tk.StringVar] = None
        self.log_text: Optional[tk.Text] = None
        
        self._setup_window()
        self._create_menu()
        self._create_tabs()
        self._create_status_bar()
        
        self.logger.info("Main window initialized")
    
    def _setup_window(self) -> None:
        """Setup the main window properties."""
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
        self._create_queue_tab()
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
        conn_frame = ttk.LabelFrame(top_frame, text="Kết Nối Router")
        conn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Host and port (on same line)
        host_port_frame = ttk.Frame(conn_frame)
        host_port_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(host_port_frame, text="Host:").pack(side=tk.LEFT, padx=2)
        self.ssh_host_var = tk.StringVar(value=self.config.network.ssh_host)
        ttk.Entry(host_port_frame, textvariable=self.ssh_host_var, width=15).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(host_port_frame, text="Port:").pack(side=tk.LEFT, padx=2)
        self.ssh_port_var = tk.StringVar(value=str(self.config.network.ssh_port))
        ttk.Entry(host_port_frame, textvariable=self.ssh_port_var, width=5).pack(side=tk.LEFT, padx=2)
        
        # Username and password (on same line)
        user_pass_frame = ttk.Frame(conn_frame)
        user_pass_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(user_pass_frame, text="User:").pack(side=tk.LEFT, padx=2)
        self.ssh_username_var = tk.StringVar(value=self.config.network.ssh_username)
        ttk.Entry(user_pass_frame, textvariable=self.ssh_username_var, width=10).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(user_pass_frame, text="Pass:").pack(side=tk.LEFT, padx=2)
        self.ssh_password_var = tk.StringVar(value=self.config.network.ssh_password)
        ttk.Entry(user_pass_frame, textvariable=self.ssh_password_var, show="*", width=10).pack(side=tk.LEFT, padx=2)
        
        # Buttons
        button_frame = ttk.Frame(conn_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save", command=self._save_connection_settings).pack(side=tk.LEFT, padx=5)
        
        # Status panel
        status_frame = ttk.LabelFrame(top_frame, text="Trạng Thái")
        status_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Connection status indicator
        status_indicator = ttk.Frame(status_frame, width=200)
        status_indicator.pack(fill=tk.X, padx=5, pady=5)
        
        self.connection_status_var = tk.StringVar(value="🔴 Not connected")
        ttk.Label(status_indicator, textvariable=self.connection_status_var, font=("Segoe UI", 9)).pack(anchor=tk.W)
        ttk.Label(status_indicator, text="Last ping: --").pack(anchor=tk.W)
        ttk.Label(status_indicator, text="Router Model: --").pack(anchor=tk.W)
        
        # ROW 2: Test Case Library with TreeView
        library_frame = ttk.LabelFrame(frame, text="Test Case Library")
        library_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Search bar
        search_frame = ttk.Frame(library_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(search_frame, text="Refresh", command=self._refresh_test_cases).pack(side=tk.RIGHT, padx=5)
        
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
        
        ttk.Button(action_frame, text="✅ Thêm vào Test Queue", command=self._add_to_test_queue).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🔍 Xem Chi Tiết", command=self._view_template_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📝 Tạo Từ Template", command=self._create_from_template).pack(side=tk.RIGHT, padx=5)
        
        # ROW 3: Parameters section
        self.params_frame = ttk.LabelFrame(frame, text="Template Parameters")
        self.params_frame.pack(fill=tk.BOTH, padx=10, pady=5)
        
        # We'll create a dynamic parameters form based on selected template
        self.create_placeholder_params()

    def _create_placeholder_params(self):
        """Alias for create_placeholder_params for consistency"""
        self.create_placeholder_params()

    def _populate_test_tree(self):
        """Populate the test case tree with hierarchical data"""
        # Clear existing items
        for item in self.test_tree.get_children():
            self.test_tree.delete(item)
        
        # Define categories and their test cases
        test_categories = {
            "WAN": [
                {"id": "wan_create", "name": "Tạo WAN mới", "impacts_network": True},
                {"id": "wan_delete", "name": "Xóa WAN", "impacts_network": True},
                {"id": "wan_modify", "name": "Chỉnh sửa WAN", "impacts_network": True},
            ],
            "LAN": [
                {"id": "lan_config", "name": "Cấu hình LAN", "impacts_network": True},
                {"id": "lan_interfaces", "name": "Quản lý interfaces LAN", "impacts_network": True},
                {"id": "lan_dhcp", "name": "Thiết lập DHCP server", "impacts_network": True},
            ],
            "Network": [
                {"id": "ping_test", "name": "Kiểm tra Ping", "impacts_network": False},
                {"id": "bandwidth_test", "name": "Kiểm tra Bandwidth", "impacts_network": False},
                {"id": "dns_test", "name": "Kiểm tra DNS", "impacts_network": False},
            ],
            "Security": [
                {"id": "firewall_rule", "name": "Thiết lập Firewall", "impacts_network": False},
                {"id": "port_forward", "name": "Cấu hình Port Forwarding", "impacts_network": False},
            ],
            "System": [
                {"id": "sys_backup", "name": "Sao lưu cấu hình", "impacts_network": False},
                {"id": "sys_restore", "name": "Phục hồi cấu hình", "impacts_network": True},
                {"id": "sys_reboot", "name": "Khởi động lại Router", "impacts_network": True},
            ],
        }
        
        # Add categories and their test cases
        for category, test_cases in test_categories.items():
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
        """Handler for test case selection from TreeView"""
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
        else:
            # It's a category - clear parameters
            self.params_frame.configure(text="Template Parameters")
            self._clear_parameters()

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
        elif test_id == "ping_test":
            params = [
                {"name": "host1", "value": "youtube.com", "type": "string", "required": True},
                {"name": "host2", "value": "google.com", "type": "string", "required": False},
                {"name": "count", "value": "4", "type": "integer", "required": False},
            ]
        else:
            # Default parameters
            params = [
                {"name": "param1", "value": "value1", "type": "string", "required": True},
                {"name": "param2", "value": "value2", "type": "string", "required": False},
            ]
            
        # Create UI for parameters
        self._create_parameter_controls(params)

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
        # Parameter table frame
        param_table_frame = ttk.Frame(self.params_frame)
        param_table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Headers
        header_frame = ttk.Frame(param_table_frame)
        header_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(header_frame, text="Tham số", width=15, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(header_frame, text="Giá trị", width=20, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="Kiểu", width=10, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=5)
        ttk.Label(header_frame, text="Bắt buộc", width=10, anchor=tk.CENTER, font=("Segoe UI", 9, "bold")).grid(row=0, column=3, padx=5)
        
        # Create parameter rows
        param_rows_frame = ttk.Frame(param_table_frame)
        param_rows_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Store parameter variables for later access
        self.param_vars = {}
        
        row = 0
        for param in params:
            ttk.Label(param_rows_frame, text=param["name"], width=15, anchor=tk.W).grid(row=row, column=0, padx=5, pady=3)
            
            # Different input types based on parameter type
            if param["type"] == "enum" and "options" in param:
                var = tk.StringVar(value=param["value"])
                ttk.Combobox(param_rows_frame, textvariable=var, values=param["options"], width=18).grid(row=row, column=1, padx=5, pady=3)
            elif param["type"] == "boolean":
                var = tk.StringVar(value=param["value"])
                options = ["true", "false"]
                ttk.Combobox(param_rows_frame, textvariable=var, values=options, width=18).grid(row=row, column=1, padx=5, pady=3)
            else:
                var = tk.StringVar(value=param["value"])
                ttk.Entry(param_rows_frame, textvariable=var, width=20).grid(row=row, column=1, padx=5, pady=3)
            
            # Store the variable
            self.param_vars[param["name"]] = var
            
            ttk.Label(param_rows_frame, text=param["type"], width=10).grid(row=row, column=2, padx=5, pady=3)
            
            required_text = "✓" if param.get("required", False) else ""
            ttk.Label(param_rows_frame, text=required_text, width=10, anchor=tk.CENTER).grid(row=row, column=3, padx=5, pady=3)
            
            row += 1
        
        # Action buttons
        button_frame = ttk.Frame(self.params_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="💾 Lưu Tham Số", command=self._save_parameters).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Reset", command=lambda: self._on_test_case_selected(None)).pack(side=tk.LEFT, padx=5)

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
        
        # In a real app, collect all parameter values
        param_values = {}
        for param_name, var in self.param_vars.items():
            param_values[param_name] = var.get()
        
        # In Phase 1, just show a message
        messagebox.showinfo("Success", f"Parameters for '{test_name}' saved successfully")
        self.logger.info(f"Template parameters saved for {test_name}")
        
        # Update status
        if self.status_var:
            self.status_var.set(f"Parameters saved for {test_name}")
        
    def create_placeholder_params(self):
        """Create placeholder parameters UI"""
        # Clear existing widgets
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        # Parameter table frame
        param_table_frame = ttk.Frame(self.params_frame)
        param_table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Headers
        header_frame = ttk.Frame(param_table_frame)
        header_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(header_frame, text="Tham số", width=15, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(header_frame, text="Giá trị", width=20, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="Kiểu", width=10, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=5)
        ttk.Label(header_frame, text="Bắt buộc", width=10, anchor=tk.CENTER, font=("Segoe UI", 9, "bold")).grid(row=0, column=3, padx=5)
        
        # Sample parameters (in a real app, these would be dynamically loaded)
        params = [
            {"name": "name", "value": "wan1", "type": "string", "required": True},
            {"name": "protocol", "value": "ipv4", "type": "enum", "required": True, "options": ["ipv4", "ipv6", "pppoe"]},
            {"name": "interface", "value": "eth1", "type": "enum", "required": True, "options": ["eth1", "eth2", "wlan0"]},
            {"name": "metric", "value": "100", "type": "integer", "required": False},
        ]
        
        # Create parameter rows
        param_rows_frame = ttk.Frame(param_table_frame)
        param_rows_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        row = 0
        for param in params:
            ttk.Label(param_rows_frame, text=param["name"], width=15, anchor=tk.W).grid(row=row, column=0, padx=5, pady=3)
            
            # Different input types based on parameter type
            if param["type"] == "enum" and "options" in param:
                var = tk.StringVar(value=param["value"])
                ttk.Combobox(param_rows_frame, textvariable=var, values=param["options"], width=18).grid(row=row, column=1, padx=5, pady=3)
            else:
                var = tk.StringVar(value=param["value"])
                ttk.Entry(param_rows_frame, textvariable=var, width=20).grid(row=row, column=1, padx=5, pady=3)
            
            ttk.Label(param_rows_frame, text=param["type"], width=10).grid(row=row, column=2, padx=5, pady=3)
            
            required_text = "✓" if param.get("required", False) else ""
            ttk.Label(param_rows_frame, text=required_text, width=10, anchor=tk.CENTER).grid(row=row, column=3, padx=5, pady=3)
            
            row += 1
        
        # Action buttons
        button_frame = ttk.Frame(self.params_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="💾 Lưu Tham Số", command=self._save_parameters).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Reset", command=lambda: self.create_placeholder_params()).pack(side=tk.LEFT, padx=5)



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
        
    def _add_to_test_queue(self):
        """Add current template with parameters to test queue"""
        selected = self.test_tree.selection()  # Sửa từ template_tree thành test_tree
        if not selected:
            messagebox.showinfo("Information", "Please select a template first")
            return
        
        template_name = self.test_tree.item(selected[0], "values")[1]  # Sửa
        messagebox.showinfo("Success", f"Template '{template_name}' added to Test Queue with current parameters")

    def _create_from_template(self):
        """Create a new test case from the selected template"""
        selected = self.test_tree.selection()
        if not selected or self.test_tree.get_children(selected[0]):
            messagebox.showinfo("Information", "Please select a test case first")
            return
            
        # Get test case info
        test_id = self.test_tree.item(selected[0], "values")[0]
        test_name = self.test_tree.item(selected[0], "text").split(" ⚠️")[0]
        category = self.test_tree.item(self.test_tree.parent(selected[0]), "text").lower()
        
        # Get service and action from test_id
        parts = test_id.split('_')
        service = parts[0]  # wan, ping, etc.
        action = parts[1] if len(parts) > 1 else ""  # create, delete, etc.
        
        # Collect parameter values
        params = {}
        for param_name, var in self.param_vars.items():
            # Special handling for array parameters
            if param_name == "ipv4_dns":
                # Split comma-separated values into array
                dns_values = var.get().split(",")
                params[param_name] = [dns.strip() for dns in dns_values if dns.strip()]
            else:
                # Handle different types
                value = var.get()
                if value.lower() == "true":
                    params[param_name] = True
                elif value.lower() == "false":
                    params[param_name] = False
                elif value.isdigit():
                    params[param_name] = int(value)
                else:
                    params[param_name] = value
        
        # Create the JSON structure
        test_case = {
            "test_cases": [
                {
                    "service": service
                }
            ]
        }
        
        # Add action if it exists
        if action:
            test_case["test_cases"][0]["action"] = action
        
        # Add params
        test_case["test_cases"][0]["params"] = params
        
        # Create a unique filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_id}_{timestamp}.json"
        
        # In a real app, save to file
        import json
        try:
            # Just for demo in Phase 1
            json_str = json.dumps(test_case, indent=4)
            messagebox.showinfo("Test Case Created", 
                            f"Created test case file '{filename}':\n\n{json_str[:200]}...")
            
            self.logger.info(f"Generated test case: {filename}")
            
            # Update status
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
        elif test_id == "ping_test":
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
        
        ttk.Button(button_frame, text="Test Connection", command=self._test_connection).pack(
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
        
        # Placeholder content
        ttk.Label(frame, text="Test queue will be implemented in Phase 2").pack(
            expand=True
        )
    
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
        """Create the status bar."""
        if not self.root:
            return
            
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status message
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(
            side=tk.LEFT, padx=10, pady=2
        )
        
        # Version info
        ttk.Label(status_frame, text=f"v{APP_VERSION}").pack(
            side=tk.RIGHT, padx=10, pady=2
        )
    
    def _test_connection(self) -> None:
        """Test SSH connection."""
        # TODO: Implement in Phase 2
        if self.connection_status_var:
            self.connection_status_var.set("Testing connection...")
        
        if self.root:
            self.root.after(2000, lambda: self._update_connection_status("Connection test not implemented"))
        
        self.logger.info("Connection test requested")
    
    def _update_connection_status(self, status: str) -> None:
        """Update connection status safely."""
        if self.connection_status_var:
            self.connection_status_var.set(status)
    
    def _save_connection_settings(self) -> None:
        """Save connection settings."""
        try:
            if self.ssh_host_var:
                self.config.network.ssh_host = self.ssh_host_var.get()
            if self.ssh_port_var:
                self.config.network.ssh_port = int(self.ssh_port_var.get())
            if self.ssh_username_var:
                self.config.network.ssh_username = self.ssh_username_var.get()
            if self.ssh_password_var:
                self.config.network.ssh_password = self.ssh_password_var.get()
            
            # TODO: Save to file in Phase 2
            if self.status_var:
                self.status_var.set("Connection settings saved")
            self.logger.info("Connection settings updated")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid port number: {e}")
    
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
        """Validate all templates."""
        # TODO: Implement in Phase 2
        messagebox.showinfo("Info", "Template validation will be implemented in Phase 2")
    
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