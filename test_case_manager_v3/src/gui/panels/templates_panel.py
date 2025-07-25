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


# Import test name utilities
from src.utils.formatters import extract_test_name



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

        # Template data for new batch interface
        self.categories: List[str] = []
        self.category_tests: Dict[str, List[Dict[str, Any]]] = {}
        self.current_category: str = ""

        # Selection state management - for preview staging
        self.preview_tests: List[Dict[str, Any]] = []  # Tests in preview/staging area

        # UI components
        self.category_var = tk.StringVar()
        self.preview_count_var = tk.StringVar(value="Preview: 0 tests")

        # UI component references
        self.test_list_frame: Optional[ttk.Frame] = None
        self.preview_frame: Optional[ttk.LabelFrame] = None
        self.preview_listbox: Optional[tk.Listbox] = None
        self.content_viewer_frame: Optional[ttk.LabelFrame] = None
        self.content_text: Optional[tk.Text] = None

        # Create UI
        self._create_ui()

        # Load template data
        self._load_templates()

    def _create_custom_styles(self) -> None:
        """Create custom TTK styles for enhanced visual appearance."""
        try:
            style = ttk.Style()

            # Only configure basic button styles that are widely supported
            style.configure("Primary.TButton",
                           font=("Segoe UI", 10, "bold"))

            style.configure("Secondary.TButton",
                           font=("Segoe UI", 9))

            style.configure("Edit.TButton",
                           font=("Segoe UI", 9))

        except Exception as e:
            # If custom styles fail, continue without them
            self.logger.warning(f"Could not apply custom styles: {e}")

    def _create_ui(self) -> None:
        """Create clean and simple UI components."""
        # Configure main layout - single column for test list and preview
        self.columnconfigure(0, weight=1)  # Single column takes full width
        self.rowconfigure(1, weight=1)  # Test list gets main space
        self.rowconfigure(2, weight=1)  # Preview section

        # Simple header section - spans both columns
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        header_frame.columnconfigure(1, weight=1)

        # Category selection - clean and simple
        ttk.Label(header_frame, text="Category:", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )

        self.category_combo = ttk.Combobox(
            header_frame,
            textvariable=self.category_var,
            state="readonly",
            width=20
        )
        self.category_combo.grid(row=0, column=1, sticky="w")
        self.category_combo.bind("<<ComboboxSelected>>", self._on_category_selected)

        # Preview counter - simple
        self.count_label = ttk.Label(
            header_frame,
            textvariable=self.preview_count_var,
            font=("Segoe UI", 10, "bold")
        )
        self.count_label.grid(row=0, column=2, sticky="e")

        # Test case list - clean
        content_frame = ttk.LabelFrame(self, text="Test Cases")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)

        # Simple scrollable frame
        canvas = tk.Canvas(content_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        self.test_list_frame = ttk.Frame(canvas)

        self.test_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.test_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=5)

        # Preview section for staging tests
        self._create_preview_section()

    def _view_test_popup(self, test_index: int) -> None:
        """Show test content in a popup dialog."""
        if not self.current_category or self.current_category not in self.category_tests:
            return

        category_tests = self.category_tests[self.current_category]
        if test_index < 0 or test_index >= len(category_tests):
            return

        test_data = category_tests[test_index]

        # Create popup dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"View Test Case - {test_data['display_name']}")
        dialog.geometry("600x500")
        dialog.resizable(True, True)

        # Center the dialog
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # Main frame
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Content text with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        content_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            state=tk.DISABLED
        )
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=content_text.yview)
        content_text.configure(yscrollcommand=scrollbar.set)

        content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Close button
        close_btn = ttk.Button(
            button_frame,
            text="Close",
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT)

        # Load and display content with syntax highlighting
        try:
            content = self._format_test_content(test_data)
            content_text.configure(state=tk.NORMAL)
            content_text.insert(1.0, content)
            self._apply_json_syntax_highlighting(content_text, content)
            content_text.configure(state=tk.DISABLED)
        except Exception as e:
            content_text.configure(state=tk.NORMAL)
            content_text.insert(1.0, f"Error loading test content: {str(e)}")
            content_text.configure(state=tk.DISABLED)

    def _edit_test_popup(self, test_index: int) -> None:
        """Show test edit dialog."""
        if not self.current_category or self.current_category not in self.category_tests:
            return

        category_tests = self.category_tests[self.current_category]
        if test_index < 0 or test_index >= len(category_tests):
            return

        test_data = category_tests[test_index]

        # Create popup dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Test Case - {test_data['display_name']}")
        dialog.geometry("700x600")
        dialog.resizable(True, True)

        # Center the dialog
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # Main frame
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Content text with scrollbar for editing
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        content_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=content_text.yview)
        content_text.configure(yscrollcommand=scrollbar.set)

        content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Save button
        def save_changes():
            try:
                # Get edited content
                edited_content = content_text.get(1.0, tk.END).strip()

                # Validate JSON
                json.loads(edited_content)

                # Save to file
                with open(test_data['template_path'], 'w', encoding='utf-8') as f:
                    f.write(edited_content)

                messagebox.showinfo("Success", "Test case saved successfully!")
                dialog.destroy()

                # Refresh the current category to show changes
                self._load_category_tests(self.current_category)

            except json.JSONDecodeError as e:
                messagebox.showerror("JSON Error", f"Invalid JSON format: {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save test case: {str(e)}")

        save_btn = ttk.Button(
            button_frame,
            text="Save",
            command=save_changes
        )
        save_btn.pack(side=tk.RIGHT, padx=(0, 5))

        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        )
        cancel_btn.pack(side=tk.RIGHT)

        # Load and display content for editing with syntax highlighting
        try:
            if test_data.get('template_path') and os.path.exists(test_data['template_path']):
                with open(test_data['template_path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                content_text.insert(1.0, content)
                # Apply JSON syntax highlighting for edit dialog
                self._apply_json_syntax_highlighting_edit(content_text, content)
            else:
                content_text.insert(1.0, "# Template file not found")
        except Exception as e:
            content_text.insert(1.0, f"# Error loading template: {str(e)}")

    def _format_test_content(self, test_data: Dict[str, Any]) -> str:
        """Format test content for display."""
        content_parts = []

        # Test metadata
        content_parts.append("=== TEST METADATA ===")
        content_parts.append(f"Display Name: {test_data.get('display_name', 'N/A')}")
        content_parts.append(f"File Name: {test_data.get('file_name', 'N/A')}")
        content_parts.append(f"Template Path: {test_data.get('template_path', 'N/A')}")
        content_parts.append("")

        # Test case parameters
        template_data = test_data.get('template_data', {})
        if template_data:
            content_parts.append("=== TEST CASE PARAMETERS ===")
            test_cases = template_data.get('test_cases', [])
            for i, test_case in enumerate(test_cases):
                content_parts.append(f"Test Case {i + 1}:")
                content_parts.append(f"  Service: {test_case.get('service', 'N/A')}")
                content_parts.append(f"  Action: {test_case.get('action', 'N/A')}")

                params = test_case.get('params', {})
                if params:
                    content_parts.append("  Parameters:")
                    for key, value in params.items():
                        content_parts.append(f"    {key}: {value}")
                content_parts.append("")

        # Raw JSON content
        content_parts.append("=== RAW JSON CONTENT ===")
        try:
            import json
            formatted_json = json.dumps(template_data, indent=2, ensure_ascii=False)
            content_parts.append(formatted_json)
        except Exception as e:
            content_parts.append(f"Error formatting JSON: {str(e)}")

        return "\n".join(content_parts)

    def _apply_json_syntax_highlighting(self, text_widget: tk.Text, content: str) -> None:
        """Apply JSON syntax highlighting to text widget."""
        # Configure text tags for different JSON elements (VSCode-like colors)
        text_widget.tag_configure("json_key", foreground="#9CDCFE")  # Light blue for keys
        text_widget.tag_configure("json_string", foreground="#CE9178")  # Orange for strings
        text_widget.tag_configure("json_number", foreground="#B5CEA8")  # Light green for numbers
        text_widget.tag_configure("json_boolean", foreground="#569CD6")  # Blue for booleans
        text_widget.tag_configure("json_null", foreground="#569CD6")  # Blue for null
        text_widget.tag_configure("json_bracket", foreground="#D4D4D4", font=("Consolas", 10, "bold"))  # Light gray for brackets
        text_widget.tag_configure("json_comment", foreground="#6A9955", font=("Consolas", 10, "italic"))  # Green for comments

        # Set dark background for better contrast
        text_widget.configure(bg="#1E1E1E", fg="#D4D4D4", insertbackground="#FFFFFF")

        lines = content.split('\n')
        json_started = False

        for line_num, line in enumerate(lines, 1):
            # Check if we're in the JSON section
            if "=== RAW JSON CONTENT ===" in line:
                json_started = True
                continue

            if not json_started:
                continue

            # Apply highlighting to JSON content
            self._highlight_json_line(text_widget, line, line_num)

    def _highlight_json_line(self, text_widget: tk.Text, line: str, line_num: int) -> None:
        """Apply syntax highlighting to a single line of JSON."""
        import re

        # Highlight JSON keys (quoted strings followed by colon)
        key_pattern = r'"([^"\\]|\\.)*"(?=\s*:)'
        for match in re.finditer(key_pattern, line):
            start_col = match.start()
            end_col = match.end()
            start_pos = f"{line_num}.{start_col}"
            end_pos = f"{line_num}.{end_col}"
            text_widget.tag_add("json_key", start_pos, end_pos)

        # Highlight JSON string values (quoted strings not followed by colon)
        string_pattern = r'"([^"\\]|\\.)*"(?!\s*:)'
        for match in re.finditer(string_pattern, line):
            start_col = match.start()
            end_col = match.end()
            start_pos = f"{line_num}.{start_col}"
            end_pos = f"{line_num}.{end_col}"
            text_widget.tag_add("json_string", start_pos, end_pos)

        # Highlight numbers
        number_pattern = r'-?\d+\.?\d*'
        for match in re.finditer(number_pattern, line):
            # Make sure it's not part of a string
            if not self._is_inside_quotes(line, match.start()):
                start_col = match.start()
                end_col = match.end()
                start_pos = f"{line_num}.{start_col}"
                end_pos = f"{line_num}.{end_col}"
                text_widget.tag_add("json_number", start_pos, end_pos)

        # Highlight booleans and null
        bool_null_pattern = r'\b(true|false|null)\b'
        for match in re.finditer(bool_null_pattern, line):
            if not self._is_inside_quotes(line, match.start()):
                start_col = match.start()
                end_col = match.end()
                start_pos = f"{line_num}.{start_col}"
                end_pos = f"{line_num}.{end_col}"
                if match.group() == "null":
                    text_widget.tag_add("json_null", start_pos, end_pos)
                else:
                    text_widget.tag_add("json_boolean", start_pos, end_pos)

        # Highlight brackets and braces
        bracket_pattern = r'[{}\[\],]'
        for match in re.finditer(bracket_pattern, line):
            if not self._is_inside_quotes(line, match.start()):
                start_col = match.start()
                end_col = match.end()
                start_pos = f"{line_num}.{start_col}"
                end_pos = f"{line_num}.{end_col}"
                text_widget.tag_add("json_bracket", start_pos, end_pos)

    def _is_inside_quotes(self, line: str, position: int) -> bool:
        """Check if a position in the line is inside quotes."""
        quote_count = 0
        for i in range(position):
            if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                quote_count += 1
        return quote_count % 2 == 1

    def _apply_json_syntax_highlighting_edit(self, text_widget: tk.Text, content: str) -> None:
        """Apply JSON syntax highlighting to edit dialog text widget."""
        # Configure text tags for different JSON elements (VSCode-like colors)
        text_widget.tag_configure("json_key", foreground="#9CDCFE")  # Light blue for keys
        text_widget.tag_configure("json_string", foreground="#CE9178")  # Orange for strings
        text_widget.tag_configure("json_number", foreground="#B5CEA8")  # Light green for numbers
        text_widget.tag_configure("json_boolean", foreground="#569CD6")  # Blue for booleans
        text_widget.tag_configure("json_null", foreground="#569CD6")  # Blue for null
        text_widget.tag_configure("json_bracket", foreground="#D4D4D4", font=("Consolas", 10, "bold"))  # Light gray for brackets

        # Set dark background for better contrast
        text_widget.configure(bg="#1E1E1E", fg="#D4D4D4", insertbackground="#FFFFFF")

        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Apply highlighting to JSON content
            self._highlight_json_line_edit(text_widget, line, line_num)

    def _highlight_json_line_edit(self, text_widget: tk.Text, line: str, line_num: int) -> None:
        """Apply syntax highlighting to a single line of JSON in edit mode."""
        import re

        # Highlight JSON keys (quoted strings followed by colon)
        key_pattern = r'"([^"\\]|\\.)*"(?=\s*:)'
        for match in re.finditer(key_pattern, line):
            start_col = match.start()
            end_col = match.end()
            start_pos = f"{line_num}.{start_col}"
            end_pos = f"{line_num}.{end_col}"
            text_widget.tag_add("json_key", start_pos, end_pos)

        # Highlight JSON string values (quoted strings not followed by colon)
        string_pattern = r'"([^"\\]|\\.)*"(?!\s*:)'
        for match in re.finditer(string_pattern, line):
            start_col = match.start()
            end_col = match.end()
            start_pos = f"{line_num}.{start_col}"
            end_pos = f"{line_num}.{end_col}"
            text_widget.tag_add("json_string", start_pos, end_pos)

        # Highlight numbers
        number_pattern = r'-?\d+\.?\d*'
        for match in re.finditer(number_pattern, line):
            # Make sure it's not part of a string
            if not self._is_inside_quotes(line, match.start()):
                start_col = match.start()
                end_col = match.end()
                start_pos = f"{line_num}.{start_col}"
                end_pos = f"{line_num}.{end_col}"
                text_widget.tag_add("json_number", start_pos, end_pos)

        # Highlight booleans and null
        bool_null_pattern = r'\b(true|false|null)\b'
        for match in re.finditer(bool_null_pattern, line):
            if not self._is_inside_quotes(line, match.start()):
                start_col = match.start()
                end_col = match.end()
                start_pos = f"{line_num}.{start_col}"
                end_pos = f"{line_num}.{end_col}"
                if match.group() == "null":
                    text_widget.tag_add("json_null", start_pos, end_pos)
                else:
                    text_widget.tag_add("json_boolean", start_pos, end_pos)

        # Highlight brackets and braces
        bracket_pattern = r'[{}\[\],]'
        for match in re.finditer(bracket_pattern, line):
            if not self._is_inside_quotes(line, match.start()):
                start_col = match.start()
                end_col = match.end()
                start_pos = f"{line_num}.{start_col}"
                end_pos = f"{line_num}.{end_col}"
                text_widget.tag_add("json_bracket", start_pos, end_pos)

    def _create_preview_section(self) -> None:
        """Create the preview/staging section for selected tests."""
        self.preview_frame = ttk.LabelFrame(self, text="Preview - Ready to Send")
        self.preview_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.preview_frame.columnconfigure(0, weight=1)

        # Preview listbox with scrollbar
        preview_content = ttk.Frame(self.preview_frame)
        preview_content.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        preview_content.columnconfigure(0, weight=1)

        self.preview_listbox = tk.Listbox(
            preview_content,
            height=4,
            font=("Segoe UI", 9)
        )
        self.preview_listbox.grid(row=0, column=0, sticky="ew")

        preview_scrollbar = ttk.Scrollbar(
            preview_content,
            orient="vertical",
            command=self.preview_listbox.yview
        )
        preview_scrollbar.grid(row=0, column=1, sticky="ns")
        self.preview_listbox.configure(yscrollcommand=preview_scrollbar.set)

        # Preview controls
        preview_controls = ttk.Frame(self.preview_frame)
        preview_controls.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        preview_controls.columnconfigure(1, weight=1)

        # Remove selected button
        ttk.Button(
            preview_controls,
            text="Remove Selected",
            command=self._remove_from_preview
        ).grid(row=0, column=0, padx=(0, 10))

        # Send to queue button
        ttk.Button(
            preview_controls,
            text="Send to Queue",
            command=self._send_preview_to_queue
        ).grid(row=0, column=2, sticky="e")

        # Initially hide preview section
        self.preview_frame.grid_remove()

    def _load_templates(self) -> None:
        """Load templates from the template directory for batch interface."""
        try:
            # Get categories
            self.categories = self.test_loader.get_categories()

            # Create category display names with test counts
            category_display_names = []
            for category in self.categories:
                try:
                    templates = self.test_loader.get_templates_for_category(category)
                    count = len(templates)
                    display_name = f"{category} ({count} tests)" if count != 1 else f"{category} (1 test)"
                    category_display_names.append(display_name)
                except Exception as e:
                    self.logger.warning(f"Could not count templates for {category}: {e}")
                    category_display_names.append(f"{category} (? tests)")

            # Update category dropdown with enhanced display names
            self.category_combo["values"] = category_display_names

            if self.categories:
                # Set the first category as selected
                self.category_var.set(category_display_names[0])
                self.current_category = self.categories[0]
                self._load_category_tests(self.categories[0])

            self._update_status("Templates loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not load templates: {str(e)}"
            )

    def _load_category_tests(self, category: str) -> None:
        """
        Load test cases for a specific category.

        Args:
            category: Category name
        """
        try:
            # Clear existing test list
            if self.test_list_frame:
                for widget in self.test_list_frame.winfo_children():
                    widget.destroy()

            # No checkbox variables needed for individual add buttons

            # Get templates for category
            templates = self.test_loader.get_templates_for_category(category)

            # Convert templates to test data
            test_data = []
            for template_file in templates:
                try:
                    # Load template content to get display name
                    template_path = self.test_loader.get_template_path(category, template_file)
                    with open(template_path, "r", encoding="utf-8") as f:
                        template_content = json.loads(f.read())

                    # Extract display name
                    display_name = extract_test_name(template_content, template_file)

                    test_data.append({
                        "file_name": template_file,
                        "display_name": display_name,
                        "template_path": template_path,
                        "template_data": template_content
                    })
                except Exception as e:
                    self.logger.warning(f"Could not load template {template_file}: {e}")
                    # Add with basic info if loading fails
                    test_data.append({
                        "file_name": template_file,
                        "display_name": template_file.replace(".json", "").replace("_", " ").title(),
                        "template_path": "",
                        "template_data": {}
                    })

            # Store test data for category
            self.category_tests[category] = test_data

            # Create UI for test list
            self._create_test_list_ui(test_data)

            # Update preview counter
            self._update_preview_counter()

        except Exception as e:
            self.logger.error(f"Error loading category tests: {e}")
            messagebox.showerror("Error", f"Could not load tests for {category}: {str(e)}")

    def _update_status(self, message: str) -> None:
        """
        Update the status message.

        Args:
            message: Status message
        """
        if self.status_callback:
            self.status_callback(message)

    def _create_test_list_ui(self, test_data: List[Dict[str, Any]]) -> None:
        """
        Create test list UI with individual add buttons.

        Args:
            test_data: List of test data dictionaries
        """
        if not self.test_list_frame:
            return

        # Configure test list frame
        self.test_list_frame.columnconfigure(0, weight=1)

        for i, test in enumerate(test_data):
            # Frame for each test item
            test_frame = ttk.Frame(self.test_list_frame)
            test_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=3)
            test_frame.columnconfigure(0, weight=1)

            # Test name label
            name_label = ttk.Label(
                test_frame,
                text=test["display_name"],
                font=("Segoe UI", 10)
            )
            name_label.grid(row=0, column=0, sticky="w")

            # Button frame for View, Edit, and Add buttons
            button_frame = ttk.Frame(test_frame)
            button_frame.grid(row=0, column=1, sticky="e", padx=(10, 0))

            # Configure button frame columns to ensure all buttons fit
            button_frame.columnconfigure(0, weight=0)
            button_frame.columnconfigure(1, weight=0)
            button_frame.columnconfigure(2, weight=0)

            # Create button commands with proper closure
            def make_view_command(index):
                return lambda: self._view_test_popup(index)

            def make_edit_command(index):
                return lambda: self._edit_test_popup(index)

            def make_add_command(index):
                return lambda: self._add_test_to_preview(index)

            # View button
            view_btn = ttk.Button(
                button_frame,
                text="View",
                width=8,
                command=make_view_command(i)
            )
            view_btn.grid(row=0, column=0, padx=(0, 3))

            # Edit button
            edit_btn = ttk.Button(
                button_frame,
                text="Edit",
                width=8,
                command=make_edit_command(i)
            )
            edit_btn.grid(row=0, column=1, padx=(0, 3))

            # Add button
            add_btn = ttk.Button(
                button_frame,
                text="Add",
                width=8,
                command=make_add_command(i)
            )
            add_btn.grid(row=0, column=2)

    def _configure_test_item_style(self, frame: ttk.Frame, index: int) -> None:
        """Configure styling for individual test items."""
        try:
            style = ttk.Style()

            # Alternating row colors for better readability
            bg_color = "#ffffff" if index % 2 == 0 else "#f8f9fa"

            style_name = f"TestItem{index}.TFrame"
            style.configure(style_name,
                           background=bg_color,
                           relief="flat",
                           borderwidth=0)

            frame.configure(style=style_name)
        except Exception as e:
            # Fallback to basic styling if custom styles fail
            self.logger.warning(f"Could not apply custom styling: {e}")
            frame.configure(relief="flat")

    def _on_category_selected(self, event: tk.Event) -> None:
        """Handle category selection change."""
        display_name = self.category_var.get()
        if display_name:
            # Extract actual category name from display name (e.g., "LAN (5 tests)" -> "LAN")
            category = display_name.split(" (")[0]
            if category != self.current_category:
                self.current_category = category
                self._load_category_tests(category)

    def _add_test_to_preview(self, test_index: int) -> None:
        """Add individual test to preview staging area."""
        if not self.current_category or self.current_category not in self.category_tests:
            return

        category_tests = self.category_tests[self.current_category]
        if test_index < 0 or test_index >= len(category_tests):
            return

        test_data = category_tests[test_index].copy()
        test_data["category"] = self.current_category

        # Check if already in preview
        for existing_test in self.preview_tests:
            if (existing_test["display_name"] == test_data["display_name"] and
                existing_test["category"] == test_data["category"]):
                messagebox.showinfo("Already Added", f"'{test_data['display_name']}' is already in preview.")
                return

        # Add to preview
        self.preview_tests.append(test_data)
        self._update_preview_display()
        self._update_preview_counter()

        # Show preview section if hidden
        if self.preview_frame:
            self.preview_frame.grid()

        self._update_status(f"Added '{test_data['display_name']}' to preview")







    def _update_preview_display(self) -> None:
        """Update the preview listbox display."""
        if not self.preview_listbox:
            return

        # Clear listbox
        self.preview_listbox.delete(0, tk.END)

        # Add tests to listbox
        for i, test in enumerate(self.preview_tests):
            display_text = f"{i+1}. {test['display_name']} ({test['category']})"
            self.preview_listbox.insert(tk.END, display_text)

    def _update_preview_counter(self) -> None:
        """Update the preview counter display."""
        count = len(self.preview_tests)
        if count == 0:
            self.preview_count_var.set("Preview: 0 tests")
        elif count == 1:
            self.preview_count_var.set("Preview: 1 test")
        else:
            self.preview_count_var.set(f"Preview: {count} tests")

    def _remove_from_preview(self) -> None:
        """Remove selected test from preview."""
        if not self.preview_listbox:
            return

        selection = self.preview_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a test to remove from preview.")
            return

        # Remove selected tests (in reverse order to maintain indices)
        for index in reversed(selection):
            if 0 <= index < len(self.preview_tests):
                removed_test = self.preview_tests.pop(index)
                self._update_status(f"Removed '{removed_test['display_name']}' from preview")

        # Update display
        self._update_preview_display()
        self._update_preview_counter()

        # Hide preview section if empty
        if not self.preview_tests and self.preview_frame:
            self.preview_frame.grid_remove()

    def _send_preview_to_queue(self) -> None:
        """Send all preview tests to queue and switch to Queue tab."""
        if not self.preview_tests:
            messagebox.showinfo("No Tests", "No tests in preview to send to queue.")
            return

        # Add all preview tests to queue
        if hasattr(self.parent, 'queue_panel'):
            for test in self.preview_tests:
                # Extract the actual test data from template_data
                actual_test_data = test.get("template_data", {})

                self.parent.queue_panel.add_to_queue(
                    test_data=actual_test_data,
                    category=test["category"],
                    name=test["display_name"]
                )

        count = len(self.preview_tests)

        # Clear preview
        self.preview_tests.clear()
        self._update_preview_display()
        self._update_preview_counter()

        # Hide preview section
        if self.preview_frame:
            self.preview_frame.grid_remove()

        # Switch to Queue tab
        if hasattr(self.parent, 'notebook') and hasattr(self.parent, 'queue_tab'):
            self.parent.notebook.select(self.parent.queue_tab)

        self._update_status(f"Sent {count} test(s) to queue")

        # Show success message
        messagebox.showinfo(
            "Tests Sent",
            f"Successfully sent {count} test case(s) to the queue!"
        )


