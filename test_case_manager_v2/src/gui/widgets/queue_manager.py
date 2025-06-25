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
    
        # Cấu hình màu sắc cho các trạng thái
        self._configure_status_tags()  
        # Bind double click để xem chi tiết
        self.queue_tree.bind("<Double-1>", self._view_test_details)
    def _view_test_details(self, event):
        """Hiển thị cửa sổ chi tiết khi double-click vào test"""
        item = self.queue_tree.identify('item', event.x, event.y)
        if not item:
            return
            
        # Lấy index và dữ liệu item
        index = self.queue_tree.index(item)
        if index < len(self.queue_items):
            test_item = self.queue_items[index]
            
            # Tạo cửa sổ popup
            detail_window = tk.Toplevel(self)
            detail_window.title(f"Test Details: {test_item.get('name', 'Unknown')}")
            detail_window.geometry("500x400")
            detail_window.grab_set()  # Make it modal
            
            # Tạo frame cho nội dung
            content_frame = ttk.Frame(detail_window, padding=10)
            content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Thông tin cơ bản
            ttk.Label(content_frame, text=f"Test ID: {test_item.get('test_id')}", 
                    font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W, pady=3)
            ttk.Label(content_frame, text=f"Name: {test_item.get('name')}").pack(anchor=tk.W, pady=2)
            ttk.Label(content_frame, text=f"Category: {test_item.get('category')}").pack(anchor=tk.W, pady=2)
            
            # Hiển thị status với màu phù hợp
            status_frame = ttk.Frame(content_frame)
            status_frame.pack(fill=tk.X, pady=5)
            
            status = test_item.get('status', 'Unknown')
            status_label = ttk.Label(status_frame, text=f"Status: {status}", width=20)
            status_label.pack(side=tk.LEFT)
            
            # Màu nền cho status dựa trên giá trị
            if status.lower() == "success":
                status_color = "#4CAF50"  # Green
            elif status.lower() == "failed":
                status_color = "#F44336"  # Red
            elif status.lower() == "error":
                status_color = "#FF9800"  # Orange
            elif status.lower() in ["sending", "running"]:
                status_color = "#2196F3"  # Blue
            else:
                status_color = "#9E9E9E"  # Grey
                
            status_indicator = tk.Canvas(status_frame, width=15, height=15, bg=status_color)
            status_indicator.pack(side=tk.LEFT, padx=5)
            
            # Chi tiết message
            if "details" in test_item and "message" in test_item["details"]:
                message_frame = ttk.LabelFrame(content_frame, text="Status Message")
                message_frame.pack(fill=tk.X, pady=5, padx=5)
                
                message = test_item["details"]["message"]
                message_text = tk.Text(message_frame, wrap=tk.WORD, height=3)
                message_text.insert("1.0", message)
                message_text.config(state="disabled")
                message_text.pack(fill=tk.X, padx=5, pady=5)
            
            # Parameters
            param_frame = ttk.LabelFrame(content_frame, text="Parameters")
            param_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
            
            # Tạo scrollable frame cho parameters
            canvas = tk.Canvas(param_frame)
            scrollbar = ttk.Scrollbar(param_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Thêm các tham số
            params = test_item.get("parameters", {})
            for i, (key, value) in enumerate(params.items()):
                param_row = ttk.Frame(scrollable_frame)
                param_row.pack(fill=tk.X, pady=2)
                
                ttk.Label(param_row, text=key, width=15, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(param_row, text="=").pack(side=tk.LEFT, padx=5)
                
                # Format value dựa vào kiểu dữ liệu
                if isinstance(value, list):
                    value_text = json.dumps(value)
                elif isinstance(value, bool):
                    value_text = str(value).lower()
                else:
                    value_text = str(value)
                    
                value_label = ttk.Label(param_row, text=value_text, anchor=tk.W)
                value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Đặt canvas và scrollbar vào param_frame
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Timing info
            if "details" in test_item and "last_updated" in test_item["details"]:
                ttk.Label(content_frame, text=f"Last updated: {test_item['details']['last_updated']}",
                        font=("TkDefaultFont", 8)).pack(anchor=tk.E, pady=5)
            
            # Nút đóng
            ttk.Button(content_frame, text="Close", command=detail_window.destroy).pack(pady=10)
    def _configure_status_tags(self):
        """Cấu hình màu sắc cho các trạng thái khác nhau"""
        self.queue_tree.tag_configure("sending", background="#FFFDE7")  # Màu vàng nhạt
        self.queue_tree.tag_configure("running", background="#E1F5FE")  # Màu xanh dương nhạt
        self.queue_tree.tag_configure("success", background="#E8F5E9")  # Màu xanh lá nhạt
        self.queue_tree.tag_configure("failed", background="#FFEBEE")   # Màu đỏ nhạt
        self.queue_tree.tag_configure("error", background="#FCE4EC")    # Màu hồng nhạt
        self.queue_tree.tag_configure("queued", background="#F5F5F5")   # Màu xám nhạt  
    def add_item(self, test_id, name, category, parameters, service="", action=""):
        """
        Add item to queue với thông tin service và action đầy đủ
        
        Args:
            test_id: Test identifier string
            name: Display name
            category: Category name
            parameters: Dictionary of parameters
            service: Service name từ file JSON gốc
            action: Action name từ file JSON gốc
        
        Returns:
            bool: True if added successfully
        """
        # Create item data object
        item_data = {
            "test_id": test_id,
            "name": name,
            "category": category,
            "parameters": parameters.copy() if parameters else {},
            "status": "Queued",
            "service": service,  # Lưu trữ service từ file JSON
            "action": action     # Lưu trữ action từ file JSON
        }
        
        # Add to internal list
        self.queue_items.append(item_data)
        
        # Add to treeview
        order = len(self.queue_items)
        param_text = ", ".join([f"{k}:{v}" for k,v in parameters.items()])[:50] if parameters else ""
        
        # Update parameter text for display
        if len(param_text) >= 50:
            param_text += "..."
        
        # Insert into treeview
        self.queue_tree.insert("", "end", values=(
            order,
            name,
            category,
            param_text,
            "Queued"
        ))
        
        # Không sử dụng logger vì không tồn tại trong class
        # Thay thế bằng print debug nếu cần
        # print(f"Added to queue: {test_id}, service={service}, action={action}")
        
        return True
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
        """Refresh the queue view with current items"""
        # Clear current view
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # Add items from queue
        for i, item in enumerate(self.queue_items):
            # Đảm bảo order tồn tại
            if "order" not in item:
                item["order"] = i + 1  # Tạo order dựa trên vị trí hiện tại
                
            self.queue_tree.insert("", "end", values=(
                item["order"],
                item.get("test_id", ""),
                item.get("name", ""),
                item.get("service", ""),
                item.get("action", ""),
                item.get("status", "Queued")
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
        """
        Cập nhật trạng thái test với hiển thị cải tiến
        
        Args:
            index: Chỉ số của test trong queue
            status: Trạng thái mới (Sending, Running, Success, Failed, Error)
            message: Thông điệp bổ sung (nếu có)
        """
        items = self.queue_tree.get_children()
        if 0 <= index < len(items):
            item_id = items[index]
            values = list(self.queue_tree.item(item_id, "values"))
            
            # Cột "status" ở index 4
            status_col = 4
            if len(values) > status_col:
                # Thêm icon cho trạng thái
                if status.lower() == "sending":
                    status_display = "🔄 " + status
                    self.queue_tree.item(item_id, tags=("sending",))
                elif status.lower() == "running":
                    status_display = "⏳ " + status
                    self.queue_tree.item(item_id, tags=("running",))
                elif status.lower() == "success":
                    status_display = "✅ " + status
                    self.queue_tree.item(item_id, tags=("success",))
                elif status.lower() == "failed":
                    status_display = "❌ " + status
                    self.queue_tree.item(item_id, tags=("failed",))
                elif status.lower() == "error":
                    status_display = "⚠️ " + status
                    self.queue_tree.item(item_id, tags=("error",))
                elif status.lower() == "queued":
                    status_display = "📋 " + status
                    self.queue_tree.item(item_id, tags=("queued",))
                else:
                    status_display = status
                
                # Thêm message nếu có
                if message:
                    status_display += f": {message}"
                    
                    # Giới hạn độ dài hiển thị
                    if len(status_display) > 40:
                        status_display = status_display[:37] + "..."
                
                values[status_col] = status_display
                
                # Cập nhật UI
                self.queue_tree.item(item_id, values=tuple(values))
                
                # Đảm bảo item nhìn thấy được trong view
                self.queue_tree.see(item_id)
                
                # Cập nhật dữ liệu nội bộ
                if index < len(self.queue_items):
                    # Cập nhật trạng thái
                    self.queue_items[index]["status"] = status
                    
                    # Lưu message vào thuộc tính tạm thời
                    if message:
                        if "details" not in self.queue_items[index]:
                            self.queue_items[index]["details"] = {}
                        
                        self.queue_items[index]["details"]["message"] = message
                        self.queue_items[index]["details"]["last_updated"] = "2025-06-24 01:25:56"  # Thời gian hiện tại

        