"""
Preset Manager Dialog for Test Case Manager

This module provides a comprehensive dialog for managing test case presets,
including viewing, editing, deleting, and organizing presets.

Author: Test Case Manager
Date: 2024-08-01
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, List, Optional, Any, Callable
import logging
from datetime import datetime

from src.core.preset_manager import PresetManager


class PresetManagerDialog:
    """
    Dialog for comprehensive preset management.
    
    Provides functionality to view, edit, delete, duplicate, and organize
    test case presets in a professional interface.
    """
    
    def __init__(self, parent: tk.Widget, preset_manager: PresetManager, 
                 refresh_callback: Optional[Callable] = None):
        """
        Initialize the preset manager dialog.
        
        Args:
            parent: Parent widget
            preset_manager: PresetManager instance
            refresh_callback: Callback to refresh main UI after changes
        """
        self.parent = parent
        self.preset_manager = preset_manager
        self.refresh_callback = refresh_callback
        self.logger = logging.getLogger(__name__)
        
        # Dialog window
        self.dialog: Optional[tk.Toplevel] = None
        self.result = None
        
        # UI components
        self.preset_listbox: Optional[tk.Listbox] = None
        self.details_frame: Optional[ttk.Frame] = None
        self.name_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.created_var = tk.StringVar()
        self.test_count_var = tk.StringVar()
        self.tests_text: Optional[tk.Text] = None
        
        # Data
        self.presets: List[Dict[str, Any]] = []
        self.selected_preset: Optional[Dict[str, Any]] = None
        
        # Create and show dialog
        self._create_dialog()
        self._load_presets()
        self._center_dialog()
    
    def _create_dialog(self) -> None:
        """Create the main dialog window."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Preset Viewer - Read Only")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Configure grid weights
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Changed to row 1 to make room for header

        # Header with explanation
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        header_label = ttk.Label(
            header_frame,
            text="📋 Preset Reference - View available test presets and their purposes",
            font=("Segoe UI", 11, "bold"),
            foreground="navy"
        )
        header_label.pack(side="left")

        info_label = ttk.Label(
            header_frame,
            text="(Read-only view)",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        info_label.pack(side="right")
        
        # Create UI sections (adjusted for header row)
        self._create_preset_list(main_frame)
        self._create_details_panel(main_frame)
        self._create_action_buttons(main_frame)
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_preset_list(self, parent: ttk.Frame) -> None:
        """Create the preset list section."""
        # Preset list frame
        list_frame = ttk.LabelFrame(parent, text="Available Presets", padding="5")
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.grid(row=0, column=0, sticky="nsew")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)
        
        self.preset_listbox = tk.Listbox(
            list_container,
            font=("Segoe UI", 9),
            selectmode=tk.SINGLE,
            height=15,
            width=30
        )
        self.preset_listbox.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar for listbox
        list_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.preset_listbox.yview)
        list_scrollbar.grid(row=0, column=1, sticky="ns")
        self.preset_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        # Bind selection event
        self.preset_listbox.bind("<<ListboxSelect>>", self._on_preset_selected)
        
        # Quick actions frame - only refresh button for read-only mode
        quick_frame = ttk.Frame(list_frame)
        quick_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        ttk.Button(quick_frame, text="Refresh", command=self._load_presets, width=10).pack(side="left")
    
    def _create_details_panel(self, parent: ttk.Frame) -> None:
        """Create the preset details panel - read-only version."""
        self.details_frame = ttk.LabelFrame(parent, text="Preset Information", padding="10")
        self.details_frame.grid(row=1, column=1, sticky="nsew")
        self.details_frame.columnconfigure(1, weight=1)
        
        # Basic info
        ttk.Label(self.details_frame, text="Name:", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        self.name_display = ttk.Label(self.details_frame, textvariable=self.name_var,
                                     font=("Segoe UI", 9), relief="sunken", padding="3")
        self.name_display.grid(row=0, column=1, sticky="ew", pady=(0, 5), padx=(5, 0))
        
        ttk.Label(self.details_frame, text="Description:", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky="nw", pady=(0, 5)
        )
        self.description_display = ttk.Label(self.details_frame, textvariable=self.description_var,
                                           font=("Segoe UI", 9), relief="sunken", padding="3", wraplength=300)
        self.description_display.grid(row=1, column=1, sticky="ew", pady=(0, 5), padx=(5, 0))
        
        ttk.Label(self.details_frame, text="Created:", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=(0, 5)
        )
        ttk.Label(self.details_frame, textvariable=self.created_var, font=("Segoe UI", 9)).grid(
            row=2, column=1, sticky="w", pady=(0, 5), padx=(5, 0)
        )
        
        ttk.Label(self.details_frame, text="Test Count:", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, sticky="w", pady=(0, 10)
        )
        ttk.Label(self.details_frame, textvariable=self.test_count_var, font=("Segoe UI", 9)).grid(
            row=3, column=1, sticky="w", pady=(0, 10), padx=(5, 0)
        )
        
        # Tests list
        ttk.Label(self.details_frame, text="Included Tests:", font=("Segoe UI", 9, "bold")).grid(
            row=4, column=0, sticky="nw", pady=(0, 5)
        )
        
        # Text widget for tests with scrollbar
        text_frame = ttk.Frame(self.details_frame)
        text_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.details_frame.rowconfigure(5, weight=1)
        
        self.tests_text = tk.Text(
            text_frame,
            height=12,
            width=50,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.tests_text.grid(row=0, column=0, sticky="nsew")
        
        text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.tests_text.yview)
        text_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tests_text.configure(yscrollcommand=text_scrollbar.set)
        
        # Read-only info note
        info_frame = ttk.Frame(self.details_frame)
        info_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        info_label = ttk.Label(info_frame,
                              text="ℹ️ This is a read-only view. Use 'Apply Selected' to use a preset.",
                              font=("Segoe UI", 8),
                              foreground="gray")
        info_label.pack(side="left")
    
    def _create_action_buttons(self, parent: ttk.Frame) -> None:
        """Create the main action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        ttk.Button(button_frame, text="Close", command=self._on_close).pack(side="right")
        ttk.Button(button_frame, text="Apply Selected", command=self._apply_selected).pack(side="right", padx=(0, 10))
    
    def _load_presets(self) -> None:
        """Load and display presets in the listbox."""
        try:
            self.presets = self.preset_manager.get_all_presets()
            
            # Clear listbox
            if self.preset_listbox:
                self.preset_listbox.delete(0, tk.END)
                
                # Add presets to listbox
                for preset in self.presets:
                    name = preset.get("name", "Unnamed")
                    test_count = preset.get("test_count", len(preset.get("test_ids", [])))
                    created_date = preset.get("created_date", "")
                    
                    # Format date
                    try:
                        if created_date:
                            dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                            date_str = dt.strftime("%Y-%m-%d")
                        else:
                            date_str = "Unknown"
                    except:
                        date_str = "Unknown"
                    
                    # Create more informative display with description
                    description = preset.get('description', '')
                    if description:
                        # Truncate description if too long
                        short_desc = description[:25] + "..." if len(description) > 25 else description
                        display_text = f"{name} ({test_count} tests) - {short_desc}"
                    else:
                        display_text = f"{name} ({test_count} tests) - No description"

                    self.preset_listbox.insert(tk.END, display_text)
                
                # Select first preset if available
                if self.presets:
                    self.preset_listbox.selection_set(0)
                    self._on_preset_selected(None)
                else:
                    self._clear_details()
                    
        except Exception as e:
            self.logger.error(f"Error loading presets: {e}")
            messagebox.showerror("Error", f"Failed to load presets: {str(e)}")
    
    def _on_preset_selected(self, event) -> None:
        """Handle preset selection in listbox."""
        try:
            selection = self.preset_listbox.curselection()
            if not selection:
                self._clear_details()
                return
            
            index = selection[0]
            if 0 <= index < len(self.presets):
                self.selected_preset = self.presets[index]
                self._display_preset_details(self.selected_preset)
            else:
                self._clear_details()
                
        except Exception as e:
            self.logger.error(f"Error handling preset selection: {e}")
            self._clear_details()
    
    def _display_preset_details(self, preset: Dict[str, Any]) -> None:
        """Display details of the selected preset."""
        try:
            # Basic info
            self.name_var.set(preset.get("name", ""))
            self.description_var.set(preset.get("description", ""))
            
            # Format created date
            created_date = preset.get("created_date", "")
            try:
                if created_date:
                    dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    self.created_var.set(dt.strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    self.created_var.set("Unknown")
            except:
                self.created_var.set("Unknown")
            
            # Test count
            test_ids = preset.get("test_ids", [])
            self.test_count_var.set(f"{len(test_ids)} tests")
            
            # Display test list
            if self.tests_text:
                self.tests_text.config(state=tk.NORMAL)
                self.tests_text.delete(1.0, tk.END)
                
                if test_ids:
                    for i, test_id in enumerate(test_ids, 1):
                        # Parse test ID to get name and category
                        if "|" in test_id:
                            test_name, category = test_id.split("|", 1)
                            self.tests_text.insert(tk.END, f"{i:2d}. {test_name} ({category})\n")
                        else:
                            self.tests_text.insert(tk.END, f"{i:2d}. {test_id}\n")
                else:
                    self.tests_text.insert(tk.END, "No tests in this preset.")
                
                self.tests_text.config(state=tk.DISABLED)
                
        except Exception as e:
            self.logger.error(f"Error displaying preset details: {e}")
            self._clear_details()
    
    def _clear_details(self) -> None:
        """Clear the details panel."""
        self.selected_preset = None
        self.name_var.set("")
        self.description_var.set("")
        self.created_var.set("")
        self.test_count_var.set("")
        
        if self.tests_text:
            self.tests_text.config(state=tk.NORMAL)
            self.tests_text.delete(1.0, tk.END)
            self.tests_text.config(state=tk.DISABLED)
    
    def _center_dialog(self) -> None:
        """Center the dialog on the parent window."""
        if self.dialog:
            self.dialog.update_idletasks()
            width = self.dialog.winfo_width()
            height = self.dialog.winfo_height()
            x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
            self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def _on_close(self) -> None:
        """Handle dialog close."""
        if self.dialog:
            self.dialog.destroy()
    
    def show(self) -> None:
        """Show the dialog and wait for result."""
        if self.dialog:
            self.dialog.wait_window()

    # ==========================================
    # Read-Only Action Methods
    # ==========================================









    def _apply_selected(self) -> None:
        """Apply the selected preset and close dialog."""
        try:
            if not self.selected_preset:
                messagebox.showwarning("No Selection", "Please select a preset to apply.")
                return

            self.result = self.selected_preset
            self._on_close()

        except Exception as e:
            self.logger.error(f"Error applying preset: {e}")
            messagebox.showerror("Error", f"Failed to apply preset: {str(e)}")




class PresetPreviewDialog:
    """Simple preview dialog for preset contents."""

    def __init__(self, parent: tk.Widget, preset: Dict[str, Any]):
        self.parent = parent
        self.preset = preset
        self.dialog: Optional[tk.Toplevel] = None

        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create the preview dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Preset Preview: {self.preset.get('name', 'Unknown')}")
        self.dialog.geometry("500x400")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text=f"Preview: {self.preset.get('name', 'Unknown')}",
            font=("Segoe UI", 12, "bold")
        )
        title_label.pack(pady=(0, 10))

        # Description
        desc = self.preset.get("description", "")
        if desc:
            desc_label = ttk.Label(main_frame, text=desc, font=("Segoe UI", 9))
            desc_label.pack(pady=(0, 10))

        # Test list
        ttk.Label(main_frame, text="This preset includes:", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        # Text widget for test list
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill="both", expand=True, pady=(5, 10))

        text_widget = tk.Text(text_frame, font=("Consolas", 9), wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate test list
        text_widget.config(state=tk.NORMAL)
        test_ids = self.preset.get("test_ids", [])
        for i, test_id in enumerate(test_ids, 1):
            if "|" in test_id:
                test_name, category = test_id.split("|", 1)
                text_widget.insert(tk.END, f"{i:2d}. {test_name} ({category})\n")
            else:
                text_widget.insert(tk.END, f"{i:2d}. {test_id}\n")
        text_widget.config(state=tk.DISABLED)

        # Close button
        ttk.Button(main_frame, text="Close", command=self._close).pack(pady=(10, 0))

        # Center dialog
        self._center_dialog()

    def _center_dialog(self) -> None:
        """Center the dialog."""
        if self.dialog:
            self.dialog.update_idletasks()
            width = self.dialog.winfo_width()
            height = self.dialog.winfo_height()
            x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
            self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _close(self) -> None:
        """Close the dialog."""
        if self.dialog:
            self.dialog.destroy()

    def show(self) -> None:
        """Show the dialog."""
        if self.dialog:
            self.dialog.wait_window()
