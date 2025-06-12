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
        status_frame = ttk.LabelFrame(top_frame, text="Status")
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
        self.params_frame.pack(fill=tk.BOTH, padx=10, pady=5)
        
        # Create dynamic parameters form based on selected template
        self.create_placeholder_params()

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
                {"id": "ping_test", "name": "ping_test", "impacts_network": False},
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
        # Parameter table frame
        param_table_frame = ttk.Frame(self.params_frame)
        param_table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Headers
        header_frame = ttk.Frame(param_table_frame)
        header_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(header_frame, text="Param", width=15, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(header_frame, text="Value", width=20, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="Type", width=10, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=5)
        ttk.Label(header_frame, text="Require", width=10, anchor=tk.CENTER, font=("Segoe UI", 9, "bold")).grid(row=0, column=3, padx=5)
        
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
        
        ttk.Button(button_frame, text="💾 Save Param", command=self._save_parameters).pack(side=tk.LEFT, padx=5)
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
        
        ttk.Label(header_frame, text="Parameter", width=15, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(header_frame, text="Value", width=20, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="Type", width=10, anchor=tk.W, font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=5)
        ttk.Label(header_frame, text="Required", width=10, anchor=tk.CENTER, font=("Segoe UI", 9, "bold")).grid(row=0, column=3, padx=5)
        
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
        
        ttk.Button(button_frame, text="💾 Save Parameters", command=self._save_parameters).pack(side=tk.LEFT, padx=5)
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
        current_time = "2025-06-12 08:11:17"
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
                "identifier": identifier
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
        
        # Import the TestQueueManager
        from gui.widgets.queue_manager import TestQueueManager
        
        # Create queue manager as a member variable to access from other methods
        self.queue_manager = TestQueueManager(frame, 
                                            on_selection_change=self._on_queue_selection_change)
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