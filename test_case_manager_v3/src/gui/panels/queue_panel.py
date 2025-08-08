#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Queue Panel for Test Case Manager v1.0

This module provides a panel for managing test execution queue.

Author: juno-kyojin
Created: 2025-06-29
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
import uuid
import time
import threading
from typing import Dict, Any, Optional, List, Callable, cast
from datetime import datetime

from src.utils.logger import get_logger
from src.network.connection_manager import affects_network_connectivity
from src.core.config import get_config


class QueuePanel(ttk.Frame):
    """
    Panel for managing test execution queue.
    
    This panel provides UI for viewing, managing, and executing
    queued test cases.
    """
    
    def __init__(self, parent: tk.Widget,
                status_callback: Optional[Callable[[str], None]] = None,
                execute_callback: Optional[Callable[[Dict[str, Any], bool], None]] = None) -> None:
        """
        Initialize the queue panel.
        
        Args:
            parent: Parent widget
            status_callback: Callback for status updates
            execute_callback: Callback for test execution
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.status_callback = status_callback
        self.execute_callback = execute_callback
        
        # Queue data - Enhanced two-section system
        self.active_queue_items: List[Dict[str, Any]] = []  # Pending/Running tests
        self.history_items: List[Dict[str, Any]] = []       # Completed/Failed tests
        self.selected_item: Optional[int] = None
        self.selected_history_item: Optional[int] = None

        # Backward compatibility - will be deprecated
        self._legacy_queue_items: List[Dict[str, Any]] = []

        # Stream panel reference for real-time execution monitoring
        self.stream_panel: Optional[Any] = None

        # Test result tracking for queue execution
        self.current_test_results: Dict[int, bool] = {}  # test_index -> success
        self.test_completion_events: Dict[int, threading.Event] = {}  # test_index -> completion event

        # Main window reference for execution time tracking
        self.main_window: Optional[Any] = None

        # Templates panel reference for clearing sent status
        self.templates_panel: Optional[Any] = None

        # Execution control
        self.is_executing: bool = False
        self.execution_delay: int = 2  # DEPRECATED: No longer used - delays removed for faster execution

        # Cancel functionality
        self.cancellation_requested: bool = False
        self.cancellation_event: threading.Event = threading.Event()
        
        # Create UI
        self._create_ui()

    def request_soft_cancellation(self) -> None:
        """
        Request soft cancellation of test execution.
        This method is called from Stream Panel when user clicks Cancel button.

        Soft cancellation behavior:
        - Current test is allowed to complete naturally
        - Remaining tests in queue are cancelled
        - No interruption of running scripts or device communication
        """
        self.logger.info("Soft cancellation requested - current test will complete, remaining tests cancelled")
        self.cancellation_requested = True
        self.cancellation_event.set()

        # Note: We do NOT signal completion events here for soft cancellation
        # This allows the current test to complete naturally

    @property
    def queue_items(self) -> List[Dict[str, Any]]:
        """
        Backward compatibility property that combines active queue and history.

        Returns:
            Combined list of active queue items and history items
        """
        return self.active_queue_items + self.history_items

    @queue_items.setter
    def queue_items(self, value: List[Dict[str, Any]]) -> None:
        """
        Backward compatibility setter for queue_items.
        Automatically separates items into active queue and history based on status.

        Args:
            value: List of queue items to set
        """
        self.active_queue_items = []
        self.history_items = []

        for item in value:
            if item.get("status") in ["Completed", "Failed"]:
                self.history_items.append(item)
            else:
                self.active_queue_items.append(item)

    def _move_to_history(self, item: Dict[str, Any]) -> None:
        """
        Move a completed test from active queue to history.

        Args:
            item: Queue item to move to history
        """
        if item in self.active_queue_items:
            # Add completion timestamp if not already set
            if not item.get("completed"):
                item["completed"] = datetime.now().isoformat()

            # Move to history (most recent first)
            self.history_items.insert(0, item)
            self.active_queue_items.remove(item)

            # Limit history size (configurable)
            max_history = 100  # TODO: Make this configurable
            if len(self.history_items) > max_history:
                self.history_items = self.history_items[:max_history]

            self.logger.debug(f"Moved test '{item['name']}' to history")

    def _requeue_from_history(self, item: Dict[str, Any]) -> None:
        """
        Move a test from history back to active queue.

        Args:
            item: History item to requeue
        """
        if item in self.history_items:
            # Reset test status and timestamps for re-execution
            requeued_item = item.copy()
            requeued_item["status"] = "Pending"
            requeued_item["added"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            requeued_item["started"] = None
            requeued_item["completed"] = None
            requeued_item["execution_time"] = None
            requeued_item["error_message"] = None

            # Move to active queue
            self.active_queue_items.append(requeued_item)
            self.history_items.remove(item)

            self.logger.debug(f"Requeued test '{item['name']}' from history")

    def _create_ui(self) -> None:
        """Create the enhanced two-section UI components."""
        # Main layout with 2 columns - queue sections and actions
        self.columnconfigure(0, weight=1)  # Queue sections (takes most space)
        self.columnconfigure(1, weight=0, minsize=160)  # Actions with fixed minimum width
        self.rowconfigure(0, weight=1)     # Main content row (full height)

        # Create main PanedWindow for resizable sections
        self.main_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.main_paned.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Active Queue section (top) - 60% of space
        active_frame = ttk.LabelFrame(self.main_paned, text="🔄 Active Queue")
        self.main_paned.add(active_frame, weight=3)  # 60% weight
        
        # Create Active Queue TreeView (Hàng đợi hoạt động)
        active_columns = ("id", "name", "category", "status", "added")
        self.active_queue_tree = ttk.Treeview(active_frame, columns=active_columns, show="headings")

        # Define column headings for active queue
        self.active_queue_tree.heading("id", text="ID")
        self.active_queue_tree.heading("name", text="Test Name")
        self.active_queue_tree.heading("category", text="Category")
        self.active_queue_tree.heading("status", text="Status")
        self.active_queue_tree.heading("added", text="Added")

        # Define column widths for active queue
        self.active_queue_tree.column("id", width=80)
        self.active_queue_tree.column("name", width=200)
        self.active_queue_tree.column("category", width=100)
        self.active_queue_tree.column("status", width=100)
        self.active_queue_tree.column("added", width=150)

        # Add scrollbar for active queue
        active_scrollbar = ttk.Scrollbar(active_frame, orient=tk.VERTICAL, command=self.active_queue_tree.yview)
        self.active_queue_tree["yscrollcommand"] = active_scrollbar.set

        # Pack active queue widgets
        active_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.active_queue_tree.pack(fill=tk.BOTH, expand=True)

        # Bind selection event for active queue
        self.active_queue_tree.bind("<<TreeviewSelect>>", self._on_active_item_selected)

        # Test History section (bottom) - 40% of space
        history_frame = ttk.LabelFrame(self.main_paned, text="📊 Test History")
        self.main_paned.add(history_frame, weight=2)  # 40% weight

        # Create History TreeView (Lịch sử test)
        history_columns = ("name", "category", "status", "duration", "completed")
        self.history_tree = ttk.Treeview(history_frame, columns=history_columns, show="headings")

        # Define column headings for history
        self.history_tree.heading("name", text="Test Name")
        self.history_tree.heading("category", text="Category")
        self.history_tree.heading("status", text="Result")
        self.history_tree.heading("duration", text="Duration")
        self.history_tree.heading("completed", text="Completed")

        # Define column widths for history
        self.history_tree.column("name", width=200)
        self.history_tree.column("category", width=100)
        self.history_tree.column("status", width=100)
        self.history_tree.column("duration", width=80)
        self.history_tree.column("completed", width=150)

        # Add scrollbar for history
        history_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree["yscrollcommand"] = history_scrollbar.set

        # Pack history widgets
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.pack(fill=tk.BOTH, expand=True)

        # Bind selection event for history
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_item_selected)

        # Maintain backward compatibility reference
        self.queue_tree = self.active_queue_tree  # For legacy code

        # Bind focus events to handle layout refresh
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<Visibility>", self._on_visibility_change)
        
        # Actions frame with stable configuration
        actions_frame = ttk.LabelFrame(self, text="Actions")
        actions_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Ensure actions frame maintains its size
        actions_frame.grid_propagate(False)
        actions_frame.configure(width=150, height=400)
        
        # Action buttons
        ttk.Button(
            actions_frame,
            text="Execute Selected",
            command=self._execute_selected
        ).pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            actions_frame,
            text="Execute All",
            command=self._execute_all
        ).pack(fill=tk.X, padx=5, pady=5)

        # Separator for reordering buttons
        ttk.Separator(actions_frame, orient='horizontal').pack(fill=tk.X, padx=5, pady=5)

        # Reordering buttons
        self.move_up_button = ttk.Button(
            actions_frame,
            text="Move Up",
            command=self._move_up,
            state=tk.DISABLED
        )
        self.move_up_button.pack(fill=tk.X, padx=5, pady=2)

        self.move_down_button = ttk.Button(
            actions_frame,
            text="Move Down",
            command=self._move_down,
            state=tk.DISABLED
        )
        self.move_down_button.pack(fill=tk.X, padx=5, pady=2)

        # Separator for management buttons
        ttk.Separator(actions_frame, orient='horizontal').pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            actions_frame,
            text="Remove Selected",
            command=self._remove_selected
        ).pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            actions_frame,
            text="Clear Completed",
            command=self._manual_clear_completed
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            actions_frame,
            text="Clear Queue",
            command=self._clear_queue
        ).pack(fill=tk.X, padx=5, pady=5)
        
        # Configure focus events for layout refresh
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<Visibility>", self._on_visibility_change)

    def _on_focus_in(self, event: tk.Event) -> None:
        """Handle focus in event."""
        pass

    def _on_visibility_change(self, event: tk.Event) -> None:
        """Handle visibility change event."""
        pass

    def _refresh_active_queue_display(self) -> None:
        """Refresh the active queue treeview display."""
        try:
            # Clear current display
            for item in self.active_queue_tree.get_children():
                self.active_queue_tree.delete(item)

            # Add all active queue items
            for queue_item in self.active_queue_items:
                self.active_queue_tree.insert(
                    "",
                    tk.END,
                    values=(
                        queue_item["id"],
                        queue_item["name"],
                        queue_item["category"],
                        queue_item["status"],
                        queue_item["added"]
                    )
                )
        except Exception as e:
            self.logger.error(f"Error refreshing active queue display: {e}")

    def _refresh_history_display(self) -> None:
        """Refresh the history treeview display."""
        try:
            # Clear current display
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            # Add all history items (most recent first)
            for history_item in self.history_items:
                # Format duration
                duration_text = ""
                if history_item.get("execution_time"):
                    duration_text = f"{history_item['execution_time']:.1f}s"

                # Format status with emoji
                status_text = history_item["status"]
                if status_text == "Completed":
                    status_text = "✅ Pass"
                elif status_text == "Failed":
                    status_text = "❌ Fail"

                # Format completion time
                completed_text = history_item.get("completed", "")
                if completed_text:
                    try:
                        # Convert ISO format to readable format
                        dt = datetime.fromisoformat(completed_text.replace('Z', '+00:00'))
                        completed_text = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass  # Keep original format if parsing fails

                self.history_tree.insert(
                    "",
                    tk.END,
                    values=(
                        history_item["name"],
                        history_item["category"],
                        status_text,
                        duration_text,
                        completed_text
                    )
                )
        except Exception as e:
            self.logger.error(f"Error refreshing history display: {e}")

    def _refresh_all_displays(self) -> None:
        """Refresh both active queue and history displays."""
        self._refresh_active_queue_display()
        self._refresh_history_display()
    
    def add_to_queue(self, test_data: Dict[str, Any], category: str, name: str) -> None:
        """
        Add a test to the queue.
        
        Args:
            test_data: Test data to add
            category: Test category
            name: Test name
        """
        try:
            # Generate unique ID for queue item
            queue_id = str(uuid.uuid4())[:8]

            # Create enhanced queue item with new fields
            queue_item = {
                "id": queue_id,
                "name": name,
                "category": category,
                "status": "Pending",
                "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "started": None,           # When execution started (ISO format)
                "completed": None,         # When execution finished (ISO format)
                "execution_time": None,    # Duration in seconds
                "error_message": None,     # Error message for failed tests
                "test_data": test_data
            }
            
            # Add to active queue (new items are always active)
            self.active_queue_items.append(queue_item)
            
            # Add to active queue treeview
            self.active_queue_tree.insert(
                "",
                tk.END,
                values=(
                    queue_item["id"],
                    queue_item["name"],
                    queue_item["category"],
                    queue_item["status"],
                    queue_item["added"]
                )
            )

            # Update button states in case this is the first item
            self._update_button_states()

            self._update_status(f"Added test {name} to queue")
        except Exception as e:
            self.logger.error(f"Error adding test to queue: {e}")
            messagebox.showerror(
                "Queue Error",
                f"Could not add test to queue: {str(e)}"
            )
    
    def _on_active_item_selected(self, event: tk.Event) -> None:
        """
        Handle active queue item selection.

        Args:
            event: Selection event
        """
        selection = self.active_queue_tree.selection()
        if not selection:
            self.selected_item = None
            self.selected_history_item = None
            self._update_button_states()
            return

        # Clear history selection
        self.history_tree.selection_remove(self.history_tree.selection())
        self.selected_history_item = None

        # Get selected item
        item = selection[0]
        item_values = self.active_queue_tree.item(item, "values")

        # Find corresponding active queue item
        selected_id = item_values[0]
        for i, queue_item in enumerate(self.active_queue_items):
            if queue_item["id"] == selected_id:
                self.selected_item = i
                self._update_button_states()
                break

    def _on_history_item_selected(self, event: tk.Event) -> None:
        """
        Handle history item selection.

        Args:
            event: Selection event
        """
        selection = self.history_tree.selection()
        if not selection:
            self.selected_history_item = None
            return

        # Clear active queue selection
        self.active_queue_tree.selection_remove(self.active_queue_tree.selection())
        self.selected_item = None

        # Get selected item
        item = selection[0]
        item_values = self.history_tree.item(item, "values")

        # Find corresponding history item by name (since history doesn't have ID column)
        selected_name = item_values[0]  # name is first column in history
        for i, history_item in enumerate(self.history_items):
            if history_item["name"] == selected_name:
                self.selected_history_item = i
                break

    def _on_item_selected(self, event: tk.Event) -> None:
        """
        Legacy method for backward compatibility.
        Delegates to active queue selection.

        Args:
            event: Selection event
        """
        self._on_active_item_selected(event)
    
    def _show_item_details(self, item: Dict[str, Any]) -> None:
        """
        Show details of a queue item.

        Args:
            item: Queue item to show
        """
        # TODO: Implement details panel if needed
        # Currently Queue Panel doesn't have a details text widget
        pass
    
    def _check_if_affects_network(self, test_data: Dict[str, Any]) -> bool:
        """
        Check if a test affects network connectivity.

        Args:
            test_data: Test data to check

        Returns:
            True if test affects network, False otherwise
        """
        return affects_network_connectivity(test_data)
    
    def _execute_selected(self) -> None:
        """Execute the selected test."""
        if self.selected_item is None:
            messagebox.showinfo(
                "Queue",
                "Please select a test to execute"
            )
            return

        if not self.execute_callback:
            self._update_status("Test execution not implemented")
            messagebox.showinfo(
                "Queue",
                "Test execution will be implemented in a future version"
            )
            return

        # Check if already executing
        if self.is_executing:
            messagebox.showwarning(
                "Execution in Progress",
                "Test execution is already in progress. Please wait for it to complete."
            )
            return

        # Get selected item
        item = self.queue_items[self.selected_item]

        # Switch to Stream tab for execution monitoring
        if self.main_window and hasattr(self.main_window, '_switch_to_tab'):
            self.main_window._switch_to_tab("Stream")

        # Set executing flag and reset cancellation state
        self.is_executing = True
        self.cancellation_requested = False
        self.cancellation_event.clear()

        try:
            # FIRST: Validate connection BEFORE changing status to Running
            self.logger.info(f"Starting execution validation for test: {item['name']}")

            if self.main_window and hasattr(self.main_window, 'connection_manager'):
                connection_manager = self.main_window.connection_manager
                is_connected = connection_manager.is_connected()

                self.logger.info(f"Connection validation for test {item['name']}: connection_manager exists={connection_manager is not None}, is_connected={is_connected}")

                if hasattr(connection_manager, 'http_client') and connection_manager.http_client:
                    http_client = connection_manager.http_client
                    self.logger.info(f"HTTP client details: connected={getattr(http_client, 'connected', 'N/A')}, url={getattr(http_client, 'url', 'N/A')}")

                if not is_connected:
                    # Connection validation failed - set status to Failed immediately
                    self.logger.warning(f"Connection validation failed for test: {item['name']} - No HTTP connection")
                    item["status"] = "Failed"
                    self._update_item_in_tree(item)

                    # Clear execution flag
                    self.is_executing = False

                    # Update status message
                    error_msg = f"Test {item['name']} failed: No HTTP connection to device"
                    self._update_status(error_msg)

                    # Show error message to user
                    messagebox.showerror(
                        "Connection Error",
                        "Not connected to device. Please establish HTTP connection first."
                    )

                    # Move failed test to history after a brief delay
                    self.after(2000, self._auto_move_completed_tests)
                    return
                else:
                    self.logger.info(f"Connection validation passed for test: {item['name']}")
            else:
                self.logger.warning("Cannot validate connection - main window or connection manager not available")

            # Connection validated - now change status to Running and record start time
            self.logger.info(f"Connection validated - changing status to Running for test: {item['name']}")
            item["status"] = "Running"
            item["started"] = datetime.now().isoformat()  # Record start time
            self._update_item_in_tree(item)

            # Update status message
            self._update_status(f"Executing test: {item['name']}")

            # Update UI before execution
            self.update()

            # Set the current queue test index in main window for result tracking
            if self.main_window and hasattr(self.main_window, '_current_queue_test_index'):
                self.main_window._current_queue_test_index = self.selected_item
                self.logger.debug(f"Set current queue test index to: {self.selected_item}")

            # Check if test affects network
            affects_network = self._check_if_affects_network(item["test_data"])

            # Call execute callback with network flag
            # Note: The execute callback runs asynchronously and will update the test status
            # through the set_test_result method when execution completes
            self.execute_callback(item["test_data"], affects_network)

            # DO NOT immediately mark as completed - wait for actual execution to finish
            # The test status will be updated by set_test_result() when execution completes

        except Exception as e:
            self.logger.error(f"Error starting test execution: {e}")
            # Mark as failed if we can't even start execution
            item["status"] = "Failed"
            self._update_item_in_tree(item)
            self._update_status(f"Failed to start test: {item['name']} - {str(e)}")
            messagebox.showerror("Execution Error", f"Failed to start test execution: {str(e)}")
            messagebox.showerror(
                "Execution Error",
                f"An error occurred during test execution: {str(e)}"
            )

            # Update status to indicate error
            item["status"] = "Failed"
            self._update_item_in_tree(item)

            # Move failed test to history after a brief delay
            self.after(2000, self._auto_move_completed_tests)
        finally:
            # SOFT CANCELLATION: Single test execution is not affected by cancellation
            # Single tests always complete naturally and get proper status
            # Only queue execution respects soft cancellation between tests

            # Reset executing flag and cancellation state
            self.is_executing = False
            # Note: Do not reset cancellation_requested here for single tests
            # It should only be reset after queue execution completes
    
    def _execute_all(self) -> None:
        """Execute all tests in the active queue sequentially."""
        if not self.active_queue_items:
            messagebox.showinfo(
                "Queue",
                "Active queue is empty"
            )
            return

        if not self.execute_callback:
            self._update_status("Test execution not implemented")
            messagebox.showinfo(
                "Queue",
                "Test execution will be implemented in a future version"
            )
            return

        # Check if already executing
        if self.is_executing:
            messagebox.showwarning(
                "Execution in Progress",
                "Test execution is already in progress. Please wait for it to complete."
            )
            return

        # FIRST: Validate connection BEFORE starting execution
        self.logger.info("Starting connection validation for Execute All")

        if self.main_window and hasattr(self.main_window, 'connection_manager'):
            if not self.main_window.connection_manager.is_connected():
                # Connection validation failed - show error and abort
                self.logger.warning("Connection validation failed for Execute All - No HTTP connection")

                error_msg = "Execute All failed: No HTTP connection to device"
                self._update_status(error_msg)

                # Show error message to user
                messagebox.showerror(
                    "Connection Error",
                    "Not connected to device. Please establish HTTP connection first."
                )
                return
            else:
                self.logger.info("Connection validation passed for Execute All")
        else:
            self.logger.warning("Cannot validate connection - main window or connection manager not available")

        # Confirm execution
        confirm = messagebox.askyesno(
            "Execute All",
            f"Execute all {len(self.active_queue_items)} tests in the active queue?"
        )

        if not confirm:
            return

        # Switch to Stream tab for execution monitoring
        if self.main_window and hasattr(self.main_window, '_switch_to_tab'):
            self.main_window._switch_to_tab("Stream")

        # Start queue execution in background thread to prevent UI blocking
        execution_thread = threading.Thread(target=self._execute_all_background)
        execution_thread.daemon = True
        execution_thread.start()

    def _execute_all_background(self) -> None:
        """Execute all tests in the queue sequentially in background thread."""
        try:
            # Set executing flag
            self.is_executing = True

            # Reset cancellation state
            self.cancellation_requested = False
            self.cancellation_event.clear()

            # Clear previous test results and completion events
            self.current_test_results.clear()
            self.test_completion_events.clear()

            # Store the original queue size for accurate final summary calculation
            original_queue_size = len(self.active_queue_items)
            original_test_names = [item["name"] for item in self.active_queue_items]

            # Start queue execution tracking in stream panel (thread-safe)
            if self.stream_panel is not None:
                stream_panel = self.stream_panel  # Capture reference for type safety
                self.after(0, lambda: stream_panel.start_queue_execution(original_queue_size, original_test_names))

            # Execute tests sequentially
            for i, item in enumerate(self.active_queue_items):
                # Check for soft cancellation request before starting each test (not during)
                if self.cancellation_requested:
                    self.logger.info(f"Soft cancellation detected before test {i+1}: {item['name']} - marking remaining tests as cancelled")

                    # Mark all remaining tests as cancelled
                    for j in range(i, len(self.active_queue_items)):
                        remaining_item = self.active_queue_items[j]
                        remaining_item["status"] = "Cancelled"
                        self.after(0, lambda item=remaining_item: self._update_item_in_tree(item))

                    self.logger.info(f"Marked {len(self.active_queue_items) - i} remaining tests as cancelled")
                    break

                # Update status (thread-safe)
                item["status"] = "Running"
                self.after(0, lambda item=item: self._update_item_in_tree(item))

                # Update status message with progress information (thread-safe)
                self.after(0, lambda i=i, item=item: self._update_status(f"Executing test {i+1} of {original_queue_size}: {item['name']}"))

                # Update queue progress in stream panel (thread-safe)
                if self.stream_panel is not None:
                    stream_panel = self.stream_panel  # Capture reference for type safety
                    self.after(0, lambda i=i, item=item: stream_panel.update_queue_progress(i, item['name']))
                    # Start queue test stream (thread-safe)
                    self.after(0, lambda i=i, item=item: stream_panel.start_queue_test_stream(i, item['name'], item['test_data']))

                    # Set current test index in main window for execution time tracking (thread-safe)
                    if self.main_window and hasattr(self.main_window, '_current_queue_test_index'):
                        self.after(0, lambda i=i: setattr(self.main_window, '_current_queue_test_index', i))

                # Determine if test affects network
                affects_network = self._check_if_affects_network(item["test_data"])

                # OPTIMIZATION: Removed pre-execution delay - device is ready when it sends final result
                # Previous delay: 30s (network tests) / 20s (normal tests) - now removed for faster execution

                # Execute test with network flag using intelligent retry
                try:
                    # Create completion event for this test
                    completion_event = threading.Event()
                    self.test_completion_events[i] = completion_event

                    # Execute test (thread-safe) - retry logic is now handled by connection manager
                    if self.execute_callback is not None:
                        execute_callback = self.execute_callback  # Capture reference for type safety
                        test_data = item["test_data"].copy()  # Create copy to avoid closure issues
                        affects = affects_network
                        self.after(0, lambda td=test_data, af=affects: execute_callback(td, af))

                    # OPTIMIZATION: Removed 5-minute timeout - wait until device sends final result
                    # Device sending final result (PASS/FAIL) indicates it has completed processing and is stable
                    # Previous: completion_event.wait(timeout=300) with timeout handling - now removed
                    completion_event.wait()  # Wait indefinitely until test completes naturally

                    # SOFT CANCELLATION: Do NOT check cancellation during test execution
                    # Let the current test complete naturally and get proper result status
                    # Cancellation is only checked BETWEEN tests, not DURING tests

                    # Test completed, get the result
                    success = self.current_test_results.get(i, False)

                    # Update status based on actual test result (thread-safe)
                    if success:
                        item["status"] = "Completed"
                    else:
                        item["status"] = "Failed"
                    self.after(0, lambda item=item: self._update_item_in_tree(item))

                    # Mark test as completed in stream panel (thread-safe)
                    if self.stream_panel is not None:
                        stream_panel = self.stream_panel  # Capture reference for type safety
                        self.after(0, lambda i=i, item=item, success=success: stream_panel.complete_queue_test(i, item['name'], success))
                        # Note: end_queue_test_stream will be called from main_window after execution completes

                    # OPTIMIZATION: Removed post-execution delay - proceed immediately to next test
                    # Previous delay: 40s (network tests) / 25s (normal tests) - now removed for faster execution
                    # Device stability is ensured by natural request-response cycle completion
                        
                except Exception as e:
                    self.logger.error(f"Error executing test {item['name']}: {e}")
                    item["status"] = "Failed"
                    self.after(0, lambda item=item: self._update_item_in_tree(item))

                    # Mark test as failed in stream panel (thread-safe)
                    if self.stream_panel is not None:
                        stream_panel = self.stream_panel  # Capture reference for type safety
                        self.after(0, lambda i=i, item=item: stream_panel.complete_queue_test(i, item['name'], False))
                        # Note: end_queue_test_stream will be called from main_window after execution completes

                    # Show error but continue with next test (thread-safe)
                    self.after(0, lambda item=item, e=e: messagebox.showwarning(
                        "Test Execution Warning",
                        f"Test '{item['name']}' failed: {str(e)}\n\nContinuing with next test..."
                    ))

                    # Keep recovery delay after failure - this is necessary for error recovery
                    self.after(0, lambda: self._update_status("Waiting 60s for device to recover after test failure..."))
                    self._wait_with_ui_updates_background(60)
            
            # Update status based on whether execution was soft cancelled or completed
            if self.cancellation_requested:
                # Count actual results for status message
                executed_count = len(self.current_test_results)
                cancelled_count = sum(1 for item in self.active_queue_items if item.get("status") == "Cancelled")
                self.after(0, lambda: self._update_status(f"Queue execution soft cancelled - {executed_count} completed, {cancelled_count} cancelled"))
            else:
                self.after(0, lambda: self._update_status(f"Executed {original_queue_size} tests"))

            # End queue execution tracking in stream panel (thread-safe)
            if self.stream_panel is not None:
                # Count actual successes, failures, and cancelled tests
                successful_count = sum(1 for success in self.current_test_results.values() if success)
                executed_count = len(self.current_test_results)  # Tests that actually ran and completed
                failed_count = executed_count - successful_count  # Tests that ran but failed

                # Count cancelled tests by checking item status in queue
                cancelled_count = 0
                for item in self.active_queue_items:
                    if item.get("status") == "Cancelled":
                        cancelled_count += 1

                total_count = original_queue_size  # Use original queue size for accurate count

                # Overall success only if all tests passed and none were cancelled or failed
                overall_success = successful_count == total_count and failed_count == 0 and cancelled_count == 0

                # Create appropriate final message based on execution results
                if self.cancellation_requested and cancelled_count > 0:
                    # Soft cancellation occurred - some tests completed, some cancelled
                    final_message = f"Queue execution soft cancelled: {executed_count}/{total_count} completed ({successful_count} successful, {failed_count} failed), {cancelled_count}/{total_count} cancelled"
                elif self.cancellation_requested and cancelled_count == 0:
                    # Cancellation requested but all tests had already completed
                    final_message = f"Queue execution completed before cancellation: {successful_count}/{total_count} successful, {failed_count}/{total_count} failed"
                else:
                    # Normal completion without cancellation
                    if failed_count > 0:
                        final_message = f"Queue execution completed: {successful_count}/{total_count} tests successful, {failed_count}/{total_count} tests failed"
                    else:
                        final_message = f"Queue execution completed: {successful_count}/{total_count} tests successful"

                # Log the final counts for debugging
                self.logger.info(f"Final execution summary: {executed_count} executed ({successful_count} successful, {failed_count} failed), {cancelled_count} cancelled, {total_count} total")

                stream_panel = self.stream_panel  # Capture reference for type safety
                self.after(0, lambda success=overall_success, msg=final_message: stream_panel.end_queue_execution(success, msg))

            # Automatically move completed tests to history (thread-safe)
            self.after(0, self._auto_move_completed_tests)

        except Exception as e:
            self.logger.error(f"Error during test execution: {e}")

            # End queue execution with error in stream panel (thread-safe)
            if self.stream_panel is not None:
                stream_panel = self.stream_panel  # Capture reference for type safety
                self.after(0, lambda e=e: stream_panel.end_queue_execution(False, f"Queue execution failed: {str(e)}"))

            # Show error message (thread-safe)
            self.after(0, lambda e=e: messagebox.showerror(
                "Execution Error",
                f"An error occurred during test execution: {str(e)}"
            ))
        finally:
            # Reset executing flag
            self.is_executing = False

            # Reset cancellation state after queue execution completes
            self.cancellation_requested = False
            self.cancellation_event.clear()
            self.current_test_results.clear()
            self.test_completion_events.clear()

            self.logger.info("Queue execution state reset - ready for next execution")

            # Reset current queue test index in main window (thread-safe)
            if self.main_window and hasattr(self.main_window, '_current_queue_test_index'):
                self.after(0, lambda: setattr(self.main_window, '_current_queue_test_index', -1))
    
    def _wait_with_ui_updates(self, seconds: int) -> None:
        """
        Wait while keeping UI responsive.

        Args:
            seconds: Number of seconds to wait
        """
        start_time = time.time()
        while time.time() - start_time < seconds:
            self.update()
            time.sleep(0.1)  # Short sleep to prevent CPU hogging

    def _wait_with_ui_updates_background(self, seconds: int) -> None:
        """
        Wait in background thread without blocking UI.

        Args:
            seconds: Number of seconds to wait
        """
        time.sleep(seconds)
    
    def _remove_selected(self) -> None:
        """Remove the selected test from the queue."""
        if self.selected_item is None:
            messagebox.showinfo(
                "Queue",
                "Please select a test to remove"
            )
            return
        
        # Get selected item
        item = self.active_queue_items[self.selected_item]

        # Remove from queue
        self.active_queue_items.pop(self.selected_item)

        # Remove from treeview
        selection = self.active_queue_tree.selection()
        if selection:
            self.active_queue_tree.delete(selection[0])
        
        # Reset selected item
        self.selected_item = None

        # Update button states
        self._update_button_states()

        self._update_status(f"Removed test {item['name']} from queue")

        # Notify templates panel to clear sent status for manually removed test
        self._notify_templates_panel_for_removed_tests([item])
    
    def _clear_queue(self) -> None:
        """Clear the queue."""
        if not self.queue_items:
            messagebox.showinfo(
                "Queue",
                "Queue is already empty"
            )
            return
        
        # Confirm clear
        confirm = messagebox.askyesno(
            "Clear Queue",
            f"Clear all {len(self.queue_items)} tests from the queue?"
        )
        
        if not confirm:
            return
        
        # Store items before clearing for notification
        removed_items = self.queue_items.copy()

        # Clear queue
        self.queue_items = []

        # Clear treeview
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)

        # Reset selected item
        self.selected_item = None

        # Update button states
        self._update_button_states()

        self._update_status("Queue cleared")

        # Notify templates panel to clear sent status for all removed tests
        if removed_items:
            self._notify_templates_panel_for_removed_tests(removed_items)

    def _move_up(self) -> None:
        """Move the selected test case up in the queue."""
        if self.selected_item is None or self.selected_item == 0:
            return

        # Check if execution is in progress
        if self.is_executing:
            messagebox.showwarning(
                "Execution in Progress",
                "Cannot reorder queue while test execution is in progress."
            )
            return

        # Get current item
        current_item = self.queue_items[self.selected_item]

        # Swap with previous item
        self.queue_items[self.selected_item], self.queue_items[self.selected_item - 1] = \
            self.queue_items[self.selected_item - 1], self.queue_items[self.selected_item]

        # Update selected index
        self.selected_item -= 1

        # Refresh the tree view
        self._refresh_queue_tree()

        # Reselect the moved item
        self._select_item_by_index(self.selected_item)

        # Update button states
        self._update_button_states()

        self._update_status(f"Moved test '{current_item['name']}' up in queue")

    def _move_down(self) -> None:
        """Move the selected test case down in the queue."""
        if self.selected_item is None or self.selected_item >= len(self.queue_items) - 1:
            return

        # Check if execution is in progress
        if self.is_executing:
            messagebox.showwarning(
                "Execution in Progress",
                "Cannot reorder queue while test execution is in progress."
            )
            return

        # Get current item
        current_item = self.queue_items[self.selected_item]

        # Swap with next item
        self.queue_items[self.selected_item], self.queue_items[self.selected_item + 1] = \
            self.queue_items[self.selected_item + 1], self.queue_items[self.selected_item]

        # Update selected index
        self.selected_item += 1

        # Refresh the tree view
        self._refresh_queue_tree()

        # Reselect the moved item
        self._select_item_by_index(self.selected_item)

        # Update button states
        self._update_button_states()

        self._update_status(f"Moved test '{current_item['name']}' down in queue")

    def _update_button_states(self) -> None:
        """Update the state of move buttons based on current selection."""
        if self.selected_item is None or len(self.queue_items) <= 1:
            # No selection or only one item - disable both buttons
            self.move_up_button.config(state=tk.DISABLED)
            self.move_down_button.config(state=tk.DISABLED)
        else:
            # Enable/disable based on position
            self.move_up_button.config(
                state=tk.NORMAL if self.selected_item > 0 else tk.DISABLED
            )
            self.move_down_button.config(
                state=tk.NORMAL if self.selected_item < len(self.queue_items) - 1 else tk.DISABLED
            )

    def _refresh_queue_tree(self) -> None:
        """Refresh the entire queue tree view to reflect current order."""
        # Clear current tree
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)

        # Re-add all items in current order
        for queue_item in self.queue_items:
            self.queue_tree.insert(
                "",
                tk.END,
                values=(
                    queue_item["id"],
                    queue_item["name"],
                    queue_item["category"],
                    queue_item["status"],
                    queue_item["added"]
                )
            )

    def _select_item_by_index(self, index: int) -> None:
        """Select an item in the tree by its index in the queue."""
        if 0 <= index < len(self.queue_items):
            # Get all tree items
            tree_items = self.queue_tree.get_children()
            if index < len(tree_items):
                # Select the item at the specified index
                self.queue_tree.selection_set(tree_items[index])
                self.queue_tree.focus(tree_items[index])
                # Ensure the item is visible
                self.queue_tree.see(tree_items[index])

    def _update_item_in_tree(self, item: Dict[str, Any]) -> None:
        """
        Update an item in the active queue treeview.

        Args:
            item: Queue item to update
        """
        # Find item in active queue treeview
        for tree_item in self.active_queue_tree.get_children():
            item_values = self.active_queue_tree.item(tree_item, "values")
            if item_values[0] == item["id"]:
                # Update values
                self.active_queue_tree.item(
                    tree_item,
                    values=(
                        item["id"],
                        item["name"],
                        item["category"],
                        item["status"],
                        item["added"]
                    )
                )
                break
    
    def set_test_result(self, test_index: int, success: bool) -> None:
        """
        Set the result of a test execution for queue tracking.
        This is called from main_window after test completion.

        Args:
            test_index: Index of the test in queue (0-based)
            success: Whether the test completed successfully
        """
        # Check if cancellation was requested - if so, don't update results
        if self.cancellation_requested:
            self.logger.debug(f"Ignoring test result for index {test_index} due to cancellation request")
            # Still signal completion to unblock waiting threads
            if test_index in self.test_completion_events:
                self.test_completion_events[test_index].set()
            return

        self.current_test_results[test_index] = success
        self.logger.debug(f"Queue test {test_index} result set to: {'SUCCESS' if success else 'FAILED'}")

        # Update the actual queue item status with timing information
        if 0 <= test_index < len(self.active_queue_items):
            item = self.active_queue_items[test_index]

            # Calculate execution time if start time was recorded
            execution_time = None
            if item.get("started"):
                try:
                    start_time = datetime.fromisoformat(item["started"])
                    end_time = datetime.now()
                    execution_time = (end_time - start_time).total_seconds()
                    item["execution_time"] = execution_time
                except Exception as e:
                    self.logger.warning(f"Could not calculate execution time: {e}")

            # Update completion information
            item["status"] = "Completed" if success else "Failed"
            item["completed"] = datetime.now().isoformat()

            # Store error message for failed tests (if available)
            if not success:
                # TODO: Get actual error message from execution context
                item["error_message"] = "Test execution failed"

            # Update display
            self._update_item_in_tree(item)

            # Update status message with execution time
            status_text = "completed successfully" if success else "failed"
            time_text = f" in {execution_time:.1f}s" if execution_time else ""
            self._update_status(f"Test {item['name']} {status_text}{time_text}")

            # Clear execution flag
            self.is_executing = False

            # Move completed test to history after a brief delay
            self.after(2000, self._auto_move_completed_tests)
        else:
            self.logger.error(f"Invalid test index for result update: {test_index}")

        # Signal test completion
        if test_index in self.test_completion_events:
            self.test_completion_events[test_index].set()

    def _auto_move_completed_tests(self) -> None:
        """
        Automatically move completed and failed tests from active queue to history.
        This keeps the active queue clean while preserving test execution history.
        """
        try:
            # Check if auto-cleanup is enabled in configuration
            config = get_config()
            if not config.test.auto_cleanup:
                self.logger.debug("Auto-move disabled in configuration")
                return

            # Find completed, failed, and cancelled tests in active queue
            completed_items = []
            remaining_items = []

            for item in self.active_queue_items:
                if item["status"] in ["Completed", "Failed", "Cancelled"]:
                    completed_items.append(item)
                else:
                    remaining_items.append(item)

            if not completed_items:
                self.logger.debug("No completed tests to move from active queue")
                return

            # Move completed items to history
            for item in completed_items:
                # Ensure completion timestamp is set
                if not item.get("completed"):
                    item["completed"] = datetime.now().isoformat()

                # Move to history (most recent first)
                self.history_items.insert(0, item)

                # Remove from active queue treeview
                for tree_item in self.active_queue_tree.get_children():
                    tree_values = self.active_queue_tree.item(tree_item)["values"]
                    if (len(tree_values) >= 5 and
                        tree_values[0] == item["id"] and
                        tree_values[1] == item["name"]):
                        self.active_queue_tree.delete(tree_item)
                        break

            # Update active queue items list
            self.active_queue_items = remaining_items

            # Refresh history display to show new items
            self._refresh_history_display()

            # Limit history size (configurable)
            max_history = 100  # TODO: Make this configurable
            if len(self.history_items) > max_history:
                self.history_items = self.history_items[:max_history]

            # Notify templates panel to clear sent status for completed tests
            if self.templates_panel and hasattr(self.templates_panel, 'clear_sent_status_for_completed_tests'):
                try:
                    # Create list of test identifiers for templates panel
                    completed_test_identifiers = []
                    for item in completed_items:
                        # Create identifier that matches templates panel format: "name|category"
                        test_identifier = f"{item['name']}|{item.get('category', 'Unknown')}"
                        completed_test_identifiers.append(test_identifier)

                    # Clear sent status in templates panel
                    self.templates_panel.clear_sent_status_for_completed_tests(completed_test_identifiers)
                    self.logger.info(f"Notified templates panel to clear sent status for {len(completed_test_identifiers)} completed test(s)")
                except Exception as e:
                    self.logger.error(f"Error notifying templates panel about completed tests: {e}")

            # Log the move action
            completed_count = len([item for item in completed_items if item["status"] == "Completed"])
            failed_count = len([item for item in completed_items if item["status"] == "Failed"])
            cancelled_count = len([item for item in completed_items if item["status"] == "Cancelled"])

            # Create appropriate message based on what types of tests were moved
            message_parts = []
            if completed_count > 0:
                message_parts.append(f"{completed_count} completed")
            if failed_count > 0:
                message_parts.append(f"{failed_count} failed")
            if cancelled_count > 0:
                message_parts.append(f"{cancelled_count} cancelled")

            if message_parts:
                move_message = f"Moved {' and '.join(message_parts)} test(s) to history"
            else:
                move_message = f"Moved {len(completed_items)} test(s) to history"

            self.logger.info(move_message)
            self._update_status(move_message)

            # Show brief user feedback
            if len(completed_items) > 0:
                # Use a brief status message instead of a popup to avoid interrupting workflow
                feedback_message = f"Tests moved to history: {len(completed_items)} test(s) completed"
                self._update_status(feedback_message)

                # Clear the feedback message after a few seconds
                self.after(3000, lambda: self._update_status("Queue execution completed"))

        except Exception as e:
            self.logger.error(f"Error during auto-cleanup of completed tests: {e}")
            # Don't show error to user as this is a background operation

    def _manual_clear_completed(self) -> None:
        """
        Manually move completed, failed, and cancelled tests from active queue to history.
        This provides user control over queue cleanup.
        """
        try:
            # Find completed, failed, and cancelled tests in active queue
            completed_items = []
            for item in self.active_queue_items:
                if item["status"] in ["Completed", "Failed", "Cancelled"]:
                    completed_items.append(item)

            if not completed_items:
                messagebox.showinfo(
                    "Move Completed Tests",
                    "No completed, failed, or cancelled tests to move from the active queue."
                )
                return

            # Ask for confirmation
            completed_count = len([item for item in completed_items if item["status"] == "Completed"])
            failed_count = len([item for item in completed_items if item["status"] == "Failed"])
            cancelled_count = len([item for item in completed_items if item["status"] == "Cancelled"])

            # Create appropriate confirmation message
            message_parts = []
            if completed_count > 0:
                message_parts.append(f"{completed_count} completed")
            if failed_count > 0:
                message_parts.append(f"{failed_count} failed")
            if cancelled_count > 0:
                message_parts.append(f"{cancelled_count} cancelled")

            if message_parts:
                message = f"Move {' and '.join(message_parts)} test(s) to history?"
            else:
                message = f"Move {len(completed_items)} test(s) to history?"

            if not messagebox.askyesno("Move Completed Tests", message):
                return

            # Perform the move to history
            self._auto_move_completed_tests()

        except Exception as e:
            self.logger.error(f"Error during manual cleanup of completed tests: {e}")
            messagebox.showerror(
                "Clear Error",
                f"An error occurred while clearing completed tests: {str(e)}"
            )

    def _on_focus_in(self, event) -> None:
        """Handle focus in event to refresh layout."""
        try:
            # Force layout update when window gains focus
            self.update_idletasks()
        except Exception as e:
            self.logger.debug(f"Error handling focus in event: {e}")

    def _on_visibility_change(self, event) -> None:
        """Handle visibility change event to refresh layout."""
        try:
            # Force layout update when visibility changes
            self.update_idletasks()
        except Exception as e:
            self.logger.debug(f"Error handling visibility change event: {e}")

    def _update_status(self, message: str) -> None:
        """
        Update status message.

        Args:
            message: Status message
        """
        if self.status_callback:
            self.status_callback(message)
        else:
            self.logger.info(message)
            
    def get_queue(self) -> List[Dict[str, Any]]:
        """
        Get the current queue items.

        Returns:
            List of test data in the queue
        """
        return [item["test_data"] for item in self.queue_items]

    def _notify_templates_panel_for_removed_tests(self, removed_items: List[Dict[str, Any]]) -> None:
        """
        Notify templates panel to clear sent status for manually removed tests.

        Args:
            removed_items: List of test items that were removed from queue
        """
        if not self.templates_panel or not hasattr(self.templates_panel, 'clear_sent_status_for_completed_tests'):
            return

        try:
            # Create list of test identifiers for templates panel
            removed_test_identifiers = []
            for item in removed_items:
                # Create identifier that matches templates panel format: "name|category"
                test_identifier = f"{item['name']}|{item.get('category', 'Unknown')}"
                removed_test_identifiers.append(test_identifier)
                self.logger.debug(f"Creating test identifier for removal: '{test_identifier}' from item: {item}")

            if removed_test_identifiers:
                # Clear sent status in templates panel
                self.templates_panel.clear_sent_status_for_completed_tests(removed_test_identifiers)
                self.logger.info(f"Notified templates panel to clear sent status for {len(removed_test_identifiers)} manually removed test(s)")
                self._update_status(f"Cleared sent status for {len(removed_test_identifiers)} removed test(s) - can now re-add to queue")

        except Exception as e:
            self.logger.error(f"Error notifying templates panel about removed tests: {e}")