#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Case Loader module for Test Case Manager v1.0

This module provides functionality for loading test cases from templates
directory, discovering category directories, and managing test case files.

Author: juno-kyojin
Created: 2025-06-12
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set, Union

from .constants import TEMPLATE_DIR
from .exceptions import FileOperationError, TemplateNotFoundError


class TestCaseLoader:
    """
    Load and manage test cases from template files.
    
    This class is responsible for discovering test case templates,
    loading them from files, and providing category-based access.
    """
    
    def __init__(self, base_dir: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize the test case loader.
        
        Args:
            base_dir: Base directory containing template files.
                     If None, defaults to the standard templates directory.
        """
        # Sử dụng thư mục data/templates hoặc các thư mục được chỉ định
        if base_dir is None:
            # Sử dụng Path từ constants
            self.base_dir = TEMPLATE_DIR
        else:
            self.base_dir = Path(base_dir)
            
        self.logger = logging.getLogger(__name__)
        
        # Tạo thư mục nếu không tồn tại
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Tự động phát hiện tất cả thư mục category thay vì hard code
        self.category_dirs: Dict[str, Path] = {}
        self._discover_category_dirs()
        
        # Ghi nhận thông tin khởi tạo
        self.logger.info(f"TestCaseLoader initialized with base directory: {self.base_dir}")
        self.logger.info(f"Found {len(self.category_dirs)} categories")

    def _discover_category_dirs(self) -> None:
        """
        Automatically discover all subdirectories in templates directory.
        
        Each subdirectory represents a test case category.
        """
        # Đặt lại category_dirs để tránh trùng lặp khi gọi lại hàm này
        self.category_dirs = {}
        
        try:
            # Sử dụng pathlib để liệt kê thư mục con
            for item in self.base_dir.iterdir():
                # Chỉ xử lý các thư mục (không phải file) và bỏ qua thư mục backup
                if item.is_dir() and item.name != "backup":
                    # Thêm thư mục này vào danh sách category
                    # Chuyển tên thư mục thành chữ hoa để dùng làm key
                    category_name = item.name.upper()
                    self.category_dirs[category_name] = item
                    
            # Log thông tin về các category được tìm thấy
            self.logger.info(f"Discovered categories: {', '.join(self.category_dirs.keys())}")
        except Exception as e:
            self.logger.error(f"Error discovering category directories: {str(e)}")
            # Đặt các category mặc định để đảm bảo ứng dụng vẫn hoạt động
            default_categories = ["wan", "lan", "network", "system"]
            for category in default_categories:
                category_path = self.base_dir / category
                category_path.mkdir(parents=True, exist_ok=True)
                self.category_dirs[category.upper()] = category_path
    
    def get_categories(self) -> List[str]:
        """
        Get list of category names.
        
        Returns:
            List of category names
        """
        return list(self.category_dirs.keys())
    
    def get_templates_for_category(self, category: str) -> List[str]:
        """
        Get list of template names for a category.
        
        Args:
            category: Category name
            
        Returns:
            List of template names
        """
        templates = []
        category_upper = category.upper()
        
        if category_upper in self.category_dirs:
            category_dir = self.category_dirs[category_upper]
            for json_file in category_dir.glob('*.json'):
                templates.append(json_file.name)
        
        return sorted(templates)
    
    def get_template_path(self, category: str, template_name: str) -> str:
        """
        Get the file path for a template.
        
        Args:
            category: Category name
            template_name: Template name
            
        Returns:
            Path to template file
            
        Raises:
            TemplateNotFoundError: If the template cannot be found
        """
        category_upper = category.upper()
        
        if category_upper not in self.category_dirs:
            raise TemplateNotFoundError(
                f"Category {category} not found",
                template_name,
                category
            )
        
        template_path = self.category_dirs[category_upper] / template_name
        
        if not template_path.exists():
            raise TemplateNotFoundError(
                f"Template {template_name} not found in category {category}",
                template_name,
                category
            )
        
        return str(template_path)
        
    def get_categories_with_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all categories with their test cases.
        
        Returns:
            Dictionary mapping category names to lists of test cases
        """
        categories: Dict[str, List[Dict[str, Any]]] = {}
        
        for category, dir_path in self.category_dirs.items():
            if not dir_path.exists():
                continue
                
            test_cases: List[Dict[str, Any]] = []
            for json_file in dir_path.glob('*.json'):
                test_id = json_file.stem  # Name without extension
                
                # Get basic info about the test
                affects_network = False
                display_name = test_id  # Default to file name without extension
                
                try:
                    with json_file.open('r', encoding='utf-8') as f:
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
                                # Generate a more descriptive display name
                                parts = test_id.split("_")
                                if len(parts) > 2:  # Có nhiều hơn 2 phần (e.g. wireless_config_ap)
                                    # Viết hoa phần đầu, viết hoa chữ cái đầu các phần sau
                                    capitalized_parts = [parts[0].upper()] + [p.title() for p in parts[1:]]
                                    display_name = " ".join(capitalized_parts)
                                elif len(parts) == 2:
                                    display_name = f"{parts[0].upper()} {parts[1].title()}"
                                else:
                                    display_name = parts[0].upper()
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON parsing error in {json_file}: {str(e)}")
                    continue
                except Exception as e:
                    self.logger.error(f"Error reading test file {json_file}: {str(e)}")
                    continue
                
                # Add this test to the category
                test_cases.append({
                    "id": test_id,
                    "name": display_name,
                    "impacts_network": affects_network,
                    "file_path": str(json_file)
                })
            
            # Add to categories if there are any tests
            if test_cases:
                categories[category] = test_cases
                
        return categories
    
    def load_test_case(self, test_id: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a test case by ID and category.
        
        Args:
            test_id: Identifier for the test case
            category: Category name (optional - searches all if None)
            
        Returns:
            Test case data as a dictionary
            
        Raises:
            TemplateNotFoundError: If the test case cannot be found
        """
        # If category is specified, look only in that category
        if category:
            category_upper = category.upper()
            if category_upper in self.category_dirs:
                file_path = self.category_dirs[category_upper] / f"{test_id}.json"
                if file_path.exists():
                    result = self._load_file(file_path)
                    if result is not None:
                        return result
        else:
            # If no category, search in all categories
            for category_dir in self.category_dirs.values():
                file_path = category_dir / f"{test_id}.json"
                if file_path.exists():
                    result = self._load_file(file_path)
                    if result is not None:
                        return result
        
        # Not found, raise exception
        category_str = category if category is not None else "any"
        self.logger.warning(f"Test case not found: {test_id} in category {category_str}")
        raise TemplateNotFoundError(
            f"Test case not found: {test_id} in category {category_str}",
            test_id,
            category or "any"
        )
    
    def _load_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load a test file as JSON.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Dictionary containing test case data or None on error
        """
        try:
            with file_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error in {file_path}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading test file {file_path}: {str(e)}")
            return None
    
    def save_test_case(self, test_id: str, category: str, test_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Save a test case to file.
        
        Args:
            test_id: Identifier for the test case
            category: Category name
            test_data: Test case data to save
            
        Returns:
            Tuple containing (success boolean, message)
        """
        try:
            category_upper = category.upper()
            if category_upper not in self.category_dirs:
                return False, f"Invalid category: {category}"
                
            category_dir = self.category_dirs[category_upper]
            file_path = category_dir / f"{test_id}.json"
            
            # Ensure metadata exists
            if "metadata" not in test_data:
                test_data["metadata"] = {}
            
            # Update modification timestamp and user
            # Use current timestamp instead of hardcoded value
            test_data["metadata"]["last_modified"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            test_data["metadata"]["modified_by"] = "juno-kyojin"  # Todo: get from current user
            
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Test case saved successfully: {file_path}")
            return True, f"Test case saved to {file_path}"
        except Exception as e:
            self.logger.error(f"Error saving test case: {str(e)}")
            return False, f"Error saving test case: {str(e)}"
    
    def get_available_categories(self) -> Set[str]:
        """
        Get a list of available category names.
        
        Returns:
            Set of category names (uppercase)
        """
        return set(self.category_dirs.keys())
    
    def refresh_categories(self) -> int:
        """
        Refresh the category directory listing.
        
        Returns:
            Number of categories found
        """
        self._discover_category_dirs()
        return len(self.category_dirs) 
