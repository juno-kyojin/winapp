# check_ip_start.py
from module import renew_ip_and_get_output, get_active_ip, check_ip_in_range
import sys

def main():
    # 1. Đọc thông số từ input.txt theo từng dòng
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 2:
            raise ValueError("File input.txt phải có ít nhất 2 dòng.")

        # Lấy giá trị và xóa các khoảng trắng/ký tự xuống dòng thừa
        start_ip = lines[0].strip()
        limit = int(lines[1].strip())

    except (ValueError, IndexError) as e:
        print(f"[Lỗi] Định dạng file input.txt không hợp lệ: {e}", file=sys.stderr)
        # Ghi lỗi ra output và thoát
        with open('output.txt', 'w') as f:
            f.write("0")
        return
    except FileNotFoundError:
        print("[Lỗi] Không tìm thấy file input.txt.", file=sys.stderr)
        with open('output.txt', 'w') as f:
            f.write("0")
        return

    # 2. Chạy logic kiểm tra (giữ nguyên như cũ)
    print("--- Bắt đầu kiểm tra IP Start ---")
    ipconfig_output = renew_ip_and_get_output()
    result = 0 # Mặc định là fail
    if ipconfig_output:
        current_ip = get_active_ip(ipconfig_output)
        if current_ip:
            print(f"-> IP hiện tại: {current_ip}")
            if check_ip_in_range(current_ip, start_ip, limit):
                print("-> Kết quả: IP hợp lệ.")
                result = 1 # Pass
            else:
                print("-> Kết quả: IP KHÔNG hợp lệ.")
        else:
            print("-> Không tìm thấy địa chỉ IP active.")
    
    # 3. Ghi kết quả ra output.txt
    with open('output.txt', 'w') as f:
        f.write(str(result))
    
    print(f"--- Hoàn thành. Đã ghi kết quả '{result}' vào output.txt ---")

if __name__ == "__main__":
    main()