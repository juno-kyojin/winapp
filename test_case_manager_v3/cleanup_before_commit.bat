@echo off
echo Cleaning up before git commit...

echo.
echo [1/7] Resetting git staging area...
git reset

echo.
echo [2/7] Removing Python cache files...
if exist "src\__pycache__" rmdir /s /q "src\__pycache__"
if exist "src\core\__pycache__" rmdir /s /q "src\core\__pycache__"
if exist "src\utils\__pycache__" rmdir /s /q "src\utils\__pycache__"
if exist "src\gui\__pycache__" rmdir /s /q "src\gui\__pycache__"
if exist "src\network\__pycache__" rmdir /s /q "src\network\__pycache__"
if exist "ToolWL\__pycache__" rmdir /s /q "ToolWL\__pycache__"

echo.
echo [3/7] Removing build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [4/7] Clearing log files...
if exist "data\logs\app.log" echo. > "data\logs\app.log"

echo.
echo [5/7] Clearing temporary test results...
if exist "data\temp\results" rmdir /s /q "data\temp\results"
if not exist "data\temp\results" mkdir "data\temp\results"

echo.
echo [6/7] Adding all source files to git...
git add .
git reset -- release/
git reset -- build/
git reset -- dist/

echo.
echo [7/7] Checking git status...
git status

echo.
echo Cleanup completed! Ready for commit.
echo.
echo Files excluded from commit:
echo - build/ directory
echo - dist/ directory
echo - release/ directory
echo - __pycache__/ directories
echo - Log files
echo - Temporary test results
