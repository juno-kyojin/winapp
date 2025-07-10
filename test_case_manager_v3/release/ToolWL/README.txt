============================================================
ToolWL - Test Case Manager v1.0 Verification Scripts
============================================================

📁 Thư mục này chứa các script verification cho Test Case Manager v1.0

🚀 HƯỚNG DẪN SỬ DỤNG LẦN ĐẦU:

1. Chạy file: install_all_dependencies.bat
   - Script sẽ tự động cài đặt tất cả thư viện cần thiết
   - Chỉ cần chạy 1 lần khi copy app sang máy mới

2. Nếu có lỗi, đảm bảo:
   - Python 3.8+ đã được cài đặt
   - Chạy Test Case Manager as Administrator
   - Antivirus không block Python scripts

📋 CÁC FILE QUAN TRỌNG:

• install_all_dependencies.bat - Cài đặt thư viện (CHẠY ĐẦU TIÊN)
• wireless_edit_ap.py - Verification cho WiFi tests
• lan_edit_leasetime.py - Verification cho LAN DHCP tests  
• lan_edit_ip_start.py - Verification cho LAN IP tests
• input.txt - File input cho scripts (tự động tạo)
• output.txt - File output từ scripts (tự động tạo)

📂 THƯ MỤC:
• wifi_connect/ - Module WiFi connection utilities

🔧 THÊM SCRIPT MỚI:

1. Tạo file .py mới trong thư mục này
2. Đọc parameters từ input.txt
3. Ghi kết quả vào output.txt ("1" = pass, "0" = fail)
4. Không cần rebuild app

💡 VÍ DỤ SCRIPT:

```python
# Đọc input
with open("input.txt", "r") as f:
    param1 = f.readline().strip()
    param2 = f.readline().strip()

# Thực hiện verification logic
success = your_verification_logic(param1, param2)

# Ghi output
with open("output.txt", "w") as f:
    f.write("1" if success else "0")
```

🆘 HỖ TRỢ:

Nếu gặp vấn đề:
1. Kiểm tra logs trong Test Case Manager (tab Logs)
2. Test script thủ công: python wireless_edit_ap.py
3. Kiểm tra dependencies: python -c "import pywifi; print('OK')"

============================================================
Test Case Manager v1.0 - ToolWL Verification Scripts
Copyright © 2025. All rights reserved.
============================================================
