"""
Error classification system for Test Case Manager v3.0.

This module provides error type classification to distinguish between
network errors (which should be retried) and application errors 
(which should fail immediately).
"""

from enum import Enum
from typing import Tuple, Optional
import re
import logging


class ErrorType(Enum):
    """Error type classification for retry logic."""
    NETWORK_ERROR = "network_error"      # Should retry - transient network issues
    APPLICATION_ERROR = "application_error"  # Should NOT retry - permanent issues
    UNKNOWN_ERROR = "unknown_error"      # Default - treat conservatively


class ErrorClassifier:
    """Classifies errors to determine retry behavior."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Network error indicators (case-insensitive)
        self.network_error_patterns = [
            # Connection issues
            r"connection.*timeout",
            r"connection.*timed.*out",
            r"connection.*refused",
            r"connection.*reset",
            r"connection.*forcibly.*closed",
            r"connection.*broken",
            r"connection.*aborted",
            r"connection.*lost",
            r"connection.*dropped",
            r"remote.*end.*closed.*connection",
            
            # Network/DNS issues
            r"network.*unreachable",
            r"host.*unreachable",
            r"dns.*resolution.*failed",
            r"name.*resolution.*failed",
            r"no.*route.*to.*host",
            r"network.*down",
            
            # Socket errors
            r"socket.*error",
            r"broken.*pipe",
            r"pipe.*broken",
            r"errno.*32",  # Broken pipe
            r"errno.*104", # Connection reset by peer
            r"errno.*110", # Connection timed out
            r"errno.*111", # Connection refused
            
            # Windows specific errors
            r"winerror.*10054",  # Connection reset by peer
            r"winerror.*10060",  # Connection timed out
            r"winerror.*10061",  # Connection refused
            r"error.*10054",
            r"error.*10060", 
            r"error.*10061",
            
            # HTTP transport errors
            r"connectionreseterror",
            r"connectionerror",
            r"timeout.*error",
            r"read.*timeout",
            r"connect.*timeout",
            
            # General network terms
            r"forcibly.*closed",
            r"reset.*by.*peer",
            r"peer.*reset",
            r"transport.*error",
            r"ssl.*error",
            r"certificate.*error",

            # Connection establishment failures
            r"failed.*to.*ensure.*connection",
            r"failed.*to.*connect.*to.*device",
            r"connection.*lost.*to.*device",
            r"device.*not.*reachable",
            r"cannot.*reach.*device",
            r"device.*connection.*failed"
        ]
        
        # Application error indicators (case-insensitive)
        self.application_error_patterns = [
            # JSON/parsing errors
            r"json.*decode.*error",
            r"json.*parse.*error",
            r"invalid.*json",
            r"malformed.*json",
            r"syntax.*error.*json",
            
            # Validation errors
            r"validation.*error",
            r"validation.*failed",
            r"test.*case.*validation.*failed",
            r"invalid.*test.*case",
            r"invalid.*format",
            r"missing.*required.*field",
            r"schema.*validation.*failed",
            
            # Authentication/authorization
            r"authentication.*failed",
            r"authorization.*failed",
            r"access.*denied",
            r"permission.*denied",
            r"unauthorized",
            r"forbidden",
            
            # Server rejection
            r"bad.*request",
            r"invalid.*request",
            r"request.*rejected",
            r"server.*rejected.*test.*case",
            r"transaction.*id.*conflict",
            r"duplicate.*transaction",
            
            # File/resource errors
            r"file.*not.*found",
            r"resource.*not.*found",
            r"path.*not.*found",
            r"method.*not.*allowed"
        ]
        
        # Compile patterns for better performance
        self.network_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.network_error_patterns]
        self.application_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.application_error_patterns]
    
    def classify_error(self, error_message: str, http_status_code: Optional[int] = None) -> ErrorType:
        """
        Classify an error based on error message and HTTP status code.
        
        Args:
            error_message: The error message to classify
            http_status_code: HTTP status code if available
            
        Returns:
            ErrorType indicating whether this error should be retried
        """
        if not error_message:
            return ErrorType.UNKNOWN_ERROR
            
        # First check HTTP status codes (most reliable)
        if http_status_code is not None:
            error_type = self._classify_by_http_status(http_status_code)
            if error_type != ErrorType.UNKNOWN_ERROR:
                self.logger.debug(f"Classified by HTTP status {http_status_code}: {error_type.value}")
                return error_type
        
        # Then check error message patterns
        error_type = self._classify_by_message(error_message)
        self.logger.debug(f"Classified error '{error_message[:100]}...' as: {error_type.value}")
        return error_type
    
    def _classify_by_http_status(self, status_code: int) -> ErrorType:
        """Classify error based on HTTP status code."""
        if 500 <= status_code <= 599:
            # 5xx server errors - usually transient, should retry
            return ErrorType.NETWORK_ERROR
        elif 400 <= status_code <= 499:
            # 4xx client errors - usually permanent, should not retry
            if status_code in [408, 429]:  # Request timeout, too many requests
                return ErrorType.NETWORK_ERROR  # These can be retried
            return ErrorType.APPLICATION_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _classify_by_message(self, error_message: str) -> ErrorType:
        """Classify error based on error message content."""
        # Check for application errors first (more specific)
        for pattern in self.application_regex:
            if pattern.search(error_message):
                return ErrorType.APPLICATION_ERROR
        
        # Check for network errors
        for pattern in self.network_regex:
            if pattern.search(error_message):
                return ErrorType.NETWORK_ERROR
        
        return ErrorType.UNKNOWN_ERROR
    
    def should_retry(self, error_type: ErrorType) -> bool:
        """
        Determine if an error type should be retried.
        
        Args:
            error_type: The classified error type
            
        Returns:
            True if the error should be retried, False otherwise
        """
        return error_type == ErrorType.NETWORK_ERROR
    
    def get_retry_reason(self, error_type: ErrorType, error_message: str) -> str:
        """
        Get a human-readable reason for retry decision.
        
        Args:
            error_type: The classified error type
            error_message: The original error message
            
        Returns:
            Explanation of retry decision
        """
        if error_type == ErrorType.NETWORK_ERROR:
            return f"Network error detected, will retry: {error_message}"
        elif error_type == ErrorType.APPLICATION_ERROR:
            return f"Application error detected, skipping retry: {error_message}"
        else:
            return f"Unknown error type, treating conservatively: {error_message}"


# Global classifier instance
_classifier = ErrorClassifier()


def classify_error(error_message: str, http_status_code: Optional[int] = None) -> ErrorType:
    """
    Convenience function to classify an error.
    
    Args:
        error_message: The error message to classify
        http_status_code: HTTP status code if available
        
    Returns:
        ErrorType indicating whether this error should be retried
    """
    return _classifier.classify_error(error_message, http_status_code)


def should_retry_error(error_type: ErrorType) -> bool:
    """
    Convenience function to determine if an error should be retried.
    
    Args:
        error_type: The classified error type
        
    Returns:
        True if the error should be retried, False otherwise
    """
    return _classifier.should_retry(error_type)


def get_retry_reason(error_type: ErrorType, error_message: str) -> str:
    """
    Convenience function to get retry decision reason.
    
    Args:
        error_type: The classified error type
        error_message: The original error message
        
    Returns:
        Explanation of retry decision
    """
    return _classifier.get_retry_reason(error_type, error_message)
