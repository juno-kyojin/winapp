#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Custom exceptions for Test Case Manager v2.0

This module defines custom exception classes for better error handling
and debugging throughout the application.

Author: juno-kyojin
Created: 2025-06-12
"""

from typing import Optional, Any


class TestCaseManagerError(Exception):
    """
    Base exception class for all Test Case Manager related errors.
    
    All custom exceptions in the application should inherit from this class
    to provide consistent error handling.
    """
    
    def __init__(self, message: str, error_code: Optional[str] = None) -> None:
        """
        Initialize the base exception.
        
        Args:
            message: Human-readable error description
            error_code: Optional error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class TemplateError(TestCaseManagerError):
    """Raised when template-related operations fail."""
    
    def __init__(self, message: str, template_id: Optional[str] = None) -> None:
        """
        Initialize template error.
        
        Args:
            message: Error description
            template_id: ID of the template that caused the error
        """
        super().__init__(message, "TEMPLATE_ERROR")
        self.template_id = template_id


class TemplateNotFoundError(TemplateError):
    """Raised when a requested template cannot be found."""
    
    def __init__(self, template_id: str) -> None:
        """
        Initialize template not found error.
        
        Args:
            template_id: ID of the missing template
        """
        message = f"Template not found: {template_id}"
        super().__init__(message, template_id)


class InvalidParameterError(TemplateError):
    """Raised when template parameters are invalid or missing."""
    
    def __init__(self, parameter_name: str, reason: str) -> None:
        """
        Initialize invalid parameter error.
        
        Args:
            parameter_name: Name of the invalid parameter
            reason: Reason why the parameter is invalid
        """
        message = f"Invalid parameter '{parameter_name}': {reason}"
        super().__init__(message)
        self.parameter_name = parameter_name
        self.reason = reason


class NetworkError(TestCaseManagerError):
    """Raised when network operations fail."""
    
    def __init__(self, message: str, host: Optional[str] = None, 
                 port: Optional[int] = None) -> None:
        """
        Initialize network error.
        
        Args:
            message: Error description
            host: Host that caused the error
            port: Port that caused the error
        """
        super().__init__(message, "NETWORK_ERROR")
        self.host = host
        self.port = port


class ConnectionError(NetworkError):
    """Raised when connection establishment fails."""
    
    def __init__(self, host: str, port: int, reason: str) -> None:
        """
        Initialize connection error.
        
        Args:
            host: Target host
            port: Target port
            reason: Reason for connection failure
        """
        message = f"Failed to connect to {host}:{port} - {reason}"
        super().__init__(message, host, port)
        self.reason = reason


class SSHError(NetworkError):
    """Raised when SSH operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None) -> None:
        """
        Initialize SSH error.
        
        Args:
            message: Error description
            operation: SSH operation that failed
        """
        super().__init__(message)
        self.operation = operation


class DatabaseError(TestCaseManagerError):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None,
                 table: Optional[str] = None) -> None:
        """
        Initialize database error.
        
        Args:
            message: Error description
            operation: Database operation that failed
            table: Table involved in the operation
        """
        super().__init__(message, "DATABASE_ERROR")
        self.operation = operation
        self.table = table


class ValidationError(TestCaseManagerError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None,
                 value: Optional[Any] = None) -> None:
        """
        Initialize validation error.
        
        Args:
            message: Error description
            field: Field that failed validation
            value: Value that failed validation
        """
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
        self.value = value


class ConfigurationError(TestCaseManagerError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: Optional[str] = None) -> None:
        """
        Initialize configuration error.
        
        Args:
            message: Error description
            config_key: Configuration key that caused the error
        """
        super().__init__(message, "CONFIG_ERROR")
        self.config_key = config_key


class FileOperationError(TestCaseManagerError):
    """Raised when file operations fail."""
    
    def __init__(self, message: str, file_path: Optional[str] = None,
                 operation: Optional[str] = None) -> None:
        """
        Initialize file operation error.
        
        Args:
            message: Error description
            file_path: Path to file that caused the error
            operation: File operation that failed
        """
        super().__init__(message, "FILE_ERROR")
        self.file_path = file_path
        self.operation = operation