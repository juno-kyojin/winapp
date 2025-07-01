#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Queue Manager Widget for Test Case Manager v3.0

This module provides a widget for managing test case execution queue.

Author: juno-kyojin
Created: 2025-06-25
"""

import tkinter as tk
from tkinter import ttk
import json
import uuid
from typing import Dict, Any, List, Optional, Callable, Tuple, Union

from utils.logger import get_logger


class QueueManager(ttk.Frame):
    """
    Widget for managing test case execution queue.
    
    This widget provides a UI for adding, removing, and executing
    test cases in a queue.
    """
    
    # Test status constants
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CANCELED = "canceled"
    
    def __init__(self, parent: tk.Widget, 
                on_selection_change: Optional[Callable] = None,
                on_double_click: Optional[Callable] = None) -> None:
        """
        Initialize the queue manager.
        
        Args:
            parent: Parent widget
            on_selection_change: Callback when selection changes
            on_double_click: Callback when item is double-clicked
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        
        # Callbacks
        self.on_selection_change = on_selection_change
        self.on_double_click = on_double_click
        
        # Queue data
        self.queue_items: List[Dict[str, Any]] = []
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Toolbar frame
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Queue controls
        ttk.Button(
            toolbar,
            text="Run All",
            command=self._run_all
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Run Selected",
            command=self._run_selected
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Remove",
            command=self._remove_selected
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Clear All",
            command=self._clear_all
        ).pack(side=tk.LEFT, padx=2)
        
        # Queue count
        self.queue_count_var = tk.StringVar(value="Queue: 0 items")
        ttk.Label(
            toolbar,
            textvariable=self.queue_count_var
        ).pack(side=tk.RIGHT, padx=5)
        
        # Queue treeview with scrollbar
        queue_frame = ttk.Frame(self)
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(queue_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        self.queue_tree = ttk.Treeview(
            queue_frame,
            columns=("name", "category", "status", "time"),
            show="headings",
            selectmode="extended"
        )
        self.queue_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=self.queue_tree.yview)
        self.queue_tree.config(yscrollcommand=scrollbar.set)
        
        # Configure columns
        self.queue_tree.heading("name", text="Test Name")
        self.queue_tree.heading("category", text="Category")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.heading("time", text="Time")
        
        self.queue_tree.column("name", width=250)
        self.queue_tree.column("category", width=100)
        self.queue_tree.column("status", width=100)
        self.queue_tree.column("time", width=100)
        
        # Configure tags for status colors
        self.queue_tree.tag_configure("pending", background="#f5f5f5")
        self.queue_tree.tag_configure("running", background="#e3f2fd")
        self.queue_tree.tag_configure("success", background="#e8f5e9")
        self.queue_tree.tag_configure("failed", background="#ffebee")
        self.queue_tree.tag_configure("canceled", background="#fafafa")
        
        # Bind events
        self.queue_tree.bind("<<TreeviewSelect>>", self._on_item_selected)
        self.queue_tree.bind("<Double-1>", self._on_item_double_clicked)
    
    def add_test(self, test_data: Dict[str, Any]) -> str:
        """
        Add a test to the queue.
        
        Args:
            test_data: Test data to add
            
        Returns:
            Queue item ID
        """
        # Generate a unique ID for this queue item
        item_id = str(uuid.uuid4())
        
        # Extract test name and category
        test_name = "Unknown Test"
        category = "Unknown"
        
        # Try to extract test name from test data
        if "metadata" in test_data and "name" in test_data["metadata"]:
            test_name = test_data["metadata"]["name"]
        elif "test_cases" in test_data and test_data["test_cases"]:
            first_test = test_data["test_cases"][0]
            if "service" in first_test and "action" in first_test:
                test_name = f"{first_test['service']}.{first_test['action']}"
            
        # Try to extract category from test data
        if "metadata" in test_data and "category" in test_data["metadata"]:
            category = test_data["metadata"]["category"]
        
        # Create queue item
        queue_item = {
            "id": item_id,
            "test_data": test_data,
            "status": self.STATUS_PENDING,
            "name": test_name,
            "category": category,
            "time": "-",
            "result": None
        }
        
        # Add to queue
        self.queue_items.append(queue_item)
        
        # Add to treeview
        self.queue_tree.insert(
            "",
            tk.END,
            item_id,
            values=(test_name, category, "Pending", "-"),
            tags=(self.STATUS_PENDING,)
        )
        
        # Update queue count
        self._update_queue_count()
        
        return item_id
    
    def update_test_status(self, item_id: str, status: str, 
                          message: Optional[str] = None,
                          execution_time: Optional[str] = None,
                          result: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the status of a test in the queue.
        
        Args:
            item_id: Queue item ID
            status: New status
            message: Optional status message
            execution_time: Optional execution time
            result: Optional test result data
        """
        # Find queue item
        item_index = None
        for i, item in enumerate(self.queue_items):
            if item["id"] == item_id:
                item_index = i
                break
        
        if item_index is None:
            self.logger.warning(f"Queue item {item_id} not found")
            return
        
        # Update queue item
        self.queue_items[item_index]["status"] = status
        if execution_time is not None:
            self.queue_items[item_index]["time"] = execution_time
        if result is not None:
            self.queue_items[item_index]["result"] = result
        
        # Update treeview
        status_text = status.capitalize()
        if message:
            status_text = f"{status_text}: {message}"
        
        time_text = execution_time if execution_time is not None else "-"
        
        self.queue_tree.item(
            item_id,
            values=(
                self.queue_items[item_index]["name"],
                self.queue_items[item_index]["category"],
                status_text,
                time_text
            ),
            tags=(status,)
        )
    
    def get_selected_items(self) -> List[Dict[str, Any]]:
        """
        Get the selected queue items.
        
        Returns:
            List of selected queue items
        """
        selected_ids = self.queue_tree.selection()
        selected_items = []
        
        for item_id in selected_ids:
            for item in self.queue_items:
                if item["id"] == item_id:
                    selected_items.append(item)
                    break
        
        return selected_items
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """
        Get all queue items.
        
        Returns:
            List of all queue items
        """
        return self.queue_items.copy()
    
    def clear_queue(self) -> None:
        """Clear the queue."""
        self.queue_items = []
        for item_id in self.queue_tree.get_children():
            self.queue_tree.delete(item_id)
        self._update_queue_count()
    
    def _update_queue_count(self) -> None:
        """Update the queue count display."""
        count = len(self.queue_items)
        self.queue_count_var.set(f"Queue: {count} items")
    
    def _on_item_selected(self, event) -> None:
        """Handle item selection event."""
        if self.on_selection_change:
            selected_items = self.get_selected_items()
            if selected_items:
                self.on_selection_change(selected_items[0])
    
    def _on_item_double_clicked(self, event) -> None:
        """Handle item double-click event."""
        if self.on_double_click:
            selected_items = self.get_selected_items()
            if selected_items:
                self.on_double_click(selected_items[0])
    
    def _run_all(self) -> None:
        """Run all tests in the queue."""
        # This is just a placeholder - actual implementation will be in the panel
        self.event_generate("<<RunAllTests>>")
    
    def _run_selected(self) -> None:
        """Run selected tests in the queue."""
        # This is just a placeholder - actual implementation will be in the panel
        self.event_generate("<<RunSelectedTests>>")
    
    def _remove_selected(self) -> None:
        """Remove selected tests from the queue."""
        selected_ids = self.queue_tree.selection()
        
        # Remove from treeview
        for item_id in selected_ids:
            self.queue_tree.delete(item_id)
        
        # Remove from queue items
        self.queue_items = [
            item for item in self.queue_items
            if item["id"] not in selected_ids
        ]
        
        # Update queue count
        self._update_queue_count()
    
    def _clear_all(self) -> None:
        """Clear all tests from the queue."""
        self.clear_queue() 