#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Queue Manager Widget

This module implements a reusable widget for managing the test queue,
including adding, removing, and reordering test cases.

Author: juno-kyojin
Created: 2025-06-12
"""

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Optional, Callable
import time
from datetime import datetime

class TestQueueManager(ttk.Frame):
    """Test Queue Manager widget for managing test cases"""
    
    def __init__(self, parent, on_selection_change=None, on_run_all=None, on_run_selected=None):
        """Initialize the queue manager"""
        super().__init__(parent)
        
        # Callbacks
        self.on_selection_change = on_selection_change
        self.on_run_all = on_run_all
        self.on_run_selected = on_run_selected
        
        # QUAN TRỌNG: Khởi tạo các thuộc tính trạng thái
        self.running = False
        self.current_index = -1
        
        # Queue data structures
        self.queue_items = []
        self.next_order = 1
        
        # Create GUI components
        self._create_widgets()
        
        # Set up drag and drop functionality
        self._setup_drag_drop()

    def _setup_drag_drop(self):
        """Set up drag and drop functionality for the queue items"""
        # Đây là các biến để theo dõi thao tác kéo thả
        self.drag_source_index = None
        self.drag_item_id = None
        
        # Bind các sự kiện chuột để hỗ trợ drag & drop
        self.queue_tree.bind("<ButtonPress-1>", self._on_drag_start)
        self.queue_tree.bind("<B1-Motion>", self._on_drag_motion)
        self.queue_tree.bind("<ButtonRelease-1>", self._on_drag_end)

    def _on_drag_start(self, event):
        """Handle start of drag operation"""
        # Xác định item được click
        item_id = self.queue_tree.identify_row(event.y)
        if item_id:
            # Lưu thông tin item đang kéo để sử dụng sau này
            self.drag_source_index = self.queue_tree.index(item_id)
            self.drag_item_id = item_id

    def _on_drag_motion(self, event):
        """Handle drag motion"""
        # Chỉ xử lý nếu đang kéo một item
        if self.drag_item_id:
            pass  # Trong phase 1, chúng ta không cần hiệu ứng đặc biệt
    
    def _on_drag_end(self, event):
        """Handle end of drag operation"""
        # Chỉ xử lý nếu đang kéo một item
        if self.drag_item_id and self.drag_source_index is not None:
            # Xác định vị trí thả
            target_id = self.queue_tree.identify_row(event.y)
            if target_id and target_id != self.drag_item_id:
                target_index = self.queue_tree.index(target_id)
                
                # Di chuyển item trong queue
                item = self.queue_items.pop(self.drag_source_index)
                self.queue_items.insert(target_index, item)
                
                # Cập nhật số thứ tự
                for i, item in enumerate(self.queue_items):
                    item["order"] = i + 1
                    
                # Cập nhật TreeView
                self._refresh_queue_view()
                
                # Chọn lại item đã di chuyển
                items = self.queue_tree.get_children()
                if 0 <= target_index < len(items):
                    self.queue_tree.selection_set(items[target_index])
            
            # Reset các biến theo dõi
            self.drag_source_index = None
            self.drag_item_id = None
            

    
    def _create_widgets(self):
        """Create all widgets for the queue manager"""
        # Control buttons at top
        self.control_frame = ttk.Frame(self)
        self.control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(self.control_frame, text="Run All", command=self.run_all_tests).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Run Selected", command=self.run_selected_tests).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Clear Queue", command=self.clear_queue).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.control_frame, text="Save Queue", command=self.save_queue).pack(side=tk.RIGHT, padx=5)
        ttk.Button(self.control_frame, text="Load Queue", command=self.load_queue).pack(side=tk.RIGHT, padx=5)
        
        # Main queue table
        self.queue_frame = ttk.Frame(self)
        self.queue_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create TreeView for queue
        columns = ("order", "name", "category", "parameters", "status")
        self.queue_tree = ttk.Treeview(self.queue_frame, columns=columns, show="headings", selectmode="browse")
        
        # Configure headings
        self.queue_tree.heading("order", text="#")
        self.queue_tree.heading("name", text="Test Name")
        self.queue_tree.heading("category", text="Category")
        self.queue_tree.heading("parameters", text="Parameters")
        self.queue_tree.heading("status", text="Status")
        
        # Configure column widths
        self.queue_tree.column("order", width=40, anchor=tk.CENTER)
        self.queue_tree.column("name", width=200, anchor=tk.W)
        self.queue_tree.column("category", width=100, anchor=tk.W)
        self.queue_tree.column("parameters", width=300, anchor=tk.W)
        self.queue_tree.column("status", width=100, anchor=tk.CENTER)
        
        # Add vertical scrollbar
        scrollbar_y = ttk.Scrollbar(self.queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=scrollbar_y.set)
        
        # Add horizontal scrollbar
        scrollbar_x = ttk.Scrollbar(self.queue_frame, orient=tk.HORIZONTAL, command=self.queue_tree.xview)
        self.queue_tree.configure(xscrollcommand=scrollbar_x.set)
        
        # Pack TreeView and scrollbars
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind selection event
        self.queue_tree.bind("<<TreeviewSelect>>", self._on_queue_item_selected)
        
        # Item control buttons at bottom
        self.item_control_frame = ttk.Frame(self)
        self.item_control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(self.item_control_frame, text="Move Up", command=self.move_item_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.item_control_frame, text="Move Down", command=self.move_item_down).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.item_control_frame, text="Remove", command=self.remove_selected_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.item_control_frame, text="Edit Parameters", command=self.edit_parameters).pack(side=tk.RIGHT, padx=5)
    
    def add_item(self, test_id: str, name: str, category: str, parameters: Dict) -> bool:
        """
        Add item to the queue
        
        Args:
            test_id: Test case ID
            name: Display name
            category: Test category
            parameters: Test parameters
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            # Create item data
            order = len(self.queue_items) + 1
            item_data = {
                "order": order,
                "test_id": test_id,
                "name": name, 
                "category": category,
                "parameters": parameters,
                "status": "Queued"
            }
            
            # Add to internal list
            self.queue_items.append(item_data)
            
            # Format parameters for display
            params_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])
            if len(params_str) > 40:
                params_str = params_str[:37] + "..."
            
            # Add to TreeView
            self.queue_tree.insert("", "end", values=(
                order,
                name,
                category,
                params_str,
                "Queued"
            ))
            
            return True
        except Exception as e:
            print(f"Error adding item to queue: {e}")
            return False
    
    def move_item_up(self):
        """Move the selected item up in the queue"""
        selected = self.queue_tree.selection()
        if not selected:
            return
        
        # Get current item and index
        curr_idx = self.queue_tree.index(selected[0])
        if curr_idx == 0:  # Already at the top
            return
        
        # Swap items in the internal list
        self.queue_items[curr_idx], self.queue_items[curr_idx-1] = \
            self.queue_items[curr_idx-1], self.queue_items[curr_idx]
        
        # Update order numbers
        self.queue_items[curr_idx]["order"] = curr_idx + 1
        self.queue_items[curr_idx-1]["order"] = curr_idx
        
        # Refresh the TreeView to reflect the changes
        self._refresh_queue_view()
        
        # Select the moved item
        items = self.queue_tree.get_children()
        self.queue_tree.selection_set(items[curr_idx-1])
    
    def move_item_down(self):
        """Move the selected item down in the queue"""
        selected = self.queue_tree.selection()
        if not selected:
            return
        
        # Get current item and index
        curr_idx = self.queue_tree.index(selected[0])
        if curr_idx >= len(self.queue_items) - 1:  # Already at the bottom
            return
        
        # Swap items in the internal list
        self.queue_items[curr_idx], self.queue_items[curr_idx+1] = \
            self.queue_items[curr_idx+1], self.queue_items[curr_idx]
        
        # Update order numbers
        self.queue_items[curr_idx]["order"] = curr_idx + 1
        self.queue_items[curr_idx+1]["order"] = curr_idx + 2
        
        # Refresh the TreeView to reflect the changes
        self._refresh_queue_view()
        
        # Select the moved item
        items = self.queue_tree.get_children()
        self.queue_tree.selection_set(items[curr_idx+1])
    
    def remove_selected_item(self):
        """Remove the selected item from the queue"""
        selected = self.queue_tree.selection()
        if not selected:
            return
        
        # Get current item and index
        curr_idx = self.queue_tree.index(selected[0])
        
        # Remove from internal list
        self.queue_items.pop(curr_idx)
        
        # Update order numbers for remaining items
        for i in range(curr_idx, len(self.queue_items)):
            self.queue_items[i]["order"] = i + 1
        
        # Refresh the TreeView
        self._refresh_queue_view()
    
    def clear_queue(self):
        """Clear the entire queue"""
        if not self.queue_items:
            return
            
        # Ask for confirmation
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the entire queue?"):
            self.queue_items = []
            self._refresh_queue_view()
    
    def _refresh_queue_view(self):
        """Refresh the TreeView to match the internal queue items"""
        # Clear existing items
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # Add updated items
        for item in self.queue_items:
            # Format parameters for display
            params = item.get("parameters", {})
            params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
            if len(params_str) > 40:
                params_str = params_str[:37] + "..."
            
            self.queue_tree.insert("", "end", values=(
                item["order"],
                item["name"],
                item["category"],
                params_str,
                item["status"]
            ))
    
    def _on_queue_item_selected(self, event):
        """Handle queue item selection"""
        if self.on_selection_change:
            selected = self.queue_tree.selection()
            if selected:
                idx = self.queue_tree.index(selected[0])
                if idx < len(self.queue_items):
                    self.on_selection_change(self.queue_items[idx])
    
    def edit_parameters(self):
        """Edit parameters for the selected test"""
        selected = self.queue_tree.selection()
        if not selected:
            messagebox.showinfo("Information", "Please select a test case first")
            return
        
        # Get current item and index
        curr_idx = self.queue_tree.index(selected[0])
        item = self.queue_items[curr_idx]
        
        # In a real implementation, this would open a parameter edit dialog
        # For Phase 1, we'll just show a message
        messagebox.showinfo("Edit Parameters", 
                           f"Parameter editing will be implemented in Phase 2\n\n"
                           f"Test: {item['name']}\n"
                           f"Parameters: {item['parameters']}")
    
    def save_queue(self):
        """Save the current queue to a file"""
        if not self.queue_items:
            messagebox.showinfo("Information", "Queue is empty, nothing to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Queue"
        )
        
        if not file_path:
            return
        
        try:
            # Create queue data structure
            queue_data = {
                "name": os.path.basename(file_path),
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "items": self.queue_items
            }
            
            with open(file_path, 'w') as f:
                json.dump(queue_data, f, indent=2)
                
            messagebox.showinfo("Success", f"Queue saved to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save queue: {str(e)}")
    
    def load_queue(self):
        """Load a queue from a file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Load Queue"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                queue_data = json.load(f)
            
            # Clear current queue
            self.queue_items = []
            
            # Load items from file
            if "items" in queue_data and isinstance(queue_data["items"], list):
                self.queue_items = queue_data["items"]
                
                # Make sure order numbers are correct
                for i, item in enumerate(self.queue_items):
                    item["order"] = i + 1
                    
                # Refresh the view
                self._refresh_queue_view()
                
                messagebox.showinfo("Success", f"Loaded {len(self.queue_items)} items from {file_path}")
            else:
                messagebox.showerror("Error", "Invalid queue file format")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load queue: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests in the queue"""
        if not self.queue_items:
            messagebox.showinfo("Information", "Queue is empty, nothing to run")
            return
        
        # Sử dụng callback nếu được cung cấp
        if callable(self.on_run_all):
            self.on_run_all()
        else:
            # Fallback to legacy behavior
            messagebox.showinfo("Run Tests", 
                        "Test execution will be implemented in Phase 2\n\n"
                            f"Would run {len(self.queue_items)} tests in sequence")


    def run_selected_tests(self):
        """Run selected test(s) from queue using callback"""
        # Lấy item được chọn
        selected = self.queue_tree.selection()
        
        if not selected:
            messagebox.showinfo("No Selection", "Please select a test to run")
            return
        
        # Lấy index của item được chọn
        try:
            index = self.queue_tree.index(selected[0])
            
            # Gọi callback nếu được cung cấp
            if self.on_run_selected:
                # Gọi callback với index đã chọn
                self.on_run_selected(index)
            else:
                messagebox.showinfo("Not Implemented", "Run Selected not implemented")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run selected test: {str(e)}")

    def _run_test_at_index(self, curr_idx):
        """Run the test at specified index with improved error handling"""
        try:
            # Kiểm tra chỉ số trước khi truy cập
            if curr_idx < 0 or curr_idx >= len(self.queue_items):
                self.running = False
                return
                
            # Lấy item và gọi callback với chỉ số
            item = self.queue_items[curr_idx]
            
            # Cập nhật trạng thái hiện tại
            self.current_index = curr_idx
            
            # Gọi callback nếu có
            if self.on_run_selected:
                self.on_run_selected(curr_idx)
        except Exception as e:
            messagebox.showerror("Error", f"Error running test: {str(e)}")
            self.running = False

    def _continue_to_next_test(self):
        """Continue to the next test if possible"""
        try:
            next_idx = self.current_index + 1
            
            # Kiểm tra có còn test nào không
            if next_idx >= len(self.queue_items):
                # Đã chạy hết các test
                self.running = False
                return
            
            # Cập nhật trạng thái và chạy test tiếp theo
            self.current_index = next_idx
            self._run_test_at_index(self.current_index)
        except Exception as e:
            messagebox.showerror("Error", f"Error advancing to next test: {str(e)}")
            self.running = False            
    def update_status(self, index, status, message=None):
        """Update status of a test in the queue"""
        items = self.queue_tree.get_children()  # Sử dụng queue_tree thay vì test_queue
        if 0 <= index < len(items):
            item_id = items[index]
            values = list(self.queue_tree.item(item_id, "values"))  # Sử dụng queue_tree
            
            # Cột "status" thực ra ở index 4 dựa vào định nghĩa columns
            # columns = ("order", "name", "category", "parameters", "status")
            status_col = 4  # Cột thứ 5 (index 4)
            if len(values) > status_col:
                values[status_col] = status
                
            # Không có cột message riêng trong implementation hiện tại
            # Có thể cập nhật vào cột parameters nếu cần hiển thị message
            
            # Cập nhật UI
            self.queue_tree.item(item_id, values=tuple(values))  # Sử dụng queue_tree
            
            # Cập nhật dữ liệu nội bộ
            if index < len(self.queue_items):
                self.queue_items[index]["status"] = status
                if message:
                    self.queue_items[index]["message"] = message

        