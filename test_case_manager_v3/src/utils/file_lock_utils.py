#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File Lock Utils for Test Case Manager v3.0

This module provides file locking utilities to prevent race conditions
when reading and writing files.

Author: juno-kyojin
Created: 2025-07-05
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)

def read_file_with_lock(file_path: Union[str, Path], 
                      max_retries: int = 5, 
                      initial_backoff: float = 0.1) -> Optional[Dict[str, Any]]:
    """
    Đọc file JSON với file locking và exponential backoff
    
    Args:
        file_path: Đường dẫn đến file
        max_retries: Số lần thử tối đa
        initial_backoff: Thời gian chờ ban đầu (giây)
        
    Returns:
        Nội dung file dạng dict hoặc None nếu có lỗi
    """
    file_path = Path(file_path)
    retry_count = 0
    backoff = initial_backoff
    lock_path = str(file_path) + ".lock"
    
    while retry_count < max_retries:
        try:
            # Kiểm tra xem file lock có tồn tại không
            if os.path.exists(lock_path):
                logger.debug(f"File {file_path} đang bị khóa, thử lại sau {backoff}s")
                time.sleep(backoff)
                backoff *= 2  # Exponential backoff
                retry_count += 1
                continue
                
            # Tạo file lock
            with open(lock_path, 'w') as lock_file:
                lock_file.write(str(os.getpid()))
                
            try:
                # Kiểm tra xem file có tồn tại không
                if not os.path.exists(file_path):
                    logger.debug(f"File {file_path} không tồn tại")
                    return None
                    
                # Kiểm tra kích thước file
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    logger.debug(f"File {file_path} trống, thử lại sau {backoff}s")
                    time.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                    retry_count += 1
                    continue
                
                # Đọc file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    return content
                    
            finally:
                # Luôn xóa file lock khi hoàn thành
                if os.path.exists(lock_path):
                    os.remove(lock_path)
                    
        except json.JSONDecodeError:
            logger.error(f"Lỗi parse JSON từ file {file_path}")
            if os.path.exists(lock_path):
                os.remove(lock_path)
            time.sleep(backoff)
            backoff *= 2
            retry_count += 1
            
        except Exception as e:
            logger.error(f"Lỗi khi đọc file {file_path}: {e}")
            if os.path.exists(lock_path):
                os.remove(lock_path)
            time.sleep(backoff)
            backoff *= 2
            retry_count += 1
    
    logger.error(f"Không thể đọc file {file_path} sau {max_retries} lần thử")
    return None


def write_file_with_lock(file_path: Union[str, Path], 
                       data: Dict[str, Any],
                       max_retries: int = 5, 
                       initial_backoff: float = 0.1) -> bool:
    """
    Ghi file JSON với file locking và exponential backoff
    
    Args:
        file_path: Đường dẫn đến file
        data: Dữ liệu cần ghi
        max_retries: Số lần thử tối đa
        initial_backoff: Thời gian chờ ban đầu (giây)
        
    Returns:
        True nếu ghi thành công, False nếu có lỗi
    """
    file_path = Path(file_path)
    retry_count = 0
    backoff = initial_backoff
    lock_path = str(file_path) + ".lock"
    
    # Đảm bảo thư mục tồn tại
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    while retry_count < max_retries:
        try:
            # Kiểm tra xem file lock có tồn tại không
            if os.path.exists(lock_path):
                logger.debug(f"File {file_path} đang bị khóa, thử lại sau {backoff}s")
                time.sleep(backoff)
                backoff *= 2  # Exponential backoff
                retry_count += 1
                continue
                
            # Tạo file lock
            with open(lock_path, 'w') as lock_file:
                lock_file.write(str(os.getpid()))
                
            try:
                # Ghi file tạm
                temp_path = str(file_path) + ".tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Đảm bảo dữ liệu được ghi xuống đĩa
                
                # Rename file tạm thành file chính (atomic operation)
                if os.path.exists(file_path):
                    os.remove(file_path)
                os.rename(temp_path, file_path)
                
                logger.debug(f"Đã ghi thành công vào file {file_path}")
                return True
                    
            finally:
                # Luôn xóa file lock khi hoàn thành
                if os.path.exists(lock_path):
                    os.remove(lock_path)
                    
        except Exception as e:
            logger.error(f"Lỗi khi ghi file {file_path}: {e}")
            if os.path.exists(lock_path):
                os.remove(lock_path)
            time.sleep(backoff)
            backoff *= 2
            retry_count += 1
    
    logger.error(f"Không thể ghi file {file_path} sau {max_retries} lần thử")
    return False 