@echo off
REM Build script for Test Case Manager v1.0
REM This script builds an executable version of the application using PyInstaller

echo ============================================================
echo Building Test Case Manager v1.0 Standalone Executable
echo ============================================================

REM Check if we're in the correct directory
if not exist src (
    echo ERROR: Source directory not found. Make sure you're in the test_case_manager_v1 directory.
    echo Current directory: %CD%
    exit /b 1
)

if not exist run.py (
    echo ERROR: run.py not found. Make sure you're in the test_case_manager_v1 directory.
    exit /b 1
)

echo ✓ Project directory verified

REM Install dependencies if requirements.txt exists
if exist requirements.txt (
    echo Installing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo WARNING: Failed to install some dependencies. Continuing with build...
    ) else (
        echo ✓ Dependencies installed successfully
    )
) else (
    echo WARNING: requirements.txt not found. Installing PyInstaller only...
    python -m pip install pyinstaller requests
)

REM Check if PyInstaller is installed
echo Checking PyInstaller installation...
python -m pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install PyInstaller. Exiting.
        exit /b 1
    )
)
echo ✓ PyInstaller is available

REM Create necessary directories if they don't exist
echo Creating necessary directories...
if not exist data\config mkdir data\config
if not exist data\logs mkdir data\logs
if not exist data\temp mkdir data\temp
if not exist data\temp\results mkdir data\temp\results
if not exist data\templates mkdir data\templates
if not exist data\backup mkdir data\backup
echo ✓ Directory structure verified

REM Clean previous build
echo Cleaning previous build...
if exist dist rmdir /S /Q dist
if exist build rmdir /S /Q build
if exist TestCaseManager.spec del TestCaseManager.spec
echo ✓ Previous build cleaned

REM Build the executable using run.py as entry point
echo Building single executable file...
echo This may take several minutes...

python -m PyInstaller --name="TestCaseManager" ^
            --onefile ^
            --windowed ^
            --hidden-import=tkinter ^
            --hidden-import=tkinter.ttk ^
            --hidden-import=tkinter.messagebox ^
            --hidden-import=tkinter.filedialog ^
            --hidden-import=requests ^
            --hidden-import=PIL ^
            --hidden-import=PIL.Image ^
            --hidden-import=PIL.ImageTk ^
            --hidden-import=json ^
            --hidden-import=logging ^
            --hidden-import=threading ^
            --hidden-import=datetime ^
            --hidden-import=pathlib ^
            --hidden-import=uuid ^
            --hidden-import=time ^
            --hidden-import=os ^
            --hidden-import=sys ^
            --hidden-import=re ^
            --hidden-import=argparse ^
            --hidden-import=typing ^
            --add-data="assets;assets" ^
            --paths=. ^
            --noupx ^
            run.py

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed!
    exit /b 1
)

echo ✓ Build completed successfully!

REM Verify the build
echo Verifying build output...
if not exist dist\TestCaseManager.exe (
    echo ERROR: Executable not found!
    exit /b 1
)

echo ✓ Executable created successfully

REM Create clean distribution folder
echo Creating clean distribution folder...
if exist release rmdir /S /Q release
mkdir release

REM Copy executable to release folder
echo Copying executable...
copy dist\TestCaseManager.exe release\TestCaseManager.exe
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy executable!
    exit /b 1
)

REM Copy data folder to release folder
echo Copying data folder...
xcopy data release\data /E /I /Y
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy data folder!
    exit /b 1
)

REM ============================================================
REM Copy ToolWL folder and dependencies (for script verification)
REM ============================================================
echo Copying ToolWL folder and dependencies...

if exist ToolWL (
    echo ✓ ToolWL folder found - copying to release...
    xcopy ToolWL release\ToolWL /E /I /Y
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to copy ToolWL folder!
        exit /b 1
    )
    echo ✓ ToolWL folder copied successfully

    REM Clean up __pycache__ folders in release
    if exist release\ToolWL\__pycache__ rmdir /S /Q release\ToolWL\__pycache__
    if exist release\ToolWL\wifi_connect\__pycache__ rmdir /S /Q release\ToolWL\wifi_connect\__pycache__
    echo ✓ Cleaned up __pycache__ folders

) else (
    echo WARNING: ToolWL folder not found - script verification may not work
    echo Creating empty ToolWL folder structure...
    mkdir release\ToolWL
    echo # ToolWL Folder > release\ToolWL\README.txt
    echo This folder contains verification scripts for Test Case Manager. >> release\ToolWL\README.txt
    echo Add your verification scripts here following the input.txt/output.txt interface. >> release\ToolWL\README.txt
)

REM Copy additional wifi_connect module if it exists separately (fallback)
echo Checking for additional wifi_connect dependencies...
if exist ..\wifi_connect\wifi_connect (
    if not exist release\ToolWL\wifi_connect (
        echo Copying wifi_connect module to ToolWL...
        xcopy ..\wifi_connect\wifi_connect release\ToolWL\wifi_connect /E /I /Y
        if %ERRORLEVEL% NEQ 0 (
            echo WARNING: Failed to copy wifi_connect module
        ) else (
            echo ✓ wifi_connect module copied successfully
        )
    ) else (
        echo ✓ wifi_connect module already included in ToolWL
    )
) else (
    echo ✓ No additional wifi_connect module found (using existing in ToolWL)
)

REM Assets are now embedded in the executable, no need to copy separately
echo ✓ Assets embedded in executable (no separate assets folder needed)

REM Remove any existing assets folder from release (assets are now embedded)
if exist release\assets rmdir /S /Q release\assets

REM Verify final release structure
echo Verifying release structure...
if not exist release\TestCaseManager.exe (
    echo ERROR: Executable not found in release folder!
    exit /b 1
)

if not exist release\data (
    echo ERROR: Data folder not found in release folder!
    exit /b 1
)

if not exist release\ToolWL (
    echo WARNING: ToolWL folder not found in release folder - script verification may not work
) else (
    echo ✓ ToolWL folder verified
)

echo ✓ Release verification passed (assets embedded in executable)

REM Clean up build artifacts
echo Cleaning up build artifacts...
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
if exist TestCaseManager.spec del TestCaseManager.spec

echo ✓ Build artifacts cleaned

echo ============================================================
echo Build Complete!
echo ============================================================
echo 📁 Release folder: release\
echo 📄 Executable: release\TestCaseManager.exe (with embedded assets)
echo 📂 Data folder: release\data\
echo 🔧 ToolWL folder: release\ToolWL\ (verification scripts)
echo
echo ✅ Ready for distribution:
echo   - Single executable file with embedded assets (no source code visible)
echo   - Data folder with templates and configuration
echo   - ToolWL folder with verification scripts (external, modifiable)
echo   - No Python installation required on target systems
echo   - No separate assets folder needed (embedded in .exe)
echo
echo 🚀 To run the application:
echo   1. Navigate to: release\
echo   2. Double-click: TestCaseManager.exe
echo
echo 📝 The application will:
echo   - Create logs in: data\logs\
echo   - Load test cases from: data\templates\
echo   - Store configuration in: data\config\
echo   - Load embedded assets automatically
echo   - Execute verification scripts from: ToolWL\
echo
echo 🔧 Adding new verification scripts:
echo   - Add new .py scripts to: release\ToolWL\
echo   - Scripts must follow input.txt/output.txt interface
echo   - No rebuild required for new scripts
echo ============================================================

exit /b 0
