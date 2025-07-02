#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stream Panel for Test Case Manager v3.0

This panel displays real-time test execution flow from PC to device,
showing the complete test lifecycle and communication status.

Author: juno-kyojin
Created: 2025-07-02
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import threading
import time
import json

from src.utils.logger import get_logger


class StreamPanel(ttk.Frame):
    """
    Panel for displaying real-time test execution stream.
    
    Shows the flow of test execution from PC to device:
    1. Test preparation and validation
    2. Sending test to device
    3. Device processing status
    4. Result reception and processing
    """
    
    def __init__(self, parent: tk.Widget,
                 status_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Initialize the stream panel.
        
        Args:
            parent: Parent widget
            status_callback: Callback for status updates
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.status_callback = status_callback
        
        # Stream data
        self.current_test: Optional[Dict[str, Any]] = None
        self.stream_entries: List[Dict[str, Any]] = []
        self.is_streaming: bool = False

        # Queue execution tracking
        self.queue_execution: Optional[Dict[str, Any]] = None
        self.is_queue_executing: bool = False

        # Queue test execution time tracking
        self.queue_test_execution_times: Dict[int, float] = {}
        
        # Create UI
        self._create_ui()
        
        self.logger.info("Stream Panel initialized")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Configure grid weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Current Test Info Frame
        self._create_current_test_frame()
        
        # Stream Display Frame
        self._create_stream_frame()
        
        # Control Buttons Frame
        self._create_controls_frame()
    
    def _create_current_test_frame(self) -> None:
        """Create frame showing current test information."""
        current_frame = ttk.LabelFrame(self, text="Current Test Execution")
        current_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        current_frame.columnconfigure(1, weight=1)

        # Queue execution info (only shown during batch execution)
        self.queue_info_frame = ttk.Frame(current_frame)
        self.queue_info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        self.queue_info_frame.columnconfigure(1, weight=1)

        ttk.Label(self.queue_info_frame, text="Queue:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.queue_status_var = tk.StringVar(value="")
        self.queue_status_label = ttk.Label(self.queue_info_frame, textvariable=self.queue_status_var,
                                           font=("TkDefaultFont", 9, "bold"), foreground="blue")
        self.queue_status_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(self.queue_info_frame, text="Progress:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.queue_progress_var = tk.StringVar(value="")
        self.queue_progress_label = ttk.Label(self.queue_info_frame, textvariable=self.queue_progress_var,
                                             font=("TkDefaultFont", 9, "bold"), foreground="green")
        self.queue_progress_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # Hide queue info initially
        self.queue_info_frame.grid_remove()

        # Test Name
        ttk.Label(current_frame, text="Test:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.current_test_var = tk.StringVar(value="No test running")
        ttk.Label(current_frame, textvariable=self.current_test_var,
                 font=("TkDefaultFont", 9, "bold")).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # Status
        ttk.Label(current_frame, text="Status:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.current_status_var = tk.StringVar(value="Idle")
        self.status_label = ttk.Label(current_frame, textvariable=self.current_status_var)
        self.status_label.grid(row=3, column=1, sticky="w", padx=5, pady=2)

        # Progress
        ttk.Label(current_frame, text="Progress:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(current_frame, variable=self.progress_var,
                                          maximum=100, length=200)
        self.progress_bar.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
    
    def _create_stream_frame(self) -> None:
        """Create frame for displaying test execution stream."""
        stream_frame = ttk.LabelFrame(self, text="Test Execution Stream")
        stream_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        stream_frame.columnconfigure(0, weight=1)
        stream_frame.rowconfigure(0, weight=1)
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(stream_frame)
        text_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # Text widget for stream display
        self.stream_text = tk.Text(text_frame, wrap=tk.WORD, height=15, 
                                  font=("Consolas", 9), state=tk.DISABLED)
        self.stream_text.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.stream_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.stream_text.configure(yscrollcommand=scrollbar.set)
        
        # Configure text tags for different message types
        self.stream_text.tag_configure("info", foreground="blue")
        self.stream_text.tag_configure("success", foreground="green", font=("Consolas", 9, "bold"))
        self.stream_text.tag_configure("error", foreground="red", font=("Consolas", 9, "bold"))
        self.stream_text.tag_configure("warning", foreground="orange")
        self.stream_text.tag_configure("timestamp", foreground="gray")
    
    def _create_controls_frame(self) -> None:
        """Create frame with control buttons."""
        controls_frame = ttk.Frame(self)
        controls_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        # Clear Stream button
        ttk.Button(controls_frame, text="Clear Stream", 
                  command=self._clear_stream).pack(side=tk.LEFT, padx=5)
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls_frame, text="Auto-scroll", 
                       variable=self.auto_scroll_var).pack(side=tk.LEFT, padx=10)
        
        # Export Stream button
        ttk.Button(controls_frame, text="Export Stream", 
                  command=self._export_stream).pack(side=tk.RIGHT, padx=5)
    
    def start_test_stream(self, test_name: str, test_data: Dict[str, Any]) -> None:
        """
        Start streaming for a new test execution.

        Args:
            test_name: Name of the test being executed
            test_data: Test data being sent
        """
        # If we're in queue execution mode, don't start individual test stream
        # The queue execution will handle the streaming
        if self.is_queue_executing:
            return

        self.current_test = {
            "name": test_name,
            "data": test_data,
            "start_time": datetime.now(),
            "status": "Starting"
        }

        self.is_streaming = True

        # Update current test display
        self.current_test_var.set(test_name)
        self.current_status_var.set("Starting")
        self.progress_var.set(0)

        # Add initial stream entry
        self._add_stream_entry("info", f"🚀 Starting test execution: {test_name}")
        self._add_stream_entry("info", f"📋 Test data prepared with {len(test_data.get('test_cases', []))} test case(s)")

        if self.status_callback:
            self.status_callback(f"Started streaming test: {test_name}")
    
    def update_stream_status(self, status: str, message: str, progress: Optional[float] = None) -> None:
        """
        Update the stream with new status information.

        Args:
            status: Current status (preparing, sending, processing, receiving, completed, failed)
            message: Status message to display
            progress: Progress percentage (0-100)
        """
        # If we're in queue execution mode, don't update individual test stream
        # The queue execution will handle the streaming
        if self.is_queue_executing:
            return

        if not self.is_streaming:
            return

        # Update current status
        self.current_status_var.set(status.title())

        if progress is not None:
            self.progress_var.set(progress)

        # Determine message type based on status
        if status.lower() in ["completed", "success"]:
            msg_type = "success"
            icon = "✅"
        elif status.lower() in ["failed", "error"]:
            msg_type = "error"
            icon = "❌"
        elif status.lower() in ["warning"]:
            msg_type = "warning"
            icon = "⚠️"
        else:
            msg_type = "info"
            icon = "📡"

        # Add to stream
        self._add_stream_entry(msg_type, f"{icon} {message}")
    
    def end_test_stream(self, success: bool, final_message: str) -> None:
        """
        End the current test stream.

        Args:
            success: Whether the test completed successfully
            final_message: Final status message
        """
        # If we're in queue execution mode, don't end individual test stream
        # The queue execution will handle the streaming
        if self.is_queue_executing:
            return

        if not self.is_streaming:
            return

        self.is_streaming = False

        # Update final status
        final_status = "Completed" if success else "Failed"
        self.current_status_var.set(final_status)
        self.progress_var.set(100)

        # Add final stream entry
        msg_type = "success" if success else "error"
        icon = "🎉" if success else "💥"
        self._add_stream_entry(msg_type, f"{icon} {final_message}")

        # Add execution time
        if self.current_test and "start_time" in self.current_test:
            duration = datetime.now() - self.current_test["start_time"]
            self._add_stream_entry("info", f"⏱️ Total execution time: {duration.total_seconds():.1f} seconds")

        self._add_stream_entry("info", "─" * 60)  # Separator line

        if self.status_callback:
            self.status_callback(f"Test stream ended: {final_status}")

    def start_queue_execution(self, total_tests: int, test_names: List[str]) -> None:
        """
        Start queue execution tracking.

        Args:
            total_tests: Total number of tests in the queue
            test_names: List of test names to be executed
        """
        self.queue_execution = {
            "total_tests": total_tests,
            "completed_tests": 0,
            "current_test_index": 0,
            "test_names": test_names,
            "start_time": datetime.now()
        }

        self.is_queue_executing = True

        # Show queue info frame
        self.queue_info_frame.grid()

        # Update queue status display
        self.queue_status_var.set(f"Executing {total_tests} tests")
        self.queue_progress_var.set(f"Completed: 0/{total_tests} tests")

        # Add initial queue stream entry
        self._add_stream_entry("info", f"🚀 Starting queue execution: {total_tests} tests")
        test_list = ", ".join(test_names)
        self._add_stream_entry("info", f"📋 Test queue: {test_list}")

        if self.status_callback:
            self.status_callback(f"Started queue execution: {total_tests} tests")

    def start_queue_test_stream(self, test_index: int, test_name: str, test_data: Dict[str, Any]) -> None:
        """
        Start streaming for a test within queue execution.

        Args:
            test_index: Index of the test in queue (0-based)
            test_name: Name of the test being executed
            test_data: Test data being sent
        """
        if not self.is_queue_executing or not self.queue_execution:
            return

        total_tests = self.queue_execution["total_tests"]

        # Update current test info with queue context
        queue_test_info = f"Test {test_index + 1} of {total_tests} - {test_name}"
        self.current_test_var.set(queue_test_info)
        self.current_status_var.set("Starting")
        self.progress_var.set(0)

        # Add test start stream entry
        self._add_stream_entry("info", f"🚀 Starting test execution: {test_name}")
        self._add_stream_entry("info", f"📋 Test data prepared with {len(test_data.get('test_cases', []))} test case(s)")

    def update_queue_test_status(self, status: str, message: str, progress: Optional[float] = None) -> None:
        """
        Update stream status for a test within queue execution.

        Args:
            status: Current status (preparing, sending, processing, receiving, completed, failed)
            message: Status message to display
            progress: Progress percentage (0-100)
        """
        if not self.is_queue_executing:
            return

        # Update current status
        self.current_status_var.set(status.title())

        if progress is not None:
            self.progress_var.set(progress)

        # Determine message type based on status
        if status.lower() in ["completed", "success"]:
            msg_type = "success"
            icon = "✅"
        elif status.lower() in ["failed", "error"]:
            msg_type = "error"
            icon = "❌"
        elif status.lower() in ["warning"]:
            msg_type = "warning"
            icon = "⚠️"
        else:
            msg_type = "info"
            icon = "📡"

        # Add to stream
        self._add_stream_entry(msg_type, f"{icon} {message}")

    def set_queue_test_execution_time(self, test_index: int, execution_time: float) -> None:
        """
        Set the execution time for a test in queue execution.
        This is called from main_window after test completion.

        Args:
            test_index: Index of the test in queue (0-based)
            execution_time: Actual execution time in seconds
        """
        self.queue_test_execution_times[test_index] = execution_time

    def end_queue_test_stream(self, test_index: int, test_name: str, success: bool, final_message: str, execution_time: float = 0.0) -> None:
        """
        End streaming for a test within queue execution.

        Args:
            test_index: Index of the test in queue (0-based)
            test_name: Name of the test
            success: Whether the test completed successfully
            final_message: Final status message
            execution_time: Test execution time in seconds (fallback if not stored)
        """
        if not self.is_queue_executing:
            return

        # Use stored execution time if available, otherwise use provided fallback
        actual_execution_time = self.queue_test_execution_times.get(test_index, execution_time)

        # Update final status
        final_status = "Completed" if success else "Failed"
        self.current_status_var.set(final_status)
        self.progress_var.set(100)

        # Add final stream entry
        msg_type = "success" if success else "error"
        icon = "🎉" if success else "💥"
        self._add_stream_entry(msg_type, f"{icon} {final_message}")

        # Add execution time
        self._add_stream_entry("info", f"⏱️ Total execution time: {actual_execution_time:.1f} seconds")
        self._add_stream_entry("info", "─" * 60)  # Separator line

        # Clean up stored execution time
        if test_index in self.queue_test_execution_times:
            del self.queue_test_execution_times[test_index]

    def update_queue_progress(self, current_test_index: int, test_name: str) -> None:
        """
        Update queue execution progress.

        Args:
            current_test_index: Index of currently executing test (0-based)
            test_name: Name of the currently executing test
        """
        if not self.is_queue_executing or not self.queue_execution:
            return

        self.queue_execution["current_test_index"] = current_test_index
        total_tests = self.queue_execution["total_tests"]

        # Update queue progress display
        self.queue_progress_var.set(f"Completed: {current_test_index}/{total_tests} tests")

        # Update current test info with queue context
        queue_test_info = f"Test {current_test_index + 1} of {total_tests} - {test_name}"
        self.current_test_var.set(queue_test_info)

        # Add queue progress stream entry
        self._add_stream_entry("info", f"📊 Currently running: {queue_test_info}")

    def complete_queue_test(self, test_index: int, test_name: str, success: bool) -> None:
        """
        Mark a test in the queue as completed.

        Args:
            test_index: Index of the completed test (0-based)
            test_name: Name of the completed test
            success: Whether the test completed successfully
        """
        if not self.is_queue_executing or not self.queue_execution:
            return

        self.queue_execution["completed_tests"] = test_index + 1
        total_tests = self.queue_execution["total_tests"]
        completed = self.queue_execution["completed_tests"]

        # Update progress display
        self.queue_progress_var.set(f"Completed: {completed}/{total_tests} tests")

        # Add completion stream entry
        status_icon = "✅" if success else "❌"
        status_text = "completed successfully" if success else "failed"
        self._add_stream_entry("success" if success else "error",
                              f"{status_icon} Test {test_index + 1}/{total_tests} ({test_name}) {status_text}")

    def end_queue_execution(self, success: bool, final_message: str) -> None:
        """
        End queue execution tracking.

        Args:
            success: Whether the queue execution completed successfully
            final_message: Final status message
        """
        if not self.is_queue_executing or not self.queue_execution:
            return

        self.is_queue_executing = False

        # Calculate execution time
        duration = datetime.now() - self.queue_execution["start_time"]
        total_tests = self.queue_execution["total_tests"]
        completed_tests = self.queue_execution["completed_tests"]

        # Update final status
        self.queue_status_var.set(f"Queue completed: {completed_tests}/{total_tests} tests")
        self.queue_progress_var.set(f"Completed: {completed_tests}/{total_tests} tests")

        # Add final queue stream entries
        msg_type = "success" if success else "error"
        icon = "🎉" if success else "💥"
        self._add_stream_entry(msg_type, f"{icon} {final_message}")
        self._add_stream_entry("info", f"⏱️ Total queue execution time: {duration.total_seconds():.1f} seconds")
        self._add_stream_entry("info", "═" * 60)  # Double separator for queue end

        # Reset current test display
        self.current_test_var.set("No test running")
        self.current_status_var.set("Idle")
        self.progress_var.set(0)

        # Hide queue info after a delay
        self.after(3000, lambda: self.queue_info_frame.grid_remove())

        if self.status_callback:
            self.status_callback(f"Queue execution ended: {final_message}")

    def _add_stream_entry(self, msg_type: str, message: str) -> None:
        """
        Add an entry to the stream display.
        
        Args:
            msg_type: Type of message (info, success, error, warning)
            message: Message to display
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Store entry
        entry = {
            "timestamp": timestamp,
            "type": msg_type,
            "message": message
        }
        self.stream_entries.append(entry)
        
        # Update text widget
        self.stream_text.configure(state=tk.NORMAL)
        
        # Add timestamp
        self.stream_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        
        # Add message with appropriate tag
        self.stream_text.insert(tk.END, f"{message}\n", msg_type)
        
        self.stream_text.configure(state=tk.DISABLED)
        
        # Auto-scroll if enabled
        if self.auto_scroll_var.get():
            self.stream_text.see(tk.END)
    
    def _clear_stream(self) -> None:
        """Clear the stream display."""
        self.stream_text.configure(state=tk.NORMAL)
        self.stream_text.delete(1.0, tk.END)
        self.stream_text.configure(state=tk.DISABLED)
        
        self.stream_entries.clear()
        
        if self.status_callback:
            self.status_callback("Stream cleared")
    
    def _export_stream(self) -> None:
        """Export stream to file."""
        if not self.stream_entries:
            messagebox.showinfo("Export Stream", "No stream data to export")
            return
            
        try:
            file_path = filedialog.asksaveasfilename(
                title="Export Stream",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if file_path:
                if file_path.endswith('.json'):
                    # Export as JSON
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.stream_entries, f, indent=2, default=str)
                else:
                    # Export as text
                    with open(file_path, 'w', encoding='utf-8') as f:
                        for entry in self.stream_entries:
                            f.write(f"[{entry['timestamp']}] {entry['message']}\n")
                
                messagebox.showinfo("Export Successful", f"Stream exported to {file_path}")
                
                if self.status_callback:
                    self.status_callback(f"Stream exported to {file_path}")
                    
        except Exception as e:
            self.logger.error(f"Error exporting stream: {e}")
            messagebox.showerror("Export Error", f"Failed to export stream: {str(e)}")
