#!/usr/bin/env python3
"""
Image utilities for Test Case Manager v1.0

This module provides utilities for loading and handling images/icons
in the application, including logo and icon management.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import tkinter as tk
from PIL import Image, ImageTk
import logging

logger = logging.getLogger(__name__)

def get_assets_dir() -> Path:
    """
    Get the assets directory path.

    Returns:
        Path to assets directory
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - assets are embedded
        # PyInstaller extracts to sys._MEIPASS
        if hasattr(sys, '_MEIPASS'):
            return Path(getattr(sys, '_MEIPASS')) / "assets"
        else:
            # Fallback to executable directory
            return Path(sys.executable).parent / "assets"
    else:
        # Running as script
        base_dir = Path(__file__).parent.parent.parent
        return base_dir / "assets"

def get_logo_path(filename: str) -> Optional[Path]:
    """
    Get path to logo file if it exists.
    
    Args:
        filename: Logo filename (e.g., 'logo.png', 'logo.ico')
        
    Returns:
        Path to logo file if exists, None otherwise
    """
    assets_dir = get_assets_dir()
    logo_path = assets_dir / filename
    
    if logo_path.exists():
        return logo_path
    
    logger.debug(f"Logo file not found: {logo_path}")
    return None

def load_window_icon() -> Optional[str]:
    """
    Load window icon for tkinter window.
    
    Returns:
        Path to icon file if available, None otherwise
    """
    # Try to find .ico file first, then .png
    for ext in ['.ico', '.png']:
        icon_path = get_logo_path(f'logo{ext}')
        if icon_path:
            return str(icon_path)
    
    return None

def load_logo_image(size: Tuple[int, int] = (64, 64)) -> Optional[ImageTk.PhotoImage]:
    """
    Load logo image for display in GUI.
    
    Args:
        size: Desired size as (width, height) tuple
        
    Returns:
        PhotoImage object if logo found, None otherwise
    """
    try:
        # Try PNG first, then ICO
        for ext in ['.png', '.ico']:
            logo_path = get_logo_path(f'logo{ext}')
            if logo_path:
                # Use PIL to load and resize image
                with Image.open(logo_path) as img:
                    # Convert to RGBA for transparency support
                    img = img.convert('RGBA')
                    # Resize maintaining aspect ratio
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                    # Convert to PhotoImage
                    return ImageTk.PhotoImage(img)
    
    except Exception as e:
        logger.warning(f"Failed to load logo image: {e}")
    
    return None

