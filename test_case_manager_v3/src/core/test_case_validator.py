#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Case Validator for Test Case Manager v3.0

This module provides functionality for validating test cases and defining
client-side verification rules. It allows users to define custom verification
rules for test cases without modifying the core application code.

Author: juno-kyojin
Created: 2025-06-30
"""

import os
import json
import re
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Callable, Union, Set

from ..utils.logger import get_logger
from .exceptions import ValidationError


class TestCaseValidator:
    """
    Test case validator for validating test cases against rules.
    
    This class provides functionality for validating test cases against
    predefined rules and custom verification functions. It allows users
    to define custom verification rules without modifying the core
    application code.
    """
    
    def __init__(self, validators_dir: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize the test case validator.
        
        Args:
            validators_dir: Directory containing custom validators.
                           If None, defaults to 'validators' in the current directory.
        """
        self.logger = get_logger(__name__)
        
        # Set validators directory
        if validators_dir is None:
            base_dir = Path(__file__).parent.parent.parent
            self.validators_dir = base_dir / "validators"
        else:
            self.validators_dir = Path(validators_dir)
        
        # Create validators directory if it doesn't exist
        self.validators_dir.mkdir(parents=True, exist_ok=True)
        
        # Dictionary to store loaded validators
        self.validators: Dict[str, Dict[str, Callable]] = {}
        
        # Load validators
        self._load_validators()
        
    def _load_validators(self) -> None:
        """
        Load validators from the validators directory.
        
        This method scans the validators directory for Python files and loads
        validator functions from them. Validator functions must follow the naming
        convention 'validate_*' and have the signature:
        
        validate_*(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]
        """
        if not self.validators_dir.exists():
            self.logger.warning(f"Validators directory not found: {self.validators_dir}")
            return
        
        # Clear existing validators
        self.validators = {}
        
        # Scan for Python files in validators directory
        for file_path in self.validators_dir.glob("*.py"):
            try:
                # Load module
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    self.logger.warning(f"Could not load validator module: {file_path}")
                    continue
                    
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find validator functions
                category_validators = {}
                for name, obj in inspect.getmembers(module):
                    if name.startswith("validate_") and inspect.isfunction(obj):
                        validator_name = name[9:]  # Remove 'validate_' prefix
                        category_validators[validator_name] = obj
                
                if category_validators:
                    self.validators[module_name] = category_validators
                    self.logger.info(f"Loaded {len(category_validators)} validators from {module_name}")
                else:
                    self.logger.warning(f"No validators found in {module_name}")
                
            except Exception as e:
                self.logger.error(f"Error loading validator module {file_path}: {e}")
    
    def validate_test_case(self, test_data: Dict[str, Any], 
                          result_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a test case against rules.
        
        Args:
            test_data: Test case data
            result_data: Test result data
            
        Returns:
            Tuple containing (success boolean, list of error messages)
        """
        errors = []
        
        # Skip validation if no validators are loaded
        if not self.validators:
            return True, []
        
        # Extract service and action from test data
        service = None
        action = None
        
        if "test_cases" in test_data and test_data["test_cases"]:
            first_test = test_data["test_cases"][0]
            service = first_test.get("service", "").lower()
            action = first_test.get("action", "").lower()
        elif "service" in test_data:
            service = test_data.get("service", "").lower()
            action = test_data.get("action", "").lower()
        
        if not service:
            errors.append("No service specified in test data")
            return False, errors
        
        # Run general validators first (from 'common' module)
        if "common" in self.validators:
            for name, validator in self.validators["common"].items():
                try:
                    valid, message = validator(test_data, result_data)
                    if not valid:
                        errors.append(f"Common validator '{name}' failed: {message}")
                except Exception as e:
                    self.logger.error(f"Error in common validator '{name}': {e}")
                    errors.append(f"Error in common validator '{name}': {str(e)}")
        
        # Run service-specific validators
        if service in self.validators:
            for name, validator in self.validators[service].items():
                # Skip if validator is not for this action
                if action and name != action and not name.startswith(f"{action}_"):
                    continue
                    
                try:
                    valid, message = validator(test_data, result_data)
                    if not valid:
                        errors.append(f"Validator '{service}.{name}' failed: {message}")
                except Exception as e:
                    self.logger.error(f"Error in validator '{service}.{name}': {e}")
                    errors.append(f"Error in validator '{service}.{name}': {str(e)}")
        
        # Check if any errors were found
        return len(errors) == 0, errors
    
    def get_available_validators(self) -> Dict[str, List[str]]:
        """
        Get available validators by category.
        
        Returns:
            Dictionary mapping categories to lists of validator names
        """
        result = {}
        for category, validators in self.validators.items():
            result[category] = list(validators.keys())
        return result
    
    def reload_validators(self) -> int:
        """
        Reload validators from the validators directory.
        
        Returns:
            Number of validators loaded
        """
        self._load_validators()
        
        # Count total validators
        count = 0
        for category in self.validators.values():
            count += len(category)
        
        return count
    
    def create_validator_template(self, service: str, action: str) -> Tuple[bool, str]:
        """
        Create a validator template file for a service and action.
        
        Args:
            service: Service name
            action: Action name
            
        Returns:
            Tuple containing (success boolean, message)
        """
        try:
            # Create validators directory if it doesn't exist
            self.validators_dir.mkdir(parents=True, exist_ok=True)
            
            # Create file path
            file_path = self.validators_dir / f"{service}.py"
            
            # Check if file already exists
            if file_path.exists():
                # Read existing file
                with file_path.open('r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if validator already exists
                validator_name = f"validate_{action}"
                if f"def {validator_name}" in content:
                    return False, f"Validator for {service}.{action} already exists"
                
                # Append new validator
                with file_path.open('a', encoding='utf-8') as f:
                    f.write("\n\n")
                    f.write(f"def validate_{action}(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:\n")
                    f.write(f"    \"\"\"\n")
                    f.write(f"    Validate {service} {action} test case.\n")
                    f.write(f"    \n")
                    f.write(f"    Args:\n")
                    f.write(f"        test_data: Test case data\n")
                    f.write(f"        result_data: Test result data\n")
                    f.write(f"    \n")
                    f.write(f"    Returns:\n")
                    f.write(f"        Tuple containing (success boolean, message)\n")
                    f.write(f"    \"\"\"\n")
                    f.write(f"    # TODO: Implement validation logic\n")
                    f.write(f"    return True, \"\"\n")
            else:
                # Create new file
                with file_path.open('w', encoding='utf-8') as f:
                    f.write("#!/usr/bin/env python3\n")
                    f.write("# -*- coding: utf-8 -*-\n\n")
                    f.write(f"\"\"\"\n")
                    f.write(f"Validators for {service} service.\n")
                    f.write(f"\n")
                    f.write(f"This module provides validation functions for {service} test cases.\n")
                    f.write(f"\"\"\"\n\n")
                    f.write("from typing import Dict, Any, Tuple\n\n")
                    f.write(f"def validate_{action}(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:\n")
                    f.write(f"    \"\"\"\n")
                    f.write(f"    Validate {service} {action} test case.\n")
                    f.write(f"    \n")
                    f.write(f"    Args:\n")
                    f.write(f"        test_data: Test case data\n")
                    f.write(f"        result_data: Test result data\n")
                    f.write(f"    \n")
                    f.write(f"    Returns:\n")
                    f.write(f"        Tuple containing (success boolean, message)\n")
                    f.write(f"    \"\"\"\n")
                    f.write(f"    # TODO: Implement validation logic\n")
                    f.write(f"    return True, \"\"\n")
            
            # Reload validators
            self._load_validators()
            
            return True, f"Validator template created for {service}.{action}"
            
        except Exception as e:
            self.logger.error(f"Error creating validator template: {e}")
            return False, f"Error creating validator template: {str(e)}"


# Create a common validator template file if it doesn't exist
def create_common_validators(validators_dir: Path) -> None:
    """
    Create a common validators file if it doesn't exist.
    
    Args:
        validators_dir: Directory to create the file in
    """
    try:
        # Create validators directory if it doesn't exist
        validators_dir.mkdir(parents=True, exist_ok=True)
        
        # Create file path
        file_path = validators_dir / "common.py"
        
        # Check if file already exists
        if file_path.exists():
            return
        
        # Create new file
        with file_path.open('w', encoding='utf-8') as f:
            f.write("#!/usr/bin/env python3\n")
            f.write("# -*- coding: utf-8 -*-\n\n")
            f.write("\"\"\"\n")
            f.write("Common validators for all test cases.\n")
            f.write("\n")
            f.write("This module provides common validation functions that apply to all test cases.\n")
            f.write("\"\"\"\n\n")
            f.write("from typing import Dict, Any, Tuple\n\n")
            f.write("def validate_result_structure(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:\n")
            f.write("    \"\"\"\n")
            f.write("    Validate result data has the correct structure.\n")
            f.write("    \n")
            f.write("    Args:\n")
            f.write("        test_data: Test case data\n")
            f.write("        result_data: Test result data\n")
            f.write("    \n")
            f.write("    Returns:\n")
            f.write("        Tuple containing (success boolean, message)\n")
            f.write("    \"\"\"\n")
            f.write("    if not result_data:\n")
            f.write("        return False, \"Result data is empty\"\n")
            f.write("    \n")
            f.write("    if \"summary\" not in result_data:\n")
            f.write("        return False, \"Result data missing 'summary' field\"\n")
            f.write("    \n")
            f.write("    summary = result_data[\"summary\"]\n")
            f.write("    if \"total_test_cases\" not in summary:\n")
            f.write("        return False, \"Summary missing 'total_test_cases' field\"\n")
            f.write("    \n")
            f.write("    if \"passed\" not in summary:\n")
            f.write("        return False, \"Summary missing 'passed' field\"\n")
            f.write("    \n")
            f.write("    if \"failed\" not in summary:\n")
            f.write("        return False, \"Summary missing 'failed' field\"\n")
            f.write("    \n")
            f.write("    return True, \"\"\n\n")
            f.write("def validate_client_verification(test_data: Dict[str, Any], result_data: Dict[str, Any]) -> Tuple[bool, str]:\n")
            f.write("    \"\"\"\n")
            f.write("    Validate client verification was performed.\n")
            f.write("    \n")
            f.write("    Args:\n")
            f.write("        test_data: Test case data\n")
            f.write("        result_data: Test result data\n")
            f.write("    \n")
            f.write("    Returns:\n")
            f.write("        Tuple containing (success boolean, message)\n")
            f.write("    \"\"\"\n")
            f.write("    # Check if client verification is present\n")
            f.write("    if \"client_verification\" not in result_data:\n")
            f.write("        return False, \"Client verification not performed\"\n")
            f.write("    \n")
            f.write("    # Check if client verification was successful\n")
            f.write("    client_verification = result_data[\"client_verification\"]\n")
            f.write("    if not client_verification.get(\"status\", False):\n")
            f.write("        return False, f\"Client verification failed: {client_verification.get('message', 'Unknown error')}\"\n")
            f.write("    \n")
            f.write("    return True, \"\"\n")
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Error creating common validators file: {e}")


# Create common validators file when module is imported
if __name__ != "__main__":
    base_dir = Path(__file__).parent.parent.parent
    validators_dir = base_dir / "validators"
    create_common_validators(validators_dir) 