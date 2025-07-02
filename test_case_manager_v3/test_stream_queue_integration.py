#!/usr/bin/env python3
"""
Test script for Stream tab queue execution integration.

This script tests the enhanced Stream tab functionality that displays
comprehensive queue execution progress information during batch test execution.

Author: juno-kyojin
Created: 2025-07-02
"""

import tkinter as tk
from tkinter import ttk
import sys
import os
import time
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.gui.panels.stream_panel import StreamPanel
from src.gui.panels.queue_panel import QueuePanel


class StreamQueueTestApp:
    """Test application for Stream tab queue execution integration."""
    
    def __init__(self):
        """Initialize the test application."""
        self.root = tk.Tk()
        self.root.title("Stream Tab Queue Execution Test")
        self.root.geometry("1000x700")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create Queue tab
        self.queue_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.queue_frame, text="Queue")
        
        # Create Stream tab
        self.stream_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stream_frame, text="Stream")
        
        # Initialize panels
        self.status_var = tk.StringVar(value="Ready")
        self.init_panels()
        
        # Create status bar
        self.create_status_bar()
        
        # Add test data
        self.add_test_data()
        
    def init_panels(self):
        """Initialize the queue and stream panels."""
        # Initialize Stream Panel
        self.stream_panel = StreamPanel(
            self.stream_frame,
            self.update_status
        )
        self.stream_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initialize Queue Panel
        self.queue_panel = QueuePanel(
            self.queue_frame,
            self.update_status,
            self.execute_test
        )
        self.queue_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Connect queue panel to stream panel
        self.queue_panel.stream_panel = self.stream_panel
        
    def create_status_bar(self):
        """Create status bar."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)
        
    def update_status(self, message: str):
        """Update status message."""
        self.status_var.set(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
        self.root.update_idletasks()
        
    def execute_test(self, test_data: dict, affects_network: bool = False):
        """
        Mock test execution function.
        
        Args:
            test_data: Test data to execute
            affects_network: Whether test affects network
        """
        test_name = test_data.get('name', 'Unknown Test')
        
        # Start test stream
        self.stream_panel.start_test_stream(test_name, test_data)
        
        # Simulate test execution phases
        phases = [
            (10, "preparing", "📋 Validating test data and connection"),
            (30, "sending", "📡 Sending test data to device"),
            (60, "processing", "⚙️ Device is processing test case"),
            (90, "receiving", "📥 Receiving test results from device"),
        ]
        
        for progress, status, message in phases:
            self.stream_panel.update_stream_status(status, message, progress)
            time.sleep(1)  # Simulate processing time
            self.root.update()
        
        # Simulate random success/failure
        import random
        success = random.choice([True, True, True, False])  # 75% success rate
        
        if success:
            final_message = f"Test completed successfully in {random.uniform(1.5, 3.0):.1f}s"
            self.stream_panel.end_test_stream(True, final_message)
        else:
            final_message = f"Test failed: Connection timeout after {random.uniform(0.5, 1.5):.1f}s"
            self.stream_panel.end_test_stream(False, final_message)
            
    def add_test_data(self):
        """Add sample test data to the queue."""
        test_cases = [
            {
                "name": "ping",
                "service": "ping",
                "params": {"host1": "google.com", "host2": "youtube.com"}
            },
            {
                "name": "wan_delete",
                "service": "wan",
                "params": {"action": "delete", "interface": "wan"}
            },
            {
                "name": "wan_create",
                "service": "wan", 
                "params": {"action": "create", "interface": "wan", "protocol": "dhcp"}
            },
            {
                "name": "wan_edit",
                "service": "wan",
                "params": {"action": "edit", "interface": "wan", "dns": "8.8.8.8"}
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            self.queue_panel.add_to_queue(
                test_data=test_case,
                category="Network" if "wan" in test_case["name"] else "Connectivity",
                name=test_case["name"]
            )
            
    def run(self):
        """Run the test application."""
        print("Stream Tab Queue Execution Test")
        print("=" * 50)
        print("1. Click on Queue tab to see test queue")
        print("2. Click 'Execute All' to run all tests")
        print("3. Switch to Stream tab to see real-time progress")
        print("4. Observe queue execution tracking:")
        print("   - Total test count display")
        print("   - Progress tracking (Completed: X/Y tests)")
        print("   - Current test information")
        print("   - Real-time status updates")
        print("=" * 50)
        
        self.root.mainloop()


if __name__ == "__main__":
    app = StreamQueueTestApp()
    app.run()
