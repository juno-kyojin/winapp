#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
History Panel for Test Case Manager v1.0

This panel displays the history of test executions and their results.

Author: juno-kyojin
Created: 2025-07-01
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import threading
import time

from src.core.result_manager import ResultManager
from src.utils.logger import get_logger


class HistoryPanel(ttk.Frame):
    """
    Panel for displaying test execution history and results.
    
    This panel shows a list of previously executed tests and allows
    viewing their results directly in the application.
    """
    
    def __init__(self, parent: ttk.Widget, 
                 result_manager: ResultManager,
                 update_status_callback: Callable[[str], None]) -> None:
        """
        Initialize the history panel.
        
        Args:
            parent: Parent widget
            result_manager: Result manager instance
            update_status_callback: Callback to update status bar
        """
        super().__init__(parent)
        self.parent = parent
        self.result_manager = result_manager
        self.update_status = update_status_callback
        self.logger = get_logger(__name__)
        
        # Current selected result
        self.current_result: Optional[Dict[str, Any]] = None
        
        # UI components
        self._create_widgets()
        
        # Load initial results
        self._load_results()
        
        # Auto-refresh timer
        self.auto_refresh = False
        self.refresh_interval = 30  # seconds
        self.refresh_thread = None
        
    def _create_widgets(self) -> None:
        """Create panel widgets."""
        # Main layout: split into left (list) and right (details) panes
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left frame: Test list
        self.list_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.list_frame, weight=1)
        
        # Controls frame
        self.controls_frame = ttk.Frame(self.list_frame)
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Filter controls
        self.filter_frame = ttk.LabelFrame(self.controls_frame, text="Filters")
        self.filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Status filter
        self.status_frame = ttk.Frame(self.filter_frame)
        self.status_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(self.status_frame, text="Status:").pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value="all")
        self.status_combo = ttk.Combobox(
            self.status_frame, 
            textvariable=self.status_var,
            values=["all", "success", "fail", "error"],
            width=10,
            state="readonly"
        )
        self.status_combo.pack(side=tk.LEFT, padx=5)
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self._load_results())
        
        # Test ID filter
        self.test_id_frame = ttk.Frame(self.filter_frame)
        self.test_id_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(self.test_id_frame, text="Test ID:").pack(side=tk.LEFT, padx=5)
        
        self.test_id_var = tk.StringVar()
        self.test_id_entry = ttk.Entry(self.test_id_frame, textvariable=self.test_id_var, width=20)
        self.test_id_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.filter_button = ttk.Button(
            self.test_id_frame, 
            text="Apply Filter", 
            command=self._load_results
        )
        self.filter_button.pack(side=tk.LEFT, padx=5)
        
        # Refresh controls
        self.refresh_frame = ttk.Frame(self.controls_frame)
        self.refresh_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.refresh_button = ttk.Button(
            self.refresh_frame,
            text="Refresh",
            command=self._load_results
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        # Auto-refresh checkbox
        self.auto_refresh_var = tk.BooleanVar(value=False)
        self.auto_refresh_check = ttk.Checkbutton(
            self.refresh_frame,
            text="Auto-refresh",
            variable=self.auto_refresh_var,
            command=self._toggle_auto_refresh
        )
        self.auto_refresh_check.pack(side=tk.LEFT, padx=5)
        
        # Delete button
        self.delete_button = ttk.Button(
            self.refresh_frame,
            text="Delete Selected",
            command=self._delete_selected
        )
        self.delete_button.pack(side=tk.RIGHT, padx=5)
        
        # Test list with scrollbar
        self.list_container = ttk.Frame(self.list_frame)
        self.list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for test list
        self.result_tree = ttk.Treeview(
            self.list_container,
            columns=("date", "test_id", "status"),
            show="headings"
        )
        
        # Configure columns
        self.result_tree.heading("date", text="Date")
        self.result_tree.heading("test_id", text="Test ID")
        self.result_tree.heading("status", text="Status")
        
        self.result_tree.column("date", width=150)
        self.result_tree.column("test_id", width=150)
        self.result_tree.column("status", width=80)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(self.list_container, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=y_scrollbar.set)
        
        # Pack treeview and scrollbar
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.result_tree.bind("<<TreeviewSelect>>", self._on_result_selected)
        
        # Right frame: Result details
        self.details_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.details_frame, weight=2)
        
        # Result details
        self.details_label = ttk.Label(
            self.details_frame, 
            text="Select a test result to view details",
            font=("Arial", 12)
        )
        self.details_label.pack(pady=10)
        
        # Create notebook for result details
        self.details_notebook = ttk.Notebook(self.details_frame)
        self.details_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Summary tab
        self.summary_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.summary_frame, text="Summary")
        
        # Create summary widgets
        self.summary_info = ttk.LabelFrame(self.summary_frame, text="Test Information")
        self.summary_info.pack(fill=tk.X, padx=10, pady=10)
        
        # Grid for test info
        info_grid = ttk.Frame(self.summary_info)
        info_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Test info labels
        ttk.Label(info_grid, text="Test ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.test_id_label = ttk.Label(info_grid, text="-")
        self.test_id_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_grid, text="Status:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.status_label = ttk.Label(info_grid, text="-")
        self.status_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_grid, text="Date:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.date_label = ttk.Label(info_grid, text="-")
        self.date_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Result summary
        self.summary_result = ttk.LabelFrame(self.summary_frame, text="Result Summary")
        self.summary_result.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Summary text widget
        self.summary_text = tk.Text(self.summary_result, wrap=tk.WORD, height=10)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar to summary text
        summary_scrollbar = ttk.Scrollbar(self.summary_text, orient=tk.VERTICAL, command=self.summary_text.yview)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.config(yscrollcommand=summary_scrollbar.set)
        
        # Raw JSON tab
        self.json_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.json_frame, text="Raw JSON")
        
        # JSON text widget with syntax highlighting
        self.json_text = tk.Text(self.json_frame, wrap=tk.WORD)
        self.json_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar to JSON text
        json_scrollbar = ttk.Scrollbar(self.json_text, orient=tk.VERTICAL, command=self.json_text.yview)
        json_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.json_text.config(yscrollcommand=json_scrollbar.set)
        
        # Configure text tags for syntax highlighting
        self.json_text.tag_configure("key", foreground="blue")
        self.json_text.tag_configure("string", foreground="green")
        self.json_text.tag_configure("number", foreground="orange")
        self.json_text.tag_configure("boolean", foreground="purple")
        self.json_text.tag_configure("null", foreground="red")
        
        # Action buttons
        self.action_frame = ttk.Frame(self.details_frame)
        self.action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.save_button = ttk.Button(
            self.action_frame,
            text="Save to File",
            command=self._save_current_result
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.export_button = ttk.Button(
            self.action_frame,
            text="Export as Report",
            command=self._export_as_report
        )
        self.export_button.pack(side=tk.LEFT, padx=5)
        
    def _load_results(self) -> None:
        """Load test results based on current filters."""
        # Get filter values
        status = None if self.status_var.get() == "all" else self.status_var.get()
        test_id = self.test_id_var.get() if self.test_id_var.get() else None
        
        try:
            # Clear existing items
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
                
            # Get results from result manager
            results = self.result_manager.get_results(
                test_id=test_id,
                status=status,
                limit=100,
                sort_by_date=True,
                reverse=True
            )
            
            # Add results to treeview
            for result in results:
                self.result_tree.insert(
                    "",
                    tk.END,
                    values=(
                        result.get("date", "Unknown"),
                        result.get("test_id", "Unknown"),
                        result.get("status", "Unknown")
                    ),
                    tags=(result.get("status", "unknown"),),
                    iid=result.get("file_path", "")
                )
                
            # Configure tag colors
            self.result_tree.tag_configure("success", background="#e6ffe6")  # Light green
            self.result_tree.tag_configure("fail", background="#ffe6e6")     # Light red
            self.result_tree.tag_configure("error", background="#fff0e6")    # Light orange
            
            # Update status
            count = len(self.result_tree.get_children())
            self.update_status(f"Loaded {count} test results")
            
        except Exception as e:
            self.logger.error(f"Error loading test results: {e}")
            messagebox.showerror("Error", f"Failed to load test results: {str(e)}")
            
    def _on_result_selected(self, event) -> None:
        """Handle selection of a result in the treeview."""
        # Get selected item
        selected_items = self.result_tree.selection()
        if not selected_items:
            return
            
        # Get file path from item ID
        file_path = selected_items[0]
        
        try:
            # Load result data
            result_data = self.result_manager.load_result(file_path)
            self.current_result = result_data
            
            # Update summary tab
            self._update_summary(result_data, file_path)
            
            # Update JSON tab
            self._update_json_view(result_data)
            
        except Exception as e:
            self.logger.error(f"Error loading result details: {e}")
            messagebox.showerror("Error", f"Failed to load result details: {str(e)}")
            
    def _update_summary(self, result_data: Dict[str, Any], file_path: str) -> None:
        """Update the summary tab with result data."""
        # Get metadata
        metadata = result_data.get("metadata", {})
        
        # Update info labels
        self.test_id_label.config(text=metadata.get("test_id", "Unknown"))
        
        # Set status with color
        status = metadata.get("status", "Unknown")
        self.status_label.config(
            text=status,
            foreground="green" if status == "success" else "red"
        )
        
        self.date_label.config(text=metadata.get("timestamp", "Unknown"))
        
        # Clear summary text
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        
        # Add summary information
        summary_text = "Test Result Summary:\n\n"
        
        # Add basic info
        summary_text += f"File: {file_path}\n"
        summary_text += f"Size: {metadata.get('file_size', 'Unknown')} bytes\n\n"
        
        # Add components info if available
        if "components_passed" in result_data:
            summary_text += f"Components Passed: {result_data.get('components_passed', 0)}\n"
            summary_text += f"Components Failed: {result_data.get('components_failed', 0)}\n\n"
            
        # Add message if available
        if "message" in result_data:
            summary_text += f"Message: {result_data.get('message', '')}\n\n"
            
        # Add details if available
        if "details" in result_data:
            summary_text += "Details:\n"
            details = result_data.get("details", [])
            if isinstance(details, list):
                for i, detail in enumerate(details):
                    summary_text += f"  {i+1}. {json.dumps(detail, indent=2)}\n"
            else:
                summary_text += f"  {json.dumps(details, indent=2)}\n"
                
        # Insert summary text
        self.summary_text.insert(tk.END, summary_text)
        self.summary_text.config(state=tk.DISABLED)
        
    def _update_json_view(self, result_data: Dict[str, Any]) -> None:
        """Update the JSON view with formatted JSON."""
        # Clear JSON text
        self.json_text.config(state=tk.NORMAL)
        self.json_text.delete(1.0, tk.END)
        
        # Format JSON
        formatted_json = json.dumps(result_data, indent=4)
        
        # Insert formatted JSON
        self.json_text.insert(tk.END, formatted_json)
        
        # Make JSON view read-only
        self.json_text.config(state=tk.DISABLED)
        
    def _save_current_result(self) -> None:
        """Save the current result to a file."""
        if not self.current_result:
            messagebox.showinfo("Info", "No result selected")
            return
            
        # Get file path from user
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.test_id_label.cget('text')}_result.json"
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.current_result, f, indent=4)
                
            self.update_status(f"Result saved to {file_path}")
            messagebox.showinfo(
                "Save Successful",
                f"Result saved to {file_path}"
            )
        except Exception as e:
            self.logger.error(f"Error saving result: {e}")
            messagebox.showerror("Error", f"Failed to save result: {str(e)}")
            
    def _export_as_report(self) -> None:
        """Export the current result as a formatted report."""
        if not self.current_result:
            messagebox.showinfo("Info", "No result selected")
            return
            
        # Get file path from user
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"{self.test_id_label.cget('text')}_report.txt"
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            # Generate report text
            report = self._generate_report(self.current_result)
            
            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report)
                
            self.update_status(f"Report exported to {file_path}")
            messagebox.showinfo(
                "Export Successful",
                f"Report exported to {file_path}"
            )
        except Exception as e:
            self.logger.error(f"Error exporting report: {e}")
            messagebox.showerror("Error", f"Failed to export report: {str(e)}")
            
    def _generate_report(self, result_data: Dict[str, Any]) -> str:
        """Generate a formatted report from result data."""
        # Get metadata
        metadata = result_data.get("metadata", {})
        
        # Build report header
        report = "=" * 80 + "\n"
        report += f"TEST RESULT REPORT\n"
        report += "=" * 80 + "\n\n"
        
        # Add basic info
        report += f"Test ID: {metadata.get('test_id', 'Unknown')}\n"
        report += f"Status: {metadata.get('status', 'Unknown')}\n"
        report += f"Date: {metadata.get('timestamp', 'Unknown')}\n"
        report += f"File: {metadata.get('filename', 'Unknown')}\n\n"
        
        # Add components info if available
        if "components_passed" in result_data:
            report += f"Components Passed: {result_data.get('components_passed', 0)}\n"
            report += f"Components Failed: {result_data.get('components_failed', 0)}\n\n"
            
        # Add message if available
        if "message" in result_data:
            report += f"Message: {result_data.get('message', '')}\n\n"
            
        # Add details if available
        if "details" in result_data:
            report += "Details:\n" + "-" * 40 + "\n"
            details = result_data.get("details", [])
            if isinstance(details, list):
                for i, detail in enumerate(details):
                    report += f"Item {i+1}:\n"
                    report += json.dumps(detail, indent=2) + "\n\n"
            else:
                report += json.dumps(details, indent=2) + "\n\n"
                
        # Add log if available
        if "log" in result_data:
            report += "Log:\n" + "-" * 40 + "\n"
            logs = result_data.get("log", [])
            if isinstance(logs, list):
                for i, log_entry in enumerate(logs):
                    report += f"Log {i+1}: {json.dumps(log_entry)}\n"
            else:
                report += f"{json.dumps(logs)}\n"
                
        # Add footer
        report += "\n" + "=" * 80 + "\n"
        report += f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += "=" * 80 + "\n"
        
        return report
        
    def _delete_selected(self) -> None:
        """Delete the selected result file."""
        selected_items = self.result_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "No result selected")
            return
            
        # Get file path from item ID
        file_path = selected_items[0]
        
        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this result?\nFile: {file_path}"
        )
        
        if not confirm:
            return
            
        try:
            # Delete the file
            success = self.result_manager.delete_result(file_path)
            
            if success:
                # Remove from treeview
                self.result_tree.delete(selected_items[0])
                
                # Clear details if this was the selected result
                if self.current_result:
                    self.current_result = None
                    self.test_id_label.config(text="-")
                    self.status_label.config(text="-", foreground="black")
                    self.date_label.config(text="-")
                    
                    # Clear text widgets
                    self.summary_text.config(state=tk.NORMAL)
                    self.summary_text.delete(1.0, tk.END)
                    self.summary_text.config(state=tk.DISABLED)
                    
                    self.json_text.config(state=tk.NORMAL)
                    self.json_text.delete(1.0, tk.END)
                    self.json_text.config(state=tk.DISABLED)
                
                self.update_status(f"Deleted result file: {file_path}")
            else:
                messagebox.showerror("Error", f"Failed to delete result file")
                
        except Exception as e:
            self.logger.error(f"Error deleting result: {e}")
            messagebox.showerror("Error", f"Failed to delete result: {str(e)}")
            
    def _toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh of results."""
        self.auto_refresh = self.auto_refresh_var.get()
        
        if self.auto_refresh:
            # Start auto-refresh thread
            if self.refresh_thread is None or not self.refresh_thread.is_alive():
                self.refresh_thread = threading.Thread(target=self._auto_refresh_thread, daemon=True)
                self.refresh_thread.start()
                self.update_status(f"Auto-refresh enabled (every {self.refresh_interval} seconds)")
        else:
            self.update_status("Auto-refresh disabled")
            
    def _auto_refresh_thread(self) -> None:
        """Thread function for auto-refreshing results."""
        while self.auto_refresh:
            # Sleep for the refresh interval
            time.sleep(self.refresh_interval)
            
            # Check if auto-refresh is still enabled
            if not self.auto_refresh:
                break
                
            # Refresh results in the main thread
            if self.winfo_exists():
                self.after(0, self._load_results) 