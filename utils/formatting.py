"""
Formatting utilities for the Streamlit interface.
Handles datetime formatting, text truncation, and markdown rendering.
"""

from datetime import datetime
from typing import Optional
import pytz


def format_event_time(event_time: datetime, timezone: str = 'Africa/Maputo') -> str:
    """
    Format event datetime to human-readable string with timezone.
    
    Args:
        event_time: Datetime object to format
        timezone: Timezone string (default: Africa/Maputo)
    
    Returns:
        Formatted string like "Monday, Feb 17, 2026 at 2:00 PM CAT"
    """
    if event_time.tzinfo is None:
        # Make timezone-aware if naive
        tz = pytz.timezone(timezone)
        event_time = tz.localize(event_time)
    
    # Format: "Monday, Feb 17, 2026 at 2:00 PM CAT"
    formatted = event_time.strftime("%A, %b %d, %Y at %I:%M %p")
    tz_abbr = event_time.strftime("%Z")
    
    return f"{formatted} {tz_abbr}"


def truncate_tool_output(output: str, max_length: int = 500) -> str:
    """
    Truncate tool output to maximum length with ellipsis.
    
    Args:
        output: Tool output string
        max_length: Maximum length before truncation
    
    Returns:
        Truncated string with "..." if longer than max_length
    """
    if len(output) <= max_length:
        return output
    
    return output[:max_length] + "..."


def format_agent_response(response: str) -> str:
    """
    Format agent response for markdown rendering.
    Preserves markdown formatting and line breaks.
    
    Args:
        response: Raw agent response text
    
    Returns:
        Formatted response ready for st.markdown()
    """
    # Preserve line breaks and markdown
    return response.strip()


def format_timestamp(dt: datetime) -> str:
    """
    Format timestamp for message display.
    
    Args:
        dt: Datetime object
    
    Returns:
        Formatted string like "2:30 PM"
    """
    return dt.strftime("%I:%M %p")


def format_session_date(dt: datetime) -> str:
    """
    Format session date for sidebar display.
    
    Args:
        dt: Datetime object
    
    Returns:
        Formatted string like "Feb 17, 2026"
    """
    return dt.strftime("%b %d, %Y")
