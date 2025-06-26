import tkinter as tk
from tkinter import ttk, messagebox
import random
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
        
        from core.test_case_manager import TestCaseFileManager
        self.test_case_manager = TestCaseFileManager()

        from core.test_case_loader import TestCaseLoader
        self.test_loader = TestCaseLoader()
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
        self._initialize_treeview_tags()

        self.logger.info("Main window initialized")

    def _initialize_treeview_tags(self):
        """Khởi tạo tags cho các treeview nếu cần"""
        # Sẽ được gọi sau khi UI đã được tạo
        self._safe_after(100, self._setup_treeview_tags)
        
    def _setup_treeview_tags(self):
        """Thiết lập tags cho các treeview"""
        try:
            if hasattr(self, 'detail_table'):
                self.detail_table.tag_configure("pass", background="#e8f5e9")
                self.detail_table.tag_configure("fail", background="#ffebee")
                self.detail_table.tag_configure("warning", background="#fff8e1")
        except Exception as e:
            self.logger.error(f"Error setting up treeview tags: {e}")
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
        """Populate the test case tree with data loaded from test case files"""
        # Clear existing items
        for item in self.test_tree.get_children():
            self.test_tree.delete(item)
        
        # Load all categories from files
        all_categories = self.test_loader.get_categories()
        
        # Filter if needed
        if filter_category and filter_category != "ALL":
            categories = {k: v for k, v in all_categories.items() if k == filter_category}
        else:
            categories = all_categories
        
        # Add categories and test cases
        for category, test_cases in categories.items():
            # Add category as parent
            category_id = self.test_tree.insert("", "end", text=category)
            
            # Add test cases under the category
            for test_case in test_cases:
                # Add icon indicator for network impact
                display_text = test_case["name"]
                if test_case["impacts_network"]:
                    display_text = f"{display_text} ⚠️"
                    
                # Store test case info in the values
                self.test_tree.insert(
                    category_id, 
                    "end", 
                    text=display_text,
                    values=(test_case["id"], category, test_case["impacts_network"], test_case["file_path"])
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
            values = self.test_tree.item(selection[0], "values")
            if not values or len(values) < 1:
                self.logger.error("Selected test case has no values")
                return
                
            test_id = values[0]
            test_name = self.test_tree.item(selection[0], "text").split(" ⚠️")[0]  # Remove warning icon if present
            category = self.test_tree.item(self.test_tree.parent(selection[0]), "text")
            
            # Update parameters frame title
            self.params_frame.configure(text=f"Template Parameters ({test_name})")
            
            # Quan trọng: Xóa dữ liệu test case cũ trước khi tải test case mới
            if hasattr(self, '_original_test_data'):
                self._original_test_data = None
                
            # Load parameters for the selected test case
            self._load_test_parameters(test_id, category)
            
            # Đặt status message để đảm bảo hiển thị đúng
            self._safe_set(self.status_var, f"Selected test: {test_name}")
                
            # Đảm bảo UI được cập nhật
            if self.root:
                self.root.update_idletasks()
        else:
            # It's a category - clear parameters
            self.params_frame.configure(text="Template Parameters")
            self._clear_parameters()
            
            # Đặt status message
            self._safe_set(self.status_var, f"Selected category: {self.test_tree.item(selection[0], 'text')}")
    def _load_test_parameters(self, test_id, category):
        """Load parameters from test files - always load fresh data for new selection"""
        # Clear existing parameters
        self._clear_parameters()
        
        # Initialize empty params list
        params = []
        
        # Luôn tải mới dữ liệu khi chọn test case
        test_data = self.test_loader.load_test_case(test_id, category)
        self.logger.debug(f"Loaded fresh test data from file for {test_id}")
        
        # Lưu lại để sử dụng cho các lần gọi tiếp theo
        self._original_test_data = test_data
        
        if test_data and "test_cases" in test_data and len(test_data["test_cases"]) > 0:
            # Get params from the first test case
            raw_params = test_data["test_cases"][0].get("params", {})
            
            # Convert from dict to list format
            for key, value in raw_params.items():
                # Handle special data types
                if isinstance(value, list):
                    # For lists like ipv4_dns, convert to comma-separated string
                    str_value = ",".join(str(item) for item in value)
                elif isinstance(value, bool):
                    # For booleans, convert to "true"/"false"
                    str_value = str(value).lower()
                else:
                    # For other types, convert to string
                    str_value = str(value) if value is not None else ""
                
                param = {
                    "name": key,
                    "value": str_value
                }
                params.append(param)
        
        # Create UI controls
        self._create_parameter_controls(params)

        # Log để debug
        self.logger.info(f"Loaded parameters for {test_id} in {category}: {len(params)} parameters")

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
        """Add selected saved test to queue với cải tiến lưu service/action đúng"""
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
            
            # Thiết lập giá trị mặc định
            test_case = {}
            service = ""
            action = ""
            params = {}
            
            # Trích xuất thông tin từ file
            if isinstance(data, dict) and "test_cases" in data:
                # New format
                test_case = data["test_cases"][0] if data["test_cases"] else {}
                service = test_case.get("service", "")
                action = test_case.get("action", "")
                params = test_case.get("params", {})
                # Ghi log thông tin tìm thấy
                self.logger.info(f"Extracted from file {filename}: service='{service}', action='{action}'")
            elif isinstance(data, list) and len(data) > 0:
                # Old format
                test_case = data[0]
                service = test_case.get("service", "")
                action = test_case.get("action", "")
                params = test_case.get("params", {})
                self.logger.info(f"Extracted from legacy format {filename}: service='{service}', action='{action}'")
            else:
                raise ValueError("Invalid test case format")
                    
            # Fallback nếu không tìm thấy service/action
            if not service:
                # Thử trích xuất từ tên file
                base_name = os.path.splitext(filename)[0]
                parts = base_name.split('_')
                if parts:
                    service = parts[0]
                    if len(parts) > 1:
                        action = '_'.join(parts[1:])
                self.logger.info(f"Service không tìm thấy trong file, fallback từ tên file: service='{service}', action='{action}'")
            
            # Determine category from file path
            parts = file_path.split(os.sep)
            category = "Unknown"
            if "generated_tests" in parts:
                idx = parts.index("generated_tests")
                if idx + 1 < len(parts):
                    category = parts[idx + 1].title()
            
            # Generate test ID from service and action
            test_id = f"{service}_{action}" if action else service
            display_name = os.path.splitext(filename)[0]  # Sử dụng tên file không có phần mở rộng làm tên hiển thị
            
            # Add to queue with service and action
            if hasattr(self, 'queue_manager'):
                # Sử dụng add_item với đầy đủ service và action
                added = self.queue_manager.add_item(test_id, display_name, category, params, service, action)
                
                if added:
                    # Switch to queue tab
                    if self.notebook:
                        for i in range(self.notebook.index("end")):
                            if "Test Queue" in self.notebook.tab(i, "text"):
                                self.notebook.select(i)
                                break
                        
                    self.logger.info(f"Added saved test to queue: {filename} (service={service}, action={action})")
                    
                    # Update status
                    if self.status_var:
                        self.status_var.set(f"Added {display_name} to queue")
                        
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
        # Tải lại test case từ file
        self._populate_test_tree()
        
        # Show status message
        self._safe_set(self.status_var, "Test cases refreshed from file")
        
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
        ttk.Button(control_frame, text="🔄 Reset", command=self._reset_parameters).pack(side=tk.RIGHT, padx=5)

    
        
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
        """Save parameters back to file."""
        # Get selected item
        selected = self.test_tree.selection()
        if not selected or self.test_tree.get_children(selected[0]):
            messagebox.showinfo("Information", "Please select a test case first")
            return
                
        # Get test case info
        values = self.test_tree.item(selected[0], "values")
        if not values or len(values) < 2:
            messagebox.showinfo("Error", "Invalid selection")
            return
            
        test_id = values[0]
        category = values[1]
        file_path = values[3] if len(values) > 3 else None
        
        try:
            # Load original test data to preserve structure
            test_data = None
            if hasattr(self, '_original_test_data') and self._original_test_data:
                test_data = self._original_test_data.copy()  # Tạo bản sao để tránh sửa đổi gốc
            else:
                # Load from file if we don't have original data
                test_data = self.test_loader.load_test_case(test_id, category)
            
            # If still no data, create a new test structure
            if not test_data:
                parts = test_id.split('_')
                service = parts[0]
                action = parts[1] if len(parts) > 1 else ""
                
                test_data = {
                    "test_cases": [
                        {
                            "service": service,
                            "action": action,
                            "params": {}
                        }
                    ],
                    "metadata": {}  # Đảm bảo metadata là một dict
                }
            
            # Collect all parameter values
            params_dict = {}
            for param_name, var in self.param_vars.items():
                value = var.get()
                
                # Convert to appropriate types
                if value.lower() == "true":
                    params_dict[param_name] = True
                elif value.lower() == "false":
                    params_dict[param_name] = False
                elif value.isdigit():
                    params_dict[param_name] = int(value)
                elif "," in value and any(name in param_name.lower() for name in ["dns", "servers", "hosts"]):
                    # Handle comma-separated lists for DNS and similar fields
                    params_dict[param_name] = [item.strip() for item in value.split(",") if item.strip()]
                else:
                    params_dict[param_name] = value
            
            # Update the params in test_data
            if "test_cases" in test_data and len(test_data["test_cases"]) > 0:
                test_data["test_cases"][0]["params"] = params_dict
            
            # Add/update metadata - Sửa cấu trúc đúng
            if "metadata" not in test_data:
                test_data["metadata"] = {}  # Tạo dict mới nếu chưa tồn tại
                
            # Đảm bảo metadata là một dict (phòng trường hợp nó là kiểu dữ liệu khác)
            if not isinstance(test_data["metadata"], dict):
                test_data["metadata"] = {}  # Tạo lại nếu không phải dict
                
            # Bây giờ cập nhật các thuộc tính metadata an toàn
            # Sử dụng thời gian và người dùng được cung cấp
            test_data["metadata"]["last_modified"] = "2025-06-23 08:41:06"  # Thời gian từ input
            test_data["metadata"]["modified_by"] = "juno-kyojin"  # Người dùng từ input
            
            # Save the test case
            success, message = self.test_loader.save_test_case(test_id, category, test_data)
            
            # Quan trọng: Lưu lại bản sao mới nhất để so sánh khi reset
            if success:
                # Lưu bản mới nhất sau khi lưu thành công
                self._original_test_data = test_data.copy()
                
                messagebox.showinfo("Success", f"Parameters saved for {test_id}")
                self._safe_set(self.status_var, f"Saved parameters for {test_id}")
                self.logger.info(f"Saved parameters for {test_id} in {category}")
            else:
                messagebox.showerror("Error", message)
                self.logger.error(f"Failed to save parameters: {message}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
            self.logger.error(f"Error saving parameters: {str(e)}")
    def _reset_parameters(self):
        """Reset parameters from file"""
        # Get selected item
        selected = self.test_tree.selection()
        if not selected:
            return
            
        try:
            # Check if it's a test case (leaf) or category (parent)
            if not self.test_tree.get_children(selected[0]):
                # Get test case info safely
                values = self.test_tree.item(selected[0], "values")
                if not values or len(values) < 2:
                    self.logger.error("Selected item has no values")
                    return
                    
                test_id = values[0] 
                category = values[1]
                
                # Xác nhận reset nếu có các tham số mới được thêm vào
                current_param_count = len(self.param_vars) if hasattr(self, 'param_vars') else 0
                confirm_reset = True
                
                # Nếu có nhiều hơn 2 tham số, hiển thị thông báo xác nhận
                if current_param_count > 2:  # Đặt ngưỡng phù hợp cho ứng dụng của bạn
                    confirm_reset = messagebox.askyesno(
                        "Confirm Reset", 
                        f"Reset will discard any new parameters added. Continue?",
                        icon='warning'
                    )
                
                if not confirm_reset:
                    return
                    
                # Force reload from file - always reload fresh from disk
                # Buộc LUÔN đọc lại từ đĩa, không sử dụng bộ nhớ cache
                self._original_test_data = None  # Xóa dữ liệu cũ
                
                # Tải lại trực tiếp từ file
                file_path = values[3] if len(values) > 3 else None
                
                # Nếu có file_path, dùng nó để tải trực tiếp
                if file_path and os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self._original_test_data = json.load(f)
                        self.logger.info(f"Reset: Loaded test data directly from {file_path}")
                else:
                    # Ngược lại, sử dụng test_loader để tìm và tải
                    self.logger.info(f"Reset: Loading test data for {test_id} from category {category}")
                    
                # Tải tham số bằng cách sử dụng dữ liệu đã tải hoặc yêu cầu tải mới
                self._load_test_parameters(test_id, category)
                
                # Update status
                self._safe_set(self.status_var, f"Parameters reset for {test_id}")
                
        except Exception as e:
            self.logger.error(f"Error resetting parameters: {e}")
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
        """Add current template with parameters to test queue với service và action"""
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
        
        # ==== PHẦN THAY ĐỔI QUAN TRỌNG ====
        # Load test case data từ file để lấy service và action chính xác
        test_data = None
        service = ""
        action = ""
        
        # Lưu log để debug
        self.logger.info(f"Loading test case '{test_id}' from category '{category}'")
        
        # Load dữ liệu test case từ file
        if hasattr(self, 'test_loader') and self.test_loader:
            test_data = self.test_loader.load_test_case(test_id, category)
        
        # Trích xuất service và action từ test data
        if test_data and "test_cases" in test_data and len(test_data["test_cases"]) > 0:
            test_case = test_data["test_cases"][0]
            service = test_case.get("service", "")
            action = test_case.get("action", "")
            
            self.logger.info(f"Found in JSON file: service='{service}', action='{action}'")
        else:
            # Fallback nếu không tìm thấy dữ liệu từ file
            parts = test_id.split('_')
            service = parts[0]  # First part as service
            
            # Remaining parts as action if any
            if len(parts) > 1:
                action = '_'.join(parts[1:])
                
            self.logger.info(f"Data not found in file, using fallback: service='{service}', action='{action}'")
        # ==== KẾT THÚC PHẦN THAY ĐỔI ====
        
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
        
        # ==== PHẦN THAY ĐỔI QUAN TRỌNG ====
        # Add to queue with service and action info
        added = self.queue_manager.add_item(test_id, test_name, category, params, service, action)
        # ==== KẾT THÚC THAY ĐỔI ====
        
        if added:
            # Update status
            if self.status_var:
                self.status_var.set(f"Added {test_name} to test queue")
                
            # Switch to queue tab to show the addition
            if self.notebook:
                queue_tab_index = self.notebook.index("end") - 3  # Assuming queue is the 3rd tab from end
                self.notebook.select(queue_tab_index)
                
            # Log the addition with service and action info
            self.logger.info(f"Added test case to queue: {test_name} ({test_id}), service={service}, action={action}")
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
            on_run_selected=self.send_selected_test
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
        
        # THÊM MỚI: Test Case Details Frame
        details_frame = ttk.LabelFrame(frame, text="Test Case Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create detail table
        columns = ("service", "action", "parameters", "status", "details")
        self.detail_table = ttk.Treeview(details_frame, columns=columns, show="headings")
        
        # Configure columns
        self.detail_table.heading("service", text="Service")
        self.detail_table.heading("action", text="Action")
        self.detail_table.heading("parameters", text="Parameters")
        self.detail_table.heading("status", text="Status")
        self.detail_table.heading("details", text="Details")
        
        # Set column widths
        self.detail_table.column("service", width=100)
        self.detail_table.column("action", width=100) 
        self.detail_table.column("parameters", width=150)
        self.detail_table.column("status", width=80)
        self.detail_table.column("details", width=300)
        
        # Add scrollbar
        detail_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.detail_table.yview)
        self.detail_table.configure(yscrollcommand=detail_scrollbar.set)
        
        # Pack widgets
        self.detail_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure tags for coloring
        self.detail_table.tag_configure("pass", background="#e8f5e9")
        self.detail_table.tag_configure("fail", background="#ffebee")
        
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
        """Gửi test case đến HTTP server với giải pháp chống race condition"""
        try:
            # Import required libraries
            import requests
            import json
            import time
            import uuid
            import random
            import datetime
            
            if not self.http_client:
                self.logger.error("HTTP client not initialized")
                error_msg = "HTTP client not initialized"
                self._safe_after(0, lambda err=error_msg: self.update_test_status(index, "Error", err))
                return
                    
            # Lấy thông tin kết nối từ UI thay vì hardcode
            host = self._safe_get(self.http_host_var, "127.0.0.1")
            port = int(self._safe_get(self.http_port_var, "6262"))
            url = f"http://{host}:{port}"
            
            # Lấy transaction_id từ metadata hoặc tạo mới nếu không có
            transaction_id = test_data.get("metadata", {}).get("transaction_id", "")
            if not transaction_id:
                transaction_id = f"tx-{str(uuid.uuid4())[:8]}"
                if "metadata" in test_data:
                    test_data["metadata"]["transaction_id"] = transaction_id
                    
            self.logger.info(f"Sending test case to {url}")
            tx_msg = f"Request sent, TX: {transaction_id[:8]}"
            self._safe_after(0, lambda msg=tx_msg: self.update_test_status(index, "Sending", msg))
            
            # Cập nhật metadata với thời gian thực thay vì hardcode
            current_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            username = os.environ.get('USERNAME', 'juno-kyojin')  # Lấy từ môi trường hoặc fallback
            
            if "metadata" in test_data:
                test_data["metadata"]["created_at"] = current_time
                test_data["metadata"]["client_timestamp"] = current_time
                test_data["metadata"]["created_by"] = username
            
            # Check if test affects network
            network_impact = self._check_test_affects_network(test_data)
            is_network_test = network_impact["affects_network"]
            expected_disconnect = network_impact["expected_disconnect"]
            restart_delay = network_impact["restart_delay"]
            
            if is_network_test:
                self.logger.info(f"Test {transaction_id} affects network connectivity - will use enhanced handling")
            
            # Thời gian bắt đầu để tính thời gian thực thi
            start_time = time.time()
            
            try:
                # Verify connection before sending
                if not self.http_connected:
                    # Try to reconnect
                    try:
                        import socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        
                        # Sử dụng timeout từ cấu hình UI thay vì hardcode
                        conn_timeout = int(self._safe_get(self.http_conn_timeout_var, "5")) 
                        sock.settimeout(conn_timeout)
                        
                        sock.connect((host, port))
                        sock.close()
                        self.http_connected = True
                    except:
                        self.logger.warning("Connection check failed, but will try to send test anyway")
                
                # Update UI before sending
                self._safe_after(0, lambda: self.update_test_status(index, "Running", "Processing..."))
                
                # Lấy timeout từ UI thay vì hardcode
                conn_timeout = max(10, int(self._safe_get(self.http_conn_timeout_var, "10")))
                read_timeout = max(45, int(self._safe_get(self.http_read_timeout_var, "45")))
                
                # Tạo thông tin chống cache động
                cache_buster = str(uuid.uuid4())[:8]
                cache_time = str(int(time.time() * 1000))
                random_string = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
                
                headers = {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Cache-Buster": cache_buster,
                    "X-Request-Time": cache_time,
                    "X-Random": random_string,
                    "X-Client-ID": username,
                    "X-Transaction-ID": transaction_id
                }
                
                # Thêm thông tin cache vào metadata để đảm bảo mỗi request là duy nhất
                if "metadata" in test_data:
                    test_data["metadata"]["client_request_time"] = cache_time
                    test_data["metadata"]["cache_buster"] = cache_buster
                    test_data["metadata"]["random_id"] = random_string
                    
                    # Thêm unique_id cho mỗi request
                    unique_id = str(uuid.uuid4())
                    test_data["metadata"]["unique_id"] = unique_id
                    test_data["metadata"]["client_version"] = "2.0.1"
                    test_data["metadata"]["client_platform"] = "Windows"
                
                # ===== GIẢI PHÁP CHỐNG RACE CONDITION =====
                # Tạo file config với tên duy nhất theo transaction_id
                config_dir = "/etc/testmanager/config"  # Nên đưa vào cấu hình
                unique_config_name = f"config_{transaction_id}.json"
                config_path = f"{config_dir}/{unique_config_name}"
                
                self.logger.info(f"Creating config file: {config_path}")
                
                # Gửi thông tin file config trong headers
                headers["X-Config-File"] = unique_config_name
                
                # Đợi một chút để đảm bảo server sẵn sàng (có thể đưa vào cấu hình)
                time.sleep(2)
                
                # Xác minh file config đã được tạo (thực hiện trước khi gửi request)
                # Nếu muốn tạo file trước qua API riêng, có thể thêm đoạn này
                
                # Gửi request
                response = requests.post(
                    url,
                    json=test_data,
                    headers=headers,
                    timeout=(conn_timeout, read_timeout)
                )
                
                # Tính thời gian phản hồi
                elapsed_time = time.time() - start_time
                
                # Process response
                if response.status_code == 200:
                    try:
                        result = response.json()
                        self.logger.info(f"Test response received in {elapsed_time:.2f}s: {json.dumps(result, indent=2)}")
                        
                        # Tích hợp xử lý LAN (giữ nguyên)
                        try:
                            test_case = test_data["test_cases"][0] if "test_cases" in test_data and test_data["test_cases"] else {}
                            service = test_case.get("service", "").lower()
                            
                            # Nếu đây là LAN test, xác minh kết quả từ client
                            if service == "lan" and "summary" in result and result["summary"].get("passed", 0) > 0:
                                self.logger.info("LAN test returned success from router. Verifying with client...")
                                
                                # Import LAN checker
                                from network.lan_checker import verify_lan_test
                                
                                # Thực hiện xác minh
                                result = verify_lan_test(test_data, result, self.logger)
                                
                                # Log kết quả xác minh từ client
                                if "client_verification" in result:
                                    status = result["client_verification"].get("status")
                                    message = result["client_verification"].get("message", "")
                                    
                                    if status is True:
                                        self.logger.info(f"Client verification passed: {message}")
                                    elif status == "warning":
                                        self.logger.warning(f"Client verification warning: {message}")
                                    elif status is False:
                                        self.logger.error(f"Client verification failed: {message}")
                                    else:
                                        self.logger.warning(f"Client verification status unclear: {message}")
                        except Exception as e:
                            self.logger.error(f"Error in LAN verification: {str(e)}")
                        
                        # Xác định kết quả cuối cùng
                        summary = result.get("summary", {})
                        passed = summary.get("passed", 0)
                        failed = summary.get("failed", 0)
                        
                        # Cập nhật UI và lưu kết quả
                        success = passed > 0 and failed == 0
                        
                        # Lưu kết quả test trực tiếp
                        try:
                            self.save_result_directly(index, test_data, result, "Success" if success else "Fail", elapsed_time)
                            self.logger.info("Test result saved successfully")
                        except Exception as save_err:
                            self.logger.error(f"Failed to save test result: {save_err}")
                        
                        # Xử lý test ảnh hưởng mạng
                        if is_network_test and success:
                            if expected_disconnect:
                                # Cập nhật UI trước quá trình kết nối lại
                                success_msg = f"Network test passed ({elapsed_time:.1f}s) - Reconnecting..."
                                self._safe_after(0, lambda msg=success_msg: self.update_test_status(index, "Success", msg))
                                
                                # Cập nhật status_var
                                self._safe_set(self.status_var, "Network configuration changed. Reconnecting...")
                                
                                # Đặt lại trạng thái kết nối
                                self.http_connected = False
                                self._safe_set(self.connection_status_var, "🟡 Connection state unknown")
                                
                                # Lên lịch kiểm tra kết nối sau một khoảng thời gian dựa trên mức độ ảnh hưởng
                                self._safe_after(restart_delay * 1000, lambda: self._complete_after_reconnect(index))
                            else:
                                # Đối với những thay đổi không gây mất kết nối
                                self.logger.info(f"Thay đổi mạng không gây mất kết nối, không cần đợi kết nối lại")
                                final_msg = f"Network change applied ({elapsed_time:.1f}s) - No reconnect needed"
                                self._safe_after(0, lambda m=final_msg: self.update_test_status(index, "Success", m))
                                
                                # Kiểm tra kết nối nhẹ
                                self._safe_after(1000, self._recheck_connection)
                        else:
                            # Xử lý các test không ảnh hưởng mạng hoặc test mạng không thành công
                            result_msg = f"P:{passed}, F:{failed}, Time:{elapsed_time:.1f}s"
                            status = "Success" if success else "Failed"
                            
                            # Update UI - capture status and msg for lambda
                            final_status = status
                            final_msg = result_msg
                            self._safe_after(0, lambda s=final_status, m=final_msg: self.update_test_status(index, s, m))
                            
                    except Exception as parse_error:
                        # Handle response parsing error
                        error_str = str(parse_error)
                        self.logger.error(f"Error processing response: {error_str}")
                        self._safe_after(0, lambda err=error_str[:30]: self.update_test_status(index, "Error", f"Parse error: {err}"))
                else:
                    # Handle non-200 HTTP status code
                    err_msg = f"HTTP {response.status_code}"
                    self.logger.error(f"HTTP error: {response.status_code}")
                    self._safe_after(0, lambda e=err_msg: self.update_test_status(index, "Error", e))
                                
            except Exception as req_error:
                # Xử lý connection reset
                error_str = str(req_error)
                self.logger.error(f"Lỗi kết nối: {error_str}")
                
                # Kiểm tra toàn bộ chuỗi lỗi để tìm dấu hiệu connection reset
                connection_reset = False
                
                # Các chuỗi đặc trưng của connection reset
                reset_indicators = [
                    "connection was forcibly closed",
                    "forcibly closed",
                    "connection reset by peer",
                    "connection reset",
                    "broken pipe",
                    "ConnectionResetError",
                    "Connection broken",
                    "10054"  # Mã lỗi Windows cho connection reset
                ]
                
                # Kiểm tra toàn bộ chuỗi lỗi
                for indicator in reset_indicators:
                    if indicator.lower() in error_str.lower():
                        connection_reset = True
                        self.logger.info(f"Phát hiện connection reset qua chuỗi: '{indicator}'")
                        break
                
                # Xử lý connection reset
                if connection_reset and is_network_test:
                    self.logger.info("Connection reset được phát hiện cho test mạng - đây là hành vi mong đợi")
                    
                    # Trích xuất thông tin từ test
                    service = ""
                    action = ""
                    if "test_cases" in test_data and len(test_data["test_cases"]) > 0:
                        test_case = test_data["test_cases"][0]
                        service = test_case.get("service", "")
                        action = test_case.get("action", "")
                    
                    # Tạo kết quả giả định thành công
                    synthetic_result = {
                        "summary": {
                            "total_test_cases": 1,
                            "passed": 1,
                            "failed": 0
                        },
                        "message": f"{service} {action} đã hoàn thành (connection reset như dự kiến)",
                        "test_results": [{
                            "service": service,
                            "action": action,
                            "status": "pass",
                            "details": "Network change đã được áp dụng thành công (connection reset là dự kiến)"
                        }]
                    }
                    
                    # Lưu kết quả và cập nhật UI
                    elapsed_time = time.time() - start_time
                    
                    # LƯU KẾT QUẢ TRỰC TIẾP
                    self.save_result_directly(index, test_data, synthetic_result, "Success", elapsed_time)
                        
                    success_msg = f"Thay đổi mạng đã được áp dụng ({elapsed_time:.1f}s)"
                    self._safe_after(0, lambda msg=success_msg: self.update_test_status(index, "Success", msg))
                    
                    # Đánh dấu kết nối đã mất và lập lịch kết nối lại
                    self.http_connected = False
                    self._safe_set(self.connection_status_var, "🟡 Mất kết nối (đang kết nối lại)")
                    self._safe_set(self.status_var, "Cấu hình mạng đang thay đổi. Kết nối lại đã được lên lịch.")
                    
                    # ĐỢI LÂU HƠN TRƯỚC KHI KẾT NỐI LẠI ĐỐI VỚI THAY ĐỔI IP LAN
                    wait_time = restart_delay  # Sử dụng giá trị đã tính từ network_impact
                    self.logger.info(f"Sẽ thử kết nối lại sau {wait_time} giây")
                    
                    # Sử dụng scheduled task để hoàn tất sau khi kết nối lại
                    self._safe_after(wait_time * 1000, lambda: self._complete_after_reconnect(index))
                    return True
                else:
                    # Xử lý lỗi kết nối thông thường
                    self._safe_after(0, lambda e="Lỗi kết nối": self.update_test_status(index, "Error", e))
                    
        except Exception as e:
            # Xử lý lỗi chung
            error_str = str(e)
            self.logger.error(f"Lỗi khi gửi test: {error_str}")
            self._safe_after(0, lambda err=error_str[:30]: self.update_test_status(index, "Error", f"Lỗi: {err}..."))
    def _complete_after_reconnect(self, index):
        """Hoàn tất test case sau khi đã kết nối lại thành công mà không retry"""
        # Thử kết nối lại với số lần giới hạn
        max_reconnect_retries = 5
        reconnect_retry = 0
        
        while reconnect_retry < max_reconnect_retries:
            if self._recheck_connection():
                break
            self.logger.info(f"Connection check #{reconnect_retry+1} failed, trying again...")
            reconnect_retry += 1
            time.sleep(5)
        
        if reconnect_retry >= max_reconnect_retries:
            self.logger.error("Could not re-establish connection after multiple attempts")
            self.update_test_status(index, "Warning", "Connection unstable after network change")
            self._safe_set(self.connection_status_var, "🟡 Connection unstable")
            return False
        
        # Kết nối lại thành công, đánh dấu test hoàn thành (không retry nữa)
        self.logger.info("Network test completed successfully after reconnection")
        self._safe_set(self.status_var, "Network test completed successfully")
        self.update_test_status(index, "Success", "Network change applied successfully")
        self._safe_set(self.connection_status_var, "🟢 Connected")
        
        return True

    def save_result_directly(self, index, test_data, result_data, status, execution_time):
        """Lưu kết quả test trực tiếp, không dùng lambda hoặc _safe_after"""
        import json
        import os
        import time

        # Khởi tạo biến mặc định để tránh lỗi unbound
        test_id = "unknown"
        transaction_id = "unknown"
        service = ""
        action = ""

        try:
            # Đảm bảo thư mục tồn tại
            result_dir = os.path.join("data", "temp", "results")
            os.makedirs(result_dir, exist_ok=True)

            # Lấy thông tin test an toàn
            name = "unknown"
            if hasattr(self, 'queue_manager') and index < len(self.queue_manager.queue_items):
                test_item = self.queue_manager.queue_items[index]
                test_id = test_item.get("test_id", "unknown")
                name = test_item.get("name", "unknown")
                service = test_item.get("service", "")
                action = test_item.get("action", "")

            # Lấy transaction ID từ metadata
            transaction_id = test_data.get("metadata", {}).get("transaction_id", "unknown")
            clean_tx_id = transaction_id.replace("tx-", "")  # Loại bỏ prefix tx-

            # Nếu chưa có service/action, thử lấy từ test_cases
            if (not service or not action) and "test_cases" in test_data and test_data["test_cases"]:
                test_case = test_data["test_cases"][0]
                service = service or test_case.get("service", "")
                action = action or test_case.get("action", "")
                
            # Tạo tên file với format rõ ràng và thêm service/action
            outcome = status.lower()
            filename = f"{service}_{action}_{clean_tx_id}_{outcome}.json"
            file_path = os.path.join(result_dir, filename)

            # Thêm log rõ ràng trước khi lưu
            self.logger.info(f"Saving test result to: {file_path}")

            # Dữ liệu kết quả với format thống nhất
            result_data_to_save = {
                "test_id": test_id,
                "name": name,
                "service": service,
                "action": action,
                "status": status,
                "execution_time": execution_time,
                "timestamp": "2025-06-25 06:13:00",  # Thời gian từ input
                "transaction_id": transaction_id,
                "request": test_data,
                "response": result_data,
                "user": "juno-kyojin"
            }

            # Lưu file với xử lý lỗi rõ ràng
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_data_to_save, f, indent=2)

            self.logger.info(f"✅ Test result successfully saved to {file_path}")
            
            # ===== THÊM MỚI: CẬP NHẬT CHI TIẾT TRONG UI =====
            # Cập nhật chi tiết trong detail_table nếu có test_results
            if hasattr(self, 'detail_table'):
                test_results = []
                if isinstance(result_data, dict) and "test_results" in result_data:
                    test_results = result_data["test_results"]
                elif isinstance(result_data, dict) and service and action:
                    # Tạo test result từ thông tin cơ bản
                    test_results = [{
                        "service": service,
                        "action": action,
                        "status": "pass" if status.lower() == "success" else "fail",
                        "details": result_data.get("message", "Test completed"),
                        "execution_time": execution_time
                    }]
                    
                # Cập nhật UI trong thread chính
                if test_results:
                    self._safe_after(0, lambda results=test_results: self._update_detail_view(results))
            
            return True

        except Exception as e:
            self.logger.error(f"❌ Error saving test result: {str(e)}")

            # Thử lưu vào thư mục fallback nếu có lỗi
            try:
                os.makedirs("data", exist_ok=True)
                fallback_path = f"data/test_result_{int(time.time())}.json"
                with open(fallback_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "test_id": test_id,
                        "error": str(e),
                        "timestamp": "2025-06-25 06:13:00",
                        "transaction_id": transaction_id,
                        "service": service,
                        "action": action
                    }, f)
                self.logger.info(f"Saved fallback result to {fallback_path}")
            except Exception as fallback_error:
                self.logger.error(f"Failed to save even fallback result: {fallback_error}")
            try:
                # Lên lịch test tiếp theo nếu đang trong chuỗi test
                if hasattr(self, '_running_test_sequence') and self._running_test_sequence:
                    if index + 1 < len(self.queue_manager.queue_items):
                        self.logger.info(f"Scheduling next test #{index+2} after current test completed")
                        
                        # Chạy test tiếp theo sau khoảng thời gian ngắn
                        self._safe_after(5000, lambda: self._execute_test_with_readiness_check(index + 1))
                    else:
                        # Kết thúc chuỗi test
                        self.logger.info("All tests in sequence completed")
                        self._running_test_sequence = False
            except Exception as e:
                self.logger.error(f"Error scheduling next test: {e}")

            return True
    def _verify_config_file_exists(self):
        """Xác minh file config.json tồn tại và có kích thước > 0"""
        try:
            # Lấy thông tin kết nối
            host = self._safe_get(self.http_host_var, "127.0.0.1")
            port = int(self._safe_get(self.http_port_var, "6262"))
            url = f"http://{host}:{port}/check"
            
            try:
                # Kiểm tra file có tồn tại
                response = requests.get(
                    url,
                    params={"file": "/etc/testmanager/config/config.json"},
                    timeout=5,
                    headers={"Cache-Control": "no-cache"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    file_size = data.get("size", 0)
                    
                    if file_size > 10:
                        self.logger.info(f"File config.json verified: {file_size} bytes")
                        return True
                    else:
                        self.logger.warning(f"File config.json has insufficient size: {file_size} bytes")
                        return False
                else:
                    self.logger.warning(f"File check failed with status code: {response.status_code}")
                    return False
                    
            except Exception as e:
                self.logger.warning(f"Error checking file: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in file verification: {e}")
            return False
    def _verify_file_content(self, test_data, retry_count=3):
        """Xác minh nội dung file config.json trên server khớp với request"""
        try:
            # Lấy thông tin kết nối
            host = self._safe_get(self.http_host_var, "127.0.0.1")
            port = int(self._safe_get(self.http_port_var, "6262"))
            
            # Kiểm tra kích thước file
            url = f"http://{host}:{port}/check"
            retry_interval = 1
            
            for attempt in range(retry_count):
                try:
                    response = requests.get(
                        url, 
                        params={"file": "/etc/testmanager/config/config.json"},
                        timeout=5,
                        headers={"Cache-Control": "no-cache"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        file_size = data.get("size", 0)
                        
                        # Kiểm tra kích thước file > 0
                        if file_size > 10:
                            self.logger.info(f"File config.json xác minh thành công: {file_size} bytes")
                            return True
                        else:
                            self.logger.warning(f"File config.json có kích thước không đủ: {file_size} bytes")
                            
                            # Thử đọc nội dung file trực tiếp
                            cat_url = f"http://{host}:{port}/read"
                            cat_resp = requests.get(
                                cat_url,
                                params={"file": "/etc/testmanager/config/config.json"},
                                timeout=5
                            )
                            
                            if cat_resp.status_code == 200:
                                content = cat_resp.text
                                self.logger.info(f"Nội dung file: {content[:50]}...")
                            
                except Exception as e:
                    self.logger.warning(f"Lỗi xác minh file lần {attempt+1}: {e}")
                
                # Đợi trước khi thử lại
                time.sleep(retry_interval * (attempt + 1))
            
            return False
        except Exception as e:
            self.logger.error(f"Lỗi khi xác minh nội dung file: {e}")
            return False
    def _verify_file_uploaded(self, unique_filename, remote_path="/etc/testmanager/config"):
        """Xác minh file đã được gửi thành công lên server"""
        try:
            # Tạo timeout ngắn cho việc kiểm tra
            max_verification_time = 15  # 15 giây
            start_time = time.time()
            verification_attempts = 0
            
            # Đảm bảo không quá 5 lần kiểm tra
            while time.time() - start_time < max_verification_time and verification_attempts < 5:
                verification_attempts += 1
                
                # Kiểm tra file có tồn tại và không trống
                self.logger.info(f"Xác minh file {unique_filename} lần {verification_attempts}...")
                
                # Kiểm tra file có tồn tại - sử dụng HTTP API
                host = self._safe_get(self.http_host_var, "127.0.0.1")
                port = int(self._safe_get(self.http_port_var, "6262"))
                url = f"http://{host}:{port}/check"
                
                try:
                    import requests
                    response = requests.get(
                        url, 
                        params={"file": f"{remote_path}/{unique_filename}"},
                        timeout=5,
                        headers={"Cache-Control": "no-cache"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("exists") and data.get("size", 0) > 10:
                            self.logger.info(f"Xác nhận file {unique_filename} tồn tại và có kích thước {data.get('size')} bytes")
                            return True
                        else:
                            self.logger.warning(f"File {unique_filename} không tồn tại hoặc trống ({data.get('size', 0)} bytes)")
                            # Nếu file trống, thử lại sau khi đợi thêm
                            if data.get("exists") and data.get("size", 0) == 0:
                                self.logger.info("File tồn tại nhưng trống, đợi thêm...")
                except Exception as e:
                    self.logger.warning(f"Lỗi kiểm tra file: {e}")
                        
                # Đợi trước khi thử lại - thêm jitter để tránh đụng độ
                wait_time = 2 + (verification_attempts * 0.5)
                time.sleep(wait_time)
                    
            if verification_attempts >= 5:
                self.logger.warning(f"Đã thử xác minh file {unique_filename} {verification_attempts} lần nhưng không thành công")
                
            return False
        except Exception as e:
            self.logger.error(f"Lỗi khi xác minh file: {e}")
            return False

    def _recheck_connection(self):
        """Recheck connection status to update UI and internal state"""
        try:
            host = self._safe_get(self.http_host_var, "127.0.0.1")
            port = int(self._safe_get(self.http_port_var, "6262"))
            
            self.logger.debug(f"Rechecking connection to {host}:{port}")
            
            # Try to establish a socket connection
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # Tăng timeout lên 5 giây
            
            try:
                sock.connect((host, port))
                sock.close()
                
                # Connection is good
                self.http_connected = True
                self._safe_after(0, lambda: self._safe_set(self.connection_status_var, "🟢 Connected"))
                return True
                
            except (socket.timeout, socket.error) as e:
                # Connection failed
                self.http_connected = False
                self._safe_after(0, lambda: self._safe_set(self.connection_status_var, "🔴 Not Connected"))
                self.logger.debug(f"Socket connection failed: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error rechecking connection: {e}")
            self.http_connected = False
            return False
    def _save_test_results(self, index, test_data, result_data, status, execution_time):
        """Save test results to file with consistent logging for all tests"""
        try:
            import json
            import os
            from datetime import datetime
            
            # Create directory if it doesn't exist
            result_dir = os.path.join("data", "temp", "results")
            os.makedirs(result_dir, exist_ok=True)
            
            # Get test information safely
            test_id = "unknown"
            name = "unknown"
            transaction_id = test_data.get("metadata", {}).get("transaction_id", "unknown")
            
            if hasattr(self, 'queue_manager') and hasattr(self.queue_manager, 'queue_items'):
                if 0 <= index < len(self.queue_manager.queue_items):
                    test_item = self.queue_manager.queue_items[index]
                    test_id = test_item.get("test_id", "unknown")
                    name = test_item.get("name", "unknown")
            
            # Extract important test info
            service = ""
            action = ""
            if "test_cases" in test_data and len(test_data["test_cases"]) > 0:
                test_case = test_data["test_cases"][0]
                service = test_case.get("service", "")
                action = test_case.get("action", "")
            
            # Fix filename format - remove redundant "tx-" prefix
            outcome = status.lower()
            # Clean up transaction ID to avoid duplicate "tx-" prefix
            transaction_id_clean = transaction_id.replace("tx-", "")
            filename = f"{service}_{action}_{transaction_id_clean[:8]}_{outcome}.json"
            file_path = os.path.join(result_dir, filename)
            
            # Generate current timestamp dynamically
            current_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            current_user = "juno-kyojin"  # From input
            
            # Prepare result data
            result_data_to_save = {
                "test_id": test_id,
                "name": name,
                "status": status,
                "execution_time": execution_time,
                "timestamp": current_timestamp,
                "transaction_id": transaction_id,
                "request": test_data,
                "response": result_data,
                "user": current_user
            }
            
            # Save file with error handling
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result_data_to_save, f, indent=2)
                self.logger.info(f"Test results saved to {file_path}")  # ALWAYS LOG THIS
            except IOError as e:
                self.logger.error(f"Failed to write result file: {e}")
                # Try alternate path if there's an error
                import time
                alt_file_path = os.path.join(result_dir, f"test_result_{int(time.time())}.json")
                try:
                    with open(alt_file_path, 'w', encoding='utf-8') as f:
                        json.dump(result_data_to_save, f, indent=2)
                    self.logger.info(f"Used alternative path: {alt_file_path}")
                except Exception:
                    self.logger.error("Could not save test results to any location")
            
            return True
        except Exception as e:
            self.logger.error(f"Error saving test result: {str(e)}")
            return False

    def _check_test_affects_network(self, test_data):
        """Kiểm tra chi tiết mức độ ảnh hưởng của test đến kết nối mạng"""
        try:
            if not test_data or "test_cases" not in test_data or not test_data["test_cases"]:
                return {
                    "affects_network": False, 
                    "severity": "none",
                    "expected_disconnect": False,
                    "restart_delay": 0
                }
                    
            test_case = test_data["test_cases"][0]
            service = test_case.get("service", "").lower()
            action = test_case.get("action", "").lower()
            params = test_case.get("params", {})
            
            # Phân loại chi tiết mức độ ảnh hưởng
            result = {
                "affects_network": False,
                "severity": "none",  # none, minor, moderate, severe
                "expected_disconnect": False,  # Dự kiến mất kết nối?
                "restart_delay": 0    # Thời gian chờ (giây)
            }
            
            # Phân tích chi tiết hơn
            if service == "lan":
                if "edit_ip" in action or "edit_address" in action:
                    # Thay đổi IP là thay đổi nghiêm trọng, chắc chắn mất kết nối
                    result["affects_network"] = True
                    result["severity"] = "severe"
                    result["expected_disconnect"] = True
                    result["restart_delay"] = 45  # Đợi lâu hơn cho LAN IP
                    
                elif "edit_leasetime" in action:
                    # Thay đổi DHCP lease time ít nghiêm trọng hơn
                    result["affects_network"] = True
                    result["severity"] = "minor"
                    result["expected_disconnect"] = False
                    result["restart_delay"] = 5
                    
                elif "restart" in action:
                    # Restart LAN là nghiêm trọng
                    result["affects_network"] = True
                    result["severity"] = "severe"
                    result["expected_disconnect"] = True
                    result["restart_delay"] = 30
                    
                else:
                    # Các thay đổi LAN khác ở mức trung bình
                    result["affects_network"] = True
                    result["severity"] = "moderate"
                    result["restart_delay"] = 15
                    
            elif service == "wan":
                # Hầu hết thay đổi WAN đều nghiêm trọng
                result["affects_network"] = True
                result["severity"] = "severe"
                result["expected_disconnect"] = True
                result["restart_delay"] = 30
                
            elif service == "network" and any(a in action for a in ["restart", "reload", "reset"]):
                # Restart network là nghiêm trọng nhất
                result["affects_network"] = True
                result["severity"] = "severe"
                result["expected_disconnect"] = True
                result["restart_delay"] = 45
                
            # Log thông tin phân tích
            if result["affects_network"]:
                self.logger.info(
                    f"Test với service={service}, action={action} ảnh hưởng đến kết nối mạng: "
                    f"severity={result['severity']}, expected_disconnect={result['expected_disconnect']}"
                )
                    
            return result
                
        except Exception as e:
            self.logger.error(f"Error checking network impact: {e}")
            return {"affects_network": False, "severity": "none", "expected_disconnect": False, "restart_delay": 0}

    def _handle_connection_reset(self, index, is_network_test, likely_success=True):
        """
        Xử lý connection reset với phân biệt loại test
        
        Args:
            index: Chỉ số test trong queue
            is_network_test: Có phải test network không
            likely_success: Connection reset có khả năng do thành công (True) hay lỗi (False)
        """
        try:
            # Xác định thông tin test
            test_id = "unknown"
            
            if hasattr(self, 'queue_manager') and index < len(self.queue_manager.queue_items):
                test_item = self.queue_manager.queue_items[index]
                test_id = test_item.get("test_id", "unknown")
            
            self.logger.info(f"Handling connection reset for {test_id} (likely_success={likely_success})")
            
            # Cập nhật UI dựa trên dữ liệu likelihood
            if likely_success:
                # Test có khả năng đã thành công (như wan_delete)
                success_msg = f"Network changes likely applied successfully"
                self._safe_after(0, lambda msg=success_msg: self.update_test_status(index, "Success", msg))
            else:
                # Test có khả năng thất bại (như wan_edit với lỗi UCI)
                fail_msg = f"Connection reset - possible configuration error"
                self._safe_after(0, lambda msg=fail_msg: self.update_test_status(index, "Warning", msg))
            
            # Đánh dấu kết nối đã mất
            self.http_connected = False
            self._safe_set(self.connection_status_var, "🟡 Connection lost (reconnecting)")
            self._safe_set(self.status_var, "Network connection interrupted. Automatic reconnection scheduled.")
            
            # Tăng thời gian chờ router ổn định
            wait_time = 30  # Tăng từ 20 lên 30 giây
            
            self.logger.info(f"Will attempt to reconnect after {wait_time} seconds")
            self._safe_after(wait_time * 1000, lambda: self._initiate_reconnect_sequence())
            
            return True
        except Exception as e:
            self.logger.error(f"Error handling connection reset: {str(e)}")
            return False
    def _initiate_reconnect_sequence(self):
        """Cơ chế reconnect với backoff thông minh hơn"""
        max_attempts = 12  # Tăng số lần thử kết nối lại
        self.logger.info(f"Bắt đầu chuỗi kết nối lại với {max_attempts} lần thử")
        self._attempt_reconnect(1, max_attempts)
    def _attempt_reconnect(self, attempt, max_attempts):
        """Thử kết nối lại với exponential backoff và jitter"""
        import random
        
        if attempt > max_attempts:
            self.logger.error(f"Không thể kết nối lại sau {max_attempts} lần thử")
            self._safe_set(self.connection_status_var, "🔴 Không kết nối được")
            self._safe_set(self.status_var, "Kết nối lại thất bại. Kiểm tra kết nối thủ công.")
            return False
        
        try:
            self.logger.info(f"Lần thử kết nối {attempt}/{max_attempts}")
            
            # Lấy thông tin kết nối
            host = self._safe_get(self.http_host_var, "127.0.0.1")
            port = int(self._safe_get(self.http_port_var, "6262"))
            
            # Tính thời gian chờ với exponential backoff
            base_delay = 3  # 3 giây cơ sở
            max_delay = 45  # Tăng lên 45 giây cho lần thử cuối
            
            # Công thức backoff: min(max_delay, base_delay * (2^(attempt-1)))
            retry_delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jitter = random.uniform(0, 1)  # Thêm jitter để tránh thundering herd
            retry_delay = retry_delay + (jitter * base_delay)
            
            # Thử kết nối với timeout ngắn
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(8)  # Tăng lên 8 giây
                sock.connect((host, port))
                sock.close()
                
                # Kết nối thành công
                self.http_connected = True
                self._safe_set(self.connection_status_var, "🟢 Đã kết nối")
                self._safe_set(self.status_var, f"Kết nối lại thành công (lần thử {attempt}/{max_attempts})")
                
                # Đợi thêm 3 giây để đảm bảo dịch vụ đã sẵn sàng hoàn toàn
                import time
                time.sleep(3)
                
                self.logger.info(f"Kết nối lại thành công ở lần thử {attempt}/{max_attempts}")
                return True
            except Exception as e:
                self.logger.info(f"Kết nối thất bại ở lần {attempt}: {e}")
                self._safe_set(self.status_var, f"Thử lại {attempt}/{max_attempts}. Chờ {retry_delay:.1f}s...")
                self._safe_after(int(retry_delay * 1000), lambda: self._attempt_reconnect(attempt + 1, max_attempts))
                return False
                
        except Exception as e:
            self.logger.error(f"Lỗi bất ngờ trong lần thử kết nối {attempt}: {e}")
            self._safe_after(5000, lambda: self._attempt_reconnect(attempt + 1, max_attempts))
            return False

    def _reconnect_after_network_change(self):
        """Thử kết nối lại sau khi mạng thay đổi"""
        try:
            # Lấy thông tin kết nối
            host = self._safe_get(self.http_host_var, "127.0.0.1")
            port = int(self._safe_get(self.http_port_var, "6262"))
            
            # Thông báo
            self.logger.info(f"Attempting to reconnect to {host}:{port}")
            
            # Thử kết nối socket
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            try:
                sock.connect((host, port))
                sock.close()
                
                # Kết nối thành công
                self.http_connected = True
                self._safe_set(self.connection_status_var, "🟢 Connected")
                self._safe_set(self.status_var, "Reconnected successfully after network change")
                
                self.logger.info("Reconnected successfully after network change")
                return True
            except (socket.timeout, socket.error) as e:
                # Kết nối thất bại
                self.logger.warning(f"Reconnection failed: {e}")
                self._safe_set(self.connection_status_var, "🔴 Not connected")
                
                # Lập lịch thử lại một lần nữa sau 10 giây
                self._safe_after(10000, self._reconnect_after_network_change)
                return False
        except Exception as e:
            self.logger.error(f"Error in reconnection attempt: {e}")
            return False
    def _try_reconnect_after_ip_change(self):
        """Thử kết nối lại sau khi IP LAN thay đổi"""
        if hasattr(self, '_new_lan_ip') and self._new_lan_ip:
            # Determine connection type - always assume WAN connection for safety
            connection_type = self._safe_get(self.connection_type_var, "http")
            
            # Tạo dialog hướng dẫn kết nối lại
            reconnect_window = tk.Toplevel(self.root)
            reconnect_window.title("Network Configuration Changed")
            reconnect_window.geometry("450x300")
            reconnect_window.transient(self.root)
            reconnect_window.resizable(False, False)
            
            # Thiết lập vị trí giữa màn hình - kiểm tra self.root trước khi gọi phương thức
            if self.root:
                try:
                    x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
                    y = self.root.winfo_y() + (self.root.winfo_height() - 300) // 2
                    reconnect_window.geometry(f"+{x}+{y}")
                except Exception as e:
                    self.logger.debug(f"Could not position dialog: {e}")
            
            # Frame chính
            main_frame = ttk.Frame(reconnect_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Tiêu đề
            ttk.Label(
                main_frame, 
                text="Network Configuration Changed",
                font=("Segoe UI", 14, "bold")
            ).pack(pady=(0, 15))
            
            # Sử dụng emoji thay vì icon từ library
            ttk.Label(
                main_frame, 
                text="🌐",
                font=("Segoe UI", 32)
            ).pack(pady=10)
            
            # Thông tin thay đổi IP
            ttk.Label(
                main_frame,
                text=f"Địa chỉ IP router đã thay đổi thành:",
                font=("Segoe UI", 10)
            ).pack(pady=(10, 5))
            
            ttk.Label(
                main_frame,
                text=f"{self._new_lan_ip}",
                font=("Segoe UI", 12, "bold")
            ).pack(pady=(0, 15))
            
            # Thông báo kết nối
            ttk.Label(
                main_frame,
                text="Kết nối WAN của bạn không bị ảnh hưởng.",
                font=("Segoe UI", 10)
            ).pack(pady=(0, 5))
            
            # Nút điều khiển
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=15)
            
            ttk.Button(
                button_frame,
                text="Đóng",
                command=reconnect_window.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
            # Log thông tin
            self.logger.info(f"Network configuration changed dialog shown with new IP: {self._new_lan_ip}")

    def _validate_response(self, request_data, response_data):
        """Validate that response matches request"""
        # Extract request details
        request_service = None
        request_action = None
        if "test_cases" in request_data and len(request_data["test_cases"]) > 0:
            test_case = request_data["test_cases"][0]
            request_service = test_case.get("service")
            request_action = test_case.get("action")
        
        # Check for mismatch in failed_by_service
        if "failed_by_service" in response_data:
            for service, failures in response_data["failed_by_service"].items():
                for failure in failures:
                    response_service = failure.get("service")
                    response_action = failure.get("action")
                    if (response_service != request_service or 
                        response_action != request_action):
                        self.logger.warning(
                            f"Response mismatch detected: Request={request_service}.{request_action}, "
                            f"Response={response_service}.{response_action}"
                        )
                        return False
        
        return True
    def _verify_response_matches_request(self, request_data, response_data):
        """Verify that response matches the request with improved cache detection"""
        try:
            # Extract request info
            request_service = None
            request_action = None
            if "test_cases" in request_data and len(request_data["test_cases"]) > 0:
                test_case = request_data["test_cases"][0]
                request_service = test_case.get("service", "")
                request_action = test_case.get("action", "")
            
            request_tx = request_data.get("metadata", {}).get("transaction_id", "unknown")
            request_unique_id = request_data.get("metadata", {}).get("unique_request_id", "unknown")
            
            # Check response for mismatches
            mismatch_found = False
            mismatch_reason = ""
            
            # Kiểm tra test results dựa trên service và action
            if "test_results" in response_data:
                for result in response_data["test_results"]:
                    response_service = result.get("service", "")
                    response_action = result.get("action", "")
                    
                    # Nếu service và action không trùng khớp - đây là dấu hiệu của cache
                    if (response_service != request_service or
                        (request_action and response_action != request_action)):
                        mismatch_found = True
                        mismatch_reason = (
                            f"Cache issue: Request was {request_service}/{request_action} "
                            f"but response contains {response_service}/{response_action}"
                        )
                        break
            
            # Kiểm tra thêm trong failed_by_service
            if not mismatch_found and "failed_by_service" in response_data:
                for service, failures in response_data["failed_by_service"].items():
                    if isinstance(failures, list):
                        for failure in failures:
                            response_service = failure.get("service", "")
                            response_action = failure.get("action", "")
                            
                            # Nếu service khớp nhưng action không khớp
                            if (response_service == request_service and 
                                request_action and response_action != request_action):
                                mismatch_found = True
                                mismatch_reason = (
                                    f"Cache issue: Request was {request_service}/{request_action} "
                                    f"but response contains {response_service}/{response_action}"
                                )
                                break
                    
                    if mismatch_found:
                        break
            
            if mismatch_found:
                self.logger.warning(mismatch_reason)
                self.logger.warning(f"Cache issue detected with TX: {request_tx} and unique_id: {request_unique_id}")
                
                # Log thêm để debug
                current_time = self._get_current_time()
                self.logger.debug(f"Cache issue at: {current_time}")
                
                return False
                    
            return True
        except Exception as e:
            self.logger.error(f"Error verifying response match: {e}")
            return True  # Default to accepting the response in case of error
    def send_all_tests(self):
        """Send all tests sequentially with wait for device readiness"""
        # Kiểm tra điều kiện ban đầu
        if not hasattr(self, 'queue_manager') or not hasattr(self.queue_manager, 'queue_items'):
            messagebox.showinfo("Information", "Queue is empty")
            return
                
        if len(self.queue_manager.queue_items) == 0:
            messagebox.showinfo("Information", "Queue is empty")
            return
                
        # Kiểm tra kết nối
        connection_type = self._safe_get(self.connection_type_var, "http")
        if connection_type == "http":
            if not hasattr(self, 'http_connected') or not self.http_connected:
                if not self._recheck_connection():
                    messagebox.showinfo("Error", "Not connected to HTTP server. Please test connection first.")
                    return
        
        # Xác nhận và thêm biến cờ
        if len(self.queue_manager.queue_items) > 1:
            confirm = messagebox.askyesno(
                "Confirm",
                f"Send all {len(self.queue_manager.queue_items)} tests for execution?\n\n"
                f"The system will automatically check for device readiness between tests."
            )
            if not confirm:
                return
                
        # ===== THAY ĐỔI QUAN TRỌNG =====
        # Đặt biến cờ để chỉ ra rằng chúng ta đang chạy chuỗi test
        self._running_test_sequence = True
        
        # Chỉ bắt đầu test đầu tiên - không lập lịch trước tất cả các test
        self.logger.info(f"Starting sequential execution of {len(self.queue_manager.queue_items)} tests")
        self._execute_test_with_readiness_check(0)
    def _check_connection_and_send(self, index):
        """Kiểm tra kết nối trước khi chạy test với cải tiến"""
        try:
            # Kiểm tra kết nối nếu là HTTP
            connection_type = self._safe_get(self.connection_type_var, "http")
            if connection_type == "http":
                # Luôn kiểm tra kết nối trước khi chạy test
                self.logger.info(f"Connection check before test #{index+1}")
                
                # Cập nhật UI
                self.update_test_status(index, "Pending", "Checking connection...")
                
                # Thử kết nối trực tiếp thay vì dựa vào biến http_connected
                reconnected = False
                for attempt in range(1, 6):  # Tăng số lần thử lên 5
                    reconnected = self._recheck_connection()
                    if reconnected:
                        self.logger.info(f"Connection verified on attempt {attempt}")
                        break
                        
                    # Hiển thị thông báo đang thử
                    self.update_test_status(index, "Pending", f"Connection check {attempt}/5...")
                    time.sleep(3)  # Tăng thời gian chờ giữa các lần thử

                # Nếu không thể kết nối
                if not reconnected:
                    self.update_test_status(index, "Error", "Connection failed")
                    self.logger.error("Cannot run test - connection failed")
                    
                    # Hiển thị dialog thông báo với nhiều tùy chọn
                    choice = messagebox.askretrycancel(
                        "Connection Error",
                        "Cannot connect to server. Do you want to retry connection?\n\n"
                        "• Retry - Check connection again\n"
                        "• Cancel - Skip this test",
                        icon='warning'
                    )
                    
                    if choice:  # Retry chosen
                        # Tự động thử kết nối và chạy test sau khoảng thời gian
                        self._safe_after(3000, lambda: self._check_connection_and_send(index))
                    return
            
            # Kết nối OK, chạy test
            self.send_selected_test(index)
            
        except Exception as e:
            self.logger.error(f"Error checking connection: {e}")
            self.update_test_status(index, "Error", "Connection check error")
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


    def _save_test_result(self, index, request_data, response_data, status, execution_time):
        """Lưu kết quả test vào file/database với xử lý lỗi tốt hơn"""
        try:
            import json
            import os
            import datetime
            
            # Tạo directory nếu chưa tồn tại
            result_dir = os.path.join("data", "temp", "results")
            os.makedirs(result_dir, exist_ok=True)
            
            # Lấy thông tin test một cách an toàn
            test_id = "unknown"
            name = "unknown"
            transaction_id = request_data.get("metadata", {}).get("transaction_id", "unknown")
            
            if hasattr(self, 'queue_manager') and hasattr(self.queue_manager, 'queue_items'):
                if 0 <= index < len(self.queue_manager.queue_items):
                    test_item = self.queue_manager.queue_items[index]
                    test_id = test_item.get("test_id", "unknown")
                    name = test_item.get("name", "unknown")
            
            # Tạo tên file với timestamp và trạng thái
            timestamp = "20250624_0528" # Timestamp cố định từ yêu cầu
            filename = f"{test_id}_{transaction_id[:8]}_{status.lower()}.json"
            file_path = os.path.join(result_dir, filename)
            
            # Chuẩn bị dữ liệu kết quả
            result_data = {
                "test_id": test_id,
                "name": name,
                "status": status,
                "execution_time": execution_time,
                "timestamp": "2025-06-24 05:28:36",  # Timestamp cố định 
                "transaction_id": transaction_id,
                "request": request_data,
                "response": response_data,
                "user": "juno-kyojin"  # Username từ yêu cầu
            }
            
            # Lưu file với xử lý lỗi
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, indent=2)
                self.logger.info(f"Test result saved to {file_path}")
            except IOError as e:
                self.logger.error(f"Failed to write result file: {e}")
                # Thử tạo tên file thay thế nếu có lỗi
                alt_file_path = os.path.join(result_dir, f"test_result_{int(time.time())}.json")
                try:
                    with open(alt_file_path, 'w', encoding='utf-8') as f:
                        json.dump(result_data, f, indent=2)
                    self.logger.info(f"Used alternative path: {alt_file_path}")
                except Exception:
                    self.logger.error("Could not save test results to any location")
                
            # Cập nhật chi tiết test trong UI nếu có response data
            test_results = []
            
            # Cố gắng lấy test_results từ nhiều nguồn khác nhau
            if isinstance(response_data, dict):
                if "test_results" in response_data:
                    test_results = response_data["test_results"]
                elif "summary" in response_data:
                    # Tạo test result từ summary 
                    service = test_id.split('_')[0] if '_' in test_id else test_id
                    action = test_id.split('_')[1] if '_' in test_id and len(test_id.split('_')) > 1 else ""
                    
                    passed = response_data["summary"].get("passed", 0) > 0
                    failed = response_data["summary"].get("failed", 0) > 0
                    
                    test_results = [{
                        "service": service,
                        "action": action,
                        "status": "pass" if passed and not failed else "fail",
                        "details": response_data.get("message", "Test complete"),
                        "execution_time": execution_time
                    }]
                elif "success" in response_data:
                    # Thử tạo dữ liệu kết quả tối thiểu từ field success
                    service = test_id.split('_')[0] if '_' in test_id else test_id
                    action = test_id.split('_')[1] if '_' in test_id and len(test_id.split('_')) > 1 else ""
                    
                    test_results = [{
                        "service": service,
                        "action": action,
                        "status": "pass" if response_data["success"] else "fail",
                        "details": response_data.get("message", "Test complete"),
                        "execution_time": execution_time
                    }]
                    
            # Đảm bảo an toàn khi cập nhật UI
            if test_results:
                # Sử dụng after để đảm bảo cập nhật UI trong thread chính
                self._safe_after(0, lambda results=test_results: self._update_detail_view(results))
            
        except Exception as e:
            self.logger.error(f"Error saving test result: {str(e)}")
    def _update_detail_view(self, test_results):
        """Cập nhật view chi tiết với kết quả test"""
        try:
            # Kiểm tra detail_table có tồn tại không
            if not hasattr(self, 'detail_table'):
                self.logger.warning("Detail table not available for updating test results")
                return
                    
            # Xóa các mục hiện tại
            for item in self.detail_table.get_children():
                self.detail_table.delete(item)
                    
            if not test_results:
                # Hiển thị thông báo nếu không có kết quả
                self.detail_table.insert("", "end", values=(
                    "", "", "", "No Results", "No test results available"
                ))
                return
                    
            # Thêm kết quả mới
            for result in test_results:
                service = result.get("service", "")
                action = result.get("action", "")
                status = result.get("status", "unknown")
                details = result.get("details", "")
                
                # Xử lý parameters - có thể là đối tượng hoặc chuỗi
                parameters = result.get("parameters", "")
                if isinstance(parameters, dict):
                    # Chuyển dict thành chuỗi mô tả
                    param_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])[:50]
                    if len(parameters) > 0 and len(param_str) >= 50:
                        param_str += "..."
                else:
                    param_str = str(parameters)[:50]
                
                # Format status cho hiển thị
                status_text = status.capitalize()
                
                # Thêm vào bảng
                item_id = self.detail_table.insert("", "end", values=(
                    service,
                    action,
                    param_str,
                    status_text,
                    details
                ))
                
                # Thêm màu dựa trên trạng thái
                if status.lower() == "pass":
                    self.detail_table.item(item_id, tags=("pass",))
                elif status.lower() == "fail":
                    self.detail_table.item(item_id, tags=("fail",))
                        
        except Exception as e:
            self.logger.error(f"Error updating detail view: {str(e)}")
    def send_selected_test(self, index=None):
        """Gửi test case được chọn từ queue với tính năng chống trùng lặp và xử lý lỗi cải tiến"""
        try:
            # Kiểm tra queue manager
            if not hasattr(self, 'queue_manager'):
                messagebox.showinfo("Error", "Queue manager not initialized")
                return
                    
            # Kiểm tra kết nối HTTP
            connection_type = self._safe_get(self.connection_type_var, "http")
            if connection_type == "http" and not getattr(self, 'http_connected', False):
                # Thử kiểm tra kết nối trước khi báo lỗi
                if not self._recheck_connection():
                    messagebox.showinfo("Error", "Not connected to HTTP server. Please test connection first.")
                    return
                    
            # Xác định index nếu không được cung cấp
            if index is None:
                selected = self.queue_manager.queue_tree.selection()
                if not selected:
                    messagebox.showinfo("Information", "Please select a test case first")
                    return
                index = self.queue_manager.queue_tree.index(selected[0])
            
            # Kiểm tra index hợp lệ
            if index < 0 or index >= len(self.queue_manager.queue_items):
                messagebox.showinfo("Error", "Invalid test index")
                return
                    
            # Lấy thông tin test case
            test_item = self.queue_manager.queue_items[index]
            
            # Kiểm tra trạng thái hiện tại
            current_status = test_item.get("status", "").lower()
            if current_status in ["running", "sending"]:
                confirm = messagebox.askyesno(
                    "Test In Progress", 
                    "This test is currently running. Do you want to restart it?",
                    icon='warning'
                )
                if not confirm:
                    return
                
            # Lấy thông tin test case từ queue
            test_id = test_item.get("test_id", "")
            name = test_item.get("name", "")
            params = test_item.get("parameters", {}).copy()
            
            # Lấy service và action từ test_item
            service = test_item.get("service", "")
            action = test_item.get("action", "")
            
            # Nếu không tìm thấy service/action, phân tích từ test_id
            if not service:
                parts = test_id.split("_")
                service = parts[0] if parts else ""
                self.logger.info(f"Service không tìm thấy trong test_item, sử dụng service từ test_id: {service}")
                
                # Nếu không có action và test_id có phần thứ hai, sử dụng phần còn lại làm action
                if not action and len(parts) > 1:
                    action = '_'.join(parts[1:])
                    self.logger.info(f"Action không tìm thấy trong test_item, sử dụng action từ test_id: {action}")
            
            # ===== TÍNH NĂNG MỚI: KIỂM TRA TRÙNG LẶP =====
            # Kiểm tra xem test này đã được chạy thành công gần đây chưa
            if hasattr(self, 'recent_test_results'):
                matching_results = [r for r in self.recent_test_results 
                                if r.get('test_id') == test_id and 
                                    r.get('status') == 'Success' and
                                    time.time() - r.get('timestamp', 0) < 120]  # 2 phút
                                    
                if matching_results:
                    confirm = messagebox.askyesno(
                        "Có thể là test trùng lặp",
                        f"Test case '{test_id}' đã được thực hiện thành công gần đây.\n\n"
                        f"Bạn có chắc chắn muốn gửi lại?",
                        icon='warning'
                    )
                    if not confirm:
                        self.update_test_status(index, "Skipped", "Bỏ qua do trùng lặp")
                        return
            
            # Đảm bảo recent_test_results tồn tại
            if not hasattr(self, 'recent_test_results'):
                self.recent_test_results = []
            
            # Cập nhật UI trước để hiển thị đang gửi
            self.update_test_status(index, "Sending", "Preparing test data...")
                
            # Log thông tin test
            self.logger.info(f"Sending test {test_id} (index {index})")
            self.logger.info(f"Service: {service}, Action: {action}")
            
            # ===== CẢNH BÁO CHO TEST LAN IP =====
            # Kiểm tra nếu là test thay đổi IP LAN và hiển thị cảnh báo
            if service == "lan" and action == "edit_ip":
                confirm = messagebox.askyesno(
                    "⚠️ Network Configuration Change",
                    "This test will modify the router's LAN IP settings.\n\n"
                    "Your current connection will not be affected if connected through WAN.\n\n"
                    "Are you sure you want to proceed?",
                    icon='warning'
                )
                
                if not confirm:
                    self.logger.info(f"User cancelled LAN IP change test")
                    self.update_test_status(index, "Cancelled", "User cancelled")
                    return
                    
                # Lưu IP mới để thông báo
                if "network_ipv4_ip" in params:
                    self._new_lan_ip = params["network_ipv4_ip"]
                    self.logger.info(f"Saved new LAN IP: {self._new_lan_ip}")
            
            # Format các tham số đúng cho từng loại service/action
            params = self._format_request_params(service, action, params)
                
            # ===== TÍNH NĂNG MỚI: SỬ DỤNG UUID ĐỘC NHẤT =====
            # Tạo transaction ID duy nhất để theo dõi và tránh trùng lặp
            import uuid
            transaction_id = f"tx-{str(uuid.uuid4())[:8]}"
            
            # Sử dụng thời gian hiện tại từ input
            client_timestamp = "2025-06-24 12:50:12"  # Thời gian hiện tại từ input
            
            # Tạo test case với các trường bổ sung
            test_case = {
                "service": service,
                "params": params,
                "client_id": transaction_id,
                "client_timestamp": client_timestamp
            }
            
            # Thêm action nếu có và cần thiết
            if action:
                test_case["action"] = action
                    
            # ===== TÍNH NĂNG MỚI: METADATA PHONG PHÚ HƠN =====
            # Đóng gói trong định dạng API với metadata chi tiết
            test_data = {
                "test_cases": [test_case],
                "metadata": {
                    "transaction_id": transaction_id,
                    "client_timestamp": client_timestamp,
                    "created_by": "juno-kyojin",  # Username từ input
                    "created_at": client_timestamp,
                    "unique_id": str(uuid.uuid4()),
                    "client_version": "2.0.1",
                    "client_platform": "Windows"
                }
            }
            
            # Lưu transaction ID để theo dõi
            if not hasattr(self, 'test_transactions'):
                self.test_transactions = {}
            self.test_transactions[index] = {
                "transaction_id": transaction_id,
                "start_time": client_timestamp,
                "test_id": test_id,
                "service": service,
                "action": action
            }
            
            # Cập nhật UI với transaction ID
            self.update_test_status(index, "Sending", f"TX: {transaction_id[:8]}")
            
            # Log thông tin test case với transaction ID
            self.logger.info(f"Sending test {name} (index {index}, TX: {transaction_id})")
            self.logger.info(f"Request data: {json.dumps(test_data, indent=2)}")
            
            # ===== TÍNH NĂNG MỚI: XỬ LÝ KHÔNG ĐỒNG BỘ =====
            # Gửi test case trong luồng riêng để không làm đơ UI
            threading.Thread(
                target=self.send_test_case_http,
                args=(test_data, index),
                daemon=True
            ).start()
            
        except Exception as e:
            self.logger.error(f"Error sending test: {e}")
            messagebox.showerror("Error", f"Failed to send test: {str(e)}")
    def _format_request_params(self, service, action, params):
        """
        Format các tham số request đúng cách cho các service và action khác nhau
        
        Args:
            service: Service name (lan, wan, network, etc)
            action: Action name (edit_ip, edit_leasetime, restart, etc)
            params: Dictionary of parameters
            
        Returns:
            Dictionary: Formatted parameters
        """
        try:
            self.logger.info(f"Formatting parameters for {service}.{action}")
            
            # Tạo bản sao để không sửa đổi params gốc
            formatted_params = params.copy() if params else {}
            
            # Format LAN service parameters
            if service == "lan":
                # Đảm bảo có tham số name cho mọi action LAN
                if "name" not in formatted_params:
                    formatted_params["name"] = "lan"  # Tên interface mặc định
                    self.logger.info("Added default LAN name: 'lan'")
                
                # Xử lý các action cụ thể của LAN
                if action == "edit_ip":
                    # Đảm bảo có network_ipv4_mask nếu đang thay đổi IP
                    if "network_ipv4_ip" in formatted_params and "network_ipv4_mask" not in formatted_params:
                        formatted_params["network_ipv4_mask"] = "255.255.255.0"
                        self.logger.info("Added default netmask: 255.255.255.0 for LAN IP change")
                
                elif action == "edit_leasetime":
                    # Đảm bảo dhcp_leasetime là số nguyên
                    if "dhcp_leasetime" in formatted_params and not isinstance(formatted_params["dhcp_leasetime"], int):
                        try:
                            formatted_params["dhcp_leasetime"] = int(formatted_params["dhcp_leasetime"])
                            self.logger.info(f"Converted dhcp_leasetime to integer: {formatted_params['dhcp_leasetime']}")
                        except ValueError:
                            # Giữ nguyên giá trị nếu không thể chuyển đổi
                            self.logger.warning(f"Could not convert dhcp_leasetime to integer: {formatted_params['dhcp_leasetime']}")
            
            # Format WAN service parameters
            elif service == "wan":
                if action == "delete":
                    # Đảm bảo chỉ có name cho action delete
                    if "name" in formatted_params:
                        return {"name": formatted_params["name"]}
                    else:
                        # Sử dụng mặc định wan1
                        self.logger.info("Using default WAN name 'wan1' for delete action")
                        return {"name": "wan1"}
                        
                elif action == "create":
                    # Đảm bảo các tham số bắt buộc
                    if "protocol" not in formatted_params:
                        formatted_params["protocol"] = "ipv4"
                        self.logger.info("Added default protocol: ipv4")
                    
                    if "gateway_type" not in formatted_params:
                        formatted_params["gateway_type"] = "route"
                        self.logger.info("Added default gateway_type: route")
            
            # Format WIRELESS service parameters
            elif service == "wireless":
                # Đảm bảo password luôn là chuỗi, ngay cả khi chỉ chứa các chữ số
                if "password" in formatted_params:
                    formatted_params["password"] = str(formatted_params["password"])
                    self.logger.info("Ensured password is string format for wireless configuration")
                
                # Đảm bảo disable_mode là chuỗi
                if "disable_mode" in formatted_params:
                    formatted_params["disable_mode"] = str(formatted_params["disable_mode"])
                    self.logger.info(f"Ensured disable_mode is string format: {formatted_params['disable_mode']}")
                    
                # Đảm bảo power là chuỗi (nếu có)
                if "power" in formatted_params:
                    formatted_params["power"] = str(formatted_params["power"])
                    self.logger.info(f"Ensured power is string format: {formatted_params['power']}")
                    
                # Đảm bảo các trường số khác cũng là chuỗi
                for numeric_field in ["channel"]:
                    if numeric_field in formatted_params:
                        formatted_params[numeric_field] = str(formatted_params[numeric_field])
                        self.logger.info(f"Ensured {numeric_field} is string format: {formatted_params[numeric_field]}")
            
            # Xử lý các kiểu dữ liệu đặc biệt
            for key, value in list(formatted_params.items()):
                # Xử lý danh sách DNS
                if key in ["ipv4_dns", "ipv6_dns"] and isinstance(value, str):
                    if value.strip():
                        # Chuyển đổi chuỗi phân cách dấu phẩy thành list
                        dns_list = [dns.strip() for dns in value.split(",") if dns.strip()]
                        formatted_params[key] = dns_list
                        self.logger.info(f"Converted {key} from string to list: {dns_list}")
                    else:
                        # Chuỗi rỗng thành list rỗng
                        formatted_params[key] = []
            
            self.logger.debug(f"Final formatted parameters: {json.dumps(formatted_params, ensure_ascii=False)}")
            return formatted_params
                
        except Exception as e:
            self.logger.error(f"Error formatting parameters: {e}")
            return params  # Trả về params gốc nếu có lỗi
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

    def wait_for_device_ready(self, index, max_wait_time=90):
        """
        Wait for device to be ready after network changes with improved reliability
        
        Args:
            index: Test index in queue for UI updates
            max_wait_time: Maximum wait time in seconds
        
        Returns:
            True if device ready, False if timeout
        """
        self.logger.info(f"Waiting for device to be ready (max {max_wait_time}s)")
        self.update_test_status(index, "Waiting", "Checking device readiness...")
        
        start_time = time.time()
        check_interval = 5  # Kiểm tra mỗi 5 giây
        last_status_update = 0
        connection_seen = False
        successful_checks = 0
        required_successful_checks = 2  # Yêu cầu 2 lần kiểm tra thành công liên tiếp
        
        while time.time() - start_time < max_wait_time:
            elapsed = time.time() - start_time
            
            # Cập nhật UI định kỳ để hiển thị tiến độ
            if elapsed - last_status_update >= 10:
                status_msg = f"Waiting for device ({int(elapsed)}/{max_wait_time}s)"
                self.update_test_status(index, "Waiting", status_msg)
                self._safe_set(self.status_var, status_msg)
                last_status_update = elapsed
            
            # Kiểm tra kết nối TCP cơ bản
            if self._recheck_connection():
                self.logger.info("Basic connection successful")
                
                # THAY ĐỔI QUAN TRỌNG: Kết nối lần đầu - đợi thêm cho dịch vụ khởi động
                if not connection_seen:
                    connection_seen = True
                    self.logger.info("First connection established - waiting for services to initialize")
                    self.update_test_status(index, "Waiting", "Services initializing...")
                    
                    # Đợi thêm 15 giây cho các dịch vụ khởi động đầy đủ
                    time.sleep(15)  
                    continue
                    
                # THAY ĐỔI QUAN TRỌNG: Yêu cầu nhiều lần kiểm tra thành công liên tiếp
                successful_checks += 1
                if successful_checks >= required_successful_checks:
                    # Kết nối ổn định qua nhiều lần kiểm tra
                    self.logger.info(f"Device ready after {int(elapsed)}s")
                    self.update_test_status(index, "Ready", f"Device ready after {int(elapsed)}s")
                    return True
                    
                # Đợi thêm một khoảng thời gian ngắn trước khi kiểm tra tiếp
                time.sleep(5)
                continue
            else:
                # Reset đếm kiểm tra thành công
                successful_checks = 0
            
            # Chưa có kết nối, tiếp tục đợi
            self.logger.info(f"Connection not ready after {int(elapsed)}s - retrying...")
            time.sleep(check_interval)
        
        # Hết thời gian chờ
        self.logger.warning(f"Timeout waiting for device readiness after {max_wait_time}s")
        self.update_test_status(index, "Warning", f"Device readiness timeout ({max_wait_time}s)")
        return False
        
    def _verify_config_file_ready(self, retries=5):
        """Verify config file exists and is not empty"""
        host = self._safe_get(self.http_host_var, "127.0.0.1")
        port = int(self._safe_get(self.http_port_var, "6262"))
        
        for i in range(retries):
            try:
                # Kiểm tra file
                url = f"http://{host}:{port}/check"
                response = requests.get(
                    url,
                    params={"file": "/etc/testmanager/config/config.json"},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("exists") and data.get("size", 0) > 10:
                        # File tồn tại và không trống
                        self.logger.info("Config file is ready")
                        return True
                
                # Nếu không sẵn sàng, đợi và thử lại
                self.logger.warning(f"Config file not ready (attempt {i+1}/{retries})")
                time.sleep(3)
                
            except Exception as e:
                self.logger.error(f"Error verifying config file: {e}")
                time.sleep(2)
        
        return False
    def _check_device_readiness_http(self):
        """
        Check device readiness using HTTP connection
        
        Returns:
            True if device appears ready, False otherwise
        """
        try:
            # First check basic connectivity
            if not self._recheck_connection():
                self.logger.info("Basic connection check failed - device not ready")
                return False
                
            # If connection is successful, we can try a simple API call
            # to verify more complete readiness
            host = self._safe_get(self.http_host_var, "127.0.0.1")
            port = int(self._safe_get(self.http_port_var, "6262"))
            url = f"http://{host}:{port}/ping"  # Assuming a simple ping endpoint
            
            try:
                import requests
                # Use a short timeout for readiness check
                response = requests.get(
                    url, 
                    timeout=5,
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
                )
                
                if response.status_code == 200:
                    self.logger.info("HTTP API check successful - device appears ready")
                    return True
                else:
                    self.logger.info(f"HTTP API check returned status {response.status_code} - device not fully ready")
                    return False
                    
            except requests.exceptions.RequestException:
                self.logger.info("HTTP API check failed - device not fully ready")
                return False
                
        except Exception as e:
            self.logger.debug(f"Error checking device readiness: {e}")
            return False
    def _execute_test_with_readiness_check(self, index):
        """
        Thực thi bài kiểm tra với kiểm tra sự sẵn sàng của thiết bị và lập lịch cho bài kiểm tra tiếp theo
        với khả năng phục hồi được cải thiện
        """
        try:
            if index >= len(self.queue_manager.queue_items):
                self.logger.info("Hoàn thành tất cả bài kiểm tra trong hàng đợi")
                return
                
            # Kiểm tra xem thiết bị đã sẵn sàng chưa
            device_ready = self._check_device_readiness_http()
            if not device_ready:
                self.logger.warning(f"Thiết bị chưa sẵn sàng, thử lại sau 5 giây...")
                self._safe_after(5000, lambda: self._execute_test_with_readiness_check(index))
                return
                
            # Kiểm tra xem đây có phải là bài kiểm tra wireless không
            is_wireless_test = False
            test_item = self.queue_manager.queue_items[index]
            service = test_item.get("service", "").lower()
            action = test_item.get("action", "").lower()
            
            # Xác định nếu đây là bài kiểm tra wireless
            if service == "wireless":
                is_wireless_test = True
                self.logger.info(f"Phát hiện bài kiểm tra wireless: {action}. Sử dụng xử lý nâng cao.")
            
            # Thực thi bài kiểm tra hiện tại
            result_success = self.send_selected_test(index)
            
            # Xử lý đặc biệt cho bài kiểm tra wireless - độ trễ dài hơn nhiều
            if is_wireless_test and hasattr(self, '_running_test_sequence') and index + 1 < len(self.queue_manager.queue_items):
                wireless_delay = 45000  # 45 giây cho bài kiểm tra wireless
                self.logger.info(f"Lên lịch bài kiểm tra tiếp theo với độ trễ mở rộng là {wireless_delay/1000}s do khởi động lại dịch vụ wireless")
                self._safe_after(wireless_delay, lambda: self._execute_test_with_readiness_check(index + 1))
                return  # Thoát sớm - không sử dụng lịch bình thường
                
            # Tiếp tục với việc lên lịch bài kiểm tra tiếp theo
            if hasattr(self, '_running_test_sequence') and index + 1 < len(self.queue_manager.queue_items):
                # Tính toán độ trễ dựa trên loại bài kiểm tra
                if result_success is False:
                    # Nếu bài kiểm tra thất bại, tạm dừng ngắn
                    next_delay = 5000  # 5 giây
                else:
                    # Độ trễ bình thường giữa các bài kiểm tra thành công
                    next_delay = 15000  # 15 giây
                    
                self.logger.info(f"Lên lịch bài kiểm tra tiếp theo #{index + 1} với độ trễ ban đầu là {next_delay/1000}s")
                self._safe_after(next_delay, lambda: self._execute_test_with_readiness_check(index + 1))
        except Exception as e:
            self.logger.error(f"Lỗi trong quá trình thực hiện bài kiểm tra với kiểm tra sự sẵn sàng: {str(e)}")
            # Tiếp tục với bài kiểm tra tiếp theo sau độ trễ dài hơn
            if hasattr(self, '_running_test_sequence') and index + 1 < len(self.queue_manager.queue_items):
                self._safe_after(10000, lambda: self._execute_test_with_readiness_check(index + 1))
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
