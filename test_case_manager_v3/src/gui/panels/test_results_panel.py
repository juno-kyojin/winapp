#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Results Panel for Test Case Manager v1.0

This panel displays real-time test execution results.

Author: juno-kyojin
Created: 2025-07-01
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import threading

from src.utils.logger import get_logger


class TestResultsPanel(ttk.Frame):
    """
    Panel for displaying real-time test execution results.
    
    This panel shows the status and results of test cases as they are executed,
    providing immediate feedback to the user.
    """
    
    def __init__(self, parent: ttk.Widget,
                 update_status_callback: Callable[[str], None]) -> None:
        """
        Initialize the test results panel.
        
        Args:
            parent: Parent widget
            update_status_callback: Callback to update status bar
        """
        super().__init__(parent)
        self.parent = parent
        self.update_status = update_status_callback
        self.logger = get_logger(__name__)
        
        # Test results data
        self.test_results: List[Dict[str, Any]] = []
        self.current_test_index = -1
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
        # UI components
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """Create panel widgets."""
        # Main layout with top summary and bottom details
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Summary section (fixed height)
        self.rowconfigure(1, weight=1)  # Details section (expandable)
        
        # Summary section
        self.summary_frame = ttk.LabelFrame(self, text="Test Execution Summary")
        self.summary_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Summary grid layout
        summary_grid = ttk.Frame(self.summary_frame)
        summary_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Progress bar
        ttk.Label(summary_grid, text="Overall Progress:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        progress_frame = ttk.Frame(summary_grid)
        progress_frame.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.grid(row=0, column=0, sticky=tk.EW)
        
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.grid(row=0, column=1, padx=5)
        
        # Test counts
        ttk.Label(summary_grid, text="Total Tests:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.total_label = ttk.Label(summary_grid, text="0")
        self.total_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(summary_grid, text="Passed:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.passed_label = ttk.Label(summary_grid, text="0", foreground="green")
        self.passed_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(summary_grid, text="Failed:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.failed_label = ttk.Label(summary_grid, text="0", foreground="red")
        self.failed_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(summary_grid, text="Current Test:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.current_test_label = ttk.Label(summary_grid, text="-")
        self.current_test_label.grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Status message
        ttk.Label(summary_grid, text="Status:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        self.status_label = ttk.Label(summary_grid, text="Ready")
        self.status_label.grid(row=5, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Details section with notebook
        self.details_frame = ttk.LabelFrame(self, text="Test Results")
        self.details_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create a notebook for test results
        self.results_notebook = ttk.Notebook(self.details_frame)
        self.results_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results list tab
        self.list_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.list_frame, text="Results List")
        
        # Create treeview for results list
        self.results_tree = ttk.Treeview(
            self.list_frame,
            columns=("id", "name", "status", "time"),
            show="headings"
        )
        
        # Configure columns
        self.results_tree.heading("id", text="#")
        self.results_tree.heading("name", text="Test Name")
        self.results_tree.heading("status", text="Status")
        self.results_tree.heading("time", text="Time")
        
        self.results_tree.column("id", width=50)
        self.results_tree.column("name", width=250)
        self.results_tree.column("status", width=100)
        self.results_tree.column("time", width=150)
        
        # Add scrollbar to treeview
        tree_scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Pack treeview and scrollbar
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.results_tree.bind("<<TreeviewSelect>>", self._on_result_selected)
        
        # Current result tab
        self.current_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.current_frame, text="Current Test")
        
        # Current test info
        current_info_frame = ttk.LabelFrame(self.current_frame, text="Test Information")
        current_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Grid for current test info
        current_grid = ttk.Frame(current_info_frame)
        current_grid.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(current_grid, text="Test Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.current_name_label = ttk.Label(current_grid, text="-")
        self.current_name_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(current_grid, text="Status:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.current_status_label = ttk.Label(current_grid, text="-")
        self.current_status_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(current_grid, text="Start Time:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.current_start_label = ttk.Label(current_grid, text="-")
        self.current_start_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(current_grid, text="End Time:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.current_end_label = ttk.Label(current_grid, text="-")
        self.current_end_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Current test result
        current_result_frame = ttk.LabelFrame(self.current_frame, text="Test Result")
        current_result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add text widget for result display
        self.current_result_text = tk.Text(current_result_frame, wrap=tk.WORD)
        self.current_result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar to result text
        result_scrollbar = ttk.Scrollbar(self.current_result_text, orient=tk.VERTICAL, command=self.current_result_text.yview)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.current_result_text.config(yscrollcommand=result_scrollbar.set)
        
        # Details tab
        self.details_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.details_tab, text="Details")
        
        # Details text widget
        self.details_text = tk.Text(self.details_tab, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar to details text
        details_scrollbar = ttk.Scrollbar(self.details_text, orient=tk.VERTICAL, command=self.details_text.yview)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.config(yscrollcommand=details_scrollbar.set)
        
        # Action buttons
        self.action_frame = ttk.Frame(self)
        self.action_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        self.clear_button = ttk.Button(
            self.action_frame,
            text="Clear Results",
            command=self.clear_results
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        
        self.export_button = ttk.Button(
            self.action_frame,
            text="Export Results",
            command=self.export_results
        )
        self.export_button.pack(side=tk.RIGHT, padx=5)
    
    def start_test_execution(self, test_queue: List[Dict[str, Any]]) -> None:
        """
        Start executing a queue of tests.
        
        Args:
            test_queue: List of test cases to execute
        """
        # Reset counters
        self.clear_results()
        
        # Set total tests
        self.total_tests = len(test_queue)
        self.total_label.config(text=str(self.total_tests))
        
        # Update progress
        self._update_progress()
        
        # Show first test as current
        if self.total_tests > 0:
            self.current_test_label.config(text=f"1 of {self.total_tests}")
            self.status_label.config(text="Executing tests...")
    
    def add_test_result(self, test_data: Dict[str, Any], result_data: Optional[Dict[str, Any]], 
                        status: str, message: str, execution_time: float) -> None:
        """
        Add a test result to the panel.
        
        Args:
            test_data: Original test data
            result_data: Result data from test execution
            status: Test status (success, fail, error)
            message: Status message
            execution_time: Time taken to execute the test in seconds
        """
        # Get test name
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
        
        # Create result object
        result = {
            "id": len(self.test_results) + 1,
            "name": test_name,
            "status": status,
            "message": message,
            "test_data": test_data,
            "result_data": result_data,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "execution_time": execution_time
        }
        
        # Add to results list
        self.test_results.append(result)
        
        # Update counters
        if status.lower() == "success":
            self.passed_tests += 1
            self.passed_label.config(text=str(self.passed_tests))
        else:
            self.failed_tests += 1
            self.failed_label.config(text=str(self.failed_tests))
        
        # Update current test index
        self.current_test_index = len(self.test_results) - 1
        
        # Update progress
        self._update_progress()
        
        # Add to treeview
        status_text = "PASS" if status.lower() == "success" else "FAIL"
        time_text = f"{execution_time:.2f}s"
        
        item_id = self.results_tree.insert(
            "",
            tk.END,
            values=(result["id"], test_name, status_text, time_text),
            tags=(status.lower(),)
        )
        
        # Configure tag colors
        self.results_tree.tag_configure("success", background="#e6ffe6")  # Light green
        self.results_tree.tag_configure("fail", background="#ffe6e6")     # Light red
        self.results_tree.tag_configure("error", background="#fff0e6")    # Light orange
        
        # Select the new item
        self.results_tree.selection_set(item_id)
        self.results_tree.see(item_id)
        
        # Update current test display
        self._update_current_test_display(result)
        
        # Update status label
        if self.current_test_index < self.total_tests - 1:
            next_test = self.current_test_index + 2  # 1-based index for display
            self.current_test_label.config(text=f"{next_test} of {self.total_tests}")
            self.status_label.config(text="Executing tests...")
        else:
            self.current_test_label.config(text=f"Completed {self.total_tests} of {self.total_tests}")
            self.status_label.config(text="Test execution completed")
    
    def _update_progress(self) -> None:
        """Update the progress bar and label."""
        if self.total_tests > 0:
            progress = int((self.current_test_index + 1) / self.total_tests * 100)
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{progress}%")
        else:
            self.progress_var.set(0)
            self.progress_label.config(text="0%")
    
    def _on_result_selected(self, event) -> None:
        """Handle selection of a result in the treeview."""
        selected_items = self.results_tree.selection()
        if not selected_items:
            return
        
        # Get the selected item ID
        item_id = selected_items[0]
        
        # Get the result ID from the treeview
        result_id = int(self.results_tree.item(item_id, "values")[0])
        
        # Find the corresponding result
        for i, result in enumerate(self.test_results):
            if result["id"] == result_id:
                # Update current test index
                self.current_test_index = i
                
                # Update current test display
                self._update_current_test_display(result)
                
                # Update details tab
                self._update_details_tab(result)
                
                # Switch to Current Test tab
                self.results_notebook.select(1)  # Index 1 is Current Test tab
                break
    
    def _update_current_test_display(self, result: Dict[str, Any]) -> None:
        """
        Update the current test display with the selected result.
        
        Args:
            result: Test result data
        """
        # Update labels
        self.current_name_label.config(text=result["name"])
        
        status_text = "PASS" if result["status"].lower() == "success" else "FAIL"
        status_color = "green" if result["status"].lower() == "success" else "red"
        self.current_status_label.config(text=status_text, foreground=status_color)
        
        self.current_start_label.config(text=result["start_time"])
        
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_end_label.config(text=end_time)
        
        # Update result text
        self.current_result_text.config(state=tk.NORMAL)
        self.current_result_text.delete(1.0, tk.END)
        
        # Add message
        if result["message"]:
            self.current_result_text.insert(tk.END, f"Message: {result['message']}\n\n")
        
        # Add result data
        if result["result_data"]:
            try:
                formatted_result = json.dumps(result["result_data"], indent=2)
                self.current_result_text.insert(tk.END, "Result Data:\n")
                self.current_result_text.insert(tk.END, formatted_result)
            except Exception as e:
                self.current_result_text.insert(tk.END, f"Error formatting result: {str(e)}\n\n")
                self.current_result_text.insert(tk.END, str(result["result_data"]))
        else:
            self.current_result_text.insert(tk.END, "No result data available")
        
        # Make text read-only
        self.current_result_text.config(state=tk.DISABLED)
    
    def _update_details_tab(self, result: Dict[str, Any]) -> None:
        """
        Update the details tab with comprehensive test information.
        
        Args:
            result: Test result data
        """
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        
        # Add header
        self.details_text.insert(tk.END, f"TEST DETAILS: {result['name']}\n")
        self.details_text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Add basic info
        self.details_text.insert(tk.END, f"Test ID: {result['id']}\n")
        self.details_text.insert(tk.END, f"Name: {result['name']}\n")
        self.details_text.insert(tk.END, f"Status: {result['status']}\n")
        self.details_text.insert(tk.END, f"Start Time: {result['start_time']}\n")
        self.details_text.insert(tk.END, f"Execution Time: {result['execution_time']:.2f} seconds\n\n")
        
        # Add message
        if result["message"]:
            self.details_text.insert(tk.END, f"Message: {result['message']}\n\n")
        
        # Add test data
        self.details_text.insert(tk.END, "TEST DATA:\n")
        self.details_text.insert(tk.END, "-" * 80 + "\n")
        try:
            formatted_test_data = json.dumps(result["test_data"], indent=2)
            self.details_text.insert(tk.END, formatted_test_data + "\n\n")
        except Exception as e:
            self.details_text.insert(tk.END, f"Error formatting test data: {str(e)}\n\n")
            self.details_text.insert(tk.END, str(result["test_data"]) + "\n\n")
        
        # Add result data
        self.details_text.insert(tk.END, "RESULT DATA:\n")
        self.details_text.insert(tk.END, "-" * 80 + "\n")
        if result["result_data"]:
            try:
                formatted_result = json.dumps(result["result_data"], indent=2)
                self.details_text.insert(tk.END, formatted_result)
            except Exception as e:
                self.details_text.insert(tk.END, f"Error formatting result: {str(e)}\n\n")
                self.details_text.insert(tk.END, str(result["result_data"]))
        else:
            self.details_text.insert(tk.END, "No result data available")
        
        # Make text read-only
        self.details_text.config(state=tk.DISABLED)
    
    def clear_results(self) -> None:
        """Clear all test results."""
        # Reset data
        self.test_results = []
        self.current_test_index = -1
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
        # Update UI
        self.total_label.config(text="0")
        self.passed_label.config(text="0")
        self.failed_label.config(text="0")
        self.current_test_label.config(text="-")
        self.status_label.config(text="Ready")
        
        # Clear treeview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Clear current test display
        self.current_name_label.config(text="-")
        self.current_status_label.config(text="-", foreground="black")
        self.current_start_label.config(text="-")
        self.current_end_label.config(text="-")
        
        self.current_result_text.config(state=tk.NORMAL)
        self.current_result_text.delete(1.0, tk.END)
        self.current_result_text.config(state=tk.DISABLED)
        
        # Clear details tab
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state=tk.DISABLED)
        
        # Update progress
        self._update_progress()
        
        # Update status
        self.update_status("Results cleared")
    
    def export_results(self) -> None:
        """Export test results to a file."""
        if not self.test_results:
            messagebox.showinfo("Export Results", "No results to export")
            return
        
        # Get file path from user
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Prepare export data
            export_data = {
                "summary": {
                    "total_tests": self.total_tests,
                    "passed_tests": self.passed_tests,
                    "failed_tests": self.failed_tests,
                    "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "results": self.test_results
            }
            
            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.update_status(f"Results exported to {file_path}")
            messagebox.showinfo("Export Successful", f"Results exported to {file_path}")
        except Exception as e:
            self.logger.error(f"Error exporting results: {e}")
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}") 