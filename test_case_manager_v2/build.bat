@echo off
REM Xóa thư mục build cũ nếu tồn tại
IF EXIST dist rmdir /S /Q dist
IF EXIST build rmdir /S /Q build

REM Build với PyInstaller - thêm tùy chọn paths để đảm bảo import hoạt động
pyinstaller --name="TestCaseManager" ^
            --onedir ^
            --add-data="data;data" ^
            --hidden-import=tkinter ^
            --hidden-import=tkinter.ttk ^
            --paths="src" ^
            --noupx ^
            src/main.py

echo Build completed. Application is in dist\TestCaseManager folder.
echo You can now run TestCaseManager.exe