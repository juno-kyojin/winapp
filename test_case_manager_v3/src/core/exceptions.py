#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Custom exceptions for Test Case Manager v3.0

This module defines custom exception classes for better error handling
and debugging throughout the application.

Author: juno-kyojin
Created: 2025-06-12
"""

from typing import Optional, Any, Dict, Union


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
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary representation.
        
        Returns:
            Dictionary with exception details
        """
        result = {
            'error': self.__class__.__name__,
            'message': self.message
        }
        
        if self.error_code:
            result['error_code'] = self.error_code
            
        return result


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
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary representation.
        
        Returns:
            Dictionary with exception details including template_id
        """
        result = super().to_dict()
        if self.template_id:
            result['template_id'] = self.template_id
        return result


class TemplateNotFoundError(TestCaseManagerError):
    """Raised when a template cannot be found."""
    
    def __init__(self, message: str, template_id: str, category: str) -> None:
        """
        Initialize the exception.
        
        Args:
            message: Error message
            template_id: ID of the template that was not found
            category: Category of the template
        """
        super().__init__(message)
        self.template_id = template_id
        self.category = category


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
        
    def to_dict(self) -> Dict[str, Any]:
        """Extend dictionary representation with parameter details."""
        result = super().to_dict()
        result.update({
            'parameter_name': self.parameter_name,
            'reason': self.reason
        })
        return result


class NetworkError(TestCaseManagerError):
    """Raised when network operations fail."""
    
    def __init__(self, message: str, host: Optional[str] = None, 
                 port: Optional[Union[int, str]] = None) -> None:
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
        
    def to_dict(self) -> Dict[str, Any]:
        """Extend dictionary representation with network details."""
        result = super().to_dict()
        if self.host:
            result['host'] = self.host
        if self.port:
            result['port'] = self.port
        return result


class ConnectionError(TestCaseManagerError):
    """Exception raised for connection errors."""
    
    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None) -> None:
        """
        Initialize the exception.
        
        Args:
            message: Error message
            host: Host that failed to connect (optional)
            port: Port that failed to connect (optional)
        """
        self.host = host
        self.port = port
        
        if host and port:
            message = f"Connection error to {host}:{port} - {message}"
        elif host:
            message = f"Connection error to {host} - {message}"
            
        super().__init__(message)


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
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """
        Initialize the exception.
        
        Args:
            message: Error message
            field: Field that failed validation (optional)
        """
        self.field = field
        
        if field:
            message = f"Validation error for field '{field}': {message}"
            
        super().__init__(message)


class ConfigurationError(TestCaseManagerError):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None) -> None:
        """
        Initialize the exception.
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error (optional)
        """
        self.config_key = config_key
        
        if config_key:
            message = f"Configuration error for '{config_key}': {message}"
            
        super().__init__(message)


class FileOperationError(TestCaseManagerError):
    """Raised when a file operation fails."""
    
    def __init__(self, message: str, file_path: str, operation: str) -> None:
        """
        Initialize the exception.
        
        Args:
            message: Error message
            file_path: Path to the file that caused the error
            operation: Operation that failed (e.g., "read", "write")
        """
        super().__init__(message)
        self.file_path = file_path
        self.operation = operation 