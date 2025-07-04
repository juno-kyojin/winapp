#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logs Panel for Test Case Manager v3.0

This module implements the Logs tab that displays real-time application logs
with proper formatting, filtering, and search capabilities.

Author: juno-kyojin
Created: 2025-07-04
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import re
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path

from src.utils.logger import LoggerMixin, get_gui_log_handler


class LogsPanel(ttk.Frame, LoggerMixin):
    """
    Logs panel for displaying real-time application logs.

    This panel provides a comprehensive logging interface with features like:
    - Real-time log display
    - Log level filtering
    - Search functionality
    - Auto-scrolling
    - Log export capabilities
    """

    def __init__(self, parent: tk.Widget, update_status: Callable[[str], None]):
        """
        Initialize the Logs panel.

        Args:
            parent: Parent widget
            update_status: Function to update application status
        """
        super().__init__(parent)
        self.update_status = update_status

        # Log storage
        self.log_messages: List[Dict[str, Any]] = []
        self.max_log_entries = 1000  # Limit to prevent memory issues

        # UI components
        self.log_text: Optional[scrolledtext.ScrolledText] = None
        self.filter_var: Optional[tk.StringVar] = None
        self.search_var: Optional[tk.StringVar] = None
        self.auto_scroll_var: Optional[tk.BooleanVar] = None

        # Threading
        self.log_queue = queue.Queue()
        self.update_thread_running = True

        # Setup UI
        self._setup_ui()
        self._setup_log_handler()
        self._start_update_thread()

        self.logger.info("Logs Panel initialized")

    def _setup_ui(self) -> None:
        """Setup the user interface components."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 5))

        # Log level filter
        ttk.Label(control_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_var = tk.StringVar(value="ALL")
        filter_combo = ttk.Combobox(
            control_frame,
            textvariable=self.filter_var,
            values=["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            state="readonly",
            width=10
        )
        filter_combo.pack(side=tk.LEFT, padx=(0, 10))
        filter_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Search
        ttk.Label(control_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(control_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        search_entry.bind("<KeyRelease>", self._on_search_changed)

        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(
            control_frame,
            text="Auto-scroll",
            variable=self.auto_scroll_var
        )
        auto_scroll_check.pack(side=tk.LEFT, padx=(0, 10))

        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT)

        ttk.Button(button_frame, text="Clear", command=self._clear_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Export", command=self._export_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Refresh", command=self._refresh_display).pack(side=tk.LEFT)

        # Log display area
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Create text widget with scrollbar
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED,
            bg="#f8f9fa",
            fg="#212529"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for different log levels
        self._configure_text_tags()

        # Status info
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))

        self.status_label = ttk.Label(status_frame, text="Ready - 0 log entries")
        self.status_label.pack(side=tk.LEFT)

    def _configure_text_tags(self) -> None:
        """Configure text tags for different log levels."""
        if not self.log_text:
            return

        # Configure tags for different log levels
        self.log_text.tag_configure("DEBUG", foreground="#6c757d")
        self.log_text.tag_configure("INFO", foreground="#28a745")
        self.log_text.tag_configure("WARNING", foreground="#ffc107")
        self.log_text.tag_configure("ERROR", foreground="#dc3545")
        self.log_text.tag_configure("CRITICAL", foreground="#6f42c1", font=("Consolas", 9, "bold"))
        self.log_text.tag_configure("TIMESTAMP", foreground="#495057", font=("Consolas", 8))
        self.log_text.tag_configure("LOGGER", foreground="#17a2b8", font=("Consolas", 8))

    def _setup_log_handler(self) -> None:
        """Setup the GUI log handler to receive log messages."""
        gui_handler = get_gui_log_handler()
        gui_handler.set_callback(self._add_log_message)

    def _start_update_thread(self) -> None:
        """Start the background thread for updating the GUI."""
        def update_worker():
            while self.update_thread_running:
                try:
                    # Process queued log messages
                    while not self.log_queue.empty():
                        try:
                            message = self.log_queue.get_nowait()
                            self._process_log_message(message)
                        except queue.Empty:
                            break

                    # Small delay to prevent excessive CPU usage
                    threading.Event().wait(0.1)

                except Exception as e:
                    # Log errors but continue running
                    print(f"Error in logs panel update thread: {e}")

        self.update_thread = threading.Thread(target=update_worker, daemon=True)
        self.update_thread.start()

    def _add_log_message(self, message: str) -> None:
        """
        Add a log message to the queue for processing.

        Args:
            message: Formatted log message
        """
        try:
            self.log_queue.put(message)
        except Exception:
            # Silently ignore queue errors
            pass

    def _process_log_message(self, message: str) -> None:
        """
        Process and display a log message.

        Args:
            message: Formatted log message
        """
        try:
            # Parse the log message
            log_entry = self._parse_log_message(message)

            # Add to storage
            self.log_messages.append(log_entry)

            # Limit storage size
            if len(self.log_messages) > self.max_log_entries:
                self.log_messages = self.log_messages[-self.max_log_entries:]

            # Update display if message matches current filter
            if self._message_matches_filter(log_entry):
                self._display_log_entry(log_entry)

            # Update status
            self._update_status_info()

        except Exception as e:
            # Log parsing errors but continue
            print(f"Error processing log message: {e}")

    def _parse_log_message(self, message: str) -> Dict[str, Any]:
        """
        Parse a log message into components.

        Args:
            message: Raw log message

        Returns:
            Dictionary with parsed log components
        """
        # Default values
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": "INFO",
            "logger": "unknown",
            "message": message.strip(),
            "raw": message
        }

        # Try to parse standard format: [timestamp] LEVEL - logger: message
        pattern = r'\[([^\]]+)\]\s+(\w+)\s+-\s+([^:]+):\s*(.*)'
        match = re.match(pattern, message)

        if match:
            timestamp_str, level, logger, msg = match.groups()

            # Extract just the time part from timestamp
            try:
                # Handle different timestamp formats
                if ' ' in timestamp_str:
                    time_part = timestamp_str.split(' ')[1]
                else:
                    time_part = timestamp_str
                log_entry["timestamp"] = time_part
            except:
                log_entry["timestamp"] = timestamp_str

            log_entry["level"] = level.upper()
            log_entry["logger"] = logger.strip()
            log_entry["message"] = msg.strip()

        return log_entry

    def _message_matches_filter(self, log_entry: Dict[str, Any]) -> bool:
        """
        Check if a log entry matches current filters.

        Args:
            log_entry: Log entry to check

        Returns:
            True if message matches filters
        """
        # Level filter
        if self.filter_var and self.filter_var.get() != "ALL":
            if log_entry["level"] != self.filter_var.get():
                return False

        # Search filter
        if self.search_var and self.search_var.get().strip():
            search_term = self.search_var.get().strip().lower()
            searchable_text = f"{log_entry['logger']} {log_entry['message']}".lower()
            if search_term not in searchable_text:
                return False

        return True

    def _display_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """
        Display a log entry in the text widget.

        Args:
            log_entry: Log entry to display
        """
        if not self.log_text:
            return

        try:
            # Enable text widget for editing
            self.log_text.config(state=tk.NORMAL)

            # Format and insert the log entry
            timestamp = log_entry["timestamp"]
            level = log_entry["level"]
            logger = log_entry["logger"]
            message = log_entry["message"]

            # Insert timestamp
            self.log_text.insert(tk.END, f"[{timestamp}] ", "TIMESTAMP")

            # Insert level with appropriate tag
            self.log_text.insert(tk.END, f"{level} ", level)

            # Insert logger name
            self.log_text.insert(tk.END, f"- {logger}: ", "LOGGER")

            # Insert message
            self.log_text.insert(tk.END, f"{message}\n")

            # Auto-scroll if enabled
            if self.auto_scroll_var and self.auto_scroll_var.get():
                self.log_text.see(tk.END)

            # Disable text widget
            self.log_text.config(state=tk.DISABLED)

        except Exception as e:
            print(f"Error displaying log entry: {e}")

    def _on_filter_changed(self, event=None) -> None:
        """Handle filter change event."""
        self._refresh_display()

    def _on_search_changed(self, event=None) -> None:
        """Handle search change event."""
        self._refresh_display()

    def _refresh_display(self) -> None:
        """Refresh the log display based on current filters."""
        if not self.log_text:
            return

        try:
            # Clear current display
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)

            # Re-display filtered messages
            for log_entry in self.log_messages:
                if self._message_matches_filter(log_entry):
                    self._display_log_entry(log_entry)

            # Auto-scroll to end
            if self.auto_scroll_var and self.auto_scroll_var.get():
                self.log_text.see(tk.END)

            self.log_text.config(state=tk.DISABLED)

            self._update_status_info()

        except Exception as e:
            self.logger.error(f"Error refreshing log display: {e}")

    def _clear_logs(self) -> None:
        """Clear all log messages."""
        if messagebox.askyesno("Clear Logs", "Are you sure you want to clear all log messages?"):
            self.log_messages.clear()
            if self.log_text:
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete(1.0, tk.END)
                self.log_text.config(state=tk.DISABLED)
            self._update_status_info()
            self.update_status("Log messages cleared")

    def _export_logs(self) -> None:
        """Export log messages to a file."""
        try:
            from tkinter import filedialog

            # Get save location
            filename = filedialog.asksaveasfilename(
                title="Export Logs",
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("Log files", "*.log"),
                    ("All files", "*.*")
                ]
            )

            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Test Case Manager v3.0 - Log Export\n")
                    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total entries: {len(self.log_messages)}\n")
                    f.write("-" * 80 + "\n\n")

                    for log_entry in self.log_messages:
                        if self._message_matches_filter(log_entry):
                            f.write(log_entry["raw"] + "\n")

                self.update_status(f"Logs exported to {filename}")

        except Exception as e:
            self.logger.error(f"Error exporting logs: {e}")
            messagebox.showerror("Export Error", f"Failed to export logs: {e}")

    def _update_status_info(self) -> None:
        """Update the status information."""
        try:
            total_entries = len(self.log_messages)

            # Count filtered entries
            filtered_entries = sum(1 for entry in self.log_messages if self._message_matches_filter(entry))

            if self.filter_var and self.filter_var.get() != "ALL" or (self.search_var and self.search_var.get().strip()):
                status_text = f"Showing {filtered_entries} of {total_entries} log entries"
            else:
                status_text = f"Total: {total_entries} log entries"

            if hasattr(self, 'status_label'):
                self.status_label.config(text=status_text)

        except Exception as e:
            print(f"Error updating status info: {e}")

    def destroy(self) -> None:
        """Clean up resources when panel is destroyed."""
        self.update_thread_running = False
        super().destroy()
