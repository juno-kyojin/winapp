@echo off
echo Cleaning up before git commit...

echo.
echo [1/5] Resetting git staging area...
git reset

echo.
echo [2/5] Removing Python cache files...
if exist "src\__pycache__" rmdir /s /q "src\__pycache__"
if exist "src\core\__pycache__" rmdir /s /q "src\core\__pycache__"
if exist "src\utils\__pycache__" rmdir /s /q "src\utils\__pycache__"
if exist "src\gui\__pycache__" rmdir /s /q "src\gui\__pycache__"

echo.
echo [3/5] Clearing log file...
echo. > "data\logs\app.log"

echo.
echo [4/5] Adding necessary files to git...
git add .gitignore
git add requirements.txt
git add build.bat
git add src\core\constants.py
git add src\main.py
git add src\utils\logger.py

echo.
echo [5/5] Checking git status...
git status

echo.
echo Cleanup completed! Ready for commit.
echo.
echo To commit, run:
echo git commit -m "Update Test Case Manager v3.0: Fix executable environment and build system"
