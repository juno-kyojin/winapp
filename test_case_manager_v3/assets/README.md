# Assets Directory

This directory contains visual assets for Test Case Manager v1.0.

## Files Structure

- `logo.ico` - Application icon for Windows (16x16, 32x32, 48x48, 256x256)
- `logo.png` - Main application logo (PNG format, transparent background)
- `banner.png` - Header banner for main window (optional)

## Logo Requirements

### For Window Icon (.ico):
- Format: ICO file with multiple sizes
- Sizes: 16x16, 32x32, 48x48, 256x256 pixels
- Background: Transparent
- Usage: Window title bar, taskbar, Alt+Tab

### For GUI Logo (.png):
- Format: PNG with transparency
- Size: 64x64 or 128x128 pixels recommended
- Background: Transparent
- Usage: Main window header, about dialog

## Adding Your Logo

1. Place your logo files in this directory:
   - `logo.ico` - For window icon
   - `logo.png` - For GUI display

2. The application will automatically detect and use these files

3. If files are not found, the application will run without logo (graceful fallback)

## Logo Design Guidelines

- Keep design simple and recognizable at small sizes
- Use high contrast colors for visibility
- Ensure logo works on both light and dark backgrounds
- Consider the application's purpose (network testing tool)