def create_default_logo(size: Tuple[int, int] = (64, 64)) -> ImageTk.PhotoImage:
    """
    Create a default logo when no logo file is available.
    
    Args:
        size: Size as (width, height) tuple
        
    Returns:
        PhotoImage with default logo design
    """
    try:
        width, height = size
        
        # Create a simple default logo using PIL
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # You can customize this default logo design
        # For now, create a simple colored rectangle with text
        from PIL import ImageDraw, ImageFont
        
        draw = ImageDraw.Draw(img)
        
        # Draw background circle
        margin = 4
        draw.ellipse([margin, margin, width-margin, height-margin], 
                    fill=(70, 130, 180, 255), outline=(25, 25, 112, 255), width=2)
        
        # Try to add text
        try:
            # Try to use a system font
            font_size = max(8, width // 8)
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Add "TCM" text (Test Case Manager)
        text = "TCM"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2
        
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
        
        return ImageTk.PhotoImage(img)
        
    except Exception as e:
        logger.warning(f"Failed to create default logo: {e}")
        # Return a very simple fallback using PIL
        fallback_img = Image.new('RGBA', size, (0, 100, 200, 255))
        return ImageTk.PhotoImage(fallback_img)

def set_window_icon(window: tk.Tk) -> bool:
    """
    Set window icon for tkinter window.
    
    Args:
        window: Tkinter window object
        
    Returns:
        True if icon was set successfully, False otherwise
    """
    try:
        icon_path = load_window_icon()
        if icon_path:
            window.iconbitmap(icon_path)
            logger.info(f"Window icon set: {icon_path}")
            return True
        else:
            logger.debug("No window icon file found")
            return False
            
    except Exception as e:
        logger.warning(f"Failed to set window icon: {e}")
        return False

class LogoWidget:
    """
    Widget for displaying application logo in GUI.
    """
    
    def __init__(self, parent: tk.Widget, size: Tuple[int, int] = (64, 64)):
        """
        Initialize logo widget.
        
        Args:
            parent: Parent widget
            size: Logo size as (width, height) tuple
        """
        self.parent = parent
        self.size = size
        self.logo_image = None
        self.label = None
        
        self._load_logo()
        self._create_widget()
    
    def _load_logo(self) -> None:
        """Load logo image."""
        logger.info(f"Loading logo image with size {self.size}")

        # Try to load custom logo first
        self.logo_image = load_logo_image(self.size)

        if self.logo_image:
            logger.info("Custom logo loaded successfully")
        else:
            logger.warning("Custom logo failed to load, creating default logo")
            # If no custom logo, create default
            self.logo_image = create_default_logo(self.size)
            if self.logo_image:
                logger.info("Default logo created successfully")
            else:
                logger.error("Failed to create default logo")
    
    def _create_widget(self) -> None:
        """Create the logo label widget."""
        try:
            logger.info("Creating logo label widget...")

            # Try to get parent background color for better integration
            parent_bg = "#f0f0f0"  # Default light gray background
            if hasattr(self.parent, 'cget'):
                try:
                    bg_color = self.parent.cget('bg')
                    if bg_color and bg_color != "":
                        parent_bg = bg_color
                        logger.info(f"Using parent background color: {parent_bg}")
                except:
                    logger.info("Could not get parent background, using default")

            # Ensure we have a logo image
            if self.logo_image:
                logger.info("Creating label with logo image")
                self.label = tk.Label(
                    self.parent,
                    image=self.logo_image,
                    bg=parent_bg,
                    bd=2,  # Small border for visibility
                    relief="solid",
                    highlightthickness=0
                )
                logger.info("Logo image label created successfully")
            else:
                logger.warning("No logo image available, creating text fallback")
                # Fallback: create simple text label
                self.label = tk.Label(
                    self.parent,
                    text="🏢",
                    font=("Segoe UI", 28),
                    bg=parent_bg,
                    fg="#2E86AB",  # Blue color for visibility
                    bd=2,
                    relief="solid",
                    highlightthickness=0
                )
                logger.info("Text fallback label created successfully")

        except Exception as e:
            logger.error(f"Failed to create logo widget: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Final fallback: create simple text label with high visibility
            try:
                self.label = tk.Label(
                    self.parent,
                    text="🏢",
                    font=("Segoe UI", 28),
                    bg="#f0f0f0",
                    fg="#2E86AB",
                    bd=2,
                    relief="solid",
                    highlightthickness=0
                )
                logger.info("Final fallback label created successfully")
            except Exception as final_e:
                logger.error(f"Even final fallback failed: {final_e}")
                self.label = None
    
    def pack(self, **kwargs) -> None:
        """Pack the logo widget."""
        if self.label:
            self.label.pack(**kwargs)
    
    def grid(self, **kwargs) -> None:
        """Grid the logo widget."""
        if self.label:
            logger.info(f"Gridding logo widget with kwargs: {kwargs}")
            self.label.grid(**kwargs)
            logger.info("Logo widget gridded successfully")
        else:
            logger.error("Cannot grid logo widget - label is None")
    
    def place(self, **kwargs) -> None:
        """Place the logo widget."""
        if self.label:
            self.label.place(**kwargs)
    
    def destroy(self) -> None:
        """Destroy the logo widget."""
        if self.label:
            self.label.destroy()
            self.label = None
        self.logo_image = None
