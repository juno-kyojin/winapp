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
        
        # Queue data
        self.queue_items: List[Dict[str, Any]] = []
        self.selected_item: Optional[int] = None

        # Stream panel reference for real-time execution monitoring
        self.stream_panel: Optional[Any] = None

        # Test result tracking for queue execution
        self.current_test_results: Dict[int, bool] = {}  # test_index -> success
        self.test_completion_events: Dict[int, threading.Event] = {}  # test_index -> completion event

        # Main window reference for execution time tracking
        self.main_window: Optional[Any] = None
        
        # Execution control
        self.is_executing: bool = False
        self.execution_delay: int = 2  # Delay in seconds between test executions
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Main layout with 2 columns
        self.columnconfigure(0, weight=3)  # Queue list
        self.columnconfigure(1, weight=1)  # Actions
        
        # Queue list frame
        list_frame = ttk.LabelFrame(self, text="Test Queue")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create treeview for queue items
        columns = ("id", "name", "category", "status", "added")
        self.queue_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Define column headings
        self.queue_tree.heading("id", text="ID")
        self.queue_tree.heading("name", text="Test Name")
        self.queue_tree.heading("category", text="Category")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.heading("added", text="Added")
        
        # Define column widths
        self.queue_tree.column("id", width=80)
        self.queue_tree.column("name", width=200)
        self.queue_tree.column("category", width=100)
        self.queue_tree.column("status", width=100)
        self.queue_tree.column("added", width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        self.queue_tree["yscrollcommand"] = scrollbar.set
        
        # Pack widgets
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.queue_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind selection event
        self.queue_tree.bind("<<TreeviewSelect>>", self._on_item_selected)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(self, text="Actions")
        actions_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
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
            text="Clear Queue",
            command=self._clear_queue
        ).pack(fill=tk.X, padx=5, pady=5)
        
        # Details frame
        details_frame = ttk.LabelFrame(self, text="Test Details")
        details_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Text widget for details
        self.details_text = tk.Text(details_frame, height=10, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.details_text.config(state=tk.DISABLED)
        
        # Add scrollbar for details
        details_scrollbar = ttk.Scrollbar(self.details_text, orient=tk.VERTICAL, command=self.details_text.yview)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text["yscrollcommand"] = details_scrollbar.set
        
        # Configure row weights for resizing
        self.rowconfigure(0, weight=3)  # Queue list and actions
        self.rowconfigure(1, weight=1)  # Details
    
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
            
            # Create queue item
            queue_item = {
                "id": queue_id,
                "name": name,
                "category": category,
                "status": "Pending",
                "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "test_data": test_data
            }
            
            # Add to queue
            self.queue_items.append(queue_item)
            
            # Add to treeview
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

            # Update button states in case this is the first item
            self._update_button_states()

            self._update_status(f"Added test {name} to queue")
        except Exception as e:
            self.logger.error(f"Error adding test to queue: {e}")
            messagebox.showerror(
                "Queue Error",
                f"Could not add test to queue: {str(e)}"
            )
    
    def _on_item_selected(self, event: tk.Event) -> None:
        """
        Handle item selection.

        Args:
            event: Selection event
        """
        selection = self.queue_tree.selection()
        if not selection:
            self.selected_item = None
            self._update_button_states()
            return

        # Get selected item
        item = selection[0]
        item_values = self.queue_tree.item(item, "values")

        # Find corresponding queue item
        selected_id = item_values[0]
        for i, queue_item in enumerate(self.queue_items):
            if queue_item["id"] == selected_id:
                self.selected_item = i
                self._show_item_details(queue_item)
                self._update_button_states()
                break
    
    def _show_item_details(self, item: Dict[str, Any]) -> None:
        """
        Show details of a queue item.
        
        Args:
            item: Queue item to show
        """
        # Enable text widget for editing
        self.details_text.config(state=tk.NORMAL)
        
        # Clear previous content
        self.details_text.delete(1.0, tk.END)
        
        # Add item details
        self.details_text.insert(tk.END, f"ID: {item['id']}\n")
        self.details_text.insert(tk.END, f"Name: {item['name']}\n")
        self.details_text.insert(tk.END, f"Category: {item['category']}\n")
        self.details_text.insert(tk.END, f"Status: {item['status']}\n")
        self.details_text.insert(tk.END, f"Added: {item['added']}\n\n")
        
        # Add test data as formatted JSON
        self.details_text.insert(tk.END, "Test Data:\n")
        try:
            formatted_data = json.dumps(item["test_data"], indent=2)
            self.details_text.insert(tk.END, formatted_data)
        except Exception:
            self.details_text.insert(tk.END, str(item["test_data"]))
        
        # Disable text widget
        self.details_text.config(state=tk.DISABLED)
    
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
        
        # Set executing flag
        self.is_executing = True
        
        try:
            # Update status
            item["status"] = "Running"
            self._update_item_in_tree(item)
            
            # Update status message
            self._update_status(f"Executing test: {item['name']}")
            
            # Update UI before execution
            self.update()
            
            # Check if test affects network
            affects_network = self._check_if_affects_network(item["test_data"])
            
            # Call execute callback with network flag
            self.execute_callback(item["test_data"], affects_network)
            
            # Update status
            item["status"] = "Completed"
            self._update_item_in_tree(item)
            
            self._update_status(f"Executed test {item['name']}")
        except Exception as e:
            self.logger.error(f"Error executing test: {e}")
            messagebox.showerror(
                "Execution Error",
                f"An error occurred during test execution: {str(e)}"
            )
            
            # Update status to indicate error
            item["status"] = "Failed"
            self._update_item_in_tree(item)
        finally:
            # Reset executing flag
            self.is_executing = False
    
    def _execute_all(self) -> None:
        """Execute all tests in the queue sequentially."""
        if not self.queue_items:
            messagebox.showinfo(
                "Queue",
                "Queue is empty"
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

        # Confirm execution
        confirm = messagebox.askyesno(
            "Execute All",
            f"Execute all {len(self.queue_items)} tests in the queue?"
        )

        if not confirm:
            return

        # Start queue execution in background thread to prevent UI blocking
        execution_thread = threading.Thread(target=self._execute_all_background)
        execution_thread.daemon = True
        execution_thread.start()

    def _execute_all_background(self) -> None:
        """Execute all tests in the queue sequentially in background thread."""
        try:
            # Set executing flag
            self.is_executing = True

            # Clear previous test results and completion events
            self.current_test_results.clear()
            self.test_completion_events.clear()

            # Start queue execution tracking in stream panel (thread-safe)
            if self.stream_panel is not None:
                test_names = [item["name"] for item in self.queue_items]
                stream_panel = self.stream_panel  # Capture reference for type safety
                self.after(0, lambda: stream_panel.start_queue_execution(len(self.queue_items), test_names))

            # Execute tests sequentially
            for i, item in enumerate(self.queue_items):
                # Update status (thread-safe)
                item["status"] = "Running"
                self.after(0, lambda item=item: self._update_item_in_tree(item))

                # Update status message with progress information (thread-safe)
                self.after(0, lambda i=i, item=item: self._update_status(f"Executing test {i+1} of {len(self.queue_items)}: {item['name']}"))

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

                # Add pre-execution delay for stability
                if i > 0:  # Don't delay before first test
                    delay_seconds = 30 if affects_network else 20  # Tăng delay để server có thời gian recover
                    self.after(0, lambda delay=delay_seconds: self._update_status(f"Waiting {delay}s before executing next test..."))
                    self._wait_with_ui_updates_background(delay_seconds)

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

                    # Wait for test completion (with timeout)
                    if completion_event.wait(timeout=300):  # 5 minute timeout
                        # Test completed, get the result
                        success = self.current_test_results.get(i, False)
                    else:
                        # Timeout occurred
                        self.logger.error(f"Test {item['name']} timed out after 5 minutes")
                        success = False

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

                    # Add post-execution delay to ensure device is ready for next test
                    if i < len(self.queue_items) - 1:  # Don't delay after last test
                        post_delay = 40 if affects_network else 25  # Tăng delay để server có thời gian recover
                        self.after(0, lambda delay=post_delay: self._update_status(f"Test completed. Waiting {delay}s for device to stabilize..."))
                        self._wait_with_ui_updates_background(post_delay)
                        
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

                    # Add longer recovery delay after failure (thread-safe)
                    self.after(0, lambda: self._update_status("Waiting 60s for device to recover after test failure..."))
                    self._wait_with_ui_updates_background(60)
            
            # Update status (thread-safe)
            self.after(0, lambda: self._update_status(f"Executed {len(self.queue_items)} tests"))

            # Add small delay to ensure last test's end_queue_test_stream completes before ending queue
            self._wait_with_ui_updates_background(1)

            # End queue execution tracking in stream panel (thread-safe)
            if self.stream_panel is not None:
                # Count actual successes and failures based on test results
                successful_count = sum(1 for success in self.current_test_results.values() if success)
                failed_count = len(self.current_test_results) - successful_count
                total_count = len(self.queue_items)

                # Overall success only if all tests passed
                overall_success = successful_count == total_count and failed_count == 0

                if failed_count > 0:
                    final_message = f"Queue execution completed: {successful_count}/{total_count} tests successful, {failed_count}/{total_count} tests failed"
                else:
                    final_message = f"Queue execution completed: {successful_count}/{total_count} tests successful"

                stream_panel = self.stream_panel  # Capture reference for type safety
                self.after(0, lambda success=overall_success, msg=final_message: stream_panel.end_queue_execution(success, msg))

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
        item = self.queue_items[self.selected_item]
        
        # Remove from queue
        self.queue_items.pop(self.selected_item)
        
        # Remove from treeview
        selection = self.queue_tree.selection()
        if selection:
            self.queue_tree.delete(selection[0])
        
        # Reset selected item
        self.selected_item = None

        # Clear details
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state=tk.DISABLED)

        # Update button states
        self._update_button_states()

        self._update_status(f"Removed test {item['name']} from queue")
    
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
        
        # Clear queue
        self.queue_items = []
        
        # Clear treeview
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # Reset selected item
        self.selected_item = None

        # Clear details
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state=tk.DISABLED)

        # Update button states
        self._update_button_states()

        self._update_status("Queue cleared")

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
        Update an item in the treeview.
        
        Args:
            item: Queue item to update
        """
        # Find item in treeview
        for tree_item in self.queue_tree.get_children():
            item_values = self.queue_tree.item(tree_item, "values")
            if item_values[0] == item["id"]:
                # Update values
                self.queue_tree.item(
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
        self.current_test_results[test_index] = success
        self.logger.debug(f"Queue test {test_index} result set to: {'SUCCESS' if success else 'FAILED'}")

        # Signal test completion
        if test_index in self.test_completion_events:
            self.test_completion_events[test_index].set()

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