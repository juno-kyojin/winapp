"""
Test Case Preset Management Module

This module provides functionality for managing test case presets, including
saving, loading, and applying collections of test cases for quick selection.

Author: Test Case Manager
Date: 2024-08-01
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from src.utils.file_utils import read_json_file, write_json_file, ensure_directory
from src.core.exceptions import FileOperationError, ValidationError


class PresetManager:
    """
    Manages test case presets with JSON persistence.
    
    Provides functionality to create, load, save, delete, and validate
    test case presets stored in JSON format.
    """
    
    def __init__(self, config_dir: Path) -> None:
        """
        Initialize PresetManager.
        
        Args:
            config_dir: Directory where preset files are stored
        """
        self.config_dir = Path(config_dir)
        self.presets_file = self.config_dir / "presets.json"
        self.backup_file = self.config_dir.parent / "backup" / "presets_backup.json"
        self.presets: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
        
        # Ensure directories exist
        ensure_directory(self.config_dir)
        ensure_directory(self.backup_file.parent)
        
        # Load presets on initialization
        self.load_presets()
    
    def load_presets(self) -> bool:
        """
        Load presets from JSON file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not self.presets_file.exists():
                # Create empty presets file
                self._create_empty_presets_file()
                return True
            
            data = read_json_file(self.presets_file)
            
            # Validate JSON structure
            if not isinstance(data, dict) or "presets" not in data:
                self.logger.warning("Invalid presets file structure, creating new file")
                self._create_empty_presets_file()
                return True
            
            self.presets = data.get("presets", [])
            
            # Validate each preset
            valid_presets = []
            for preset in self.presets:
                if self._validate_preset_structure(preset):
                    valid_presets.append(preset)
                else:
                    self.logger.warning(f"Invalid preset structure: {preset.get('name', 'Unknown')}")
            
            self.presets = valid_presets
            self.logger.info(f"Loaded {len(self.presets)} presets successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading presets: {e}")
            # Try to load from backup
            return self._load_from_backup()
    
    def save_presets(self) -> bool:
        """
        Save presets to JSON file with backup.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Create backup before saving
            if self.presets_file.exists():
                self._create_backup()
            
            # Prepare data structure
            data = {
                "presets": self.presets,
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
            
            # Save to file
            write_json_file(self.presets_file, data, indent=2)
            self.logger.info(f"Saved {len(self.presets)} presets successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving presets: {e}")
            return False
    
    def create_preset(self, name: str, description: str, test_ids: List[str]) -> str:
        """
        Create a new preset.
        
        Args:
            name: Preset name
            description: Preset description
            test_ids: List of test IDs to include
            
        Returns:
            Preset ID if created successfully
            
        Raises:
            ValidationError: If preset name is invalid or already exists
        """
        # Validate inputs
        if not self._validate_preset_name(name):
            raise ValidationError(f"Invalid preset name: {name}")
        
        if self._preset_name_exists(name):
            raise ValidationError(f"Preset name already exists: {name}")
        
        if not test_ids:
            raise ValidationError("Preset must contain at least one test case")
        
        # Create preset
        preset_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat() + "Z"
        
        preset = {
            "id": preset_id,
            "name": name.strip(),
            "description": description.strip(),
            "test_ids": list(set(test_ids)),  # Remove duplicates
            "created_date": current_time,
            "modified_date": current_time,
            "test_count": len(set(test_ids))
        }
        
        self.presets.append(preset)
        
        # Save to file
        if self.save_presets():
            self.logger.info(f"Created preset: {name} with {len(test_ids)} tests")
            return preset_id
        else:
            # Remove from memory if save failed
            self.presets.remove(preset)
            raise FileOperationError("Failed to save preset to file", str(self.presets_file), "write")
    
    def delete_preset(self, preset_id: str) -> bool:
        """
        Delete a preset by ID.
        
        Args:
            preset_id: ID of preset to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            preset = self.get_preset_by_id(preset_id)
            if not preset:
                self.logger.warning(f"Preset not found for deletion: {preset_id}")
                return False
            
            self.presets = [p for p in self.presets if p["id"] != preset_id]
            
            if self.save_presets():
                self.logger.info(f"Deleted preset: {preset['name']}")
                return True
            else:
                self.logger.error(f"Failed to save after deleting preset: {preset_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting preset {preset_id}: {e}")
            return False

    def rename_preset(self, preset_id: str, new_name: str) -> bool:
        """
        Rename a preset.

        Args:
            preset_id: ID of preset to rename
            new_name: New name for the preset

        Returns:
            True if renamed successfully, False otherwise

        Raises:
            ValidationError: If new name is invalid or already exists
        """
        if not self._validate_preset_name(new_name):
            raise ValidationError(f"Invalid preset name: {new_name}")

        if self._preset_name_exists(new_name, exclude_id=preset_id):
            raise ValidationError(f"Preset name already exists: {new_name}")

        preset = self.get_preset_by_id(preset_id)
        if not preset:
            return False

        preset["name"] = new_name.strip()
        preset["modified_date"] = datetime.utcnow().isoformat() + "Z"

        if self.save_presets():
            self.logger.info(f"Renamed preset {preset_id} to: {new_name}")
            return True
        else:
            return False

    def update_preset_description(self, preset_id: str, new_description: str) -> bool:
        """
        Update preset description.

        Args:
            preset_id: ID of preset to update
            new_description: New description for the preset

        Returns:
            True if updated successfully, False otherwise
        """
        preset = self.get_preset_by_id(preset_id)
        if not preset:
            return False

        preset["description"] = new_description.strip()
        preset["modified_date"] = datetime.utcnow().isoformat() + "Z"

        if self.save_presets():
            self.logger.info(f"Updated description for preset {preset_id}")
            return True
        else:
            return False

    def get_preset_by_id(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get preset by ID.
        
        Args:
            preset_id: Preset ID to search for
            
        Returns:
            Preset dictionary or None if not found
        """
        for preset in self.presets:
            if preset.get("id") == preset_id:
                return preset
        return None
    
    def get_preset_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get preset by name.
        
        Args:
            name: Preset name to search for
            
        Returns:
            Preset dictionary or None if not found
        """
        for preset in self.presets:
            if preset.get("name", "").lower() == name.lower():
                return preset
        return None
    
    def get_all_presets(self) -> List[Dict[str, Any]]:
        """
        Get all presets.
        
        Returns:
            List of all preset dictionaries
        """
        return self.presets.copy()
    
    def get_preset_names(self) -> List[str]:
        """
        Get list of all preset names.
        
        Returns:
            List of preset names
        """
        return [preset.get("name", "") for preset in self.presets]
    
    def validate_preset_tests(self, test_ids: List[str], available_test_ids: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate which test IDs from a preset are still available.
        
        Args:
            test_ids: Test IDs from preset
            available_test_ids: Currently available test IDs
            
        Returns:
            Tuple of (valid_test_ids, missing_test_ids)
        """
        available_set = set(available_test_ids)
        valid_tests = []
        missing_tests = []
        
        for test_id in test_ids:
            if test_id in available_set:
                valid_tests.append(test_id)
            else:
                missing_tests.append(test_id)
        
        return valid_tests, missing_tests
    
    def _validate_preset_name(self, name: str) -> bool:
        """Validate preset name format."""
        if not name or not isinstance(name, str):
            return False
        
        name = name.strip()
        if len(name) < 1 or len(name) > 100:
            return False
        
        # Check for invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
        if any(char in name for char in invalid_chars):
            return False
        
        return True
    
    def _preset_name_exists(self, name: str, exclude_id: str = None) -> bool:
        """Check if preset name already exists."""
        name_lower = name.lower().strip()
        for preset in self.presets:
            if exclude_id and preset.get("id") == exclude_id:
                continue
            if preset.get("name", "").lower() == name_lower:
                return True
        return False
    
    def _validate_preset_structure(self, preset: Dict[str, Any]) -> bool:
        """Validate preset dictionary structure."""
        required_fields = ["id", "name", "test_ids", "created_date"]
        
        for field in required_fields:
            if field not in preset:
                return False
        
        if not isinstance(preset["test_ids"], list):
            return False
        
        return True
    
    def _create_empty_presets_file(self) -> None:
        """Create empty presets file with proper structure."""
        data = {
            "presets": [],
            "version": "1.0",
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
        write_json_file(self.presets_file, data, indent=2)
        self.presets = []
    
    def _create_backup(self) -> bool:
        """Create backup of current presets file."""
        try:
            if self.presets_file.exists():
                import shutil
                shutil.copy2(self.presets_file, self.backup_file)
                return True
        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")
        return False
    
    def _load_from_backup(self) -> bool:
        """Load presets from backup file."""
        try:
            if self.backup_file.exists():
                data = read_json_file(self.backup_file)
                self.presets = data.get("presets", [])
                self.logger.info("Loaded presets from backup file")
                return True
        except Exception as e:
            self.logger.error(f"Failed to load from backup: {e}")
        
        # Create empty file as last resort
        self._create_empty_presets_file()
        return True
