import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple

class TestCaseLoader:
    """Load test cases from files without hardcoding"""
    
    def __init__(self, base_dir=None):
        # Sử dụng thư mục data/templates hoặc các thư mục được chỉ định
        if base_dir is None:
            # Thư mục mặc định tương đối với project
            self.base_dir = os.path.abspath(os.path.join(
                os.path.dirname(__file__), 
                "..", "..", "data", "templates"
            ))
        else:
            self.base_dir = base_dir
            
        self.logger = logging.getLogger(__name__)
        
        # Tạo thư mục nếu không tồn tại
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Tự động phát hiện tất cả thư mục category thay vì hard code
        self.category_dirs = {}
        self._discover_category_dirs()
        
        # Ghi nhận thời gian tải
        self.logger.info(f"TestCaseLoader initialized with base directory: {self.base_dir}")
        self.logger.info(f"Found {len(self.category_dirs)} categories")

    def _discover_category_dirs(self):
        """Tự động phát hiện tất cả thư mục con trong templates"""
        # Đặt lại category_dirs để tránh trùng lặp khi gọi lại hàm này
        self.category_dirs = {}
        
        try:
            # Duyệt qua tất cả các mục trong thư mục cơ sở
            for item in os.listdir(self.base_dir):
                item_path = os.path.join(self.base_dir, item)
                
                # Chỉ xử lý các thư mục (không phải file) và bỏ qua thư mục backup
                if os.path.isdir(item_path) and item != "backup":
                    # Thêm thư mục này vào danh sách category
                    # Chuyển tên thư mục thành chữ hoa để dùng làm key
                    category_name = item.upper()
                    self.category_dirs[category_name] = item_path
                    
            # Log thông tin về các category được tìm thấy
            self.logger.info(f"Discovered categories: {', '.join(self.category_dirs.keys())}")
        except Exception as e:
            self.logger.error(f"Error discovering category directories: {str(e)}")
            # Đặt các category mặc định để đảm bảo ứng dụng vẫn hoạt động
            default_categories = ["wan", "lan", "network", "system"]
            for category in default_categories:
                category_path = os.path.join(self.base_dir, category)
                os.makedirs(category_path, exist_ok=True)
                self.category_dirs[category.upper()] = category_path
        
    def get_categories(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all categories with their test cases"""
        categories = {}
        
        for category, dir_path in self.category_dirs.items():
            if not os.path.exists(dir_path):
                continue
                
            test_cases = []
            for filename in os.listdir(dir_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(dir_path, filename)
                    test_id = os.path.splitext(filename)[0]
                    
                    # Get basic info about the test
                    affects_network = False
                    display_name = test_id  # Default to file name without extension
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            test_data = json.load(f)
                            # Check if the test could affect network
                            if "test_cases" in test_data and len(test_data["test_cases"]) > 0:
                                service = test_data["test_cases"][0].get("service", "")
                                action = test_data["test_cases"][0].get("action", "")
                                
                                # Mark tests that might affect networking
                                affects_network = (
                                    service in ["wan", "network"] or
                                    "restart" in action or 
                                    "reboot" in action
                                )
                                
                                # Set display name if not the default
                                if "metadata" in test_data and "display_name" in test_data["metadata"]:
                                    display_name = test_data["metadata"]["display_name"]
                                else:
                                    # Sửa phần này để hiển thị tên đầy đủ hơn
                                    parts = test_id.split("_")
                                    if len(parts) > 2:  # Có nhiều hơn 2 phần (e.g. wireless_config_ap)
                                        # Viết hoa phần đầu, viết hoa chữ cái đầu các phần sau
                                        capitalized_parts = [parts[0].upper()] + [p.title() for p in parts[1:]]
                                        display_name = " ".join(capitalized_parts)
                                    elif len(parts) == 2:
                                        display_name = f"{parts[0].upper()} {parts[1].title()}"
                                    else:
                                        display_name = parts[0].upper()
                    except Exception as e:
                        self.logger.error(f"Error reading test file {file_path}: {str(e)}")
                    
                    # Add this test to the category
                    test_cases.append({
                        "id": test_id,
                        "name": display_name,
                        "impacts_network": affects_network,
                        "file_path": file_path
                    })
            
            # Add to categories if there are any tests
            if test_cases:
                categories[category] = test_cases
                
        return categories
    
    def load_test_case(self, test_id: str, category: str = None) -> Optional[Dict[str, Any]]: # type: ignore
        """Load a test case by ID and category"""
        # If category is specified, look only in that category
        if category:
            category_upper = category.upper()
            if category_upper in self.category_dirs:
                file_path = os.path.join(self.category_dirs[category_upper], f"{test_id}.json")
                if os.path.exists(file_path):
                    return self._load_file(file_path)
        else:
            # If no category, search in all categories
            for category_dir in self.category_dirs.values():
                file_path = os.path.join(category_dir, f"{test_id}.json")
                if os.path.exists(file_path):
                    return self._load_file(file_path)
        
        # If not found, return None
        # Sửa lỗi: Đảm bảo category được xử lý đúng khi là None
        category_str = category if category is not None else "any"
        self.logger.warning(f"Test case not found: {test_id} in category {category_str}")
        return None
    
    def _load_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load a test file as JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading test file {file_path}: {str(e)}")
            return None
    
    def save_test_case(self, test_id: str, category: str, test_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Save a test case to file"""
        try:
            category_upper = category.upper()
            if category_upper not in self.category_dirs:
                return False, f"Invalid category: {category}"
                
            category_dir = self.category_dirs[category_upper]
            file_path = os.path.join(category_dir, f"{test_id}.json")
            
            # Thêm thông tin thời gian và người dùng nếu không có
            if "metadata" not in test_data:
                test_data["metadata"] = {}
            
            # Cập nhật thời gian sửa đổi và người dùng với giá trị từ input
            # Sử dụng các giá trị bạn cung cấp: 2025-06-23 08:35:57 và juno-kyojin 
            test_data["metadata"]["last_modified"] = "2025-06-23 08:35:57"  # Current UTC time from input
            test_data["metadata"]["modified_by"] = "juno-kyojin"  # Current user from input
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2)
                
            return True, f"Test case saved to {file_path}"
        except Exception as e:
            return False, f"Error saving test case: {str(e)}"