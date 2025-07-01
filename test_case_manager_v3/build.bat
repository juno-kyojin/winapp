@echo off
REM Build script for Test Case Manager v3.0
REM This script builds an executable version of the application using PyInstaller

echo Building Test Case Manager v3.0...

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install PyInstaller. Exiting.
        exit /b 1
    )
)

REM Check if the src directory exists
if not exist src (
    echo Source directory not found. Make sure you're in the correct directory.
    exit /b 1
)

REM Create necessary directories if they don't exist
if not exist data\config mkdir data\config
if not exist data\logs mkdir data\logs
if not exist data\temp\results mkdir data\temp\results
if not exist data\templates mkdir data\templates

REM Build the executable
echo Building executable...
pyinstaller --name="TestCaseManager" ^
            --windowed ^
            --icon=src/resources/icon.ico ^
            --add-data="src/resources;resources" ^
            --add-data="data;data" ^
            --hidden-import=tkinter ^
            --hidden-import=requests ^
            src/main.py

echo Build complete!
echo Executable can be found in the dist/TestCaseManager directory.

exit /b 0
