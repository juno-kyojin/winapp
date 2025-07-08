# check_leasetime.py
from module import renew_ip_and_get_output, get_active_leasetime_str, parse_leasetime_str
from datetime import datetime
import sys

def main():
    # 1. Đọc leasetime_config (giây) từ input.txt
    try:
        with open('input.txt', 'r') as f:
            leasetime_config = int(f.readline().strip())
    except Exception as e:
        print(f"[Lỗi] Không thể đọc hoặc phân tích input.txt: {e}", file=sys.stderr)
        with open('output.txt', 'w') as f: f.write("0")
        return

    # 2. Chạy logic kiểm tra
    print("--- Bắt đầu kiểm tra thời gian thuê bao còn lại ---")
    ipconfig_output = renew_ip_and_get_output()
    result = 0 # Mặc định là fail
    if ipconfig_output:
        # Lấy thời gian hệ thống ngay sau khi có kết quả ipconfig
        check_time = datetime.now()
        
        leasetime_str = get_active_leasetime_str(ipconfig_output)
        if leasetime_str:
            print(f"-> Lease Expires: {leasetime_str}")
            print(f"-> Thời điểm kiểm tra: {check_time.strftime('%A, %B %d, %Y %I:%M:%S %p')}")
            
            expires_dt = parse_leasetime_str(leasetime_str)
            if expires_dt:
                # Tính thời gian thuê bao CÒN LẠI (giây)
                remaining_seconds = (expires_dt - check_time).total_seconds()
                
                print(f"-> Thời gian thuê bao còn lại: ~{int(remaining_seconds)} giây.")
                print(f"-> Thời gian thuê bao cấu hình: {leasetime_config} giây.")
                
                # Logic: Thời gian còn lại phải > 0 và <= thời gian cấu hình
                if 0 < remaining_seconds <= leasetime_config:
                    print("-> Kết quả: Thời gian còn lại hợp lệ.")
                    result = 1 # Pass
                else:
                    print("-> Kết quả: Thời gian còn lại KHÔNG hợp lệ.")
            else:
                print("-> Không thể phân tích chuỗi thời gian.")
        else:
            print("-> Không tìm thấy thông tin 'Lease Expires'.")

    # 3. Ghi kết quả ra output.txt
    with open('output.txt', 'w') as f:
        f.write(str(result))
    
    print(f"--- Hoàn thành. Đã ghi kết quả '{result}' vào output.txt ---")

if __name__ == "__main__":
    main()