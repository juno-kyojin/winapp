#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main Window for Test Case Manager v3.0

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

from src.core.config import AppConfig
from src.core.constants import APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from src.core.exceptions import TestCaseManagerError
from src.core.test_case_loader import TestCaseLoader
from src.core.result_manager import ResultManager
# from core.test_case_manager import TestCaseManager
# from core.result_manager import ResultManager

from src.utils.logger import get_logger
from src.network.connection_manager import ConnectionManager, affects_network_connectivity


def extract_test_name(test_data: Dict[str, Any], template_name: Optional[str] = None) -> str:
    """
    Extract test name from test data with fallback strategies.

    Args:
        test_data: Test data to extract name from
        template_name: Optional template name as fallback

    Returns:
        Test name string, or "unknown" if cannot be determined
    """
    # Strategy 1: Check metadata.name
    if "metadata" in test_data and isinstance(test_data["metadata"], dict):
        name = test_data["metadata"].get("name")
        if name and isinstance(name, str) and name.strip():
            return name.strip()

    # Strategy 2: Check direct name field
    if "name" in test_data:
        name = test_data["name"]
        if name and isinstance(name, str) and name.strip():
            return name.strip()

    # Strategy 3: Generate from service and action
    if "test_cases" in test_data and test_data["test_cases"]:
        first_case = test_data["test_cases"][0]
        service = first_case.get("service", "")
        action = first_case.get("action", "")
        if service and action:
            return f"{service}_{action}"

    # Strategy 4: Direct service and action
    elif "service" in test_data and "action" in test_data:
        service = test_data.get("service", "")
        action = test_data.get("action", "")
        if service and action:
            return f"{service}_{action}"

    # Strategy 5: Use template name if provided
    if template_name:
        name = template_name
        if name.endswith('.json'):
            name = name[:-5]
        if name and name.strip():
            return name.strip()

    return "unknown"
from src.network.test_executor import TestExecutor
# from network.test_executor import TestExecutor

# Import panels (will be implemented separately)
from src.gui.panels.connection_panel import ConnectionPanel
from src.gui.panels.templates_panel import TemplatesPanel
from src.gui.panels.queue_panel import QueuePanel

# from gui.panels.history_panel import HistoryPanel
from src.gui.panels.logs_panel import LogsPanel

# Import dialogs (will be implemented separately)
# from gui.dialogs.preferences_dialog import PreferencesDialog
from src.gui.dialogs.about_dialog import AboutDialog
# from gui.dialogs.test_details_dialog import TestDetailsDialog

