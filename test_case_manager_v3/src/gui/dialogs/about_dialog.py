#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
About Dialog for Test Case Manager v3.0

This module provides an about dialog for displaying application information.

Author: juno-kyojin
Created: 2025-06-25
"""

import tkinter as tk
from tkinter import ttk
import platform
import sys
from typing import Optional

from src.core.constants import APP_NAME, APP_VERSION


class AboutDialog:
    """
    About dialog for displaying application information.
    
    This dialog displays information about the application, including
    version, author, and system information.
    """
    
    def __init__(self, parent: tk.Tk) -> None:
        """
        Initialize the about dialog.
        
        Args:
            parent: Parent widget
        """
        self.parent = parent
        self.dialog: Optional[tk.Toplevel] = None
        
        self._create_dialog()
    
    def _create_dialog(self) -> None:
        """Create the about dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"About {APP_NAME}")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Application name and version
        title_frame = ttk.Frame(self.dialog)
        title_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Label(
            title_frame,
            text=APP_NAME,
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 5))
        
        ttk.Label(
            title_frame,
            text=f"Version {APP_VERSION}",
            font=("Arial", 12)
        ).pack()
        
        # Separator
        ttk.Separator(self.dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=10)
        
        # Application information
        info_frame = ttk.Frame(self.dialog)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        ttk.Label(
            info_frame,
            text="Test Case Manager for Network Devices",
            wraplength=360,
            justify=tk.CENTER
        ).pack(pady=5)
        
        ttk.Label(
            info_frame,
            text="© 2025 Juno Kyojin",
            foreground="gray"
        ).pack(pady=5)
        
        # System information
        sys_frame = ttk.LabelFrame(info_frame, text="System Information")
        sys_frame.pack(fill=tk.X, pady=10)
        
        # Python version
        py_frame = ttk.Frame(sys_frame)
        py_frame.pack(fill=tk.X, padx=10, pady=2)
        
        ttk.Label(
            py_frame,
            text="Python:",
            width=12,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            py_frame,
            text=f"{platform.python_version()} ({platform.python_implementation()})"
        ).pack(side=tk.LEFT)
        
        # OS version
        os_frame = ttk.Frame(sys_frame)
        os_frame.pack(fill=tk.X, padx=10, pady=2)
        
        ttk.Label(
            os_frame,
            text="OS:",
            width=12,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            os_frame,
            text=f"{platform.system()} {platform.version()}"
        ).pack(side=tk.LEFT)
        
        # Close button
        ttk.Button(
            self.dialog,
            text="Close",
            command=self._close_dialog
        ).pack(pady=10)
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self._close_dialog)
        
        # Make dialog modal
        self.dialog.wait_window()
    
    def _close_dialog(self) -> None:
        """Close the dialog."""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None 
