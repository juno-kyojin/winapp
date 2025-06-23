import os
import json
import logging
import shutil
from datetime import datetime

class TestCaseFileManager:
    """Manager for test case files with save/reset functionality"""
    
    def __init__(self, base_dir=None):
        # Sử dụng đường dẫn tương đối đến thư mục data/templates
        if base_dir is None:
            # Tính đường dẫn từ vị trí hiện tại đến data/templates
            self.base_dir = os.path.abspath(os.path.join(
                os.path.dirname(__file__), 
                "..", "..", "data", "templates"
            ))
        else:
            self.base_dir = base_dir
            
        self.backup_dir = os.path.join(self.base_dir, "backup")
        self.logger = logging.getLogger(__name__)
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def get_test_categories(self):
        """Load and return all test categories based on subdirectories"""
        categories = {}
        
        try:
            # Kiểm tra các thư mục con là categories
            for item in os.listdir(self.base_dir):
                category_path = os.path.join(self.base_dir, item)
                
                # Chỉ xử lý thư mục (không phải file hoặc thư mục backup)
                if os.path.isdir(category_path) and item != "backup":
                    category_name = item.upper()  # Chuyển tên thư mục thành category name
                    test_cases = []
                    
                    # Duyệt qua từng file JSON trong thư mục
                    for file in os.listdir(category_path):
                        if file.endswith(".json"):
                            test_file_path = os.path.join(category_path, file)
                            test_id = os.path.splitext(file)[0]  # Bỏ phần mở rộng .json
                            
                            # Đọc file để lấy thông tin khác nếu có
                            try:
                                with open(test_file_path, 'r', encoding='utf-8') as f:
                                    test_data = json.load(f)
                                    
                                    # Kiểm tra xem có trường impacts_network không
                                    affects_network = test_data.get("affects_network", False)
                                    display_name = test_data.get("display_name", test_id)
                                    
                                    test_cases.append({
                                        "id": test_id,
                                        "name": display_name,
                                        "impacts_network": affects_network,
                                        "file_path": test_file_path
                                    })
                            except Exception as e:
                                self.logger.error(f"Error reading test file {test_file_path}: {e}")
                                # Thêm với thông tin tối thiểu
                                test_cases.append({
                                    "id": test_id,
                                    "name": test_id,
                                    "impacts_network": False,
                                    "file_path": test_file_path
                                })
                    
                    # Thêm category và test cases của nó
                    categories[category_name] = test_cases
            
            return categories
            
        except Exception as e:
            self.logger.error(f"Error loading test categories: {e}")
            return {}
    
    def load_test_parameters(self, test_id, category=None, file_path=None):
        """Load parameters for a specific test"""
        try:
            # Nếu có file_path, sử dụng trực tiếp
            if file_path and os.path.exists(file_path):
                params_file = file_path
            # Ngược lại tìm file dựa theo category và test_id
            elif category:
                category_dir = os.path.join(self.base_dir, category.lower())
                params_file = os.path.join(category_dir, f"{test_id}.json")
            else:
                # Tìm file trong tất cả các category
                params_file = None
                for dir_name in os.listdir(self.base_dir):
                    if os.path.isdir(os.path.join(self.base_dir, dir_name)) and dir_name != "backup":
                        test_path = os.path.join(self.base_dir, dir_name, f"{test_id}.json")
                        if os.path.exists(test_path):
                            params_file = test_path
                            break
            
            if params_file and os.path.exists(params_file):
                with open(params_file, 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                    
                    # Trích xuất parameters từ file
                    if "parameters" in test_data:
                        return test_data["parameters"]
                    elif "params" in test_data:  # Hỗ trợ cả định dạng cũ
                        return test_data["params"]
                    else:
                        # Lấy toàn bộ file nếu không có key parameters
                        return test_data
            else:
                self.logger.warning(f"Test file not found for {test_id} in {category}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error loading parameters for {test_id}: {e}")
            return []
    
    def save_test_parameters(self, test_id, category, parameters, create_backup=True):
        """Save parameters for a specific test"""
        try:
            # Tìm đường dẫn file
            category_dir = os.path.join(self.base_dir, category.lower())
            params_file = os.path.join(category_dir, f"{test_id}.json")
            
            # Nếu file không tồn tại, thử tìm trong tất cả các category
            if not os.path.exists(params_file):
                for dir_name in os.listdir(self.base_dir):
                    if os.path.isdir(os.path.join(self.base_dir, dir_name)) and dir_name != "backup":
                        test_path = os.path.join(self.base_dir, dir_name, f"{test_id}.json")
                        if os.path.exists(test_path):
                            params_file = test_path
                            category_dir = os.path.join(self.base_dir, dir_name)
                            break
            
            # Đảm bảo thư mục category tồn tại
            os.makedirs(category_dir, exist_ok=True)
            
            # Tạo backup nếu file đã tồn tại
            if create_backup and os.path.exists(params_file):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(self.backup_dir, f"{test_id}_{timestamp}.json")
                shutil.copy2(params_file, backup_file)
                self.logger.info(f"Created backup of {test_id} at {backup_file}")
            
            # Đọc file hiện tại nếu có để giữ các trường khác
            existing_data = {}
            if os.path.exists(params_file):
                try:
                    with open(params_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass
            
            # Cập nhật hoặc thêm trường parameters
            existing_data["parameters"] = parameters
            
            # Thêm metadata
            existing_data["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            existing_data["modified_by"] = os.environ.get('USERNAME', 'unknown')
            
            # Đảm bảo các trường cần thiết khác tồn tại
            if "display_name" not in existing_data:
                existing_data["display_name"] = test_id
                
            if "affects_network" not in existing_data:
                # Đánh dấu tự động dựa trên tên
                affects_network = any(keyword in test_id.lower() for keyword in 
                                    ["wan", "network", "reboot", "reset", "restart"])
                existing_data["affects_network"] = affects_network
            
            # Lưu file
            with open(params_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=4, ensure_ascii=False)
                
            self.logger.info(f"Saved parameters for {test_id} in {category}")
            return True, params_file
            
        except Exception as e:
            self.logger.error(f"Error saving parameters for {test_id}: {e}")
            return False, str(e)