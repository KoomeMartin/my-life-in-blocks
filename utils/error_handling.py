"""
Error handling utilities for the Streamlit interface.
Provides centralized error handling with user-friendly messages.
"""

import logging
from typing import Optional

# Configure logger
logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded"""
    pass


class SupabaseError(Exception):
    """Raised when Supabase operation fails"""
    pass


class CalendarAPIError(Exception):
    """Raised when Calendar API operation fails"""
    pass


def handle_error(error: Exception, context: str) -> str:
    """
    Centralized error handling with logging and user-friendly messages.
    
    Args:
        error: The exception that occurred
        context: Context string (e.g., "query_processing", "session_load")
    
    Returns:
        User-friendly error message
    """
    # Log full error for debugging
    logger.error(f"Error in {context}: {str(error)}", exc_info=True)
    
    # Return user-friendly message based on error type
    if isinstance(error, RateLimitError):
        return "⚠️ API rate limit exceeded. Please wait a moment and try again."
    elif isinstance(error, SupabaseError):
        return "⚠️ Database connection issue. Please check your connection and try again."
    elif isinstance(error, CalendarAPIError):
        return "⚠️ Calendar API error. Please verify your calendar permissions."
    elif "rate_limit" in str(error).lower():
        return "⚠️ API rate limit exceeded. Please wait a moment and try again."
    elif "supabase" in str(error).lower() or "database" in str(error).lower():
        return "⚠️ Database connection issue. Please check your connection and try again."
    elif "calendar" in str(error).lower() or "google" in str(error).lower():
        return "⚠️ Calendar API error. Please verify your calendar permissions."
    else:
        return f"⚠️ An unexpected error occurred: {str(error)}"


def log_error(error: Exception, context: str, additional_info: Optional[dict] = None) -> None:
    """
    Log error with additional context information.
    
    Args:
        error: The exception that occurred
        context: Context string
        additional_info: Optional dictionary with additional context
    """
    error_msg = f"Error in {context}: {str(error)}"
    if additional_info:
        error_msg += f" | Additional info: {additional_info}"
    
    logger.error(error_msg, exc_info=True)
