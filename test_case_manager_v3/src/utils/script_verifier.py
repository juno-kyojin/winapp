#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Verifier for Test Case Manager v1.0

This module provides comprehensive script verification functionality for test cases
that require PC-side verification after device execution. Supports any script
in the ToolWL folder with standardized input/output interface.

Author: juno-kyojin
Created: 2025-07-08
"""

import subprocess
import sys
import os
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from .logger import get_logger


class ScriptVerifier:
    """
    Handles verification script execution for test cases.
    
    This class provides a generic framework for executing verification scripts
    located in the ToolWL folder. All scripts must follow the standardized
    interface:
    - Read input from ToolWL/input.txt (one parameter per line)
    - Write output to ToolWL/output.txt ("1" = pass, "0" = fail)
    """

    def __init__(self, toolwl_path: Optional[str] = None):
        """
        Initialize the script verifier.
        
        Args:
            toolwl_path: Optional custom path to ToolWL directory
        """
        self.logger = get_logger(__name__)
        
        # Set ToolWL path
        if toolwl_path:
            self.toolwl_path = Path(toolwl_path)
        else:
            # Auto-detect ToolWL directory location
            self.toolwl_path = self._find_toolwl_directory()
        
        self.logger.debug(f"ToolWL path: {self.toolwl_path}")
        
        # Verify ToolWL directory exists
        if not self.toolwl_path.exists():
            self.logger.warning(f"ToolWL directory not found: {self.toolwl_path}")

    def _find_toolwl_directory(self) -> Path:
        """
        Auto-detect ToolWL directory location.

        This method handles both development and built executable scenarios:
        - Development: ToolWL is relative to project root
        - Built executable: ToolWL is next to the .exe file

        Returns:
            Path to ToolWL directory
        """
        import sys

        # Method 1: Check if running from built executable
        if getattr(sys, 'frozen', False):
            # Running from PyInstaller executable
            # ToolWL should be next to the .exe file
            exe_dir = Path(sys.executable).parent
            toolwl_path = exe_dir / "ToolWL"
            if toolwl_path.exists():
                self.logger.debug(f"Found ToolWL in executable directory: {toolwl_path}")
                return toolwl_path

        # Method 2: Development mode - relative to project root
        project_root = Path(__file__).parent.parent.parent
        toolwl_path = project_root / "ToolWL"
        if toolwl_path.exists():
            self.logger.debug(f"Found ToolWL in project root: {toolwl_path}")
            return toolwl_path

        # Method 3: Check current working directory
        cwd_toolwl = Path.cwd() / "ToolWL"
        if cwd_toolwl.exists():
            self.logger.debug(f"Found ToolWL in current directory: {cwd_toolwl}")
            return cwd_toolwl

        # Method 4: Fallback to project root (even if doesn't exist)
        fallback_path = project_root / "ToolWL"
        self.logger.warning(f"ToolWL not found, using fallback: {fallback_path}")
        return fallback_path

    def should_run_verification(self, result_data: Optional[Dict[str, Any]]) -> bool:
        """
        Determine if verification script should be executed based on result data.
        
        Args:
            result_data: Response data from OpenWrt device
            
        Returns:
            True if verification is needed, False otherwise
        """
        if not result_data:
            self.logger.debug("No result data provided - no verification needed")
            return False

        try:
            summary = result_data.get("summary", {})
            if not isinstance(summary, dict):
                self.logger.debug("Summary is not a dictionary - no verification needed")
                return False

            script_field = summary.get("script")
            if not script_field:
                self.logger.debug("No script field found in summary - no verification needed")
                return False

            # Check for "none" value (string)
            if isinstance(script_field, str) and script_field.lower() == "none":
                self.logger.debug("Script field is 'none' - no verification needed")
                return False

            # Check for script object with cmd and input
            if isinstance(script_field, dict):
                if "cmd" in script_field and "input" in script_field:
                    self.logger.debug(f"Script verification required: {script_field['cmd']}")
                    return True
                else:
                    self.logger.warning(f"Script object missing required fields: {script_field}")
                    return False

            self.logger.warning(f"Unknown script field format: {script_field}")
            return False

        except Exception as e:
            self.logger.error(f"Error checking verification requirement: {e}")
            return False

    def extract_script_info(self, result_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[List[str]]]:
        """
        Extract script command and input parameters from result data.
        
        Args:
            result_data: Response data from OpenWrt device
            
        Returns:
            Tuple of (script_command, input_parameters) or (None, None) if extraction fails
        """
        try:
            summary = result_data.get("summary", {})
            script_field = summary.get("script")
            
            if not isinstance(script_field, dict):
                self.logger.error(f"Script field is not a dictionary: {script_field}")
                return None, None
                
            script_cmd = script_field.get("cmd")
            input_params = script_field.get("input")
            
            if not script_cmd:
                self.logger.error("No 'cmd' field in script object")
                return None, None
                
            if not isinstance(input_params, list):
                self.logger.error(f"Input parameters is not a list: {input_params}")
                return None, None
                
            self.logger.debug(f"Extracted script info - cmd: {script_cmd}, input: {input_params}")
            return script_cmd, input_params
            
        except Exception as e:
            self.logger.error(f"Error extracting script info: {e}")
            return None, None

    def execute_verification_script(self, script_cmd: str, input_params: List[str]) -> Tuple[bool, str]:
        """
        Execute a verification script with given parameters.
        
        Args:
            script_cmd: Name of the script file in ToolWL directory
            input_params: List of input parameters for the script
            
        Returns:
            Tuple of (success, message)
        """
        if not script_cmd:
            return False, "No script command provided"

        try:
            script_path = self.toolwl_path / script_cmd
            
            if not script_path.exists():
                error_msg = f"Verification script not found: {script_path}"
                self.logger.error(error_msg)
                return False, error_msg

            self.logger.info(f"Executing verification script: {script_path}")
            self.logger.info(f"Script input parameters: {input_params}")

            # Prepare input and output files
            input_file = self.toolwl_path / "input.txt"
            output_file = self.toolwl_path / "output.txt"

            self.logger.info(f"Input file path: {input_file}")
            self.logger.info(f"Output file path: {output_file}")

            # Write input parameters to input.txt
            try:
                with open(input_file, "w", encoding="utf-8") as f:
                    for param in input_params:
                        f.write(f"{param}\n")
                self.logger.info(f"Successfully wrote {len(input_params)} parameters to input.txt")
            except Exception as e:
                error_msg = f"Failed to write input file: {e}"
                self.logger.error(error_msg)
                return False, error_msg

            # Remove existing output file if present
            if output_file.exists():
                output_file.unlink()
                self.logger.info("Removed existing output.txt file")

            self.logger.info(f"Executing command: {sys.executable} {script_path}")
            self.logger.info(f"Working directory: {self.toolwl_path}")

            # Check if script file actually exists and is readable
            if not script_path.is_file():
                error_msg = f"Script file does not exist or is not a file: {script_path}"
                self.logger.error(error_msg)
                return False, error_msg

            # Execute the script with timeout and proper encoding
            start_time = time.time()

            # Set environment variables for proper Unicode handling
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.toolwl_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace problematic characters instead of failing
                timeout=60,  # 60 second timeout
                env=env
            )
            execution_time = time.time() - start_time

            self.logger.debug(f"Script execution completed in {execution_time:.2f}s with return code: {result.returncode}")

            # Log stdout and stderr if present (use INFO level for debugging)
            if result.stdout:
                self.logger.info(f"Script stdout: {result.stdout}")
            if result.stderr:
                self.logger.error(f"Script stderr: {result.stderr}")

            # Log return code for debugging
            self.logger.info(f"Script return code: {result.returncode}")

            # Read and interpret output
            if output_file.exists():
                try:
                    with open(output_file, "r", encoding="utf-8") as f:
                        output_content = f.read().strip()

                    self.logger.debug(f"Script output content: '{output_content}'")

                    if output_content == "1":
                        success_msg = f"Verification script passed: {script_cmd} (execution time: {execution_time:.2f}s)"
                        self.logger.info(success_msg)
                        return True, success_msg
                    elif output_content == "0":
                        fail_msg = f"Verification script failed: {script_cmd} (execution time: {execution_time:.2f}s)"
                        self.logger.warning(fail_msg)
                        return False, fail_msg
                    else:
                        error_msg = f"Unexpected script output: '{output_content}' (expected '1' or '0')"
                        self.logger.error(error_msg)
                        return False, error_msg

                except Exception as e:
                    error_msg = f"Error reading script output: {e}"
                    self.logger.error(error_msg)
                    return False, error_msg
            else:
                error_msg = f"Script did not create output file: {output_file}"
                self.logger.error(error_msg)
                return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = f"Script execution timed out after 60 seconds: {script_cmd}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error executing verification script: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def verify_test_result(self, result_data: Optional[Dict[str, Any]]) -> Tuple[bool, str, bool]:
        """
        Main method to verify test result with automatic script execution.
        
        Args:
            result_data: Response data from OpenWrt device
            
        Returns:
            Tuple of (verification_needed, message, verification_passed)
            - verification_needed: True if verification was attempted
            - message: Descriptive message about the verification process
            - verification_passed: True if verification succeeded (only meaningful if verification_needed=True)
        """
        try:
            # Check if verification is needed
            if not self.should_run_verification(result_data):
                return False, "No verification required", True

            # Extract script information
            script_cmd, input_params = self.extract_script_info(result_data or {})

            if not script_cmd or input_params is None:
                error_msg = "Failed to extract script information from result data"
                self.logger.error(error_msg)
                return True, error_msg, False

            # Execute verification script
            verification_success, verification_message = self.execute_verification_script(
                script_cmd, input_params
            )

            return True, verification_message, verification_success

        except Exception as e:
            error_msg = f"Error during test result verification: {e}"
            self.logger.error(error_msg)
            return True, error_msg, False
