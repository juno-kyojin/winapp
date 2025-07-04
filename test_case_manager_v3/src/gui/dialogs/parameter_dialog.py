#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parameter Dialog for Test Case Manager v1.0

This module provides a dialog for editing test case parameters.

Author: juno-kyojin
Created: 2025-06-25
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, cast

from gui.widgets.parameter_editor import ParameterEditor
from utils.logger import get_logger


class ParameterDialog:
    """
    Dialog for editing test case parameters.
    
    This dialog allows the user to edit parameters for a test case.
    """
    
    def __init__(self, parent: tk.Tk, parameters: Dict[str, Any],
                title: str = "Edit Parameters") -> None:
        """
        Initialize the parameter dialog.
        
        Args:
            parent: Parent widget
            parameters: Parameter data to edit
            title: Dialog title
        """
        self.parent = parent
        self.parameters = parameters.copy() if parameters else {}
        self.title = title
        self.logger = get_logger(__name__)
        self.dialog: Optional[tk.Toplevel] = None
        self.result: Optional[Dict[str, Any]] = None
        
        # Create and show dialog
        self._create_dialog()
    
    def _create_dialog(self) -> None:
        """Create the parameter dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("600x400")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create parameter editor
        self.parameter_editor = ParameterEditor(cast(tk.Widget, self.dialog))
        self.parameter_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Set parameters
        self.parameter_editor.set_parameters(self.parameters)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self._cancel
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            buttons_frame,
            text="OK",
            command=self._ok
        ).pack(side=tk.RIGHT, padx=5)
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self._cancel)
        
        # Make dialog modal
        self.dialog.wait_window()
    
    def _ok(self) -> None:
        """Save parameters and close dialog."""
        try:
            # Get parameters from editor
            self.result = self.parameter_editor.get_parameters()
            if self.dialog:
                self.dialog.destroy()
        except Exception as e:
            self.logger.error(f"Error saving parameters: {e}")
            self.result = None
            if self.dialog:
                self.dialog.destroy()
    
    def _cancel(self) -> None:
        """Cancel and close dialog."""
        self.result = None
        if self.dialog:
            self.dialog.destroy() 
