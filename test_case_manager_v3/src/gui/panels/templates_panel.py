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
from typing import Dict, Any, Optional, List, Callable, Set, cast

from src.core.test_case_loader import TestCaseLoader
from src.core.preset_manager import PresetManager
from src.core.constants import CONFIG_DIR
from src.gui.dialogs.preset_manager_dialog import PresetManagerDialog
from src.utils.logger import get_logger


# Import test name utilities
from src.utils.formatters import extract_test_name

# UI Constants for improved UX
SPACING = {
    'xs': 4,   # Between related elements
    'sm': 8,   # Between groups within section
    'md': 16,  # Between sections
    'lg': 24,  # Between major areas
    'xl': 32   # Panel margins
}

# Color scheme for visual hierarchy
COLORS = {
    'primary': '#005a9e',      # Darker Microsoft Blue for better contrast
    'success': '#107c10',      # Green
    'warning': '#ff8c00',      # Orange
    'error': '#d13438',        # Red
    'background': '#f3f2f1',   # Light Gray
    'surface': '#ffffff',      # White
    'text_primary': '#323130', # Dark Gray
    'text_secondary': '#605e5c' # Medium Gray
}



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

        # Initialize PresetManager
        self.preset_manager = PresetManager(CONFIG_DIR)

        # Reference to parent window (will be set by MainWindow)
        self.parent: Any = None

        # Template data for new batch interface
        self.categories: List[str] = []
        self.category_tests: Dict[str, List[Dict[str, Any]]] = {}
        self.current_category: str = ""

        # Search functionality data
        self.all_test_data: List[Dict[str, Any]] = []  # All tests from all categories
        self.original_test_data: List[Dict[str, Any]] = []  # Current category original data
        self.filtered_test_data: List[Dict[str, Any]] = []  # Current filtered data

        # Selection state management - for preview staging
        self.preview_tests: List[Dict[str, Any]] = []  # Tests in preview/staging area

        # Checkbox selection state management
        self.selected_tests: Set[str] = set()  # Set of selected test IDs (using display_name + category as ID)
        self.checkbox_vars: Dict[str, tk.BooleanVar] = {}  # Checkbox variables keyed by test ID
        self.sent_tests: Set[str] = set()  # Track tests that have been sent to queue

        # Selection order tracking - for maintaining user's intended execution sequence
        self.selection_order: List[str] = []  # List of test IDs in the order they were selected

        # UI components
        self.category_var = tk.StringVar()
        self.preview_count_var = tk.StringVar(value="0 tests ready")

        # Search UI components
        self.search_var = tk.StringVar()
        self.search_results_var = tk.StringVar(value="")

        # Preset UI components
        self.preset_var = tk.StringVar()
        self.preset_combo: Optional[ttk.Combobox] = None
        self.save_preset_btn: Optional[ttk.Button] = None

        # UI component references
        self.test_list_frame: Optional[ttk.Frame] = None
        self.preview_frame: Optional[ttk.LabelFrame] = None
        self.preview_listbox: Optional[tk.Listbox] = None
        self.content_viewer_frame: Optional[ttk.LabelFrame] = None
        self.content_text: Optional[tk.Text] = None

        # Performance optimization variables
        self._resize_timer: Optional[str] = None
        self._last_width: int = 0
        self._resize_debounce_ms: int = 150  # Debounce resize events
        self._is_resizing: bool = False
        self._is_ui_refresh: bool = False  # Flag to indicate UI refresh vs category change

        # Create UI
        self._create_ui()

        # Load template data
        self._load_templates()

    def _create_custom_styles(self) -> None:
        """Create custom TTK styles for enhanced visual appearance and button hierarchy."""
        try:
            style = ttk.Style()

            # Keep the default Windows theme for native appearance
            self.logger.info(f"Using default TTK theme: {style.theme_use()}")

            # Primary Button - for main actions like "Send to Queue"
            # Use minimal styling to maintain native Windows appearance
            style.configure("Primary.TButton",
                           font=("Segoe UI", 10, "bold"))

            # Secondary Button - for common actions like "All", "None", "Filtered"
            # Use minimal styling to maintain native appearance
            style.configure("Secondary.TButton",
                           font=("Segoe UI", 9))

            # Tertiary Button - for less important actions like "Clear"
            # Use minimal styling to maintain native appearance
            style.configure("Tertiary.TButton",
                           font=("Segoe UI", 9))

            # Link Button - for actions like "Manage Presets"
            style.configure("Link.TButton",
                           font=("Segoe UI", 9, "underline"),
                           foreground=COLORS['primary'])

            # Status Label - for selection counter
            style.configure("Status.TLabel",
                           font=("Segoe UI", 9, "bold"),
                           foreground=COLORS['primary'])

            # Heading Label - for section headers
            style.configure("Heading.TLabel",
                           font=("Segoe UI", 10, "bold"),
                           foreground=COLORS['text_primary'])

            self.logger.info("Minimal custom TTK styles configured successfully")

        except Exception as e:
            # If custom styles fail, continue without them
            self.logger.warning(f"Could not apply custom styles: {e}")

    def _apply_manual_button_styling(self, button: ttk.Button, style_type: str) -> None:
        """Apply minimal styling to maintain native Windows appearance."""
        try:
            # Just apply the style, let Windows handle the appearance
            if style_type == "Primary":
                button.configure(style="Primary.TButton")
            elif style_type == "Secondary":
                button.configure(style="Secondary.TButton")
            elif style_type == "Tertiary":
                button.configure(style="Tertiary.TButton")
        except Exception as e:
            self.logger.debug(f"Using default styling for {style_type} button: {e}")

    def _create_ui(self) -> None:
        """Create clean and simple UI components with responsive layout."""
        # Create custom styles first
        self._create_custom_styles()

        # Configure main grid layout for responsive two-panel design
        # Initial layout - will be adjusted by resize handler
        self.columnconfigure(0, weight=2)  # Left panel (Test Cases) - more space
        self.columnconfigure(1, weight=1)  # Right panel (Preview) - less space
        self.rowconfigure(1, weight=1)  # Main content area

        # Header section with search and category (spans both columns)
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        header_frame.columnconfigure(1, weight=1)  # Search entry expands
        header_frame.columnconfigure(4, weight=1)  # Space before preview counter

        # Search row (row 0)
        self._create_search_ui(header_frame, row=0)

        # Category row (row 1)
        self._create_category_ui(header_frame, row=1)

        # Selection toolbar (row 2) - Clean toolbar with logical grouping
        self._create_selection_toolbar(header_frame, row=2)

        # Preset controls (row 3) - Separate row for preset management
        self._create_preset_controls(header_frame, row=3)

        # Test case list - left panel with responsive padding
        content_frame = ttk.LabelFrame(self, text="Test Cases")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=8)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)

        # Add container frame to control max width on large screens
        self.content_container = ttk.Frame(content_frame)
        self.content_container.grid(row=0, column=0, sticky="nsew")
        self.content_container.columnconfigure(0, weight=1)
        self.content_container.rowconfigure(0, weight=1)

        # Improved scrollable frame with better integration
        self.test_canvas = tk.Canvas(
            self.content_container,
            highlightthickness=0,
            borderwidth=0,
            relief='flat',
            background='SystemButtonFace'  # Match system theme
        )
        self.scrollbar = ttk.Scrollbar(
            self.content_container,
            orient="vertical",
            command=self.test_canvas.yview
        )
        self.test_list_frame = ttk.Frame(self.test_canvas)

        self.test_list_frame.bind(
            "<Configure>",
            self._on_test_list_configure
        )

        self.test_canvas.create_window((0, 0), window=self.test_list_frame, anchor="nw")
        self.test_canvas.configure(yscrollcommand=self.scrollbar.set)

        # Grid with no padding for seamless integration
        self.test_canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Initially hide scrollbar
        self.scrollbar.grid_remove()

        # Bind mouse wheel events for better scrolling experience
        self._bind_mouse_wheel_events()

        # Bind window resize events to handle responsive layout
        self.bind("<Configure>", self._on_panel_resize)

        # Preview section for staging tests
        self._create_preview_section()

        # Ensure preview is visible after creation
        self.after(100, self._force_show_preview)

    def _on_panel_resize(self, event) -> None:
        """Handle panel resize events with debouncing for better performance."""
        if event.widget != self:
            return

        # Cancel previous timer if exists
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
            self._resize_timer = None

        # Set flag to indicate resizing is in progress
        self._is_resizing = True

        # Schedule debounced resize handling
        self._resize_timer = self.after(self._resize_debounce_ms, self._handle_resize_debounced)

    def _handle_resize_debounced(self) -> None:
        """Handle the actual resize logic after debouncing."""
        try:
            # Set UI refresh flag to preserve selections during resize
            self._is_ui_refresh = True

            # Get current panel width
            panel_width = self.winfo_width()
            if panel_width <= 1:
                self._is_resizing = False
                self._is_ui_refresh = False
                return

            # Skip if width hasn't changed significantly (avoid unnecessary updates)
            if abs(panel_width - self._last_width) < 10:
                self._is_resizing = False
                self._is_ui_refresh = False
                return

            self._last_width = panel_width

            # Simplified responsive layout - always show preview
            if panel_width < 800:
                # Small windows - prioritize test list
                self.columnconfigure(0, weight=3)  # Test list gets more space
                self.columnconfigure(1, weight=1)  # Preview gets less space
                self._adjust_responsive_padding(panel_width, "standard")
            elif panel_width < 1200:
                # Medium windows - balanced layout
                self.columnconfigure(0, weight=2)  # Test list
                self.columnconfigure(1, weight=1)  # Preview
                self._adjust_responsive_padding(panel_width, "standard")
            elif panel_width < 1600:
                # Large windows - more balanced
                self.columnconfigure(0, weight=3)  # Test list
                self.columnconfigure(1, weight=2)  # Preview gets more space
                self._adjust_responsive_padding(panel_width, "wide")
            else:
                # Very large windows - controlled
                self.columnconfigure(0, weight=2)  # Test list controlled
                self.columnconfigure(1, weight=1)  # Preview controlled
                self._adjust_responsive_padding(panel_width, "ultrawide")

            # Always ensure preview is visible
            self._force_show_preview()

            # Update scrollbar visibility after layout changes
            self.after(50, self._update_scrollbar_visibility)

        except Exception as e:
            self.logger.debug(f"Error in panel resize handler: {e}")
        finally:
            self._is_resizing = False
            self._is_ui_refresh = False
            self._resize_timer = None

    def _apply_compact_layout(self, panel_width: int) -> None:
        """Apply compact layout for small screens (<800px)."""
        try:
            # Hide preview panel completely on very small screens
            self.columnconfigure(0, weight=1)  # Test list takes full width
            self.columnconfigure(1, weight=0)  # Hide preview

            # Hide preview panel
            if hasattr(self, 'preview_frame') and self.preview_frame:
                self.preview_frame.grid_remove()

            # Compact header with smaller elements
            self._adjust_responsive_padding(panel_width, "compact")

        except Exception as e:
            self.logger.debug(f"Error applying compact layout: {e}")

    def _apply_standard_layout(self, panel_width: int) -> None:
        """Apply standard layout for medium screens (800-1200px)."""
        try:
            # Standard two-panel layout
            self.columnconfigure(0, weight=3)  # Test list gets more space
            self.columnconfigure(1, weight=1)  # Preview gets less space

            # Show preview panel
            if hasattr(self, 'preview_frame') and self.preview_frame:
                self.preview_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)

            self._adjust_responsive_padding(panel_width, "standard")

        except Exception as e:
            self.logger.debug(f"Error applying standard layout: {e}")

    def _apply_wide_layout(self, panel_width: int) -> None:
        """Apply wide layout for large screens (1200-1600px)."""
        try:
            # Balanced layout with more preview space
            self.columnconfigure(0, weight=2)  # Test list
            self.columnconfigure(1, weight=1)  # Preview

            # Show preview panel
            if hasattr(self, 'preview_frame') and self.preview_frame:
                self.preview_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)

            self._adjust_responsive_padding(panel_width, "wide")

        except Exception as e:
            self.logger.debug(f"Error applying wide layout: {e}")

    def _apply_ultrawide_layout(self, panel_width: int) -> None:
        """Apply ultrawide layout for very large screens (>1600px)."""
        try:
            # Controlled layout to prevent excessive stretching
            self.columnconfigure(0, weight=3)  # Test list controlled
            self.columnconfigure(1, weight=2)  # Preview gets more space

            # Show preview panel
            if hasattr(self, 'preview_frame') and self.preview_frame:
                self.preview_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)

            # Add max width constraints for test items
            self._adjust_responsive_padding(panel_width, "ultrawide")

        except Exception as e:
            self.logger.debug(f"Error applying ultrawide layout: {e}")

    def _adjust_responsive_padding(self, panel_width: int, size_category: str) -> None:
        """Adjust padding and margins based on window size and layout mode."""
        try:
            # Define padding values for different adaptive layouts
            if size_category == "compact":
                header_pad = 2
                content_pad = (2, 1)
                item_pad = 1
                button_width = 5  # Smaller buttons for compact
            elif size_category == "standard":
                header_pad = 4
                content_pad = (4, 2)
                item_pad = 2
                button_width = 6  # Standard button size
            elif size_category == "wide":
                header_pad = 6
                content_pad = (6, 3)
                item_pad = 2
                button_width = 7  # Slightly larger buttons
            else:  # ultrawide
                header_pad = 8
                content_pad = (8, 4)
                item_pad = 3
                button_width = 8  # Larger buttons for ultrawide

            # Store current layout configuration
            self._current_layout = {
                'mode': size_category,
                'header_pad': header_pad,
                'content_pad': content_pad,
                'item_pad': item_pad,
                'button_width': button_width,
                'panel_width': panel_width
            }

        except Exception as e:
            self.logger.debug(f"Error adjusting responsive padding: {e}")

    def _get_adaptive_button_width(self) -> int:
        """Get button width based on current layout mode."""
        if hasattr(self, '_current_layout'):
            return self._current_layout.get('button_width', 6)
        return 6  # Default width

    def _refresh_adaptive_layout(self) -> None:
        """Refresh the current adaptive layout after changes."""
        try:
            # Skip if currently resizing to avoid conflicts
            if self._is_resizing:
                return

            current_width = self.winfo_width()
            if current_width > 1 and abs(current_width - self._last_width) >= 10:
                # Only refresh if width has changed significantly
                self._handle_resize_debounced()
        except Exception as e:
            self.logger.debug(f"Error refreshing adaptive layout: {e}")

    def _force_show_preview(self) -> None:
        """Force show preview panel if it was hidden."""
        try:
            if hasattr(self, 'preview_frame') and self.preview_frame:
                # Ensure preview panel is visible
                self.preview_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
                # Reset column weights to show both panels
                self.columnconfigure(0, weight=2)  # Test list
                self.columnconfigure(1, weight=1)  # Preview
        except Exception as e:
            self.logger.debug(f"Error forcing preview show: {e}")

    def _view_test_popup(self, test_index: int) -> None:
        """Show test content in a popup dialog."""
        # Get the currently displayed tests (could be filtered)
        if self.current_category == "All":
            current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
            if current_search.strip():
                displayed_tests = self._filter_tests_by_search(current_search, self.all_test_data)
            else:
                displayed_tests = self.all_test_data
        else:
            current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
            if current_search.strip():
                displayed_tests = self._filter_tests_by_search(current_search, self.original_test_data)
            else:
                displayed_tests = self.original_test_data

        if test_index < 0 or test_index >= len(displayed_tests):
            return

        test_data = displayed_tests[test_index]

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





    def _create_preview_section(self) -> None:
        """Create the preview/staging section for selected tests with responsive design."""
        # Create main preview frame with improved header and consistent spacing
        self.preview_frame = ttk.LabelFrame(self, text="")
        self.preview_frame.grid(row=1, column=1, sticky="nsew",
                               padx=(SPACING['xs'], SPACING['md']),
                               pady=SPACING['md'])
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.rowconfigure(1, weight=1)  # Allow listbox to expand

        # Preview header with title and counter
        preview_header = ttk.Frame(self.preview_frame)
        preview_header.grid(row=0, column=0, sticky="ew",
                           padx=SPACING['xs'],
                           pady=(SPACING['xs'], 0))
        preview_header.columnconfigure(1, weight=1)

        # Preview title with improved styling
        title_label = ttk.Label(
            preview_header,
            text="📋 Ready to Execute",
            style="Heading.TLabel"
        )
        title_label.grid(row=0, column=0, sticky="w")

        # Preview counter with modern styling
        self.count_label = ttk.Label(
            preview_header,
            textvariable=self.preview_count_var,
            style="Status.TLabel"
        )
        self.count_label.grid(row=0, column=2, sticky="e", padx=(SPACING['md'], 0))

        # Preview listbox with scrollbar and consistent spacing
        preview_content = ttk.Frame(self.preview_frame)
        preview_content.grid(row=1, column=0, sticky="nsew",
                           padx=SPACING['xs'],
                           pady=SPACING['xs'])
        preview_content.columnconfigure(0, weight=1)
        preview_content.rowconfigure(0, weight=1)  # Allow listbox to expand vertically

        self.preview_listbox = tk.Listbox(
            preview_content,
            font=("Segoe UI", 9),
            selectmode=tk.EXTENDED,
            relief="flat",
            borderwidth=1
        )
        self.preview_listbox.grid(row=0, column=0, sticky="nsew")

        preview_scrollbar = ttk.Scrollbar(
            preview_content,
            orient="vertical",
            command=self.preview_listbox.yview
        )
        preview_scrollbar.grid(row=0, column=1, sticky="ns")
        self.preview_listbox.configure(yscrollcommand=preview_scrollbar.set)

        # Preview controls with clear hierarchy
        preview_controls = ttk.Frame(self.preview_frame)
        preview_controls.grid(row=2, column=0, sticky="ew", padx=SPACING['xs'], pady=SPACING['xs'])
        preview_controls.columnconfigure(1, weight=1)

        # Secondary action: Remove selected (left side)
        remove_btn = ttk.Button(
            preview_controls,
            text="Remove Selected",
            command=self._remove_from_preview,
            style="Tertiary.TButton",
            width=15
        )
        remove_btn.grid(row=0, column=0, sticky="w")

        # Primary action: Send to Queue (right side, prominent)
        self.send_btn = ttk.Button(
            preview_controls,
            text="Send to Queue",
            command=self._send_preview_to_queue,
            style="Primary.TButton",
            width=15
        )
        self.send_btn.grid(row=0, column=2, sticky="e")

        # Apply manual styling as fallback
        self._apply_manual_button_styling(self.send_btn, "Primary")

        # Preview section is always visible in two-panel layout
        # No need to hide initially

    def _create_search_ui(self, parent: ttk.Frame, row: int) -> None:
        """Create search UI components."""
        # Search label
        ttk.Label(
            parent,
            text="Search:",
            font=("Segoe UI", 10)
        ).grid(row=row, column=0, sticky="w", padx=(0, 10))

        # Search entry
        self.search_entry = ttk.Entry(
            parent,
            textvariable=self.search_var,
            width=30,
            font=("Segoe UI", 10)
        )
        self.search_entry.grid(row=row, column=1, sticky="ew", padx=(0, 10))

        # Bind real-time search
        self.search_var.trace('w', self._on_search_changed)
        self.search_entry.bind('<KeyRelease>', self._on_search_changed)

        # Clear button moved to batch action area

        # Search results counter
        self.search_results_label = ttk.Label(
            parent,
            textvariable=self.search_results_var,
            font=("Segoe UI", 9),
            foreground="gray"
        )
        self.search_results_label.grid(row=row, column=3, sticky="e")

    def _create_category_ui(self, parent: ttk.Frame, row: int) -> None:
        """Create category selection UI components."""
        # Category label
        ttk.Label(
            parent,
            text="Category:",
            font=("Segoe UI", 10)
        ).grid(row=row, column=0, sticky="w", padx=(0, 10))

        # Category combobox
        self.category_combo = ttk.Combobox(
            parent,
            textvariable=self.category_var,
            state="readonly",
            width=25
        )
        self.category_combo.grid(row=row, column=1, sticky="w", padx=(0, 10))
        self.category_combo.bind("<<ComboboxSelected>>", self._on_category_selected)

        # Remove preview counter from header - will be moved to preview section

    def _create_selection_toolbar(self, parent: ttk.Frame, row: int) -> None:
        """Create clean selection toolbar with cohesive grouping."""
        # Main toolbar frame
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(SPACING['sm'], SPACING['xs']))
        toolbar_frame.columnconfigure(1, weight=1)  # Space between selection group and right side

        # Unified Selection Group (left side) - includes all selection controls
        selection_group = ttk.LabelFrame(toolbar_frame, text="Quick Select", padding=SPACING['xs'])
        selection_group.grid(row=0, column=0, sticky="w", padx=(0, SPACING['md']))

        # Select All button
        self.select_all_btn = ttk.Button(
            selection_group,
            text="All",
            command=self._select_all_tests,
            width=6,
            style="Secondary.TButton"
        )
        self.select_all_btn.grid(row=0, column=0, padx=(0, SPACING['xs']))

        # Select None button
        self.select_none_btn = ttk.Button(
            selection_group,
            text="None",
            command=self._select_none_tests,
            width=6,
            style="Secondary.TButton"
        )
        self.select_none_btn.grid(row=0, column=1, padx=(0, SPACING['xs']))



        # Clear All button - now integrated within the same group
        self.clear_button = ttk.Button(
            selection_group,
            text="Clear All",
            width=8,
            command=self._clear_search,
            style="Tertiary.TButton"
        )
        self.clear_button.grid(row=0, column=2, padx=(SPACING['sm'], 0))

        # Selection counter - moved inside selection group for better cohesion
        self.selection_counter_label = ttk.Label(
            selection_group,
            text="0 selected",
            style="Status.TLabel",
            font=("Segoe UI", 9, "bold")
        )
        self.selection_counter_label.grid(row=0, column=3, padx=(SPACING['md'], 0), sticky="e")

    def _create_preset_controls(self, parent: ttk.Frame, row: int) -> None:
        """Create preset management controls in a separate, cleaner row."""
        # Preset frame
        preset_frame = ttk.Frame(parent)
        preset_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(SPACING['xs'], SPACING['sm']))
        preset_frame.columnconfigure(1, weight=1)  # Space between preset controls and toggle

        # Preset controls group
        preset_group = ttk.LabelFrame(preset_frame, text="Presets", padding=SPACING['xs'])
        preset_group.grid(row=0, column=0, sticky="w")

        # Preset dropdown
        self.preset_combo = ttk.Combobox(
            preset_group,
            textvariable=self.preset_var,
            values=("Select Preset...",),
            state="readonly",
            width=15,
            font=("Segoe UI", 9)
        )
        self.preset_combo.grid(row=0, column=0, padx=(0, SPACING['xs']))
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)
        self.preset_combo.bind("<Button-3>", self._show_preset_context_menu)

        # Save Preset button
        self.save_preset_btn = ttk.Button(
            preset_group,
            text="Save Preset",
            command=self._save_preset_dialog,
            width=12,
            style="Secondary.TButton"
        )
        self.save_preset_btn.grid(row=0, column=1, padx=(0, SPACING['xs']))

        # View Presets link
        view_presets_btn = ttk.Button(
            preset_group,
            text="View...",
            command=self._show_preset_manager_dialog,
            width=8,
            style="Link.TButton"
        )
        view_presets_btn.grid(row=0, column=2)

        # Set default placeholder text
        self.preset_var.set("Select Preset...")

    def _create_batch_action_ui_legacy(self, parent: ttk.Frame, row: int) -> None:
        """Legacy method - replaced by _create_selection_toolbar and _create_preset_controls."""
        # This method is kept for reference but should not be used
        # All functionality has been moved to the new methods above
        pass

    def _on_search_changed(self, *args) -> None:
        """Handle real-time search changes."""
        search_term = self.search_var.get()

        # Debounce search to avoid excessive filtering
        if hasattr(self, '_search_timer'):
            self.after_cancel(self._search_timer)

        # Delay 100ms to avoid lag when typing fast
        self._search_timer = self.after(100, lambda: self._perform_search(search_term))

    def _perform_search(self, search_term: str) -> None:
        """Perform the actual search and update UI."""
        if not hasattr(self, 'original_test_data'):
            return

        # Get data to search in
        if self.current_category == "All":
            search_data = self.all_test_data
        else:
            search_data = self.original_test_data

        # Filter tests
        if search_term.strip():
            filtered_tests = self._filter_tests_by_search(search_term, search_data)
            self._update_search_results_display(len(filtered_tests), len(search_data))
        else:
            # Show original data when search is empty
            filtered_tests = search_data
            self._update_search_results_display(0, 0)

        # Update UI
        if self.current_category == "All":
            self._create_test_list_ui_with_categories(filtered_tests)
        else:
            self._create_test_list_ui(filtered_tests)

        # Update scrollbar visibility after search
        self.after(100, self._update_scrollbar_visibility)

    def _filter_tests_by_search(self, search_term: str, test_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter test cases by search term (case insensitive)."""
        search_lower = search_term.lower().strip()
        return [
            test for test in test_data
            if search_lower in test.get("display_name", "").lower()
        ]

    def _clear_search(self) -> None:
        """Clear search and restore original list."""
        self.search_var.set("")  # Clear search text

        # Reset preset dropdown to default
        self.preset_var.set("Select Preset...")

        # Reset category dropdown to "All"
        total_tests = len(self.all_test_data) if hasattr(self, 'all_test_data') else 0
        self.category_var.set(f"All ({total_tests} tests)")
        self.current_category = "All"

        # Clear all selections
        self._select_none_tests()

        # Restore original list based on current category
        if self.current_category == "All":
            self._display_all_tests()
        else:
            # Show original tests for current category
            original_tests = self.category_tests.get(self.current_category, [])
            self._create_test_list_ui(original_tests)

        # Reset search results counter
        self._update_search_results_display(0, 0)

        # Update scrollbar visibility after clearing search
        self.after(100, self._update_scrollbar_visibility)

        # Update status
        self._update_status("All filters and selections cleared")

    def _update_search_results_display(self, found_count: int, total_count: int) -> None:
        """Update search results counter display."""
        if found_count == 0 and total_count == 0:
            self.search_results_var.set("")
        elif found_count == total_count or found_count == 0:
            self.search_results_var.set(f"Showing all {total_count} tests")
        else:
            self.search_results_var.set(f"Found {found_count} of {total_count} tests")

    def _load_templates(self) -> None:
        """Load templates with 'All' category option."""
        try:
            # Get individual categories
            self.categories = self.test_loader.get_categories()

            # Load all test data from all categories
            self.all_test_data = []
            category_display_names = []
            total_all_tests = 0

            for category in self.categories:
                try:
                    templates = self.test_loader.get_templates_for_category(category)
                    count = len(templates)
                    total_all_tests += count

                    # Load test data for this category
                    category_test_data = self._load_category_test_data(category, templates)

                    # Add to all_test_data with category info
                    for test in category_test_data:
                        test['source_category'] = category  # Track original category
                        self.all_test_data.append(test)

                    # Store category data
                    self.category_tests[category] = category_test_data

                    # Create display name for individual category
                    display_name = f"{category} ({count} tests)" if count != 1 else f"{category} (1 test)"
                    category_display_names.append(display_name)

                except Exception as e:
                    self.logger.warning(f"Could not load category {category}: {e}")
                    category_display_names.append(f"{category} (? tests)")

            # Add "All" option at the beginning
            all_display_name = f"All ({total_all_tests} tests)" if total_all_tests != 1 else "All (1 test)"
            category_display_names.insert(0, all_display_name)

            # Update category dropdown
            self.category_combo["values"] = category_display_names

            # Set default to "All"
            if category_display_names:
                self.category_var.set(category_display_names[0])  # Select "All"
                self.current_category = "All"
                self._display_all_tests()

            # Update the select by category dropdown
            self._update_category_dropdown()

            # Load presets
            self._load_presets_on_startup()

            self._update_status("Templates loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
            messagebox.showerror(
                "Template Error",
                f"Could not load templates: {str(e)}"
            )

    def _load_category_test_data(self, category: str, templates: List[str]) -> List[Dict[str, Any]]:
        """Load test data for a specific category."""
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
                    "template_data": template_content,
                    "category": category  # Original category
                })
            except Exception as e:
                self.logger.warning(f"Could not load template {template_file}: {e}")
                # Add with basic info if loading fails
                test_data.append({
                    "file_name": template_file,
                    "display_name": template_file.replace(".json", "").replace("_", " ").title(),
                    "template_path": "",
                    "template_data": {},
                    "category": category
                })

        return test_data

    def _display_all_tests(self) -> None:
        """Display all test cases from all categories."""
        if not hasattr(self, 'all_test_data'):
            return

        # Store as original data for search
        self.original_test_data = self.all_test_data

        # Apply current search if any
        current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
        if current_search.strip():
            filtered_data = self._filter_tests_by_search(current_search, self.all_test_data)
            self._update_search_results_display(len(filtered_data), len(self.all_test_data))
        else:
            filtered_data = self.all_test_data
            self._update_search_results_display(0, 0)

        # Create UI with all test data showing categories
        # Preserve selection if this is just a UI refresh (e.g., from resize)
        preserve_selection = self._is_ui_refresh or self._is_resizing
        self._create_test_list_ui_with_categories(filtered_data, preserve_selection=preserve_selection)

        # Update scrollbar visibility after displaying tests
        self.after(100, self._update_scrollbar_visibility)

    def _create_test_list_ui_with_categories(self, test_data: List[Dict[str, Any]], preserve_selection: bool = False) -> None:
        """Create test list UI showing category info for 'All' view with checkboxes."""
        if not self.test_list_frame:
            return

        # Store current selection state before clearing widgets
        current_selections = {}
        if preserve_selection:
            for test_id, var in self.checkbox_vars.items():
                current_selections[test_id] = var.get()

        # Clear existing widgets
        for widget in self.test_list_frame.winfo_children():
            widget.destroy()

        # Clear selection state for new data only if not preserving
        if not preserve_selection:
            self._clear_selection_state()
        else:
            # Only clear checkbox vars, keep selected_tests and selection_order
            self.checkbox_vars.clear()

        self.test_list_frame.columnconfigure(0, weight=1)

        for i, test in enumerate(test_data):
            # Generate unique test ID
            test_id = self._get_test_id(test)

            # Check if test has been sent to queue
            is_sent = test_id in self.sent_tests

            # Frame for each test item with improved responsive layout
            test_frame = ttk.Frame(self.test_list_frame, relief="flat", borderwidth=0)
            test_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            test_frame.columnconfigure(1, weight=1)  # Test name column expands
            test_frame.columnconfigure(2, weight=0)  # Button column fixed size

            # Add max width constraint for very wide windows
            if hasattr(self, '_current_layout') and self._current_layout.get('panel_width', 0) > 1600:
                test_frame.configure(width=1200)  # Limit max width on very large screens

            # Checkbox for selection
            checkbox_var = tk.BooleanVar()
            self.checkbox_vars[test_id] = checkbox_var

            # Restore previous selection state if preserving (but not for sent tests)
            if preserve_selection and test_id in current_selections and not is_sent:
                checkbox_var.set(current_selections[test_id])
            elif is_sent:
                # Sent tests should remain unchecked
                checkbox_var.set(False)

            checkbox = ttk.Checkbutton(
                test_frame,
                variable=checkbox_var,
                command=lambda tid=test_id, tdata=test: self._on_checkbox_toggle(tid, tdata)
            )
            checkbox.grid(row=0, column=0, sticky="w", padx=(2, 8))

            # Test name with category info for All view
            display_text = f"{test['display_name']} ({test.get('source_category', 'Unknown')})"

            if is_sent:
                display_text += " [SENT]"

            name_label = ttk.Label(
                test_frame,
                text=display_text,
                font=("Segoe UI", 10),
                foreground="gray" if is_sent else "black"
            )
            name_label.grid(row=0, column=1, sticky="w", padx=(0, 5))

            # Button frame for View button only
            button_frame = ttk.Frame(test_frame)
            button_frame.grid(row=0, column=2, sticky="e", padx=(5, 0))

            # Create button command with proper closure
            def make_view_command(index):
                return lambda: self._view_test_popup(index)

            # View button with adaptive width and proper styling
            view_btn = ttk.Button(
                button_frame,
                text="View",
                width=self._get_adaptive_button_width(),
                command=make_view_command(i),
                style="Tertiary.TButton"
            )
            view_btn.grid(row=0, column=0)

    def _load_category_tests(self, category: str) -> None:
        """
        Load test cases for a specific category.

        Args:
            category: Category name
        """
        try:
            # Use existing data if already loaded
            if category in self.category_tests:
                test_data = self.category_tests[category]
            else:
                # Load fresh data
                templates = self.test_loader.get_templates_for_category(category)
                test_data = self._load_category_test_data(category, templates)
                self.category_tests[category] = test_data

            # Store as original data for search
            self.original_test_data = test_data

            # Apply current search if any
            current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
            if current_search.strip():
                filtered_data = self._filter_tests_by_search(current_search, test_data)
                self._update_search_results_display(len(filtered_data), len(test_data))
            else:
                filtered_data = test_data
                self._update_search_results_display(0, 0)

            # Create UI for test list
            # Preserve selection if this is just a UI refresh (e.g., from resize)
            preserve_selection = self._is_ui_refresh or self._is_resizing
            self._create_test_list_ui(filtered_data, preserve_selection=preserve_selection)

            # Update preview counter
            self._update_preview_counter()

            # Update scrollbar visibility after loading category
            self.after(100, self._update_scrollbar_visibility)

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

    def _create_test_list_ui(self, test_data: List[Dict[str, Any]], preserve_selection: bool = False) -> None:
        """
        Create test list UI with checkboxes for selection.

        Args:
            test_data: List of test data dictionaries
            preserve_selection: Whether to preserve current selection state
        """
        if not self.test_list_frame:
            return

        # Store current selection state before clearing widgets
        current_selections = {}
        if preserve_selection:
            for test_id, var in self.checkbox_vars.items():
                current_selections[test_id] = var.get()

        # Clear existing widgets
        for widget in self.test_list_frame.winfo_children():
            widget.destroy()

        # Clear selection state for new data only if not preserving
        if not preserve_selection:
            self._clear_selection_state()
        else:
            # Only clear checkbox vars, keep selected_tests and selection_order
            self.checkbox_vars.clear()

        # Configure test list frame
        self.test_list_frame.columnconfigure(0, weight=1)

        for i, test in enumerate(test_data):
            # Generate unique test ID
            test_id = self._get_test_id(test)

            # Check if test has been sent to queue
            is_sent = test_id in self.sent_tests

            # Frame for each test item with improved responsive layout
            test_frame = ttk.Frame(self.test_list_frame, relief="flat", borderwidth=0)
            test_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            test_frame.columnconfigure(1, weight=1)  # Test name column expands
            test_frame.columnconfigure(2, weight=0)  # Button column fixed size

            # Add max width constraint for very wide windows
            if hasattr(self, '_current_layout') and self._current_layout.get('panel_width', 0) > 1600:
                test_frame.configure(width=1200)  # Limit max width on very large screens

            # Checkbox for selection
            checkbox_var = tk.BooleanVar()
            self.checkbox_vars[test_id] = checkbox_var

            # Restore previous selection state if preserving (but not for sent tests)
            if preserve_selection and test_id in current_selections and not is_sent:
                checkbox_var.set(current_selections[test_id])
            elif is_sent:
                # Sent tests should remain unchecked
                checkbox_var.set(False)

            checkbox = ttk.Checkbutton(
                test_frame,
                variable=checkbox_var,
                command=lambda tid=test_id, tdata=test: self._on_checkbox_toggle(tid, tdata)
            )
            checkbox.grid(row=0, column=0, sticky="w", padx=(2, 8))

            # Test name label
            display_text = test["display_name"]

            if is_sent:
                display_text += " [SENT]"

            name_label = ttk.Label(
                test_frame,
                text=display_text,
                font=("Segoe UI", 10),
                foreground="gray" if is_sent else "black"
            )
            name_label.grid(row=0, column=1, sticky="w", padx=(0, 5))

            # Button frame for View button only
            button_frame = ttk.Frame(test_frame)
            button_frame.grid(row=0, column=2, sticky="e", padx=(5, 0))

            # Create button command with proper closure
            def make_view_command(index):
                return lambda: self._view_test_popup(index)

            # View button with adaptive width and proper styling
            view_btn = ttk.Button(
                button_frame,
                text="View",
                width=self._get_adaptive_button_width(),
                command=make_view_command(i),
                style="Tertiary.TButton"
            )
            view_btn.grid(row=0, column=0)

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
        """Handle category selection including 'All' option."""
        display_name = self.category_var.get()
        if not display_name:
            return

        if display_name.startswith("All ("):
            # Show all test cases from all categories
            self.current_category = "All"
            self._display_all_tests()
        else:
            # Extract category name from display (e.g., "LAN (5 tests)" -> "LAN")
            category = display_name.split(" (")[0]
            if category != self.current_category:
                self.current_category = category
                self._load_category_tests(category)

    def _add_test_to_preview(self, test_index: int) -> None:
        """Add individual test to preview staging area."""
        # Get the currently displayed tests (could be filtered)
        if self.current_category == "All":
            # For All category, get from currently displayed filtered data
            current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
            if current_search.strip():
                displayed_tests = self._filter_tests_by_search(current_search, self.all_test_data)
            else:
                displayed_tests = self.all_test_data
        else:
            # For specific category, get from currently displayed filtered data
            current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
            if current_search.strip():
                displayed_tests = self._filter_tests_by_search(current_search, self.original_test_data)
            else:
                displayed_tests = self.original_test_data

        if test_index < 0 or test_index >= len(displayed_tests):
            return

        test_data = displayed_tests[test_index].copy()

        # Set category info
        if self.current_category == "All":
            test_data["category"] = test_data.get("source_category", "Unknown")
        else:
            test_data["category"] = self.current_category

        # Check if already in preview
        for existing_test in self.preview_tests:
            if (existing_test["display_name"] == test_data["display_name"] and
                existing_test.get("category") == test_data.get("category")):
                messagebox.showinfo("Already Added", f"'{test_data['display_name']}' is already in preview.")
                return

        # Add to preview
        self.preview_tests.append(test_data)
        self._update_preview_display()
        self._update_preview_counter()

        # Preview section is always visible in two-panel layout

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
        """Update the preview counter display with better formatting."""
        count = len(self.preview_tests)
        if count == 0:
            self.preview_count_var.set("0 tests ready")
        elif count == 1:
            self.preview_count_var.set("1 test ready")
        else:
            self.preview_count_var.set(f"{count} tests ready")

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

        # Preview section remains visible in two-panel layout

    def _is_test_in_queue(self, test_name: str, test_category: str) -> bool:
        """
        Check if a test is already in the execution queue.

        Args:
            test_name: Name of the test to check
            test_category: Category of the test to check

        Returns:
            True if test is already in queue, False otherwise
        """
        if not hasattr(self.parent, 'queue_panel') or not self.parent.queue_panel:
            return False

        # Check if test is already in queue
        for queue_item in self.parent.queue_panel.queue_items:
            if (queue_item.get("name") == test_name and
                queue_item.get("category") == test_category and
                queue_item.get("status") in ["Pending", "Running"]):  # Only check active items
                return True
        return False

    def _send_preview_to_queue(self) -> None:
        """Send all preview tests to queue and switch to Queue tab."""
        if not self.preview_tests:
            messagebox.showinfo("No Tests", "No tests in preview to send to queue.")
            return

        # Check for duplicate tests already in queue or already sent
        duplicates = []
        already_sent = []
        valid_tests = []

        for test in self.preview_tests:
            test_name = test["display_name"]
            test_category = test["category"]
            test_id = self._get_test_id(test)

            if test_id in self.sent_tests:
                already_sent.append(f"• {test_name} ({test_category})")
                self.logger.info(f"DEBUG: Skipping already sent test: {test_name} (ID: {test_id})")
            elif self._is_test_in_queue(test_name, test_category):
                duplicates.append(f"• {test_name} ({test_category})")
            else:
                valid_tests.append(test)

        # Handle duplicates and already sent tests
        issues = []
        if already_sent:
            issues.extend([f"Already sent: {item}" for item in already_sent])
        if duplicates:
            issues.extend([f"In queue: {item}" for item in duplicates])

        if issues:
            issue_list = "\n".join(issues)
            if valid_tests:
                # Some tests are valid, some have issues
                response = messagebox.askyesno(
                    "Some Tests Cannot Be Sent",
                    f"The following tests cannot be sent:\n\n{issue_list}\n\n"
                    f"Do you want to send the remaining {len(valid_tests)} test(s) to the queue?"
                )
                if not response:
                    return
            else:
                # All tests have issues
                messagebox.showwarning(
                    "No Tests Can Be Sent",
                    f"All selected tests cannot be sent:\n\n{issue_list}\n\n"
                    "Please select different tests or clear the queue/sent tests."
                )
                return

        # Add valid tests to queue
        if hasattr(self.parent, 'queue_panel') and valid_tests:
            for test in valid_tests:
                # Extract the actual test data from template_data
                actual_test_data = test.get("template_data", {})

                self.parent.queue_panel.add_to_queue(
                    test_data=actual_test_data,
                    category=test["category"],
                    name=test["display_name"]
                )

        count = len(valid_tests)

        # Only proceed if we actually sent some tests
        if count > 0:
            # Clear preview
            self.preview_tests.clear()
            self._update_preview_display()
            self._update_preview_counter()

            # Clear selections for tests that were sent to queue
            self._clear_sent_test_selections(valid_tests)

            # Refresh UI to show [SENT] indicators
            self._refresh_ui_after_send()

            # Preview section remains visible in two-panel layout

            # Switch to Queue tab
            if hasattr(self.parent, 'notebook') and hasattr(self.parent, 'queue_tab'):
                self.parent.notebook.select(self.parent.queue_tab)

            self._update_status(f"Sent {count} test(s) to queue")

            # Show success message with duplicate info if applicable
            if duplicates:
                messagebox.showinfo(
                    "Tests Sent",
                    f"Successfully sent {count} test case(s) to the queue!\n\n"
                    f"Note: {len(duplicates)} test(s) were skipped because they are already queued."
                )
            else:
                messagebox.showinfo(
                    "Tests Sent",
                    f"Successfully sent {count} test case(s) to the queue!"
                )
        else:
            # No tests were sent (all were duplicates)
            self._update_status("No tests sent - all were already in queue")

    def _bind_mouse_wheel_events(self) -> None:
        """Bind mouse wheel events with intelligent scrolling."""
        def _on_mousewheel(event):
            # Only scroll if content actually needs scrolling and scrollbar is visible
            if hasattr(self, 'test_canvas') and self.test_canvas:
                if hasattr(self, 'scrollbar') and self.scrollbar:
                    # Check if scrollbar is currently visible (gridded)
                    scrollbar_info = self.scrollbar.grid_info()
                    if scrollbar_info and self._is_scrolling_needed():
                        self.test_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                        return "break"  # Consume the event
                # If no scrolling needed, let parent handle the event
                return None

        # Bind mouse wheel to canvas and test list frame
        if hasattr(self, 'test_canvas') and self.test_canvas:
            self.test_canvas.bind("<MouseWheel>", _on_mousewheel)

        if hasattr(self, 'test_list_frame') and self.test_list_frame:
            self.test_list_frame.bind("<MouseWheel>", _on_mousewheel)

            # Also bind to all child widgets recursively, but more efficiently
            def bind_to_children(widget):
                if widget:
                    widget.bind("<MouseWheel>", _on_mousewheel)
                    # Only bind to immediate children to avoid deep recursion
                    for child in widget.winfo_children():
                        if isinstance(child, (ttk.Frame, tk.Frame)):
                            bind_to_children(child)

            # Bind after a short delay to ensure all widgets are created
            self.after(100, lambda: bind_to_children(self.test_list_frame))

    def _is_scrolling_needed(self) -> bool:
        """Check if the canvas actually needs scrolling with improved accuracy."""
        try:
            if not hasattr(self, 'test_canvas') or not self.test_canvas:
                return False

            # Get canvas dimensions
            canvas_height = self.test_canvas.winfo_height()
            if canvas_height <= 1:
                return False

            # Get the scroll region using bbox
            bbox = self.test_canvas.bbox("all")
            if not bbox:
                return False

            # Calculate content height from bbox
            content_height = bbox[3] - bbox[1]  # y2 - y1

            # Add some tolerance to prevent flickering
            tolerance = 5
            scrolling_needed = content_height > (canvas_height - tolerance)

            return scrolling_needed

        except Exception as e:
            self.logger.debug(f"Error checking scroll necessity: {e}")
            return False

    def _on_test_list_configure(self, event) -> None:
        """Handle test list frame configuration changes with optimization."""
        try:
            if hasattr(self, 'test_canvas') and self.test_canvas:
                # Update scroll region only when necessary
                bbox = self.test_canvas.bbox("all")
                if bbox:
                    current_scrollregion = self.test_canvas.cget("scrollregion")
                    new_scrollregion = bbox

                    # Only update if scroll region actually changed
                    if current_scrollregion != new_scrollregion:
                        self.test_canvas.configure(scrollregion=bbox)

                    # Update scrollbar visibility based on content
                    self._update_scrollbar_visibility()
        except Exception as e:
            self.logger.debug(f"Error in test list configure: {e}")

    def _update_scrollbar_visibility(self) -> None:
        """Update scrollbar visibility based on content size."""
        try:
            if not hasattr(self, 'test_canvas') or not self.test_canvas:
                return

            if not hasattr(self, 'scrollbar') or not self.scrollbar:
                return

            # Get canvas dimensions
            canvas_height = self.test_canvas.winfo_height()
            if canvas_height <= 1:
                # Canvas not yet rendered, schedule for later
                self.after(50, self._update_scrollbar_visibility)
                return

            # Check if scrolling is needed
            scroll_needed = self._is_scrolling_needed()

            if scroll_needed:
                # Show scrollbar if content exceeds canvas height
                self.scrollbar.grid(row=0, column=1, sticky="ns")
                # Adjust canvas column weight to accommodate scrollbar
                self.content_container.columnconfigure(0, weight=1)
                self.content_container.columnconfigure(1, weight=0)
            else:
                # Hide scrollbar if content fits within canvas
                self.scrollbar.grid_remove()
                # Canvas takes full width
                self.content_container.columnconfigure(0, weight=1)
                self.content_container.columnconfigure(1, weight=0)

        except Exception as e:
            self.logger.debug(f"Error updating scrollbar visibility: {e}")

    def _get_test_id(self, test_data: Dict[str, Any]) -> str:
        """Generate unique ID for a test case."""
        display_name = test_data.get('display_name', '')
        category = test_data.get('category', test_data.get('source_category', ''))
        test_id = f"{display_name}|{category}"

        # Debug logging for test ID generation
        if not display_name or not category:
            self.logger.warning(f"DEBUG: Incomplete test data for ID generation: display_name='{display_name}', category='{category}', data={test_data}")

        return test_id



    def _clear_selection_state(self) -> None:
        """Clear all selection state when switching categories or refreshing."""
        self.selected_tests.clear()
        self.checkbox_vars.clear()
        self.selection_order.clear()  # Clear selection order tracking

    def _reset_sent_tests(self) -> None:
        """Reset sent tests tracking (useful when changing categories)."""
        self.sent_tests.clear()
        self.logger.debug("Reset sent tests tracking")

    def _refresh_ui_after_send(self) -> None:
        """Refresh UI to show [SENT] indicators after sending tests to queue."""
        try:
            # Set flag to preserve selections during refresh
            self._is_ui_refresh = True

            # Refresh the current view to update visual indicators
            if self.current_category == "All":
                self._display_all_tests()
            else:
                self._load_category_tests(self.current_category)

            self.logger.debug("Refreshed UI after sending tests to queue")

        except Exception as e:
            self.logger.error(f"Error refreshing UI after send: {e}")
        finally:
            self._is_ui_refresh = False

    def _clear_sent_test_selections(self, sent_tests: List[Dict[str, Any]]) -> None:
        """Clear selections for tests that were successfully sent to queue.

        Args:
            sent_tests: List of test dictionaries that were sent to queue
        """
        try:
            # Create set of test IDs that were sent
            sent_test_ids = set()
            for test in sent_tests:
                test_id = self._get_test_id(test)
                sent_test_ids.add(test_id)

            # Add sent tests to sent_tests tracking
            self.sent_tests.update(sent_test_ids)

            # Remove sent tests from selection tracking
            self.selected_tests -= sent_test_ids

            # Remove sent tests from selection order
            self.selection_order = [test_id for test_id in self.selection_order
                                  if test_id not in sent_test_ids]

            # Uncheck checkboxes for sent tests
            for test_id in sent_test_ids:
                if test_id in self.checkbox_vars:
                    self.checkbox_vars[test_id].set(False)

            # Update UI feedback
            self._update_selection_feedback()

            self.logger.info(f"DEBUG: Cleared selections for {len(sent_test_ids)} sent tests. Total sent: {len(self.sent_tests)}")
            self.logger.info(f"DEBUG: Sent tests tracking: {list(self.sent_tests)}")
            self.logger.info(f"DEBUG: Remaining selected tests: {list(self.selected_tests)}")

        except Exception as e:
            self.logger.error(f"Error clearing sent test selections: {e}")
            # Fallback: clear all selections if there's an error
            self._select_none_tests()

    def _on_checkbox_toggle(self, test_id: str, test_data: Dict[str, Any]) -> None:
        """Handle checkbox toggle events."""
        checkbox_var = self.checkbox_vars.get(test_id)
        if not checkbox_var:
            # Log warning if checkbox variable is missing
            print(f"Warning: Checkbox variable not found for test_id: {test_id}")
            return

        is_checked = checkbox_var.get()
        if is_checked:
            # Checkbox checked - add to selection and track order
            self.selected_tests.add(test_id)
            # Add to selection order if not already present
            if test_id not in self.selection_order:
                self.selection_order.append(test_id)
        else:
            # Checkbox unchecked - remove from selection and order tracking
            self.selected_tests.discard(test_id)
            # Remove from selection order
            if test_id in self.selection_order:
                self.selection_order.remove(test_id)

        # Update UI feedback - now shows feedback for both checking and unchecking
        self._update_selection_feedback()

    def _update_selection_feedback(self) -> None:
        """Update UI to show current selection count and automatically update preview."""
        selection_count = len(self.selected_tests)

        # Update selection counter label with dynamic styling
        if hasattr(self, 'selection_counter_label'):
            if selection_count == 0:
                self.selection_counter_label.config(
                    text="0 selected",
                    foreground=COLORS['text_secondary']
                )
            elif selection_count == 1:
                self.selection_counter_label.config(
                    text="1 selected",
                    foreground=COLORS['primary']
                )
            else:
                self.selection_counter_label.config(
                    text=f"{selection_count} selected",
                    foreground=COLORS['primary']
                )

        # Automatically update preview when selection changes (simplified workflow)
        self._auto_update_preview()

        # Update status bar - show feedback for both selecting and deselecting
        self._update_status(f"Selected {selection_count} test(s)")

    def _auto_update_preview(self) -> None:
        """Automatically update preview when selection changes (simplified workflow)."""
        if not self.selected_tests:
            # Clear preview if no selection
            self.preview_tests.clear()
            self._update_preview_display()
            self._update_preview_counter()
            return

        # Get current displayed test data
        if self.current_category == "All":
            current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
            if current_search.strip():
                displayed_tests = self._filter_tests_by_search(current_search, self.all_test_data)
            else:
                displayed_tests = self.all_test_data
        else:
            current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
            if current_search.strip():
                displayed_tests = self._filter_tests_by_search(current_search, self.original_test_data)
            else:
                displayed_tests = self.original_test_data

        # Create a lookup map for quick test data access
        test_lookup = {}
        for test in displayed_tests:
            test_id = self._get_test_id(test)
            test_lookup[test_id] = test

        # Update preview with selected tests in selection order (user's intended execution sequence)
        new_preview_tests = []
        for test_id in self.selection_order:
            if test_id in self.selected_tests and test_id in test_lookup:
                test = test_lookup[test_id]

                # Prepare test data
                test_data = test.copy()
                if self.current_category == "All":
                    test_data["category"] = test_data.get("source_category", "Unknown")
                else:
                    test_data["category"] = self.current_category

                # Check if already in preview to avoid duplicates
                already_exists = False
                for existing_test in new_preview_tests:
                    if (existing_test["display_name"] == test_data["display_name"] and
                        existing_test.get("category") == test_data.get("category")):
                        already_exists = True
                        break

                if not already_exists:
                    new_preview_tests.append(test_data)

        # Update preview
        self.preview_tests = new_preview_tests
        self._update_preview_display()
        self._update_preview_counter()

    def _add_selected_to_preview_legacy(self) -> None:
        """Legacy method - functionality moved to _auto_update_preview."""
        # This method is no longer used as preview updates automatically
        # when selection changes via _auto_update_preview()
        pass

    def _show_success_feedback_legacy(self, added_count: int, skipped_count: int) -> None:
        """Legacy method - no longer needed with auto-update preview."""
        pass

    def _restore_add_button_legacy(self, original_text: str) -> None:
        """Legacy method - no longer needed without Add Selected button."""
        pass

    def _clear_added_selections_legacy(self, added_test_ids: list) -> None:
        """Legacy method - no longer needed with auto-update preview."""
        pass

    def _select_all_tests(self) -> None:
        """Select all currently displayed tests."""
        try:
            # Get currently displayed tests
            if self.current_category == "All":
                current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
                if current_search.strip():
                    displayed_tests = self._filter_tests_by_search(current_search, self.all_test_data)
                else:
                    displayed_tests = self.all_test_data
            else:
                current_search = self.search_var.get() if hasattr(self, 'search_var') else ""
                if current_search.strip():
                    displayed_tests = self._filter_tests_by_search(current_search, self.original_test_data)
                else:
                    displayed_tests = self.original_test_data

            # Select all displayed tests and maintain selection order
            self.logger.info(f"DEBUG: ALL button - selecting {len(displayed_tests)} displayed tests")
            self.logger.info(f"DEBUG: Current sent_tests: {list(self.sent_tests)}")

            for test in displayed_tests:
                test_id = self._get_test_id(test)
                self.selected_tests.add(test_id)

                is_sent = test_id in self.sent_tests
                self.logger.info(f"DEBUG: Selecting test {test_id}, is_sent: {is_sent}")

                # Add to selection order if not already present
                if test_id not in self.selection_order:
                    self.selection_order.append(test_id)

                # Update checkbox if it exists
                if test_id in self.checkbox_vars:
                    self.checkbox_vars[test_id].set(True)

            self.logger.info(f"DEBUG: After ALL - selected_tests: {list(self.selected_tests)}")
            self.logger.info(f"DEBUG: After ALL - selection count: {len(self.selected_tests)}")

            # Update UI feedback
            self._update_selection_feedback()
            self._update_status(f"Selected all {len(displayed_tests)} displayed tests")

        except Exception as e:
            self.logger.error(f"Error selecting all tests: {e}")

    def _select_none_tests(self) -> None:
        """Deselect all tests."""
        try:
            # Clear all selections and selection order
            self.selected_tests.clear()
            self.selection_order.clear()

            # Update all checkboxes
            for checkbox_var in self.checkbox_vars.values():
                checkbox_var.set(False)

            # Update UI feedback
            self._update_selection_feedback()
            self._update_status("Cleared all selections")

        except Exception as e:
            self.logger.error(f"Error clearing selections: {e}")



    def _on_select_by_category(self, event) -> None:
        """Handle selection by category from dropdown."""
        try:
            selected_category = self.select_category_var.get()
            if not selected_category or selected_category == "Select Category...":
                return

            self.logger.debug(f"Selected category from dropdown: {selected_category}")

            # Clear current selections first
            self._select_none_tests()

            # Get all tests from the selected category
            if selected_category == "All Categories":
                # Select all tests from all categories
                self._select_all_tests()
                return

            # Select tests from specific category
            selected_count = 0

            if self.current_category == "All":
                # When viewing "All", filter by source category
                for test in self.all_test_data:
                    test_category = test.get('source_category', test.get('category', ''))
                    if test_category == selected_category:
                        test_id = self._get_test_id(test)
                        self.selected_tests.add(test_id)

                        # Add to selection order if not already present
                        if test_id not in self.selection_order:
                            self.selection_order.append(test_id)

                        # Update checkbox if it exists
                        if test_id in self.checkbox_vars:
                            self.checkbox_vars[test_id].set(True)
                        selected_count += 1
            else:
                # When viewing specific category, select all if it matches
                if self.current_category == selected_category:
                    for test in self.original_test_data:
                        test_id = self._get_test_id(test)
                        self.selected_tests.add(test_id)

                        # Add to selection order if not already present
                        if test_id not in self.selection_order:
                            self.selection_order.append(test_id)

                        # Update checkbox if it exists
                        if test_id in self.checkbox_vars:
                            self.checkbox_vars[test_id].set(True)
                        selected_count += 1

            # Update UI feedback
            self._update_selection_feedback()
            self._update_status(f"Selected {selected_count} tests from {selected_category} category")

            # Reset dropdown to placeholder
            self.select_category_var.set("Select Category...")

        except Exception as e:
            self.logger.error(f"Error selecting by category: {e}")

    def _update_category_dropdown(self) -> None:
        """Update the select by category dropdown with available categories."""
        try:
            if hasattr(self, 'select_category_combo') and hasattr(self, 'categories'):
                # Debug logging
                self.logger.debug(f"Updating category dropdown with categories: {self.categories}")

                # Get unique categories - ensure they are strings
                categories = ["Select Category...", "All Categories"]
                if self.categories:
                    # Convert to list and ensure all items are strings
                    category_list = [str(cat) for cat in self.categories if cat]
                    categories.extend(category_list)

                self.logger.debug(f"Final dropdown values: {categories}")

                # Update dropdown values
                self.select_category_combo['values'] = tuple(categories)  # Use tuple for better compatibility

                # Keep current selection if valid, otherwise set to placeholder
                current_selection = self.select_category_var.get()
                if current_selection not in categories:
                    self.select_category_var.set("Select Category...")

        except Exception as e:
            self.logger.error(f"Error updating category dropdown: {e}")
            # Fallback to basic categories if available
            try:
                if hasattr(self, 'select_category_combo'):
                    self.select_category_combo['values'] = ("Select Category...", "All Categories")
                    self.select_category_var.set("Select Category...")
            except:
                pass

    # ==========================================
    # Preset Management Methods
    # ==========================================

    def _on_preset_selected(self, event) -> None:
        """Handle preset selection from dropdown."""
        try:
            preset_name = self.preset_var.get()
            if not preset_name or preset_name == "Select Preset...":
                return

            preset = self.preset_manager.get_preset_by_name(preset_name)
            if not preset:
                messagebox.showerror("Error", f"Preset not found: {preset_name}")
                return

            self._apply_preset(preset)

        except Exception as e:
            self.logger.error(f"Error applying preset: {e}")
            messagebox.showerror("Error", f"Failed to apply preset: {str(e)}")

    def _apply_preset(self, preset: Dict[str, Any]) -> None:
        """Apply a preset to current selection."""
        try:
            # Get current available test IDs
            available_test_ids = []
            if self.current_category == "All":
                for test in self.all_test_data:
                    available_test_ids.append(self._get_test_id(test))
            else:
                for test in self.original_test_data:
                    available_test_ids.append(self._get_test_id(test))

            # Validate preset tests
            valid_tests, missing_tests = self.preset_manager.validate_preset_tests(
                preset['test_ids'], available_test_ids
            )

            if not valid_tests:
                messagebox.showwarning("No Valid Tests",
                    "None of the tests in this preset are currently available.")
                return

            # Clear current selection
            self._select_none_tests()

            # Apply preset selection and maintain selection order
            applied_count = 0
            for test_id in valid_tests:
                if test_id in self.checkbox_vars:
                    self.checkbox_vars[test_id].set(True)
                    self.selected_tests.add(test_id)

                    # Add to selection order if not already present
                    if test_id not in self.selection_order:
                        self.selection_order.append(test_id)
                    applied_count += 1

            # Update UI
            self._update_selection_feedback()

            # Show feedback
            if missing_tests:
                messagebox.showwarning("Partial Application",
                    f"Applied {applied_count} tests from preset '{preset['name']}'.\n"
                    f"{len(missing_tests)} tests are no longer available.")
            else:
                # Brief success feedback
                if hasattr(self, 'selection_counter_label'):
                    original_color = self.selection_counter_label.cget('foreground')
                    self.selection_counter_label.config(foreground="#28a745")
                    self.after(1000, lambda: self.selection_counter_label.config(foreground=original_color))

            self.logger.info(f"Applied preset '{preset['name']}': {applied_count} tests selected")

        except Exception as e:
            self.logger.error(f"Error applying preset: {e}")
            messagebox.showerror("Error", f"Failed to apply preset: {str(e)}")

    def _save_preset_dialog(self) -> None:
        """Open dialog to save current selection as preset."""
        try:
            if not self.selected_tests:
                messagebox.showinfo("No Selection", "Please select test cases first.")
                return

            # Simple input dialog for preset name
            preset_name = simpledialog.askstring(
                "Save Preset",
                "Enter preset name:",
                parent=self
            )

            if not preset_name:
                return

            preset_name = preset_name.strip()
            if not preset_name:
                messagebox.showerror("Invalid Name", "Preset name cannot be empty.")
                return

            # Check if name already exists
            if self.preset_manager.get_preset_by_name(preset_name):
                if not messagebox.askyesno("Preset Exists",
                    f"Preset '{preset_name}' already exists. Overwrite?"):
                    return
                # Delete existing preset
                existing_preset = self.preset_manager.get_preset_by_name(preset_name)
                if existing_preset:
                    self.preset_manager.delete_preset(existing_preset['id'])

            # Get description
            description = simpledialog.askstring(
                "Preset Description",
                "Enter preset description (optional):",
                parent=self
            ) or ""

            # Create preset
            preset_id = self.preset_manager.create_preset(
                name=preset_name,
                description=description,
                test_ids=list(self.selected_tests)
            )

            # Refresh preset dropdown
            self._refresh_preset_dropdown()

            # Show success message
            messagebox.showinfo("Success", f"Preset '{preset_name}' saved successfully!")
            self.logger.info(f"Created preset '{preset_name}' with {len(self.selected_tests)} tests")

        except Exception as e:
            self.logger.error(f"Error saving preset: {e}")
            messagebox.showerror("Error", f"Failed to save preset: {str(e)}")

    def _refresh_preset_dropdown(self) -> None:
        """Refresh the preset dropdown with current presets."""
        try:
            preset_names = self.preset_manager.get_preset_names()
            values = ["Select Preset..."] + preset_names

            if self.preset_combo:
                self.preset_combo['values'] = values
                # Reset to default if current selection is not in list
                current = self.preset_var.get()
                if current not in values:
                    self.preset_var.set("Select Preset...")

        except Exception as e:
            self.logger.error(f"Error refreshing preset dropdown: {e}")

    def _load_presets_on_startup(self) -> None:
        """Load presets when panel is initialized."""
        try:
            self._refresh_preset_dropdown()
        except Exception as e:
            self.logger.error(f"Error loading presets on startup: {e}")

    def _show_preset_context_menu(self, event) -> None:
        """Show context menu for preset management."""
        try:
            # Create context menu
            context_menu = tk.Menu(self.parent, tearoff=0)

            # Add menu items
            context_menu.add_command(
                label="Manage Presets...",
                command=self._show_preset_manager_dialog
            )

            # Show context menu at cursor position
            context_menu.tk_popup(event.x_root, event.y_root)

        except Exception as e:
            self.logger.error(f"Error showing preset context menu: {e}")

    def _show_preset_manager_dialog(self) -> None:
        """Show the preset manager dialog."""
        try:
            dialog = PresetManagerDialog(
                parent=self,
                preset_manager=self.preset_manager,
                refresh_callback=self._refresh_preset_dropdown
            )

            dialog.show()

            # If a preset was selected for application, apply it
            if dialog.result:
                self._apply_preset(dialog.result)

        except Exception as e:
            self.logger.error(f"Error showing preset manager: {e}")
            messagebox.showerror("Error", f"Failed to open preset manager: {str(e)}")