# Import widgets
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
        self._create_tabs()
        self._create_status_bar()
        
        # Initialize panels
        self._initialize_panels()
        
        self.logger.info(f"{APP_NAME} v{APP_VERSION} initialized")
    
    def _setup_window(self) -> None:
        """Setup the main window properties with improved layout management."""
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        
        # Set window size and position
        width = 800  # Default width
        height = 600  # Default height
        
        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # Set grid weights for proper resizing
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
        tools_menu.add_command(label="Execute Queue", command=self._execute_queue)
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
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Create tab frames - these will be populated by panels
        self.connection_tab = ttk.Frame(self.notebook)
        self.templates_tab = ttk.Frame(self.notebook)
        self.queue_tab = ttk.Frame(self.notebook)
        self.stream_tab = ttk.Frame(self.notebook)
        self.logs_tab = ttk.Frame(self.notebook)

        # Add tabs to notebook
        self.notebook.add(self.connection_tab, text="Connection")
        self.notebook.add(self.templates_tab, text="Templates")
        self.notebook.add(self.queue_tab, text="Queue")
        self.notebook.add(self.stream_tab, text="Stream")
        self.notebook.add(self.logs_tab, text="Logs")
    
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
                self._update_status
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
                # Thiết lập tham chiếu parent cho TemplatesPanel
                self.templates_panel.parent = self
                
                def new_add_to_queue(self=self.templates_panel):
                    # Get selected template
                    template = self.get_selected_template()
                    if template:
                        # Add to queue
                        self.parent._add_to_queue(template)
                
                self.templates_panel.add_to_queue = new_add_to_queue
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
                template_name = test_data.get("template_name")

                # Use robust test name extraction
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
            
        # Get test name for display
        test_name = "Unknown"
        if "metadata" in test_data and "name" in test_data["metadata"]:
            test_name = test_data["metadata"]["name"]
        elif "test_cases" in test_data and len(test_data["test_cases"]) > 0:
            service = test_data["test_cases"][0].get("service", "")
            action = test_data["test_cases"][0].get("action", "")
            if service and action:
                test_name = f"{service}_{action}"
            elif service:
                test_name = service
        
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
                # Get test name for thread context
                thread_test_name = "Unknown"
                if "metadata" in test_data and "name" in test_data["metadata"]:
                    thread_test_name = test_data["metadata"]["name"]
                elif "metadata" in test_data and "test_id" in test_data["metadata"]:
                    thread_test_name = test_data["metadata"]["test_id"]
                elif "test_cases" in test_data and len(test_data["test_cases"]) > 0:
                    service = test_data["test_cases"][0].get("service", "")
                    action = test_data["test_cases"][0].get("action", "")
                    if service and action:
                        thread_test_name = f"{service}_{action}"
                    elif service:
                        thread_test_name = service

                # Update stream: preparing to send
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.update_stream_status("preparing", "Validating test data and connection", 10)

                # Execute the test
                self.logger.info("Sending test to device...")

                # Update stream: sending test
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.update_stream_status("sending", "Sending test data to device", 30)

                # Start measuring ACTUAL test execution time (excluding delays and preparation)
                test_start_time = time.time()

                # Send test to device using intelligent retry mechanism
                success, result_data, message = self.connection_manager.send_test_with_retry(
                    test_data,
                    affects_network=affects_network,
                    max_retries=3  # Use intelligent retry with 3 attempts for network errors only
                )

                # Calculate ACTUAL execution time (only test execution, excluding delays)
                execution_time = time.time() - test_start_time

                # Update stream: processing
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.update_stream_status("processing", "Device is processing test case", 60)

                # Update stream: receiving results
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.update_stream_status("receiving", "Receiving test results from device", 90)

                # Update status
                if success:
                    status = "success"
                    self._update_status(f"Test executed successfully: {thread_test_name}")
                else:
                    status = "fail"
                    self._update_status(f"Test execution failed: {message}")
                

                
                # Save result to history
                try:
                    # Save to file
                    self.result_manager.save_result(
                        thread_test_name,
                        status,
                        {
                            "test_data": test_data,
                            "result_data": result_data,
                            "message": message,
                            "metadata": {
                                "test_id": thread_test_name,
                                "status": status,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "affects_network": affects_network,
                                "execution_time": execution_time
                            }
                        }
                    )
                    


                except Exception as e:
                    self.logger.error(f"Error saving result to history: {e}")

                # End stream with success
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    final_message = f"Test completed successfully in {execution_time:.1f}s" if success else f"Test failed: {message}"
                    self.stream_panel.end_test_stream(success, final_message)

                    # If we're in queue execution mode, also store the execution time and end queue test stream
                    if self.stream_panel.is_queue_executing and hasattr(self, '_current_queue_test_index'):
                        self.stream_panel.set_queue_test_execution_time(self._current_queue_test_index, execution_time)

                        # Report test result to queue panel for accurate tracking
                        if hasattr(self, 'queue_panel') and self.queue_panel:
                            self.queue_panel.set_test_result(self._current_queue_test_index, success)

                        # End queue test stream with appropriate message based on success
                        # Get total tests for proper indexing display
                        total_tests = len(self.queue_panel.queue_items) if hasattr(self, 'queue_panel') and self.queue_panel else 1
                        test_display_index = self._current_queue_test_index + 1

                        if success:
                            completion_msg = f"✅ Test {test_display_index}/{total_tests} ({thread_test_name}) completed successfully"
                            self.stream_panel.end_queue_test_stream(self._current_queue_test_index, thread_test_name, success, completion_msg)
                        else:
                            failure_msg = f"❌ Test {test_display_index}/{total_tests} ({thread_test_name}) failed: {message}"
                            self.stream_panel.end_queue_test_stream(self._current_queue_test_index, thread_test_name, success, failure_msg)

            except Exception as e:
                # Set default execution time for failed tests (no actual test was executed)
                execution_time = 0.0

                # Get test name for error context
                thread_test_name = "Unknown"
                if "metadata" in test_data and "name" in test_data["metadata"]:
                    thread_test_name = test_data["metadata"]["name"]
                elif "metadata" in test_data and "test_id" in test_data["metadata"]:
                    thread_test_name = test_data["metadata"]["test_id"]
                elif "test_cases" in test_data and len(test_data["test_cases"]) > 0:
                    service = test_data["test_cases"][0].get("service", "")
                    action = test_data["test_cases"][0].get("action", "")
                    if service and action:
                        thread_test_name = f"{service}_{action}"
                    elif service:
                        thread_test_name = service

                # Handle any exceptions
                error_msg = f"Error executing test: {str(e)}"
                self.logger.error(error_msg)

                # End stream with error
                if hasattr(self, 'stream_panel') and self.stream_panel:
                    self.stream_panel.end_test_stream(False, f"Test execution error: {str(e)}")

                    # If we're in queue execution mode, also store the execution time and end queue test stream
                    if self.stream_panel.is_queue_executing and hasattr(self, '_current_queue_test_index'):
                        self.stream_panel.set_queue_test_execution_time(self._current_queue_test_index, execution_time)

                        # Report test failure to queue panel for accurate tracking
                        if hasattr(self, 'queue_panel') and self.queue_panel:
                            self.queue_panel.set_test_result(self._current_queue_test_index, False)

                        # End queue test stream with error
                        self.stream_panel.end_queue_test_stream(self._current_queue_test_index, thread_test_name, False,
                                                               f"Test execution error: {str(e)}")

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
            self.connection_panel.test_connection()
        else:
            self._update_status("Connection panel not initialized")
    
    def _new_template(self) -> None:
        """Create a new template."""
        if self.templates_panel:
            self.templates_panel._new_template()
        else:
            self._update_status("Templates panel not initialized")
    
    def _open_template(self) -> None:
        """Open an existing template."""
        if self.templates_panel:
            self.templates_panel._import_template()
        else:
            self._update_status("Templates panel not initialized")
    
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
        if self.templates_panel:
            self.templates_panel._validate_template()
        else:
            self._update_status("Templates panel not initialized")
    
    def _execute_queue(self) -> None:
        """Execute all tests in the queue."""
        if not self.queue_panel:
            self._update_status("Queue panel not initialized")
            return
            
        test_queue = self.queue_panel.get_queue()
        if not test_queue:
            messagebox.showinfo(
                "Execute Queue",
                "Queue is empty. Add tests to the queue first."
            )
            return
            
        # Check if we're connected
        if not self.connection_manager.is_connected():
            messagebox.showerror(
                "Connection Error",
                "Not connected to device. Please connect first."
            )
            return
            

            
        # Execute tests one by one
        for test_data in test_queue:
            # Check if the test affects network connectivity
            affects_network = affects_network_connectivity(test_data)

            # Execute the test
            self._execute_test(test_data, affects_network=affects_network)
            
            # Wait a bit between tests
            time.sleep(1)
    
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
    
    def _show_about(self) -> None:
        """Show about dialog."""
        if not self.root:
            return
            
        dialog = AboutDialog(self.root)
    
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


            