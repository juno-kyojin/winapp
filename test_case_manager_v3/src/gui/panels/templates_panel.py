#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Templates Panel for Test Case Manager v1.0

This module provides a panel for browsing and managing test templates.

Author: juno-kyojin
Created: 2025-06-29
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Dict, Any, Optional, List, Callable, cast

from src.core.test_case_loader import TestCaseLoader
from src.utils.logger import get_logger


def extract_test_name(test_data: Dict[str, Any], template_name: Optional[str] = None) -> str:
    """Extract test name from test data - simplified version."""
    # Check metadata.name first
    if "metadata" in test_data and isinstance(test_data["metadata"], dict):
        name = test_data["metadata"].get("name")
        if name and isinstance(name, str) and name.strip():
            return name.strip()

    # Check direct name field
    if "name" in test_data:
        name = test_data["name"]
        if name and isinstance(name, str) and name.strip():
            return name.strip()

    # Use template name if provided
    if template_name:
        name = template_name
        if name.endswith('.json'):
            name = name[:-5]
        if name and name.strip():
            return name.strip()

    return "unknown"



class TemplatesPanel(ttk.Frame):
    """
    Panel for browsing and managing test templates.

    This panel provides UI for browsing, viewing, and editing test templates
    organized by categories.
    """

    def __init__(self, parent: tk.Widget, test_loader: TestCaseLoader,
                status_callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Initialize the templates panel.

        Args:
            parent: Parent widget
            test_loader: Test case loader instance
            status_callback: Callback for status updates
        """
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.test_loader = test_loader
        self.status_callback = status_callback

        # Reference to parent window (will be set by MainWindow)
        self.parent: Any = None

        # Template data
        self.categories: List[str] = []
        self.templates: Dict[str, List[str]] = {}
        self.current_template: Dict[str, Any] = {}
        self.current_template_path: str = ""

        # Method that can be overridden by MainWindow
        self.add_to_queue = self._add_to_queue

        # UI components
        self.category_var = tk.StringVar()
        self.template_var = tk.StringVar()

        # Create UI
        self._create_ui()

        # Load template data
        self._load_templates()

    def _create_ui(self) -> None:
        """Create the UI components."""
        # Main layout with 3 columns
        self.columnconfigure(0, weight=1)  # Template browser
        self.columnconfigure(1, weight=3)  # Template content

        # Left panel - Template browser
        browser_frame = ttk.LabelFrame(self, text="Template Browser")
        browser_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Category selection
        ttk.Label(browser_frame, text="Category:").pack(anchor=tk.W, padx=5, pady=5)

        self.category_combo = ttk.Combobox(
            browser_frame,
            textvariable=self.category_var,
            state="readonly"
        )
        self.category_combo.pack(fill=tk.X, padx=5, pady=5)
        self.category_combo.bind("<<ComboboxSelected>>", self._on_category_selected)

        # Template selection
        ttk.Label(browser_frame, text="Template:").pack(anchor=tk.W, padx=5, pady=5)

        self.template_listbox = tk.Listbox(browser_frame, height=15)
        self.template_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.template_listbox.bind("<<ListboxSelect>>", self._on_template_selected)

        # Template actions
        actions_frame = ttk.Frame(browser_frame)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            actions_frame,
            text="New",
            command=self._new_template
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            actions_frame,
            text="Import",
            command=self._import_template
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            actions_frame,
            text="Delete",
            command=self._delete_template
        ).pack(side=tk.LEFT, padx=2)

        # Right panel - Template content
        content_frame = ttk.LabelFrame(self, text="Template Content")
        content_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Template content editor
        self.content_text = tk.Text(content_frame, wrap=tk.WORD, width=60, height=20)
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.content_text, command=self.content_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_text.config(yscrollcommand=scrollbar.set)

        # Content actions
        content_actions = ttk.Frame(content_frame)
        content_actions.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            content_actions,
            text="Save",
            command=self._save_template
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            content_actions,
            text="Format JSON",
            command=self._format_json
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            content_actions,
            text="Validate",
            command=self._validate_template
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            content_actions,
            text="Add to Queue",
            command=self.add_to_queue
        ).pack(side=tk.RIGHT, padx=2)

    def _load_templates(self) -> None:
        """Load templates from the template directory."""
        try:
            # Get categories
            self.categories = self.test_loader.get_categories()

            # Update category dropdown
            self.category_combo["values"] = self.categories

            if self.categories:
                self.category_var.set(self.categories[0])
                self._load_templates_for_category(self.categories[0])

            self._update_status("Templates loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not load templates: {str(e)}"
            )

    def _load_templates_for_category(self, category: str) -> None:
        """
        Load templates for a specific category.

        Args:
            category: Template category
        """
        try:
            # Clear template listbox
            self.template_listbox.delete(0, tk.END)

            # Get templates for category
            templates = self.test_loader.get_templates_for_category(category)

            # Store templates
            self.templates[category] = templates

            # Update template listbox
            for template in templates:
                self.template_listbox.insert(tk.END, template)

            # Select first template if available
            if templates:
                self.template_listbox.selection_set(0)
                self._load_template(category, templates[0])
        except Exception as e:
            self.logger.error(f"Error loading templates for category {category}: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not load templates for category {category}: {str(e)}"
            )

    def _load_template(self, category: str, template_name: str) -> None:
        """
        Load a specific template.

        Args:
            category: Template category
            template_name: Template name
        """
        try:
            # Get template path
            template_path = self.test_loader.get_template_path(category, template_name)

            # Load template content
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Update content editor
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(tk.END, template_content)

            # Store current template info
            self.current_template_path = template_path

            # Try to parse JSON
            try:
                self.current_template = json.loads(template_content)
            except json.JSONDecodeError:
                self.current_template = {}

            self._update_status(f"Loaded template: {template_name}")
        except Exception as e:
            self.logger.error(f"Error loading template {template_name}: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not load template {template_name}: {str(e)}"
            )

    def _on_category_selected(self, event: tk.Event) -> None:
        """
        Handle category selection.

        Args:
            event: Selection event
        """
        category = self.category_var.get()
        if category:
            self._load_templates_for_category(category)

    def _on_template_selected(self, event: tk.Event) -> None:
        """
        Handle template selection.

        Args:
            event: Selection event
        """
        selection = self.template_listbox.curselection()
        if selection:
            index = selection[0]
            template_name = self.template_listbox.get(index)
            category = self.category_var.get()
            self._load_template(category, template_name)

    def _new_template(self) -> None:
        """Create a new template."""
        category = self.category_var.get()
        if not category:
            messagebox.showerror(
                "Template Error",
                "Please select a category first"
            )
            return

        # Ask for template name
        template_name = simpledialog.askstring(
            "New Template",
            "Enter template name:",
            parent=self
        )

        if not template_name:
            return

        # Add .json extension if not present
        if not template_name.endswith(".json"):
            template_name += ".json"

        # Create template path
        template_path = os.path.join(
            self.test_loader.base_dir,
            category.lower(),
            template_name
        )

        # Check if template already exists
        if os.path.exists(template_path):
            messagebox.showerror(
                "Template Error",
                f"Template {template_name} already exists"
            )
            return

        # Create empty template
        empty_template = {
            "service": "",
            "method": "",
            "params": {},
            "metadata": {
                "description": "New template",
                "category": category,
                "created_by": "Test Case Manager v1.0"
            }
        }

        try:
            # Create template file
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump(empty_template, f, indent=2)

            # Update template list
            self._load_templates_for_category(category)

            # Select the new template
            for i in range(self.template_listbox.size()):
                if self.template_listbox.get(i) == template_name:
                    self.template_listbox.selection_set(i)
                    self._load_template(category, template_name)
                    break

            self._update_status(f"Created new template: {template_name}")
        except Exception as e:
            self.logger.error(f"Error creating template {template_name}: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not create template {template_name}: {str(e)}"
            )

    def _import_template(self) -> None:
        """Import a template from a file."""
        # Ask for file
        file_path = filedialog.askopenfilename(
            title="Import Template",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            parent=self
        )

        if not file_path:
            return

        category = self.category_var.get()
        if not category:
            messagebox.showerror(
                "Template Error",
                "Please select a category first"
            )
            return

        try:
            # Read template file
            with open(file_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Validate JSON
            try:
                json.loads(template_content)
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Template Error",
                    f"Invalid JSON: {str(e)}"
                )
                return

            # Get template name
            template_name = os.path.basename(file_path)

            # Create template path
            template_path = os.path.join(
                self.test_loader.base_dir,
                category.lower(),
                template_name
            )

            # Check if template already exists
            if os.path.exists(template_path):
                overwrite = messagebox.askyesno(
                    "Template Exists",
                    f"Template {template_name} already exists. Overwrite?"
                )
                if not overwrite:
                    return

            # Copy template file
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(template_content)

            # Update template list
            self._load_templates_for_category(category)

            # Select the imported template
            for i in range(self.template_listbox.size()):
                if self.template_listbox.get(i) == template_name:
                    self.template_listbox.selection_set(i)
                    self._load_template(category, template_name)
                    break

            self._update_status(f"Imported template: {template_name}")
        except Exception as e:
            self.logger.error(f"Error importing template: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not import template: {str(e)}"
            )

    def _delete_template(self) -> None:
        """Delete the selected template."""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showerror(
                "Template Error",
                "Please select a template to delete"
            )
            return

        index = selection[0]
        template_name = self.template_listbox.get(index)
        category = self.category_var.get()

        # Confirm deletion
        confirm = messagebox.askyesno(
            "Delete Template",
            f"Are you sure you want to delete template {template_name}?"
        )

        if not confirm:
            return

        try:
            # Get template path
            template_path = self.test_loader.get_template_path(category, template_name)

            # Delete template file
            os.remove(template_path)

            # Update template list
            self._load_templates_for_category(category)

            self._update_status(f"Deleted template: {template_name}")
        except Exception as e:
            self.logger.error(f"Error deleting template {template_name}: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not delete template {template_name}: {str(e)}"
            )

    def _save_template(self) -> None:
        """Save the current template."""
        if not self.current_template_path:
            messagebox.showerror(
                "Template Error",
                "No template selected"
            )
            return

        try:
            # Get template content
            template_content = self.content_text.get(1.0, tk.END)

            # Validate JSON
            try:
                json.loads(template_content)
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Template Error",
                    f"Invalid JSON: {str(e)}"
                )
                return

            # Save template file
            with open(self.current_template_path, "w", encoding="utf-8") as f:
                f.write(template_content)

            self._update_status("Template saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving template: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not save template: {str(e)}"
            )

    def _format_json(self) -> None:
        """Format the JSON content in the editor."""
        try:
            # Get template content
            template_content = self.content_text.get(1.0, tk.END)

            # Parse JSON
            try:
                template_json = json.loads(template_content)
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Template Error",
                    f"Invalid JSON: {str(e)}"
                )
                return

            # Format JSON
            formatted_json = json.dumps(template_json, indent=2)

            # Update content editor
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(tk.END, formatted_json)

            self._update_status("JSON formatted successfully")
        except Exception as e:
            self.logger.error(f"Error formatting JSON: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not format JSON: {str(e)}"
            )

    def _validate_template(self) -> None:
        """Validate the current template."""
        try:
            # Get template content
            template_content = self.content_text.get(1.0, tk.END)

            # Parse JSON
            try:
                template_json = json.loads(template_content)
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Template Error",
                    f"Invalid JSON: {str(e)}"
                )
                return

            # Validate template structure
            errors = []

            # Check required fields
            if "service" not in template_json:
                errors.append("Missing 'service' field")

            if "method" not in template_json:
                errors.append("Missing 'method' field")

            if "params" not in template_json:
                errors.append("Missing 'params' field")
            elif not isinstance(template_json["params"], dict):
                errors.append("'params' field must be an object")

            # Show validation results
            if errors:
                messagebox.showerror(
                    "Validation Error",
                    "Template validation failed:\n" + "\n".join(errors)
                )
            else:
                messagebox.showinfo(
                    "Validation Success",
                    "Template is valid"
                )

            self._update_status("Template validation completed")
        except Exception as e:
            self.logger.error(f"Error validating template: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not validate template: {str(e)}"
            )

    def _add_to_queue(self) -> None:
        """Add the current template to the test queue."""
        try:
            # Get template content
            template_content = self.content_text.get(1.0, tk.END)

            # Parse JSON
            try:
                template_json = json.loads(template_content)
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Template Error",
                    f"Invalid JSON: {str(e)}"
                )
                return

            # Validate template - check for either direct service/method or test_cases structure
            is_valid = False

            # Check for direct service/method structure
            if "service" in template_json and "method" in template_json:
                is_valid = True

            # Check for test_cases array structure
            if "test_cases" in template_json and isinstance(template_json["test_cases"], list):
                # If there's at least one test case, consider it valid
                if len(template_json["test_cases"]) > 0:
                    is_valid = True

            if not is_valid:
                messagebox.showerror(
                    "Template Error",
                    "Template must have 'service'/'method' fields or 'test_cases' array"
                )
                return

            # Add to queue
            category = self.category_var.get()
            selection = self.template_listbox.curselection()
            if selection:
                template_name = self.template_listbox.get(selection[0])
            else:
                template_name = None

            # Use robust test name extraction
            extracted_name = extract_test_name(template_json, template_name)

            # Add to queue panel if parent reference is available
            if hasattr(self, 'parent') and hasattr(self.parent, 'queue_panel') and self.parent.queue_panel:
                self.parent.queue_panel.add_to_queue(
                    template_json,
                    category,
                    extracted_name
                )

                # Switch to queue tab
                if hasattr(self.parent, 'notebook') and self.parent.notebook:
                    self.parent.notebook.select(self.parent.queue_tab)

                self._update_status(f"Added template {template_name} to queue")
            else:
                messagebox.showinfo(
                    "Add to Queue",
                    "Queue panel not available"
                )

            self._update_status("Template added to queue")
        except Exception as e:
            self.logger.error(f"Error adding template to queue: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not add template to queue: {str(e)}"
            )

    def _update_status(self, message: str) -> None:
        """
        Update the status message.

        Args:
            message: Status message
        """
        if self.status_callback:
            self.status_callback(message)

    def get_selected_template(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently selected template.

        Returns:
            The template data as a dictionary, or None if no template is selected
            or the template is invalid.
        """
        try:
            # Get template content
            template_content = self.content_text.get(1.0, tk.END)

            # Parse JSON
            try:
                template_json = json.loads(template_content)
            except json.JSONDecodeError as e:
                messagebox.showerror(
                    "Template Error",
                    f"Invalid JSON: {str(e)}"
                )
                return None

            # Validate template - check for either direct service/method or test_cases structure
            is_valid = False

            # Check for direct service/method structure
            if "service" in template_json and "method" in template_json:
                is_valid = True

            # Check for test_cases array structure
            if "test_cases" in template_json and isinstance(template_json["test_cases"], list):
                # If there's at least one test case, consider it valid
                if len(template_json["test_cases"]) > 0:
                    is_valid = True

            if not is_valid:
                messagebox.showerror(
                    "Template Error",
                    "Template must have 'service'/'method' fields or 'test_cases' array"
                )
                return None

            # Add category and template name
            category = self.category_var.get()
            selection = self.template_listbox.curselection()
            if selection:
                template_name = self.template_listbox.get(selection[0])
            else:
                template_name = None

            # Use robust test name extraction
            extracted_name = extract_test_name(template_json, template_name)

            # Return template with metadata
            return {
                "template_data": template_json,
                "category": category,
                "template_name": extracted_name
            }

        except Exception as e:
            self.logger.error(f"Error getting selected template: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not get selected template: {str(e)}"
            )
            return None
