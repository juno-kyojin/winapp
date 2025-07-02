#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Status Bar Widget for Test Case Manager v3.0

This module provides a status bar widget for displaying status information.

Author: juno-kyojin
Created: 2025-06-25
"""

import tkinter as tk
from tkinter import ttk
import time
from typing import Optional

from src.utils.logger import get_logger


class StatusBar(ttk.Frame):
    """
    Status bar widget for displaying status information.
    
    This widget provides a status bar with message display and
    optional progress indicator.
    """
    
    def __init__(self, parent: tk.Widget) -> None:
        """
        Initialize the status bar.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        
        # Create UI
        self._create_ui()
        
        # Initialize status
        self.set_status("Ready")
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Status message
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Progress indicator (hidden by default)
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            mode="determinate",
            length=100
        )
        

        
        # Time display
        self.time_var = tk.StringVar()
        self.time_label = ttk.Label(
            self,
            textvariable=self.time_var,
            width=8,
            anchor=tk.E,
            padding=(5, 2)
        )
        self.time_label.pack(side=tk.RIGHT)
        
        # Update time
        self._update_time()
    
    def set_status(self, message: str) -> None:
        """
        Set the status message.
        
        Args:
            message: Status message to display
        """
        self.status_var.set(message)
        self.logger.info(f"Status: {message}")
    

    
    def show_progress(self, show: bool = True) -> None:
        """
        Show or hide the progress bar.
        
        Args:
            show: Whether to show the progress bar
        """
        if show:
            self.progress_bar.pack(side=tk.RIGHT, padx=5)
        else:
            self.progress_bar.pack_forget()
    
    def set_progress(self, value: int) -> None:
        """
        Set the progress value.
        
        Args:
            value: Progress value (0-100)
        """
        self.progress_var.set(value)
    
    def _update_time(self) -> None:
        """Update the time display."""
        current_time = time.strftime("%H:%M:%S")
        self.time_var.set(current_time)
        
        # Update every second
        self.after(1000, self._update_time) 