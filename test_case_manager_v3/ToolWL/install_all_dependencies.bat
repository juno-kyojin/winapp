@echo off
REM ToolWL Dependencies Installer
REM Install all required libraries for ToolWL verification scripts

echo ToolWL Dependencies Installer
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found
    echo Please install Python 3.8+ from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check pip
python -m pip --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing pip...
    python -m ensurepip --upgrade
)

REM Install dependencies
echo Installing dependencies...

python -m pip install pywifi
if %ERRORLEVEL% NEQ 0 set INSTALL_FAILED=1

python -m pip install requests
if %ERRORLEVEL% NEQ 0 set INSTALL_FAILED=1

python -m pip install psutil
if %ERRORLEVEL% NEQ 0 set INSTALL_FAILED=1

REM Add more libraries here as needed:
REM python -m pip install library_name
REM if %ERRORLEVEL% NEQ 0 set INSTALL_FAILED=1

REM Test installation
echo.
echo Testing installation...
cd /d "%~dp0"

python -c "import pywifi; print('pywifi OK')" 2>nul || set TEST_FAILED=1
python -c "import requests; print('requests OK')" 2>nul || set TEST_FAILED=1
python -c "import psutil; print('psutil OK')" 2>nul || set TEST_FAILED=1
python -c "from wifi_connect import wifi_check_connect_to_ap; print('wifi_connect OK')" 2>nul || set TEST_FAILED=1
python -c "import module; print('module.py OK')" 2>nul || set TEST_FAILED=1

REM Results
echo.
if defined INSTALL_FAILED (
    echo INSTALLATION FAILED
    echo Please install manually: pip install pywifi requests psutil
) else if defined TEST_FAILED (
    echo INSTALLATION COMPLETED WITH ISSUES
    echo Some libraries may not work properly
) else (
    echo INSTALLATION SUCCESSFUL
    echo All dependencies are ready
)

echo.
pause
