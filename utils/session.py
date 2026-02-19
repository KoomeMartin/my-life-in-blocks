"""
Session management utilities for the Streamlit interface.
Handles session initialization, loading, and persistence.
"""

import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid
import logging

logger = logging.getLogger(__name__)


def initialize_session_state() -> None:
    """
    Initialize Streamlit session state with default values.
    Sets up agent_system, session_id, messages, tool_calls, and processing flags.
    """
    # Initialize agent system (will be set by main app)
    if 'agent_system' not in st.session_state:
        st.session_state.agent_system = None
    
    # Generate unique session ID
    if 'session_id' not in st.session_state:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        st.session_state.session_id = f"session_{timestamp}_{unique_id}"
    
    # Initialize user ID
    if 'user_id' not in st.session_state:
        st.session_state.user_id = "default_user"
    
    # Initialize messages list
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Initialize current agent
    if 'current_agent' not in st.session_state:
        st.session_state.current_agent = None
    
    # Initialize tool calls
    if 'tool_calls' not in st.session_state:
        st.session_state.tool_calls = []
    
    # Initialize processing flag
    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False
    
    # Initialize selected session
    if 'selected_session' not in st.session_state:
        st.session_state.selected_session = None


def load_session_history(session_id: str, memory_manager) -> List[Dict[str, Any]]:
    """
    Load conversation history from Supabase for a given session.
    
    Args:
        session_id: Session ID to load
        memory_manager: SupabaseMemoryManager instance
    
    Returns:
        List of message dictionaries sorted by message_index
    """
    try:
        # Get conversation history from memory manager
        history = memory_manager.get_conversation_history(
            session_id=session_id,
            max_turns=100  # Load up to 100 messages
        )
        
        # Convert to message format
        messages = []
        for entry in history:
            if isinstance(entry, dict):
                # Already in dict format
                messages.append(entry)
            elif isinstance(entry, tuple) and len(entry) == 2:
                # (role, content) tuple format
                role, content = entry
                messages.append({
                    'role': role,
                    'content': content,
                    'timestamp': datetime.now().isoformat()
                })
        
        return messages
    
    except Exception as e:
        logger.error(f"Error loading session history: {e}")
        return []


def save_session(session_id: str, memory_manager, metadata: Optional[Dict] = None) -> bool:
    """
    Persist session to Supabase.
    
    Args:
        session_id: Session ID to save
        memory_manager: SupabaseMemoryManager instance
        metadata: Optional session metadata
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Session is automatically tracked by memory manager
        # Just ensure it's initialized
        if not hasattr(memory_manager, 'session_id') or memory_manager.session_id != session_id:
            memory_manager._initialize_session(session_id)
        
        return True
    
    except Exception as e:
        logger.error(f"Error saving session: {e}")
        return False


def get_session_metadata(session_id: str, messages: List[Dict]) -> Dict[str, Any]:
    """
    Generate session metadata for display.
    
    Args:
        session_id: Session ID
        messages: List of messages in session
    
    Returns:
        Dictionary with session metadata
    """
    # Extract agents used
    agents_used = set()
    for msg in messages:
        if msg.get('role') == 'assistant' and msg.get('agent_type'):
            agents_used.add(msg['agent_type'])
    
    # Get session date (from first message or now)
    if messages:
        first_msg = messages[0]
        if 'timestamp' in first_msg:
            session_date = first_msg['timestamp']
        else:
            session_date = datetime.now().isoformat()
    else:
        session_date = datetime.now().isoformat()
    
    return {
        'session_id': session_id,
        'date': session_date,
        'message_count': len(messages),
        'agents_used': list(agents_used)
    }


def create_new_session() -> str:
    """
    Create a new session with unique ID.
    
    Returns:
        New session ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"session_{timestamp}_{unique_id}"
