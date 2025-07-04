#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Result Manager for Test Case Manager v1.0

This module handles test result operations including saving, loading,
and managing test execution results.

Author: juno-kyojin
Created: 2025-06-12
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union, Set

from .constants import TEMP_DIR
from .exceptions import FileOperationError


class ResultManager:
    """
    Manages test execution results.
    
    This class provides methods to work with test result files,
    including saving, loading, and analyzing test result data.
    """
    
    def __init__(self, results_dir: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize the result manager.
        
        Args:
            results_dir: Directory to store results.
                     If None, defaults to the standard temp/results directory.
        """
        if results_dir is None:
            self.results_dir = TEMP_DIR / "results"
        else:
            self.results_dir = Path(results_dir)
            
        self.logger = logging.getLogger(__name__)
        
        # Ensure directory exists
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize connection state
        self._connected = False
        
        self.logger.info(f"ResultManager initialized with results directory: {self.results_dir}")
    
    def is_connected(self) -> bool:
        """
        Check if the result manager is connected.
        
        Returns:
            Always returns True since the result manager doesn't 
            have a connection state in the traditional sense.
        """
        return self._connected
    
    def connect(self, *args, **kwargs) -> bool:
        """
        Simulate connecting to a result storage system. This method exists
        for compatibility with other components that expect a connect method.
        
        Returns:
            Always returns True as the result manager is always "connected"
            once initialized.
        """
        self._connected = True
        self.logger.info("ResultManager connected")
        return True
    
    def disconnect(self) -> None:
        """
        Simulate disconnecting from a result storage system. This method exists
        for compatibility with other components that expect a disconnect method.
        """
        self._connected = False
        self.logger.info("ResultManager disconnected")
    
    def save_result(self, test_id: str, status: str, result_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Save a test result to file.
        
        Args:
            test_id: Identifier for the test case
            status: Test execution status (success, fail, etc.)
            result_data: Test result data to save
            
        Returns:
            Tuple containing (success boolean, file path or error message)
        """
        try:
            # Kiểm tra xem kết quả thực sự có thành công hay không
            actual_status = status
            
            # Kiểm tra trong result_data có thông tin về thành công/thất bại không
            if "result_data" in result_data and isinstance(result_data["result_data"], dict):
                result_obj = result_data["result_data"]
                
                # Kiểm tra summary
                if "summary" in result_obj and isinstance(result_obj["summary"], dict):
                    summary = result_obj["summary"]
                    if "failed" in summary and summary["failed"] > 0:
                        self.logger.warning(f"Test {test_id} has failed tests in summary: {summary['failed']}")
                        actual_status = "fail"
                
                # Kiểm tra error
                if "error" in result_obj:
                    self.logger.warning(f"Test {test_id} has error: {result_obj['error']}")
                    actual_status = "fail"
                    
                # Kiểm tra failed_services
                if "failed_services" in result_obj and result_obj["failed_services"]:
                    self.logger.warning(f"Test {test_id} has failed services: {result_obj['failed_services']}")
                    actual_status = "fail"
                    
            # Cập nhật trạng thái trong metadata
            if actual_status != status:
                self.logger.warning(f"Correcting status from {status} to {actual_status} for test {test_id}")
                status = actual_status
                if "metadata" in result_data:
                    result_data["metadata"]["status"] = actual_status
            
            # Generate unique filename with test_id, status, and unique identifier
            unique_id = uuid.uuid4().hex[:8]  # 8 chars from UUID for uniqueness
            filename = f"{test_id}_{unique_id}_{status}.json"
            result_file = self.results_dir / filename
            
            # Add metadata to the results
            if "metadata" not in result_data:
                result_data["metadata"] = {}
                
            # Update result metadata
            result_data["metadata"]["test_id"] = test_id
            result_data["metadata"]["status"] = status
            result_data["metadata"]["timestamp"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            result_data["metadata"]["filename"] = filename
            
            # Save to file
            with result_file.open('w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Test result saved: {result_file}")
            return True, str(result_file)
            
        except Exception as e:
            self.logger.error(f"Error saving test result: {e}")
            return False, str(e)
    
    def load_result(self, result_file: Union[str, Path]) -> Dict[str, Any]:
        """
        Load a test result from file.

        Args:
            result_file: Path to the result file

        Returns:
            Dictionary containing the test result data

        Raises:
            FileOperationError: If file cannot be read or contains invalid JSON
        """
        # Initialize file_path outside try block to ensure it's always bound
        file_path = Path(result_file)

        try:
            if not file_path.exists():
                raise FileOperationError(
                    f"Result file not found: {file_path}",
                    str(file_path),
                    "read"
                )

            with file_path.open('r', encoding='utf-8') as f:
                return json.load(f)

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error in {file_path}: {str(e)}")
            raise FileOperationError(
                f"Invalid JSON in result file: {e}",
                str(file_path),
                "read"
            )
        except FileOperationError:
            raise
        except Exception as e:
            self.logger.error(f"Error loading result file {file_path}: {str(e)}")
            raise FileOperationError(
                f"Error loading result file: {e}",
                str(file_path),
                "read"
            )
    
    def get_results(self, test_id: Optional[str] = None, 
                    status: Optional[str] = None, 
                    limit: int = 100,
                    sort_by_date: bool = True,
                    reverse: bool = True) -> List[Dict[str, Any]]:
        """
        Get test results, optionally filtered by test_id and status.
        
        Args:
            test_id: Filter by test ID (optional)
            status: Filter by status (optional)
            limit: Maximum number of results to return
            sort_by_date: Whether to sort by date
            reverse: Sort in descending order if True
            
        Returns:
            List of dictionaries containing result file info
        """
        results = []
        try:
            # Generate glob pattern based on filters
            pattern = ""
            if test_id and status:
                pattern = f"{test_id}_*_{status}.json"
            elif test_id:
                pattern = f"{test_id}_*.json"
            elif status:
                pattern = f"*_{status}.json"
            else:
                pattern = "*.json"
            
            # Find matching files
            matching_files = list(self.results_dir.glob(pattern))
            
            # Sort by modification time if requested
            if sort_by_date:
                matching_files.sort(key=lambda x: x.stat().st_mtime, reverse=reverse)
            
            # Limit number of results
            matching_files = matching_files[:limit]
            
            # Process each file
            for result_file in matching_files:
                try:
                    # Extract basic info from filename
                    file_parts = result_file.stem.split('_')
                    file_test_id = file_parts[0] if len(file_parts) > 0 else "unknown"
                    file_status = file_parts[-1] if len(file_parts) > 2 else "unknown"
                    
                    # Get file stats
                    file_stats = result_file.stat()
                    mod_time = datetime.fromtimestamp(file_stats.st_mtime)
                    file_size = file_stats.st_size
                    
                    # Get metadata from file if possible
                    metadata = {}
                    try:
                        with result_file.open('r', encoding='utf-8') as f:
                            data = json.load(f)
                            metadata = data.get("metadata", {})
                    except Exception:
                        # Skip metadata if can't read
                        pass
                    
                    # Create result entry
                    result_info = {
                        "test_id": file_test_id,
                        "status": file_status,
                        "file_path": str(result_file),
                        "file_size": file_size,
                        "date": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "metadata": metadata
                    }
                    
                    results.append(result_info)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing result file {result_file}: {e}")
                    # Skip problematic files
                    continue
                    
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting test results: {e}")
            return []
    
    def delete_result(self, result_file: Union[str, Path]) -> bool:
        """
        Delete a test result file.
        
        Args:
            result_file: Path to the result file
            
        Returns:
            True if file was deleted, False otherwise
        """
        try:
            file_path = Path(result_file)
            if not file_path.exists():
                self.logger.warning(f"Result file not found: {file_path}")
                return False
                
            file_path.unlink()
            self.logger.info(f"Result file deleted: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting result file {result_file}: {e}")
            return False
    
    def cleanup_old_results(self, days: int = 30) -> int:
        """
        Clean up old result files.
        
        Args:
            days: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        count = 0
        try:
            # Calculate cutoff time
            now = datetime.now()
            cutoff = now.timestamp() - (days * 24 * 60 * 60)  # days in seconds
            
            # Find old files
            for result_file in self.results_dir.glob("*.json"):
                try:
                    # Check file modification time
                    mtime = result_file.stat().st_mtime
                    if mtime < cutoff:
                        result_file.unlink()
                        count += 1
                except Exception as e:
                    self.logger.warning(f"Error processing file {result_file}: {e}")
                    continue
                    
            self.logger.info(f"Cleanup completed: {count} files deleted")
            return count
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return count
    
    def get_test_statistics(self, timeframe_days: int = 7) -> Dict[str, Any]:
        """
        Get statistics about test executions.
        
        Args:
            timeframe_days: Number of days to analyze
            
        Returns:
            Dictionary containing statistics
        """
        try:
            # Calculate cutoff time
            now = datetime.now()
            cutoff = now.timestamp() - (timeframe_days * 24 * 60 * 60)
            
            # Initialize counters
            total_tests = 0
            successful_tests = 0
            failed_tests = 0
            test_types: Set[str] = set()
            test_counts: Dict[str, int] = {}
            
            # Process all result files within timeframe
            for result_file in self.results_dir.glob("*.json"):
                try:
                    # Skip if file is too old
                    mtime = result_file.stat().st_mtime
                    if mtime < cutoff:
                        continue
                        
                    # Get basic info from filename
                    file_parts = result_file.stem.split('_')
                    file_test_id = file_parts[0] if len(file_parts) > 0 else "unknown"
                    file_status = file_parts[-1] if len(file_parts) > 2 else "unknown"
                    
                    # Update counters
                    total_tests += 1
                    test_types.add(file_test_id)
                    test_counts[file_test_id] = test_counts.get(file_test_id, 0) + 1
                    
                    if file_status.lower() == "success":
                        successful_tests += 1
                    else:
                        failed_tests += 1
                
                except Exception:
                    # Skip problematic files
                    continue
            
            # Calculate success rate
            success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
            
            # Build statistics
            stats = {
                "timeframe_days": timeframe_days,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": round(success_rate, 2),
                "unique_test_types": len(test_types),
                "test_counts": test_counts
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {e}")
            return {
                "error": str(e),
                "timeframe_days": timeframe_days,
                "total_tests": 0,
                "successful_tests": 0,
                "failed_tests": 0,
                "success_rate": 0,
                "unique_test_types": 0
            } 