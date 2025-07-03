#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Name Extractor for Test Case Manager v3.0

This module provides robust test name extraction with comprehensive fallback mechanisms
to prevent "unknown" test names from appearing in the queue system.

Author: juno-kyojin
Created: 2025-07-03
"""

import re
import logging
from typing import Dict, Any, Optional, Union


class TestNameExtractor:
    """
    Robust test name extraction with multiple fallback strategies.

    This class ensures that test names are always extracted correctly,
    preventing intermittent "unknown" test name issues.
    """

    logger = logging.getLogger(__name__)
    
    @staticmethod
    def extract_test_name(test_data: Dict[str, Any], template_name: Optional[str] = None) -> str:
        """
        Extract test name from test data with comprehensive fallback logic.
        
        Args:
            test_data: Test case data dictionary
            template_name: Optional template name as fallback
            
        Returns:
            Extracted test name (never returns "unknown" or empty string)
        """
        # Strategy 1: Try metadata.name field
        name = TestNameExtractor._extract_from_metadata_name(test_data)
        if name:
            TestNameExtractor.logger.debug(f"Extracted name from metadata.name: {name}")
            return name

        # Strategy 2: Try metadata.display_name field
        name = TestNameExtractor._extract_from_metadata_display_name(test_data)
        if name:
            TestNameExtractor.logger.debug(f"Extracted name from metadata.display_name: {name}")
            return name

        # Strategy 3: Try metadata.test_id field
        name = TestNameExtractor._extract_from_metadata_test_id(test_data)
        if name:
            TestNameExtractor.logger.debug(f"Extracted name from metadata.test_id: {name}")
            return name

        # Strategy 4: Generate from service + action
        name = TestNameExtractor._extract_from_service_action(test_data)
        if name:
            TestNameExtractor.logger.debug(f"Extracted name from service+action: {name}")
            return name

        # Strategy 5: Use template name if provided
        name = TestNameExtractor._extract_from_template_name(template_name)
        if name:
            TestNameExtractor.logger.debug(f"Extracted name from template_name: {name}")
            return name

        # Strategy 6: Generate from test_cases structure
        name = TestNameExtractor._extract_from_test_cases(test_data)
        if name:
            TestNameExtractor.logger.debug(f"Extracted name from test_cases: {name}")
            return name

        # Final fallback: Generate a descriptive name
        fallback_name = TestNameExtractor._generate_fallback_name(test_data)
        TestNameExtractor.logger.warning(f"Using fallback name: {fallback_name} for test_data: {test_data}")
        return fallback_name
    
    @staticmethod
    def _extract_from_metadata_name(test_data: Dict[str, Any]) -> Optional[str]:
        """Extract name from metadata.name field."""
        try:
            if not isinstance(test_data, dict):
                return None
                
            metadata = test_data.get("metadata")
            if not isinstance(metadata, dict):
                return None
                
            name = metadata.get("name")
            return TestNameExtractor._validate_name(name)
        except Exception:
            return None
    
    @staticmethod
    def _extract_from_metadata_display_name(test_data: Dict[str, Any]) -> Optional[str]:
        """Extract name from metadata.display_name field."""
        try:
            if not isinstance(test_data, dict):
                return None
                
            metadata = test_data.get("metadata")
            if not isinstance(metadata, dict):
                return None
                
            name = metadata.get("display_name")
            return TestNameExtractor._validate_name(name)
        except Exception:
            return None
    
    @staticmethod
    def _extract_from_metadata_test_id(test_data: Dict[str, Any]) -> Optional[str]:
        """Extract name from metadata.test_id field."""
        try:
            if not isinstance(test_data, dict):
                return None
                
            metadata = test_data.get("metadata")
            if not isinstance(metadata, dict):
                return None
                
            test_id = metadata.get("test_id")
            if TestNameExtractor._validate_name(test_id):
                # Convert test_id to readable format
                return TestNameExtractor._format_test_id(test_id)
        except Exception:
            return None
    
    @staticmethod
    def _extract_from_service_action(test_data: Dict[str, Any]) -> Optional[str]:
        """Extract name from direct service + action fields."""
        try:
            if not isinstance(test_data, dict):
                return None
                
            service = test_data.get("service")
            action = test_data.get("action")
            method = test_data.get("method")  # Alternative to action
            
            # Try service + action
            if service and action:
                service_str = TestNameExtractor._validate_name(str(service))
                action_str = TestNameExtractor._validate_name(str(action))
                if service_str and action_str:
                    return f"{service_str.title()} {action_str.title()}"
            
            # Try service + method
            if service and method:
                service_str = TestNameExtractor._validate_name(str(service))
                method_str = TestNameExtractor._validate_name(str(method))
                if service_str and method_str:
                    return f"{service_str.title()} {method_str.title()}"
                    
            # Try just service
            if service:
                service_str = TestNameExtractor._validate_name(str(service))
                if service_str:
                    return f"{service_str.title()} Test"
                    
        except Exception:
            return None
    
    @staticmethod
    def _extract_from_template_name(template_name: Optional[str]) -> Optional[str]:
        """Extract name from template filename."""
        try:
            if not template_name:
                return None
                
            # Remove .json extension if present
            name = template_name
            if name.endswith('.json'):
                name = name[:-5]
                
            # Validate and format
            if TestNameExtractor._validate_name(name):
                return TestNameExtractor._format_test_id(name)
                
        except Exception:
            return None
    
    @staticmethod
    def _extract_from_test_cases(test_data: Dict[str, Any]) -> Optional[str]:
        """Extract name from test_cases array structure."""
        try:
            if not isinstance(test_data, dict):
                return None
                
            test_cases = test_data.get("test_cases")
            if not isinstance(test_cases, list) or not test_cases:
                return None
                
            first_test = test_cases[0]
            if not isinstance(first_test, dict):
                return None
                
            service = first_test.get("service")
            action = first_test.get("action")
            method = first_test.get("method")
            
            # Try service + action
            if service and action:
                service_str = TestNameExtractor._validate_name(str(service))
                action_str = TestNameExtractor._validate_name(str(action))
                if service_str and action_str:
                    return f"{service_str.title()} {action_str.title()}"
            
            # Try service + method
            if service and method:
                service_str = TestNameExtractor._validate_name(str(service))
                method_str = TestNameExtractor._validate_name(str(method))
                if service_str and method_str:
                    return f"{service_str.title()} {method_str.title()}"
                    
            # Try just service
            if service:
                service_str = TestNameExtractor._validate_name(str(service))
                if service_str:
                    return f"{service_str.title()} Test"
                    
        except Exception:
            return None
    
    @staticmethod
    def _generate_fallback_name(test_data: Dict[str, Any]) -> str:
        """Generate a fallback name when all other strategies fail."""
        try:
            # Try to find any meaningful field
            if isinstance(test_data, dict):
                # Look for any field that might indicate test type
                for key in ["type", "category", "kind", "test_type"]:
                    value = test_data.get(key)
                    if TestNameExtractor._validate_name(str(value)):
                        return f"{str(value).title()} Test"
                
                # Check if there are test_cases
                test_cases = test_data.get("test_cases")
                if isinstance(test_cases, list) and test_cases:
                    return f"Test Case ({len(test_cases)} steps)"
                    
                # Check for any service-like fields
                for key in test_data.keys():
                    if "service" in key.lower() or "action" in key.lower():
                        value = test_data.get(key)
                        if TestNameExtractor._validate_name(str(value)):
                            return f"{str(value).title()} Test"
            
            # Ultimate fallback
            return "Custom Test Case"
            
        except Exception:
            return "Test Case"
    
    @staticmethod
    def _validate_name(name: Any) -> Optional[str]:
        """
        Validate that a name is usable (not None, empty, or whitespace-only).
        
        Args:
            name: Name to validate
            
        Returns:
            Cleaned name string if valid, None otherwise
        """
        try:
            if name is None:
                return None
                
            # Convert to string and strip whitespace
            name_str = str(name).strip()
            
            # Check if empty or whitespace-only
            if not name_str:
                return None
                
            # Check for common "unknown" variants
            if name_str.lower() in ["unknown", "none", "null", "undefined", ""]:
                return None
                
            # Check for very short names (likely not meaningful)
            if len(name_str) < 2:
                return None
                
            return name_str
            
        except Exception:
            return None
    
    @staticmethod
    def _format_test_id(test_id: str) -> str:
        """
        Format a test_id into a readable display name.
        
        Args:
            test_id: Test identifier (e.g., "wireless_config_ap")
            
        Returns:
            Formatted display name (e.g., "Wireless Config Ap")
        """
        try:
            # Split by underscores and hyphens
            parts = re.split(r'[_\-]', test_id)
            
            # Capitalize each part
            capitalized_parts = []
            for part in parts:
                if part:  # Skip empty parts
                    capitalized_parts.append(part.title())
            
            # Join with spaces
            if capitalized_parts:
                return " ".join(capitalized_parts)
            else:
                return test_id.title()
                
        except Exception:
            return test_id


# Convenience function for backward compatibility
def extract_test_name(test_data: Dict[str, Any], template_name: Optional[str] = None) -> str:
    """
    Extract test name from test data with comprehensive fallback logic.
    
    Args:
        test_data: Test case data dictionary
        template_name: Optional template name as fallback
        
    Returns:
        Extracted test name (never returns "unknown" or empty string)
    """
    return TestNameExtractor.extract_test_name(test_data, template_name)
