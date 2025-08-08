#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Template Editor Dialog for Test Case Manager v3

This module provides an in-app JSON template editor with syntax validation,
backup functionality, and real-time updates.

Author: juno-kyojin
Created: 2025-08-06
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
import shutil

from src.utils.logger import get_logger
from src.utils.file_utils import ensure_directory, write_json_file


class TemplateEditorDialog:
    """
    Dialog for editing JSON template files with validation and backup.
    
    Features:
    - JSON syntax highlighting (basic)
    - Real-time validation
    - Auto-backup before save
    - Format JSON functionality
    - File info display
    """
    
    def __init__(self, parent: tk.Widget, template_path: str, template_data: Dict[str, Any],
                 on_save_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the template editor dialog.
        
        Args:
            parent: Parent widget
            template_path: Path to the template file
            template_data: Current template data
            on_save_callback: Callback function called after successful save
        """
        self.parent = parent
        self.template_path = template_path
        self.original_data = template_data.copy()
        self.on_save_callback = on_save_callback
        self.logger = get_logger(__name__)
        
        # Dialog state
        self.dialog: Optional[tk.Toplevel] = None
        self.text_editor: Optional[scrolledtext.ScrolledText] = None
        self.validation_label: Optional[ttk.Label] = None
        self.status_label: Optional[ttk.Label] = None
        self.save_button: Optional[ttk.Button] = None
        
        # Track if content has been modified
        self.is_modified = False
        self.last_validation_result = True
        
        # Create and show dialog
        self._create_dialog()
        self._load_content()
        
    def _create_dialog(self) -> None:
        """Create the main dialog window."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Template Editor - {os.path.basename(self.template_path)}")
        self.dialog.geometry("800x600")
        self.dialog.minsize(600, 400)
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog on parent
        self._center_dialog()
        
        # Configure grid weights
        self.dialog.rowconfigure(1, weight=1)  # Editor area expands
        self.dialog.columnconfigure(0, weight=1)
        
        # Create UI components
        self._create_header()
        self._create_editor()
        self._create_validation_panel()
        self._create_action_buttons()
        self._create_status_bar()
        
        # Bind events
        self._bind_events()
        
    def _center_dialog(self) -> None:
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate center position
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
        
    def _create_header(self) -> None:
        """Create the header with file information."""
        header_frame = ttk.Frame(self.dialog)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.columnconfigure(1, weight=1)
        
        # File path label
        ttk.Label(header_frame, text="File:", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        ttk.Label(header_frame, text=self.template_path, font=("Segoe UI", 9)).grid(
            row=0, column=1, sticky="w"
        )
        
        # File size and last modified
        try:
            file_stat = os.stat(self.template_path)
            file_size = file_stat.st_size
            last_modified = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            info_text = f"Size: {file_size} bytes | Last modified: {last_modified}"
            ttk.Label(header_frame, text=info_text, font=("Segoe UI", 8), foreground="gray").grid(
                row=1, column=0, columnspan=2, sticky="w", pady=(2, 0)
            )
        except Exception as e:
            self.logger.warning(f"Could not get file info: {e}")
            
    def _create_editor(self) -> None:
        """Create the JSON editor with basic syntax highlighting."""
        editor_frame = ttk.LabelFrame(self.dialog, text="JSON Content")
        editor_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)
        
        # Create text editor with scrollbars
        self.text_editor = scrolledtext.ScrolledText(
            editor_frame,
            wrap=tk.NONE,
            font=("Consolas", 10),
            undo=True,
            maxundo=50
        )
        self.text_editor.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure basic syntax highlighting tags
        self._configure_syntax_highlighting()
        
    def _configure_syntax_highlighting(self) -> None:
        """Configure basic JSON syntax highlighting."""
        if not self.text_editor:
            return
            
        # Define color scheme
        self.text_editor.tag_configure("string", foreground="#008000")  # Green for strings
        self.text_editor.tag_configure("number", foreground="#0000FF")  # Blue for numbers
        self.text_editor.tag_configure("keyword", foreground="#800080")  # Purple for keywords
        self.text_editor.tag_configure("brace", foreground="#FF0000")   # Red for braces
        
    def _create_validation_panel(self) -> None:
        """Create the validation status panel."""
        validation_frame = ttk.Frame(self.dialog)
        validation_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        validation_frame.columnconfigure(1, weight=1)
        
        ttk.Label(validation_frame, text="Validation:", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        
        self.validation_label = ttk.Label(
            validation_frame, 
            text="✅ Valid JSON", 
            font=("Segoe UI", 9),
            foreground="green"
        )
        self.validation_label.grid(row=0, column=1, sticky="w")
        
    def _create_action_buttons(self) -> None:
        """Create action buttons."""
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        
        # Left side buttons
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Button(left_frame, text="Validate JSON", command=self._validate_json).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(left_frame, text="Format JSON", command=self._format_json).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        
        # Right side buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(right_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        
        self.save_button = ttk.Button(right_frame, text="Save", command=self._on_save)
        self.save_button.pack(side=tk.LEFT)
        
    def _create_status_bar(self) -> None:
        """Create status bar."""
        status_frame = ttk.Frame(self.dialog, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=4, column=0, sticky="ew", padx=0, pady=0)
        
        self.status_label = ttk.Label(status_frame, text="Ready", font=("Segoe UI", 8))
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
    def _bind_events(self) -> None:
        """Bind events for real-time validation and modification tracking."""
        if self.text_editor:
            # Track modifications
            self.text_editor.bind('<KeyRelease>', self._on_content_changed)
            self.text_editor.bind('<Button-1>', self._on_content_changed)
            
        # Handle dialog closing
        if self.dialog:
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
            
    def _load_content(self) -> None:
        """Load the template content into the editor."""
        if not self.text_editor:
            return
            
        try:
            # Format JSON with proper indentation
            formatted_json = json.dumps(self.original_data, indent=2, ensure_ascii=False)
            
            # Insert content
            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(1.0, formatted_json)
            
            # Apply basic syntax highlighting
            self._apply_syntax_highlighting()
            
            # Reset modification flag
            self.is_modified = False
            self._update_title()
            
            self._update_status("Template loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading template content: {e}")
            messagebox.showerror("Load Error", f"Could not load template content: {str(e)}")
            
    def _apply_syntax_highlighting(self) -> None:
        """Apply basic JSON syntax highlighting."""
        if not self.text_editor:
            return
            
        content = self.text_editor.get(1.0, tk.END)
        
        # Clear existing tags
        for tag in ["string", "number", "keyword", "brace"]:
            self.text_editor.tag_remove(tag, 1.0, tk.END)
            
        # Simple highlighting (basic implementation)
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Highlight braces and brackets
            for i, char in enumerate(line):
                if char in '{}[]':
                    char_pos = f"{line_num}.{i}"
                    char_end = f"{line_num}.{i+1}"
                    self.text_editor.tag_add("brace", char_pos, char_end)

    def _on_content_changed(self, event=None) -> None:
        """Handle content changes for modification tracking and validation."""
        if not self.is_modified:
            self.is_modified = True
            self._update_title()

        # Perform real-time validation (with delay to avoid too frequent calls)
        if self.dialog:
            self.dialog.after(500, self._validate_json_silent)

    def _update_title(self) -> None:
        """Update dialog title to show modification status."""
        if self.dialog:
            base_title = f"Template Editor - {os.path.basename(self.template_path)}"
            if self.is_modified:
                self.dialog.title(f"{base_title} *")
            else:
                self.dialog.title(base_title)

    def _update_status(self, message: str) -> None:
        """Update status bar message."""
        if self.status_label:
            self.status_label.config(text=message)

    def _validate_json(self) -> bool:
        """Validate JSON content and show result."""
        result = self._validate_json_silent()

        if result:
            messagebox.showinfo("Validation", "✅ JSON is valid!")
        else:
            # Error message already shown in _validate_json_silent
            pass

        return result

    def _validate_json_silent(self) -> bool:
        """Validate JSON content silently and update validation label."""
        if not self.text_editor or not self.validation_label:
            return False

        try:
            content = self.text_editor.get(1.0, tk.END).strip()
            if not content:
                self._update_validation_status(False, "Empty content")
                return False

            # Parse JSON to validate
            json.loads(content)

            # Update UI
            self._update_validation_status(True, "Valid JSON")
            self.last_validation_result = True

            # Enable save button
            if self.save_button:
                self.save_button.config(state=tk.NORMAL)

            return True

        except json.JSONDecodeError as e:
            error_msg = f"JSON Error: {str(e)}"
            self._update_validation_status(False, error_msg)
            self.last_validation_result = False

            # Disable save button
            if self.save_button:
                self.save_button.config(state=tk.DISABLED)

            return False
        except Exception as e:
            error_msg = f"Validation Error: {str(e)}"
            self._update_validation_status(False, error_msg)
            self.last_validation_result = False

            # Disable save button
            if self.save_button:
                self.save_button.config(state=tk.DISABLED)

            return False

    def _update_validation_status(self, is_valid: bool, message: str) -> None:
        """Update validation status display."""
        if not self.validation_label:
            return

        if is_valid:
            self.validation_label.config(
                text=f"✅ {message}",
                foreground="green"
            )
        else:
            self.validation_label.config(
                text=f"❌ {message}",
                foreground="red"
            )

    def _format_json(self) -> None:
        """Format JSON content with proper indentation."""
        if not self.text_editor:
            return

        try:
            content = self.text_editor.get(1.0, tk.END).strip()
            if not content:
                messagebox.showwarning("Format JSON", "No content to format")
                return

            # Parse and reformat JSON
            parsed_data = json.loads(content)
            formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)

            # Replace content
            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(1.0, formatted_json)

            # Apply syntax highlighting
            self._apply_syntax_highlighting()

            self._update_status("JSON formatted successfully")

        except json.JSONDecodeError as e:
            messagebox.showerror("Format Error", f"Cannot format invalid JSON: {str(e)}")
        except Exception as e:
            messagebox.showerror("Format Error", f"Error formatting JSON: {str(e)}")

    def _create_backup(self) -> bool:
        """Create backup of original file before saving."""
        try:
            backup_dir = Path(self.template_path).parent / "backup"
            ensure_directory(backup_dir)

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = Path(self.template_path).name
            backup_filename = f"{filename}.backup_{timestamp}"
            backup_path = backup_dir / backup_filename

            # Copy original file to backup
            shutil.copy2(self.template_path, backup_path)

            self.logger.info(f"Created backup: {backup_path}")
            self._update_status(f"Backup created: {backup_filename}")

            return True

        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            messagebox.showerror("Backup Error", f"Could not create backup: {str(e)}")
            return False

    def _on_save(self) -> None:
        """Handle save button click."""
        if not self.last_validation_result:
            if not messagebox.askyesno(
                "Invalid JSON",
                "The JSON content is invalid. Do you want to save anyway?"
            ):
                return

        try:
            # Get content from editor
            content = self.text_editor.get(1.0, tk.END).strip()
            if not content:
                messagebox.showwarning("Save", "Cannot save empty content")
                return

            # Parse JSON to ensure it's valid
            parsed_data = json.loads(content)

            # Create backup before saving
            if not self._create_backup():
                if not messagebox.askyesno(
                    "Backup Failed",
                    "Could not create backup. Continue saving anyway?"
                ):
                    return

            # Save to file
            with open(self.template_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)

            # Update state
            self.is_modified = False
            self._update_title()
            self._update_status("Template saved successfully")

            # Call callback if provided
            if self.on_save_callback:
                self.on_save_callback(self.template_path)

            messagebox.showinfo("Save", "Template saved successfully!")

        except json.JSONDecodeError as e:
            messagebox.showerror("Save Error", f"Invalid JSON: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error saving template: {e}")
            messagebox.showerror("Save Error", f"Could not save template: {str(e)}")

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self.is_modified:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?"
            )

            if result is True:  # Yes - save first
                self._on_save()
                return
            elif result is None:  # Cancel - don't close
                return
            # False - don't save, continue closing

        self._close_dialog()

    def _on_close(self) -> None:
        """Handle dialog close event."""
        self._on_cancel()

    def _close_dialog(self) -> None:
        """Close the dialog."""
        if self.dialog:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None
