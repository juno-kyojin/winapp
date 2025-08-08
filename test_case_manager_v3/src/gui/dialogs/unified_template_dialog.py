#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Template Dialog for Test Case Manager v3

This module provides a unified dialog that can operate in both view and edit modes,
replacing the separate view popup and template editor implementations.

Author: juno-kyojin
Created: 2025-08-06
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Any, Optional, Callable, Literal
from datetime import datetime
from pathlib import Path
import shutil

from src.utils.logger import get_logger
from src.utils.file_utils import ensure_directory


class UnifiedTemplateDialog:
    """
    Unified dialog for viewing and editing JSON template files.
    
    Supports two modes:
    - VIEW: Read-only display with formatted content
    - EDIT: Full editing capabilities with validation and backup
    """
    
    def __init__(self, parent: tk.Widget, template_path: str, template_data: Dict[str, Any],
                 mode: Literal["VIEW", "EDIT"] = "VIEW",
                 on_save_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the unified template dialog.

        Args:
            parent: Parent widget
            template_path: Path to the template file
            template_data: Current template data
            mode: Dialog mode - "VIEW" or "EDIT"
            on_save_callback: Callback function called after save (EDIT mode only)
        """
        self.parent = parent
        self.template_path = template_path
        self.original_data = template_data.copy()
        self.mode = mode
        self.on_save_callback = on_save_callback
        self.logger = get_logger(__name__)

        # Dialog state
        self.dialog: Optional[tk.Toplevel] = None
        self.text_editor: Optional[scrolledtext.ScrolledText] = None
        self.validation_label: Optional[ttk.Label] = None
        self.status_label: Optional[ttk.Label] = None
        self.save_button: Optional[ttk.Button] = None
        self.edit_button: Optional[ttk.Button] = None

        # Track if content has been modified (EDIT mode only)
        self.is_modified = False
        self.last_validation_result = True
        self._loading_content = False  # Flag to prevent false positive during content loading


        
        # Create and show dialog
        self._create_dialog()
        self._load_content()
        
    def _create_dialog(self) -> None:
        """Create the main dialog window without visual glitches."""
        template_name = os.path.basename(self.template_path)
        mode_text = "Viewer" if self.mode == "VIEW" else "Editor"

        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Template {mode_text} - {template_name}")

        # Hide dialog initially to prevent flashing
        self.dialog.withdraw()

        # Set size and constraints
        self.dialog.geometry("800x600")
        self.dialog.minsize(600, 400)

        # Make dialog modal
        self.dialog.transient(self.parent)

        # Configure grid weights
        self.dialog.rowconfigure(1, weight=1)  # Editor area expands
        self.dialog.columnconfigure(0, weight=1)

        # Create UI components based on mode
        self._create_header()
        self._create_editor()

        if self.mode == "EDIT":
            self._create_validation_panel()
            self._create_edit_action_buttons()
        else:
            self._create_view_action_buttons()

        self._create_status_bar()

        # Bind events
        self._bind_events()

        # Center dialog and show it smoothly
        self._show_dialog_smoothly()
        
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

    def _show_dialog_smoothly(self) -> None:
        """Show dialog smoothly without flashing."""
        # Update dialog to ensure all components are rendered
        self.dialog.update_idletasks()

        # Center the dialog
        self._center_dialog()

        # Show dialog and grab focus
        self.dialog.deiconify()
        self.dialog.grab_set()

        # Focus on the dialog
        self.dialog.focus_set()

        # If in EDIT mode, focus on the text editor
        if self.mode == "EDIT" and self.text_editor:
            self.text_editor.focus_set()
        
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
        
        # Mode indicator
        mode_color = "blue" if self.mode == "EDIT" else "green"
        mode_label = ttk.Label(
            header_frame, 
            text=f"Mode: {self.mode}", 
            font=("Segoe UI", 9, "bold"),
            foreground=mode_color
        )
        mode_label.grid(row=0, column=2, sticky="e", padx=(5, 0))
        
        # File size and last modified
        try:
            file_stat = os.stat(self.template_path)
            file_size = file_stat.st_size
            last_modified = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            info_text = f"Size: {file_size} bytes | Last modified: {last_modified}"
            ttk.Label(header_frame, text=info_text, font=("Segoe UI", 8), foreground="gray").grid(
                row=1, column=0, columnspan=3, sticky="w", pady=(2, 0)
            )
        except Exception as e:
            self.logger.warning(f"Could not get file info: {e}")
            
    def _create_editor(self) -> None:
        """Create the content editor/viewer."""
        editor_label = "JSON Content" if self.mode == "EDIT" else "Template Content"
        editor_frame = ttk.LabelFrame(self.dialog, text=editor_label)
        editor_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)
        
        # Create text editor with scrollbars
        self.text_editor = scrolledtext.ScrolledText(
            editor_frame,
            wrap=tk.NONE,
            font=("Consolas", 10),
            undo=True if self.mode == "EDIT" else False,
            maxundo=50 if self.mode == "EDIT" else 0,
            state=tk.NORMAL if self.mode == "EDIT" else tk.DISABLED
        )
        self.text_editor.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure syntax highlighting tags
        self._configure_syntax_highlighting()
        
    def _configure_syntax_highlighting(self) -> None:
        """Configure JSON syntax highlighting."""
        if not self.text_editor:
            return
            
        # Define color scheme
        self.text_editor.tag_configure("string", foreground="#008000")  # Green for strings
        self.text_editor.tag_configure("number", foreground="#0000FF")  # Blue for numbers
        self.text_editor.tag_configure("keyword", foreground="#800080")  # Purple for keywords
        self.text_editor.tag_configure("brace", foreground="#FF0000")   # Red for braces
        self.text_editor.tag_configure("metadata", foreground="#666666", font=("Segoe UI", 9))  # Gray for metadata

    def _create_validation_panel(self) -> None:
        """Create the validation status panel (EDIT mode only)."""
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

    def _create_edit_action_buttons(self) -> None:
        """Create simplified action buttons for EDIT mode."""
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        # Left side buttons - utilities
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)

        ttk.Button(left_frame, text="Validate JSON", command=self._validate_json).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(left_frame, text="Format JSON", command=self._format_json).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(left_frame, text="🔄 Restore", command=self._show_restore_dialog).pack(
            side=tk.LEFT, padx=(0, 5)
        )

        # Mode switch button
        ttk.Button(left_frame, text="Switch to View", command=self._switch_to_view_mode).pack(
            side=tk.LEFT, padx=(10, 5)
        )

        # Right side buttons - simplified actions
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)

        # Cancel button
        ttk.Button(right_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=(0, 5)
        )

        # Single Save button (simplified)
        self.save_button = ttk.Button(
            right_frame,
            text="Save Changes",
            command=self._on_save
        )
        self.save_button.pack(side=tk.LEFT)

    def _create_view_action_buttons(self) -> None:
        """Create action buttons for VIEW mode."""
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        # Left side - mode switch
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)

        # Mode switch button
        self.edit_button = ttk.Button(left_frame, text="Switch to Edit", command=self._switch_to_edit_mode)
        self.edit_button.pack(side=tk.LEFT)

        # Right side - close
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)

        ttk.Button(right_frame, text="Close", command=self._close_dialog).pack(side=tk.LEFT)

    def _create_status_bar(self) -> None:
        """Create status bar."""
        status_row = 4 if self.mode == "EDIT" else 3
        status_frame = ttk.Frame(self.dialog, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=status_row, column=0, sticky="ew", padx=0, pady=0)

        self.status_label = ttk.Label(status_frame, text="Ready", font=("Segoe UI", 8))
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)

    def _bind_events(self) -> None:
        """Bind events for real-time validation and modification tracking."""
        if self.text_editor and self.mode == "EDIT":
            # Track modifications - only bind events that actually change content
            self.text_editor.bind('<KeyRelease>', self._on_content_changed)

            # Handle paste operations (Ctrl+V)
            self.text_editor.bind('<Control-v>', self._on_paste)
            self.text_editor.bind('<Control-V>', self._on_paste)

            # Handle cut operations (Ctrl+X)
            self.text_editor.bind('<Control-x>', self._on_content_changed)
            self.text_editor.bind('<Control-X>', self._on_content_changed)

            # Note: Removed <Button-1> binding as mouse clicks don't change content
            # Only actual content modification events should trigger change detection

        # Handle dialog closing
        if self.dialog:
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_content(self) -> None:
        """Load the template content into the editor."""
        if not self.text_editor:
            return

        try:
            # Set loading flag to prevent false positive modification detection
            self._loading_content = True

            if self.mode == "VIEW":
                # Load simple formatted content for viewing
                content = self._format_view_content()
            else:
                # Load raw JSON for editing
                content = json.dumps(self.original_data, indent=2, ensure_ascii=False)

            # Insert content
            if self.mode == "VIEW":
                self.text_editor.config(state=tk.NORMAL)

            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(1.0, content)

            # Apply syntax highlighting
            self._apply_syntax_highlighting()

            if self.mode == "VIEW":
                self.text_editor.config(state=tk.DISABLED)

            # Reset modification flag after loading
            self.is_modified = False
            self._update_title()

            self._update_status("Template loaded successfully")

        except Exception as e:
            self.logger.error(f"Error loading template content: {e}")
            messagebox.showerror("Load Error", f"Could not load template content: {str(e)}")
        finally:
            # Clear loading flag
            self._loading_content = False

    def _format_view_content(self) -> str:
        """Format content for VIEW mode display - minimal and focused."""
        content_parts = []

        # Test case parameters only (no extra headers)
        if self.original_data:
            test_cases = self.original_data.get('test_cases', [])

            for i, test_case in enumerate(test_cases):
                if len(test_cases) > 1:
                    content_parts.append(f"Test Case {i + 1}:")

                # Service and Action
                content_parts.append(f"Service: {test_case.get('service', 'N/A')}")
                content_parts.append(f"Action: {test_case.get('action', 'N/A')}")

                # Parameters
                params = test_case.get('params', {})
                if params:
                    content_parts.append("Parameters:")
                    for key, value in params.items():
                        content_parts.append(f"  {key}: {value}")

                if len(test_cases) > 1 and i < len(test_cases):
                    content_parts.append("")  # Space between multiple test cases

            # JSON content (clean, no extra labels)
            content_parts.append("")
            content_parts.append("JSON:")
            content_parts.append(json.dumps(self.original_data, indent=2, ensure_ascii=False))
        else:
            content_parts.append("No test case data found")

        return "\n".join(content_parts)

    def _apply_syntax_highlighting(self) -> None:
        """Apply syntax highlighting based on mode."""
        if not self.text_editor:
            return

        content = self.text_editor.get(1.0, tk.END)

        # Clear existing tags
        for tag in ["string", "number", "keyword", "brace", "metadata"]:
            self.text_editor.tag_remove(tag, 1.0, tk.END)

        if self.mode == "VIEW":
            # Highlight metadata sections
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                if line.startswith("===") and line.endswith("==="):
                    line_start = f"{line_num}.0"
                    line_end = f"{line_num}.end"
                    self.text_editor.tag_add("metadata", line_start, line_end)
        else:
            # Apply JSON syntax highlighting for EDIT mode
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                # Highlight braces and brackets
                for i, char in enumerate(line):
                    if char in '{}[]':
                        char_pos = f"{line_num}.{i}"
                        char_end = f"{line_num}.{i+1}"
                        self.text_editor.tag_add("brace", char_pos, char_end)

    def _switch_to_edit_mode(self) -> None:
        """Switch from VIEW to EDIT mode."""
        if self.mode == "EDIT":
            return

        # Ask for confirmation
        if not messagebox.askyesno(
            "Switch to Edit Mode",
            "Switch to edit mode? You will be able to modify the template content."
        ):
            return

        # Close current dialog and reopen in EDIT mode
        template_path = self.template_path
        template_data = self.original_data
        callback = self.on_save_callback
        parent = self.parent

        self._close_dialog()

        # Create new dialog in EDIT mode
        UnifiedTemplateDialog(parent, template_path, template_data, "EDIT", callback)

    def _switch_to_view_mode(self) -> None:
        """Switch from EDIT to VIEW mode."""
        if self.mode == "VIEW":
            return

        # Check for unsaved changes
        if self.is_modified:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Save before switching to view mode?"
            )

            if result is True:  # Yes - save first
                if not self._save_changes():
                    return  # Save failed, don't switch
            elif result is None:  # Cancel - don't switch
                return
            # False - don't save, continue switching

        # Close current dialog and reopen in VIEW mode
        template_path = self.template_path
        template_data = self.original_data
        parent = self.parent

        self._close_dialog()

        # Create new dialog in VIEW mode
        UnifiedTemplateDialog(parent, template_path, template_data, "VIEW")

    def _on_paste(self, event=None) -> None:
        """Handle paste operations with delayed change detection."""
        if self.mode != "EDIT" or self._loading_content:
            return

        # Delay change detection to allow paste operation to complete
        if self.dialog:
            self.dialog.after(100, self._on_content_changed)

    def _on_content_changed(self, event=None) -> None:
        """Handle content changes for modification tracking and validation."""
        if self.mode != "EDIT":
            return

        # Ignore changes during content loading to prevent false positive
        if self._loading_content:
            return

        if not self.is_modified:
            self.is_modified = True
            self._update_title()

        # Perform real-time validation (with delay to avoid too frequent calls)
        if self.dialog:
            self.dialog.after(500, self._validate_json_silent)

    def _update_title(self) -> None:
        """Update dialog title to show modification status."""
        if self.dialog:
            template_name = os.path.basename(self.template_path)
            mode_text = "Viewer" if self.mode == "VIEW" else "Editor"
            base_title = f"Template {mode_text} - {template_name}"

            if self.mode == "EDIT" and self.is_modified:
                self.dialog.title(f"{base_title} *")
            else:
                self.dialog.title(base_title)

    def _update_status(self, message: str) -> None:
        """Update status bar message."""
        if self.status_label:
            self.status_label.config(text=message)

    def _validate_json(self) -> bool:
        """Validate JSON content and show result."""
        if self.mode != "EDIT":
            return True

        result = self._validate_json_silent()

        if result:
            messagebox.showinfo("Validation", "✅ JSON is valid!")

        return result

    def _validate_json_silent(self) -> bool:
        """Validate JSON content silently and update validation label."""
        if self.mode != "EDIT" or not self.text_editor or not self.validation_label:
            return True

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
        if self.mode != "EDIT" or not self.text_editor:
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

    def _on_save(self) -> None:
        """Handle save button click with simplified workflow."""
        if self.mode != "EDIT":
            return

        self._save_changes()

    def _validate_current_content(self) -> bool:
        """Validate current content and show result if invalid."""
        if not self.last_validation_result:
            if not messagebox.askyesno(
                "Invalid JSON",
                "The JSON content is invalid. Do you want to proceed anyway?"
            ):
                return False
        return True

    def _save_changes(self) -> bool:
        """Save changes to file. Returns True if successful."""
        if not self._validate_current_content():
            return False

        try:
            # Get content from editor
            content = self.text_editor.get(1.0, tk.END).strip()
            if not content:
                messagebox.showwarning("Save", "Cannot save empty content")
                return False

            # Parse JSON to ensure it's valid
            parsed_data = json.loads(content)

            # Create backup before saving
            if not self._create_backup():
                if not messagebox.askyesno(
                    "Backup Failed",
                    "Could not create backup. Continue saving anyway?"
                ):
                    return False

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
            return True

        except json.JSONDecodeError as e:
            messagebox.showerror("Save Error", f"Invalid JSON: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error saving template: {e}")
            messagebox.showerror("Save Error", f"Could not save template: {str(e)}")
            return False

    def _create_backup(self) -> bool:
        """Create backup of original file before saving."""
        try:
            from pathlib import Path
            import shutil

            backup_dir = Path(self.template_path).parent / "backup"
            backup_dir.mkdir(exist_ok=True)

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
            return False

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self.is_modified:
            result = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?"
            )

            if result is True:  # Yes - save first
                if self._save_changes():
                    self._close_dialog()
                return
            elif result is None:  # Cancel - don't close
                return
            # False - don't save, continue closing

        self._close_dialog()

    def _on_close(self) -> None:
        """Handle dialog close event."""
        if self.mode == "EDIT":
            self._on_cancel()
        else:
            self._close_dialog()

    def _close_dialog(self) -> None:
        """Close the dialog."""
        if self.dialog:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None

    def _show_restore_dialog(self) -> None:
        """Show restore from backup dialog."""
        try:
            backup_files = self._get_backup_files()
            if not backup_files:
                messagebox.showinfo(
                    "No Backups",
                    "No backup files found for this template."
                )
                return

            # Create restore dialog
            self._create_restore_dialog(backup_files)

        except Exception as e:
            self.logger.error(f"Error showing restore dialog: {e}")
            messagebox.showerror("Error", f"Could not show restore dialog: {str(e)}")

    def _get_backup_files(self) -> list:
        """Get list of backup files for current template."""
        try:
            backup_dir = Path(self.template_path).parent / "backup"
            if not backup_dir.exists():
                return []

            template_name = Path(self.template_path).name
            backup_pattern = f"{template_name}.backup_*"

            backup_files = []
            for backup_file in backup_dir.glob(backup_pattern):
                if backup_file.is_file():
                    # Extract timestamp from filename
                    timestamp_str = backup_file.name.split('.backup_')[-1]
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        backup_files.append({
                            'path': backup_file,
                            'timestamp': timestamp,
                            'display_name': f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {backup_file.name}"
                        })
                    except ValueError:
                        # Skip files with invalid timestamp format
                        continue

            # Sort by timestamp (newest first)
            backup_files.sort(key=lambda x: x['timestamp'], reverse=True)
            return backup_files

        except Exception as e:
            self.logger.error(f"Error getting backup files: {e}")
            return []

    def _create_restore_dialog(self, backup_files: list) -> None:
        """Create and show restore dialog."""
        # Create restore dialog window
        restore_dialog = tk.Toplevel(self.dialog)
        restore_dialog.title("Restore from Backup")
        restore_dialog.geometry("600x400")
        restore_dialog.minsize(500, 300)

        # Make dialog modal
        restore_dialog.transient(self.dialog)
        restore_dialog.grab_set()

        # Center dialog
        restore_dialog.update_idletasks()
        x = (restore_dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (restore_dialog.winfo_screenheight() // 2) - (400 // 2)
        restore_dialog.geometry(f"600x400+{x}+{y}")

        # Configure grid weights
        restore_dialog.rowconfigure(1, weight=1)
        restore_dialog.columnconfigure(0, weight=1)

        # Header
        header_frame = ttk.Frame(restore_dialog)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        ttk.Label(
            header_frame,
            text=f"Select backup to restore for: {Path(self.template_path).name}",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        # Backup list frame
        list_frame = ttk.Frame(restore_dialog)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # Create treeview for backup files
        columns = ("timestamp", "filename")
        tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", height=10)
        tree.grid(row=0, column=0, sticky="nsew")

        # Configure columns
        tree.heading("#0", text="Backup Files")
        tree.heading("timestamp", text="Created")
        tree.heading("filename", text="Filename")

        tree.column("#0", width=200)
        tree.column("timestamp", width=150)
        tree.column("filename", width=200)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        # Populate backup files
        for i, backup_info in enumerate(backup_files):
            tree.insert(
                "", "end",
                text=f"Backup {i+1}",
                values=(
                    backup_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    backup_info['path'].name
                ),
                tags=(str(i),)
            )

        # Preview frame
        preview_frame = ttk.LabelFrame(restore_dialog, text="Preview")
        preview_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        preview_frame.columnconfigure(0, weight=1)

        preview_text = scrolledtext.ScrolledText(
            preview_frame,
            height=6,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        preview_text.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Store references for event handlers
        restore_dialog.backup_files = backup_files
        restore_dialog.tree = tree
        restore_dialog.preview_text = preview_text

        # Bind selection event
        tree.bind("<<TreeviewSelect>>", lambda e: self._on_backup_selected(restore_dialog))

        # Buttons frame
        button_frame = ttk.Frame(restore_dialog)
        button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        # Right side buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)

        ttk.Button(right_frame, text="Cancel", command=restore_dialog.destroy).pack(
            side=tk.LEFT, padx=(0, 5)
        )

        restore_button = ttk.Button(
            right_frame,
            text="Restore Selected",
            command=lambda: self._restore_selected_backup(restore_dialog)
        )
        restore_button.pack(side=tk.LEFT)

        # Store restore button reference
        restore_dialog.restore_button = restore_button
        restore_button.config(state="disabled")  # Initially disabled

    def _on_backup_selected(self, restore_dialog) -> None:
        """Handle backup selection in restore dialog."""
        try:
            tree = restore_dialog.tree
            preview_text = restore_dialog.preview_text
            backup_files = restore_dialog.backup_files
            restore_button = restore_dialog.restore_button

            selection = tree.selection()
            if not selection:
                preview_text.delete(1.0, tk.END)
                restore_button.config(state="disabled")
                return

            # Get selected backup index
            item = tree.item(selection[0])
            backup_index = int(item['tags'][0])
            backup_info = backup_files[backup_index]

            # Load and preview backup content
            try:
                with open(backup_info['path'], 'r', encoding='utf-8') as f:
                    backup_content = f.read()

                # Show preview
                preview_text.delete(1.0, tk.END)
                preview_text.insert(1.0, backup_content)

                # Enable restore button
                restore_button.config(state="normal")

            except Exception as e:
                preview_text.delete(1.0, tk.END)
                preview_text.insert(1.0, f"Error loading backup: {str(e)}")
                restore_button.config(state="disabled")

        except Exception as e:
            self.logger.error(f"Error handling backup selection: {e}")

    def _restore_selected_backup(self, restore_dialog) -> None:
        """Restore selected backup file."""
        try:
            tree = restore_dialog.tree
            backup_files = restore_dialog.backup_files

            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a backup to restore.")
                return

            # Get selected backup
            item = tree.item(selection[0])
            backup_index = int(item['tags'][0])
            backup_info = backup_files[backup_index]

            # Confirm restore
            if not messagebox.askyesno(
                "Confirm Restore",
                f"Are you sure you want to restore from backup?\n\n"
                f"Backup: {backup_info['display_name']}\n\n"
                f"This will replace the current template content and cannot be undone."
            ):
                return

            # Create backup of current state before restore
            current_backup_created = self._create_backup()
            if not current_backup_created:
                if not messagebox.askyesno(
                    "Backup Failed",
                    "Could not create backup of current state. Continue with restore anyway?"
                ):
                    return

            # Restore from backup
            shutil.copy2(backup_info['path'], self.template_path)

            # Reload content in editor
            with open(self.template_path, 'r', encoding='utf-8') as f:
                restored_content = f.read()

            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(1.0, restored_content)

            # Update state
            self.is_modified = False
            self._update_title()
            self._update_status(f"Restored from backup: {backup_info['path'].name}")

            # Call callback if provided
            if self.on_save_callback:
                self.on_save_callback(self.template_path)

            # Close restore dialog
            restore_dialog.destroy()

            # Show success message
            messagebox.showinfo(
                "Restore Successful",
                f"Template restored from backup:\n{backup_info['display_name']}"
            )

        except Exception as e:
            self.logger.error(f"Error restoring backup: {e}")
            messagebox.showerror("Restore Error", f"Could not restore backup: {str(e)}")
