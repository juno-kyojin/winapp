#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parameter Editor Widget for Test Case Manager v1.0

This module provides a widget for editing test case parameters.

Author: juno-kyojin
Created: 2025-06-25
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
from typing import Dict, Any, List, Optional, Callable, Tuple, Union

from utils.logger import get_logger


class ParameterEditor(ttk.Frame):
    """
    Widget for editing test case parameters.
    
    This widget provides a UI for editing key-value parameters
    for test cases.
    """
    
    # Parameter types
    TYPE_STRING = "string"
    TYPE_NUMBER = "number"
    TYPE_BOOLEAN = "boolean"
    TYPE_ARRAY = "array"
    TYPE_OBJECT = "object"
    
    def __init__(self, parent: tk.Widget) -> None:
        """
        Initialize the parameter editor.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.parameters: Dict[str, Any] = {}
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Create the UI components."""
        # Parameter list frame
        self.param_frame = ttk.Frame(self)
        self.param_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable frame for parameters
        self.canvas = tk.Canvas(self.param_frame)
        scrollbar = ttk.Scrollbar(self.param_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """
        Set parameters to edit.
        
        Args:
            parameters: Parameter data to edit
        """
        self.parameters = parameters.copy() if parameters else {}
        self._refresh_parameters()
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get edited parameters.
        
        Returns:
            Edited parameter data
        """
        # In a real implementation, this would collect values from UI elements
        return self.parameters
    
    def _refresh_parameters(self) -> None:
        """Refresh parameter UI elements."""
        # Clear existing parameters
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Add parameters
        row = 0
        for key, value in self.parameters.items():
            # Parameter key
            ttk.Label(
                self.scrollable_frame,
                text=key,
                width=20,
                anchor=tk.W
            ).grid(row=row, column=0, padx=5, pady=2, sticky=tk.W)
            
            # Parameter value
            if isinstance(value, bool):
                # Boolean value
                var = tk.BooleanVar(value=value)
                ttk.Checkbutton(
                    self.scrollable_frame,
                    variable=var
                ).grid(row=row, column=1, padx=5, pady=2, sticky=tk.W)
            elif isinstance(value, (int, float)):
                # Numeric value
                var = tk.StringVar(value=str(value))
                ttk.Entry(
                    self.scrollable_frame,
                    textvariable=var,
                    width=30
                ).grid(row=row, column=1, padx=5, pady=2, sticky=tk.W)
            else:
                # String or other value
                var = tk.StringVar(value=str(value))
                ttk.Entry(
                    self.scrollable_frame,
                    textvariable=var,
                    width=30
                ).grid(row=row, column=1, padx=5, pady=2, sticky=tk.W)
            
            row += 1
    
    def _add_parameter(self) -> None:
        """Add a new parameter."""
        # Create dialog for adding parameter
        dialog = tk.Toplevel(self)
        dialog.title("Add Parameter")
        dialog.geometry("400x200")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Dialog content
        ttk.Label(
            dialog,
            text="Parameter Name:"
        ).pack(padx=10, pady=(10, 5), anchor=tk.W)
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(
            dialog,
            textvariable=name_var,
            width=40
        )
        name_entry.pack(padx=10, pady=5, fill=tk.X)
        
        ttk.Label(
            dialog,
            text="Parameter Type:"
        ).pack(padx=10, pady=5, anchor=tk.W)
        
        type_var = tk.StringVar(value=self.TYPE_STRING)
        type_combo = ttk.Combobox(
            dialog,
            textvariable=type_var,
            values=[
                self.TYPE_STRING,
                self.TYPE_NUMBER,
                self.TYPE_BOOLEAN,
                self.TYPE_ARRAY,
                self.TYPE_OBJECT
            ],
            state="readonly",
            width=10
        )
        type_combo.pack(padx=10, pady=5, fill=tk.X)
        
        # Buttons frame
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(padx=10, pady=10, fill=tk.X)
        
        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        add_button = ttk.Button(
            buttons_frame,
            text="Add",
            command=lambda: self._add_parameter_action(
                name_var.get(),
                type_var.get(),
                dialog
            )
        )
        add_button.pack(side=tk.RIGHT, padx=5)
        
        # Validate name on change
        def validate_name(*args):
            name = name_var.get()
            if not name:
                add_button.config(state=tk.DISABLED)
            elif name in self.parameters:
                add_button.config(state=tk.DISABLED)
            else:
                add_button.config(state=tk.NORMAL)
        
        name_var.trace("w", validate_name)
        validate_name()
        
        # Focus name entry
        name_entry.focus_set()
    
    def _add_parameter_action(self, name: str, param_type: str, dialog: tk.Toplevel) -> None:
        """
        Add a new parameter with the specified name and type.
        
        Args:
            name: Parameter name
            param_type: Parameter type
            dialog: Dialog window to close
        """
        if not name or name in self.parameters:
            return
        
        # Create default value based on type
        default_value = ""
        if param_type == self.TYPE_NUMBER:
            default_value = 0
        elif param_type == self.TYPE_BOOLEAN:
            default_value = False
        elif param_type == self.TYPE_ARRAY:
            default_value = []
        elif param_type == self.TYPE_OBJECT:
            default_value = {}
        
        # Add parameter
        self.parameters[name] = {
            "type": param_type,
            "value": default_value,
            "description": ""
        }
        
        # Refresh UI
        self._refresh_parameters()
        
        # Close dialog
        dialog.destroy()
    
    def _delete_parameter(self, param_name: str) -> None:
        """
        Delete a parameter.
        
        Args:
            param_name: Name of the parameter to delete
        """
        if param_name in self.parameters:
            # Confirm deletion
            if not messagebox.askyesno(
                "Delete Parameter",
                f"Are you sure you want to delete parameter '{param_name}'?"
            ):
                return
                
            # Delete parameter
            del self.parameters[param_name]
            
            # Refresh UI
            self._refresh_parameters()
    
    def _reset_parameters(self) -> None:
        """Reset all parameters to their default values."""
        if not self.parameters:
            return
            
        # Confirm reset
        if not messagebox.askyesno(
            "Reset Parameters",
            "Are you sure you want to reset all parameters to their default values?"
        ):
            return
            
        # Reset each parameter to its default value
        for name, param in self.parameters.items():
            param_type = param.get("type", self.TYPE_STRING)
            
            if param_type == self.TYPE_STRING:
                param["value"] = ""
            elif param_type == self.TYPE_NUMBER:
                param["value"] = 0
            elif param_type == self.TYPE_BOOLEAN:
                param["value"] = False
            elif param_type == self.TYPE_ARRAY:
                param["value"] = []
            elif param_type == self.TYPE_OBJECT:
                param["value"] = {}
        
        # Refresh UI
        self._refresh_parameters()
    
    def _on_mousewheel(self, event) -> None:
        """
        Handle mousewheel scrolling.
        
        Args:
            event: Mousewheel event
        """
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units") 
