#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window for Test Case Manager v1.0

This module implements the main application window with tabbed interface,
menu bar, status bar, and core application functionality.

Author: juno-kyojin
Created: 2025-06-25
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import time
import threading
import logging
from typing import Dict, Any, Optional, List, Callable, Union, Tuple, cast
from datetime import datetime

# Core imports
from src.core.config import AppConfig
from src.core.constants import (
    APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT
)
from src.core.exceptions import TestCaseManagerError
from src.core.test_case_loader import TestCaseLoader
from src.core.result_manager import ResultManager

# Utility imports
from src.utils.logger import get_logger
from src.utils.script_verifier import ScriptVerifier
from src.utils.formatters import extract_test_name, get_test_display_name

# Network imports
from src.network.connection_manager import ConnectionManager
from src.network.test_executor import TestExecutor

# GUI imports - panels
from src.gui.panels.connection_panel import ConnectionPanel
from src.gui.panels.templates_panel import TemplatesPanel
from src.gui.panels.queue_panel import QueuePanel
from src.gui.panels.logs_panel import LogsPanel

# GUI imports - widgets
from src.gui.widgets.status_bar import StatusBar







class MainWindow:
    """
    Main application window for Test Case Manager.

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
        self.logger = get_logger(__name__)

        # Core components
        # self.test_case_manager = TestCaseManager()
        self.test_loader = TestCaseLoader()
        self.result_manager = ResultManager()
        self.connection_manager = ConnectionManager()
        self.test_executor = TestExecutor(self.connection_manager)
        self.script_verifier = ScriptVerifier()  # For automatic script execution

        # UI components
        self.root: Optional[tk.Tk] = None
        self.notebook: Optional[ttk.Notebook] = None
        self.status_bar: Optional[StatusBar] = None

        # Panels
        self.connection_panel: Optional[ConnectionPanel] = None
        self.templates_panel: Optional[TemplatesPanel] = None
        self.logs_panel: Optional[LogsPanel] = None

        # Setup UI
        self._setup_window()
        self._create_menu()
        self._create_header()
        self._create_tabs()
        self._create_status_bar()

        # Initialize panels
        self._initialize_panels()

        self.logger.info(f"{APP_NAME} v{APP_VERSION} initialized")

    def _setup_window(self) -> None:
        """Setup the main window properties with improved layout management."""
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")

        # Get window size from config or use defaults
        width = getattr(self.config.gui, 'window_width', WINDOW_DEFAULT_WIDTH)
        height = getattr(self.config.gui, 'window_height', WINDOW_DEFAULT_HEIGHT)

        # Ensure minimum size
        width = max(width, WINDOW_MIN_WIDTH)
        height = max(height, WINDOW_MIN_HEIGHT)

        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # Set grid weights for proper resizing (no header)
        self.root.rowconfigure(0, weight=1)  # Main content expands
        self.root.rowconfigure(1, weight=0)  # Status bar fixed height
        self.root.columnconfigure(0, weight=1)  # Expand horizontally

        # Set window icon (if available)
        try:
            from src.utils.image_utils import set_window_icon
            set_window_icon(self.root)
        except Exception as e:
            self.logger.debug(f"Could not set window icon: {e}")

        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_header(self) -> None:
        """Header removed - clean interface without redundant title display."""
        pass

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
        # Removed Execute Queue - use Queue Panel's Execute All button instead
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self._show_documentation)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

    def _create_tabs(self) -> None:
        """Create the tabbed interface with enlarged tab buttons."""
        if not self.root:
            return

        # Configure style for expanded tab buttons
        style = ttk.Style()

        # Calculate tab width to fill the window
        # We'll update this in resize event
        self._update_tab_width()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Bind multiple events to adjust tab styling
        self.root.bind('<Configure>', self._on_window_resize)
        self.root.bind('<Map>', self._on_window_resize)  # When window is mapped
        self.root.bind('<FocusIn>', self._on_window_resize)  # When window gets focus

        # Initial resize call to set proper sizing
        self.root.after(100, lambda: self._on_window_resize(None))

        # Create tab frames - these will be populated by panels
        self.connection_tab = ttk.Frame(self.notebook)
        self.templates_tab = ttk.Frame(self.notebook)
        self.queue_tab = ttk.Frame(self.notebook)
        self.stream_tab = ttk.Frame(self.notebook)
        self.logs_tab = ttk.Frame(self.notebook)

        # Add tabs to notebook
        # Add tabs with normal text
        self.notebook.add(self.connection_tab, text="Connection")
        self.notebook.add(self.templates_tab, text="Templates")
        self.notebook.add(self.queue_tab, text="Queue")
        self.notebook.add(self.stream_tab, text="Stream")
        self.notebook.add(self.logs_tab, text="Logs")

    def _update_tab_width(self) -> None:
        """Update tab width to fill the window."""
        if not self.root:
            return

        try:
            # Get window width
            window_width = self.root.winfo_width()
            if window_width <= 1:  # Window not yet mapped
                window_width = 1000  # Default width

            # Calculate width per tab (5 tabs total)
            # Account for padding and margins
            available_width = window_width - 40  # Account for window padding
            tab_width = available_width // 5  # 5 tabs

            # Ensure minimum width
            tab_width = max(tab_width, 100)

            # Configure style with calculated width and centered text
            style = ttk.Style()
            style.configure('TNotebook.Tab',
                           font=('Segoe UI', 12, 'bold'),
                           padding=[15, 8],
                           width=tab_width)

            # Try different approach: configure layout for centering
            style.layout('TNotebook.Tab', [
                ('Notebook.tab', {
                    'sticky': 'nswe',
                    'children': [
                        ('Notebook.padding', {
                            'side': 'top',
                            'sticky': 'nswe',
                            'children': [
                                ('Notebook.label', {
                                    'side': 'top',
                                    'sticky': ''  # No sticky = center
                                })
                            ]
                        })
                    ]
                })
            ])

            # Try to map anchor for centering
            style.map('TNotebook.Tab',
                     anchor=[('selected', 'center'), ('!selected', 'center')],
                     justify=[('selected', 'center'), ('!selected', 'center')])

        except Exception as e:
            print(f"Error updating tab width: {e}")

    def _on_window_resize(self, event) -> None:
        """Adjust tab styling based on window size."""
        if not self.root:
            return

        # Skip if event is from child widget (not main window)
        if event and hasattr(event, 'widget') and event.widget != self.root:
            return

        try:
            # Get current window width
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()

            # More aggressive responsive scaling based on screen area
            screen_area = window_width * window_height

            if window_width > 1600 or screen_area > 1500000:  # Very large screens/full screen
                font_size = 16
                padding_x = 35
                padding_y = 15
            elif window_width > 1200 or screen_area > 800000:  # Large screens
                font_size = 14
                padding_x = 28
                padding_y = 12
            elif window_width > 900:  # Medium screens
                font_size = 12
                padding_x = 20
                padding_y = 10
            else:  # Small screens
                font_size = 11
                padding_x = 15
                padding_y = 8

            # Calculate width per tab (5 tabs total)
            available_width = window_width - 40  # Account for window padding
            tab_width = available_width // 5  # 5 tabs
            tab_width = max(tab_width, 100)  # Ensure minimum width

            # Update tab style with responsive sizing and width (layout already set)
            style = ttk.Style()
            style.configure('TNotebook.Tab',
                           font=('Segoe UI', font_size, 'bold'),
                           padding=[padding_x, padding_y],
                           width=tab_width)

            # Debug info removed to prevent spam

        except Exception as e:
            print(f"Error in window resize: {e}")

    def _create_status_bar(self) -> None:
        """Create the application status bar."""
        if not self.root:
            return

        # Cast the root to tk.Widget which is what StatusBar expects
        self.status_bar = StatusBar(cast(tk.Widget, self.root))
        self.status_bar.grid(row=1, column=0, sticky="ew")

    def _initialize_panels(self) -> None:
        """Initialize panels for each tab."""
        if not self.root:
            return

        # Initialize Connection Panel
        try:
            self.connection_panel = ConnectionPanel(
                self.connection_tab,
                self.test_executor,
                self.config,
                self._update_status,
                self._switch_to_tab  # Add tab switching callback
            )
            self.connection_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        except Exception as e:
            self.logger.error(f"Failed to initialize Connection Panel: {e}")
            self._show_placeholder(self.connection_tab, "Connection Panel")



        # Initialize Queue Panel
        try:
            from src.gui.panels.queue_panel import QueuePanel
            self.queue_panel: QueuePanel = QueuePanel(
                self.queue_tab,
                self._update_status,
                self._execute_test
            )
            self.queue_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Set main window reference for execution time tracking
            self.queue_panel.main_window = self

            # Initialize current queue test index for execution time tracking
            self._current_queue_test_index: int = -1
        except Exception as e:
            self.logger.error(f"Failed to initialize Queue Panel: {e}")
            self._show_placeholder(self.queue_tab, "Queue Panel")

        # Initialize Templates Panel
        try:
            self.templates_panel = TemplatesPanel(
                self.templates_tab,
                self.test_loader,
                self._update_status
            )
            self.templates_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Connect Templates Panel to Queue Panel
            if self.templates_panel and self.queue_panel:
                # Set parent reference for templates panel
                self.templates_panel.parent = self
                # Set templates panel reference for queue panel (for clearing sent status)
                self.queue_panel.templates_panel = self.templates_panel
        except Exception as e:
            self.logger.error(f"Failed to initialize Templates Panel: {e}")
            self._show_placeholder(self.templates_tab, "Templates Panel")

        # Initialize Stream Panel
        try:
            from src.gui.panels.stream_panel import StreamPanel
            self.stream_panel: StreamPanel = StreamPanel(
                self.stream_tab,
                self._update_status
            )
            self.stream_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        except Exception as e:
            self.logger.error(f"Failed to initialize Stream Panel: {e}")
            self._show_placeholder(self.stream_tab, "Stream Panel")

        # Connect Queue Panel to Stream Panel for queue execution streaming
        if hasattr(self, 'queue_panel') and hasattr(self, 'stream_panel') and self.queue_panel and self.stream_panel:
            self.queue_panel.stream_panel = self.stream_panel
            # Connect Stream Panel to Queue Panel for cancellation functionality
            self.stream_panel.queue_panel_ref = self.queue_panel

        # Store reference to queue panel for potential future use
        self.queue_panel_ref = self.queue_panel if hasattr(self, 'queue_panel') else None

        # Initialize Logs Panel
        try:
            self.logs_panel = LogsPanel(
                self.logs_tab,
                self._update_status
            )
            self.logs_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        except Exception as e:
            self.logger.error(f"Failed to initialize Logs Panel: {e}")
            self._show_placeholder(self.logs_tab, "Logs Panel")

    def _show_placeholder(self, parent: ttk.Frame, panel_name: str) -> None:
        """
        Show a placeholder for panels that are not yet implemented.

        Args:
            parent: Parent widget
            panel_name: Name of the panel
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)

        label = ttk.Label(
            frame,
            text=f"{panel_name} will be implemented in a future version.",
            font=("Arial", 12)
        )
        label.pack(expand=True)

    def _update_status(self, message: str) -> None:
        """
        Update the status bar message.

        Args:
            message: Status message to display
        """
        if self.status_bar:
            self.status_bar.set_status(message)

    def _switch_to_tab(self, tab_name: str) -> None:
        """
        Switch to the specified tab.

        Args:
            tab_name: Name of the tab to switch to
        """
        if not self.notebook:
            return

        # Map tab names to indices
        tab_mapping = {
            "Connection": 0,
            "Templates": 1,
            "Queue": 2,
            "Stream": 3,
            "Logs": 4
        }

        if tab_name in tab_mapping:
            tab_index = tab_mapping[tab_name]
            self.notebook.select(tab_index)
            self.logger.info(f"Switched to {tab_name} tab")
        else:
            self.logger.warning(f"Unknown tab name: {tab_name}")

    def _add_to_queue(self, test_data: Dict[str, Any]) -> None:
        """
        Add a test to the queue.

        Args:
            test_data: Test data to add to the queue
        """
        if not test_data:
            self._update_status("Invalid test data: empty")
            return

        if self.queue_panel:
            # Handle template data returned from templates_panel.get_selected_template()
            if "template_data" in test_data:
                # Extract template data and metadata
                template_data = test_data["template_data"]
                category = test_data.get("category", "Unknown")
                template_name = test_data.get("template_name")  # Original filename
                extracted_name = test_data.get("extracted_name")  # Pre-extracted name

                # Use pre-extracted name if available, otherwise extract from template
                if extracted_name:
                    name = extracted_name
                else:
                    name = extract_test_name(template_data, template_name)

                # Add to queue
                self.queue_panel.add_to_queue(template_data, category, name)
            else:
                # Handle direct test data
                category = test_data.get("metadata", {}).get("category", "Unknown")

                # Use robust test name extraction
                name = extract_test_name(test_data)

                self.queue_panel.add_to_queue(test_data, category, name)

            # Switch to queue tab
            if self.notebook:
                self.notebook.select(self.queue_tab)

            self._update_status("Test added to queue")
        else:
            self._update_status("Queue panel not initialized")

    def _execute_test(self, test_data: Dict[str, Any], affects_network: bool = False) -> None:
        """
        Execute a test.

        Args:
            test_data: Test data to execute
            affects_network: Whether the test affects network connectivity
        """
        # Validate test data
        if not test_data:
            self._update_status("Invalid test data: empty")
            messagebox.showerror(
                "Test Error",
                "Test data is empty. Cannot execute test."
            )
            return

        # Check if we're connected
        if not self.connection_manager.is_connected():
            self._update_status("Not connected to device. Please connect first.")
            messagebox.showerror(
                "Connection Error",
                "Not connected to device. Please connect first."
            )
            return

        # Get test name for display using utility function
        test_name = get_test_display_name(test_data)

        # Validate test structure
        if "test_cases" not in test_data and "service" not in test_data:
            self._update_status("Invalid test data: missing required fields")
            messagebox.showerror(
                "Test Error",
                "Test data is invalid. Missing both 'test_cases' array and 'service' field."
            )
            return

        # If test_cases exists, ensure it's not empty
        if "test_cases" in test_data and (not test_data["test_cases"] or len(test_data["test_cases"]) == 0):
            self._update_status("Invalid test data: empty test_cases array")
            messagebox.showerror(
                "Test Error",
                "Test data contains an empty test_cases array."
            )
            return

        # Log test execution
        self.logger.info(f"Executing test: {test_name}")
        if affects_network:
            self.logger.info("Test affects network connectivity")
            self._update_status(f"Executing network-affecting test: {test_name}...")
        else:
            self._update_status(f"Executing test: {test_name}...")

        # Start stream for this test
        if hasattr(self, 'stream_panel') and self.stream_panel:
            self.stream_panel.start_test_stream(test_name, test_data)

        # Note: Execution time will be measured during actual test execution

        # Function to execute in a separate thread
        def execute_test_thread():
            try:
                # Get test name for thread context using utility function
                thread_test_name = get_test_display_name(test_data)

                # SOFT CANCELLATION: Do not check cancellation during test execution
                # Let the current test complete naturally - cancellation only affects future tests

                # Update stream: preparing to send
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.update_stream_status("preparing", "Validating test data and connection", 10)

                # SOFT CANCELLATION: Do not interrupt test preparation

                # Execute the test
                self.logger.info("Sending test to device...")

                # Update stream: sending test
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.update_stream_status("sending", "Sending test data to device", 30)

                # SOFT CANCELLATION: Do not interrupt device communication

                # Start measuring ACTUAL test execution time (excluding delays and preparation)
                test_start_time = time.time()

                # Send test to device using intelligent retry mechanism
                success, result_data, message = self.connection_manager.send_test_with_retry(
                    test_data,
                    affects_network=affects_network,
                    max_retries=3  # Use intelligent retry with 3 attempts for network errors only
                )

                # SOFT CANCELLATION: Do not interrupt after device communication

                # Calculate ACTUAL execution time (only test execution, excluding delays)
                execution_time = time.time() - test_start_time

                # Update stream: processing
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.update_stream_status("processing", "Device is processing test case", 60)

                # Update stream: receiving results
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.update_stream_status("receiving", "Receiving test results from device", 90)

                # Automatic Script Verification Logic
                final_status = "fail"  # Default to fail
                final_message = message
                verification_message = ""

                if success:
                    # HTTP communication successful - now handle natural request-response cycle
                    final_status, final_message = self._handle_natural_test_flow(result_data or {})

                else:
                    # HTTP communication failed - treat as failure
                    final_status = "fail"
                    final_message = f"HTTP communication failed: {message}"
                    self.logger.info(f"Final result: FAIL - HTTP communication failed, skipping verification")

                # Update final status
                status = final_status

                # Handle cancelled status
                if final_status == "cancelled":
                    self._update_status(f"Test cancelled: {thread_test_name}")
                    # End stream with cancelled status
                    if hasattr(self, 'stream_panel') and self.stream_panel:
                        self.stream_panel.end_test_stream(False, f"🛑 {final_message}")
                    return  # Don't save cancelled tests to history
                else:
                    self._update_status(f"Test completed: {thread_test_name} - {final_status.upper()}")

                # Save result to history
                try:
                    # Save to file
                    self.result_manager.save_result(
                        thread_test_name,
                        status,
                        {
                            "test_data": test_data,
                            "result_data": result_data,
                            "message": final_message,  # Use final message with verification info
                            "original_device_message": message,  # Keep original device message
                            "verification_message": verification_message,  # Store verification details
                            "metadata": {
                                "test_id": thread_test_name,
                                "status": status,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "affects_network": affects_network,
                                "execution_time": execution_time,
                                "verification_executed": verification_message != ""  # Track if verification ran
                            }
                        }
                    )



                except Exception as e:
                    self.logger.error(f"Error saving result to history: {e}")

                # End stream with final status
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    stream_message = f"Test completed in {execution_time:.1f}s - {final_status.upper()}: {final_message}"
                    self.stream_panel.end_test_stream(final_status == "success", stream_message)

                    # If we're in queue execution mode, also store the execution time and end queue test stream
                    if self.stream_panel.is_queue_executing and hasattr(self, '_current_queue_test_index'):
                        self.stream_panel.set_queue_test_execution_time(self._current_queue_test_index, execution_time)

                        # End queue test stream with appropriate message based on final status
                        # Get total tests for proper indexing display
                        total_tests = len(self.queue_panel.queue_items) if hasattr(self, 'queue_panel') and self.queue_panel else 1
                        test_display_index = self._current_queue_test_index + 1

                        final_success = (final_status == "success")
                        if final_success:
                            completion_msg = f"✅ Test {test_display_index}/{total_tests} ({thread_test_name}) completed successfully"
                            if verification_message:
                                completion_msg += f" (with verification)"
                            self.stream_panel.end_queue_test_stream(self._current_queue_test_index, thread_test_name, final_success, completion_msg, execution_time)
                        else:
                            failure_msg = f"❌ Test {test_display_index}/{total_tests} ({thread_test_name}) failed: {final_message}"
                            self.stream_panel.end_queue_test_stream(self._current_queue_test_index, thread_test_name, final_success, failure_msg, execution_time)

                # Report test result to queue panel for accurate tracking (regardless of queue execution mode)
                if hasattr(self, '_current_queue_test_index') and self._current_queue_test_index >= 0:
                    final_success = (final_status == "success")
                    if hasattr(self, 'queue_panel') and self.queue_panel:
                        self.queue_panel.set_test_result(self._current_queue_test_index, final_success)
                        self.logger.debug(f"Reported test result to queue panel: index={self._current_queue_test_index}, success={final_success}")

                    # Reset the queue test index after reporting
                    self._current_queue_test_index = -1

            except Exception as e:
                # Set default execution time for failed tests (no actual test was executed)
                execution_time = 0.0

                # Get test name for error context using utility function
                thread_test_name = get_test_display_name(test_data)

                # Handle any exceptions
                error_msg = f"Error executing test: {str(e)}"
                self.logger.error(error_msg)

                # End stream with error
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.end_test_stream(False, f"Test execution error: {str(e)}")

                    # If we're in queue execution mode, also store the execution time and end queue test stream
                    if self.stream_panel.is_queue_executing and hasattr(self, '_current_queue_test_index'):
                        self.stream_panel.set_queue_test_execution_time(self._current_queue_test_index, execution_time)

                        # End queue test stream with error
                        self.stream_panel.end_queue_test_stream(self._current_queue_test_index, thread_test_name, False,
                                                               f"Test execution error: {str(e)}", execution_time)

                # Report test failure to queue panel for accurate tracking (regardless of queue execution mode)
                if hasattr(self, '_current_queue_test_index') and self._current_queue_test_index >= 0:
                    if hasattr(self, 'queue_panel') and self.queue_panel:
                        self.queue_panel.set_test_result(self._current_queue_test_index, False)
                        self.logger.debug(f"Reported test failure to queue panel: index={self._current_queue_test_index}")

                    # Reset the queue test index after reporting
                    self._current_queue_test_index = -1

                # Show error message
                if self.root:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Test Execution Error",
                        error_msg
                    ))

        # Start the execution thread
        execution_thread = threading.Thread(target=execute_test_thread)
        execution_thread.daemon = True
        execution_thread.start()

    def _save_test_result(self, result_data: Optional[Dict[str, Any]], test_name: str) -> None:
        """
        Save test result to a file.

        Args:
            result_data: Result data to save
            test_name: Name of the test
        """
        if not result_data:
            messagebox.showerror(
                "Save Error",
                "No result data to save."
            )
            return

        # Get file path from user
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{test_name}_result.json"
        )

        if not file_path:
            return  # User cancelled

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(result_data, f, indent=4)

            self._update_status(f"Result saved to {file_path}")
            messagebox.showinfo(
                "Save Successful",
                f"Result saved to {file_path}"
            )
        except Exception as e:
            error_msg = f"Error saving result: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror(
                "Save Error",
                error_msg
            )

    def _test_connection(self) -> None:
        """Test the current connection."""
        if self.connection_panel:
            self.connection_panel._connect()
        else:
            self._update_status("Connection panel not initialized")

    def _new_template(self) -> None:
        """Create a new template."""
        # Template creation will be handled by Editor tab in future
        self._update_status("Template creation will be available in Editor tab")

    def _open_template(self) -> None:
        """Open an existing template."""
        # Template editing will be handled by Editor tab in future
        self._update_status("Template editing will be available in Editor tab")

    def _export_results(self) -> None:
        """Export test results."""
        # Will be implemented when history panel is available
        # if self.history_panel:
        #     self.history_panel.export_results()
        self._update_status("Export results feature not yet implemented")

    def _show_preferences(self) -> None:
        """Show preferences dialog."""
        # Will be implemented when preferences dialog is available
        # if not self.root:
        #     return
        #
        # dialog = PreferencesDialog(self.root, self.config)
        # if dialog.result:
        #     # Apply new preferences
        #     self._update_status("Preferences updated")
        self._update_status("Preferences dialog not yet implemented")

    def _validate_templates(self) -> None:
        """Validate all templates."""
        # Template validation will be handled by Editor tab in future
        self._update_status("Template validation will be available in Editor tab")

    # Removed _execute_queue method - Queue Panel handles execution directly

    def _show_documentation(self) -> None:
        """Show documentation."""
        try:
            import webbrowser
            # TODO: Update documentation URL
            doc_url = "https://example.com/testcasemanager/docs"
            webbrowser.open(doc_url)
            self._update_status("Opening documentation in browser")
        except Exception as e:
            self.logger.error(f"Failed to open documentation: {e}")
            messagebox.showerror(
                "Documentation Error",
                f"Could not open documentation: {str(e)}"
            )

    def _determine_device_test_result(self, result_data: Dict[str, Any]) -> Optional[bool]:
        """
        Determine if device test actually passed based on device response.
        Device is the sole authority for test results.

        Args:
            result_data: Response data from device

        Returns:
            True if device indicates test passed, False otherwise
        """
        if not result_data or not isinstance(result_data, dict):
            return False

        # Check summary field for device determination
        if "summary" in result_data:
            summary = result_data["summary"]
            if isinstance(summary, dict):
                # Device reports failed tests
                failed_count = summary.get("failed", 0)
                if failed_count > 0:
                    self.logger.info(f"Device reports {failed_count} failed tests")
                    return False

                # Device reports passed tests
                passed_count = summary.get("passed", 0)
                if passed_count > 0:
                    self.logger.info(f"Device reports {passed_count} passed tests")
                    return True

        # Check for script verification request (NOT final result)
        if "script" in result_data and "script_params" in result_data:
            self.logger.info("Device requesting script verification - this is NOT final result")
            return None  # Special value indicating script verification needed

        # Check for explicit error status
        if "status" in result_data and result_data["status"] == "error":
            self.logger.info("Device returned explicit error status")
            return False

        # Default: if we got a valid response, assume success unless explicitly failed
        self.logger.info("Device response format unclear - defaulting to success")
        return True






    def _handle_natural_test_flow(self, initial_response: Dict[str, Any]) -> Tuple[str, str]:
        """
        Handle the natural request-response cycle with device.

        Each HTTP request gets exactly one response:
        1. App sends test case → Device responds with script request OR final result
        2. If script request: App sends script result → Device responds with next script request OR final result
        3. Repeat until device sends final result

        Args:
            initial_response: Initial response from device after sending test case

        Returns:
            Tuple of (final_status, final_message)
        """
        try:
            current_response = initial_response
            script_count = 0
            max_script_iterations = 10  # Prevent infinite loops

            while script_count < max_script_iterations:
                # SOFT CANCELLATION: Do not interrupt natural request-response flow
                # Let the current test complete its natural cycle

                # Check what type of response we received
                device_test_result = self._determine_device_test_result(current_response)

                if device_test_result is None:
                    # Device is requesting script verification
                    script_count += 1
                    script_name = current_response.get("script", "unknown")
                    script_params = current_response.get("script_params", [])

                    self.logger.info(f"Device requesting script verification #{script_count}: {script_name} with params: {script_params}")

                    # SOFT CANCELLATION: Do not interrupt script verification
                    # Let the script execute and complete naturally

                    # Execute the requested script
                    verification_needed, verification_msg, verification_passed = self.script_verifier.verify_test_result(current_response)

                    # SOFT CANCELLATION: Do not interrupt after script execution
                    # Let the result be sent back to device naturally

                    if not verification_needed:
                        return "fail", f"Script verification was requested but could not be executed: {verification_msg}"

                    # Send script result back to device and get next response
                    script_result = "1" if verification_passed else "0"
                    script_response = {
                        "type": "script",
                        "script_result": [script_result]
                    }

                    self.logger.info(f"Sending script #{script_count} result: {script_result} ({'PASS' if verification_passed else 'FAIL'})")

                    # SOFT CANCELLATION: Do not interrupt before sending script result
                    # Device is waiting for this result - must complete the cycle

                    # Send script result and get device's next response
                    success, next_response, error_msg = self.connection_manager.send_script_result(script_response)

                    if not success:
                        return "fail", f"Failed to send script result #{script_count}: {error_msg}"

                    # SOFT CANCELLATION: Do not interrupt after sending script result
                    # Wait for device's natural response

                    # Device's next response (either another script request or final result)
                    current_response = next_response or {}
                    self.logger.info(f"Received device response after script #{script_count}")

                elif device_test_result is True:
                    # Device sent final result: PASS
                    self.logger.info(f"Device completed test successfully after {script_count} script verifications")
                    return "success", f"Test passed with {script_count} script verifications"

                elif device_test_result is False:
                    # Device sent final result: FAIL
                    self.logger.info(f"Device reported test failure after {script_count} script verifications")
                    return "fail", f"Device test failed after {script_count} script verifications"

                else:
                    # Unexpected response format
                    self.logger.warning(f"Unexpected device response format: {current_response}")
                    return "fail", "Unexpected device response format"

            # Too many script iterations
            self.logger.error(f"Exceeded maximum script iterations ({max_script_iterations})")
            return "fail", f"Test exceeded maximum script iterations ({max_script_iterations})"

        except Exception as e:
            self.logger.error(f"Error in natural test flow: {e}")
            return "fail", f"Error in test flow: {str(e)}"







    def _show_about(self) -> None:
        """Show about dialog with logo."""
        if not self.root:
            return

        # Create about dialog window
        about_window = tk.Toplevel(self.root)
        about_window.title("About Test Case Manager")
        about_window.geometry("400x300")
        about_window.resizable(False, False)

        # Center the dialog
        about_window.transient(self.root)
        about_window.grab_set()

        # Create main frame
        main_frame = ttk.Frame(about_window, padding="20")
        main_frame.pack(fill="both", expand=True)

        try:
            # Add logo
            from src.utils.image_utils import load_logo_image
            logo_image = load_logo_image(size=(64, 64))
            if logo_image:
                logo_label = ttk.Label(main_frame, image=logo_image)
                setattr(logo_label, 'image', logo_image)  # Keep a reference
                logo_label.pack(pady=(0, 15))
            else:
                # Fallback: create a simple text logo
                logo_text = ttk.Label(
                    main_frame,
                    text="📱",
                    font=("Segoe UI", 32)
                )
                logo_text.pack(pady=(0, 15))
        except Exception as e:
            self.logger.debug(f"Could not create logo in about dialog: {e}")
            # Fallback: create a simple text logo
            logo_text = ttk.Label(
                main_frame,
                text="📱",
                font=("Segoe UI", 32)
            )
            logo_text.pack(pady=(0, 15))

        # Add application info
        app_label = ttk.Label(
            main_frame,
            text=f"{APP_NAME}",
            font=("Segoe UI", 16, "bold"),
            anchor="center"
        )
        app_label.pack(pady=(0, 5))

        version_label = ttk.Label(
            main_frame,
            text=f"Version {APP_VERSION}",
            font=("Segoe UI", 12),
            anchor="center"
        )
        version_label.pack(pady=(0, 10))

        description_label = ttk.Label(
            main_frame,
            text="OpenWrt Test Case Management Tool\nfor Network Device Testing",
            font=("Segoe UI", 10),
            anchor="center",
            justify="center"
        )
        description_label.pack(pady=(0, 20))

        # Add close button
        close_button = ttk.Button(
            main_frame,
            text="Close",
            command=about_window.destroy
        )
        close_button.pack(pady=(10, 0))

        # Center the window on parent
        about_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (about_window.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (about_window.winfo_height() // 2)
        about_window.geometry(f"+{x}+{y}")

    def _on_closing(self) -> None:
        """Handle window closing."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.root:
                # Save configuration
                # self.config.save()

                # Destroy root window
                self.root.destroy()

    def run(self) -> None:
        """Run the application main loop."""
        if self.root:
            self.root.mainloop()


