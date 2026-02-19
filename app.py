"""
Streamlit Web Interface for Multi-Agent Calendar Scheduling System
Main application entry point with chat interface, agent visualization, and session management.
"""

import streamlit as st
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import MultiAgentSystem
from config import AGENT_CONFIG, QUICK_ACTIONS, PAGE_CONFIG, MAX_TOOL_OUTPUT_LENGTH
from utils.session import initialize_session_state, load_session_history, create_new_session
from utils.formatting import format_event_time, truncate_tool_output, format_timestamp
from utils.error_handling import handle_error, log_error

# Configure page
st.set_page_config(**PAGE_CONFIG)

# Custom CSS for better styling
st.markdown("""
<style>
    .user-message {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        text-align: right;
    }
    .agent-message {
        background-color: #f5f5f5;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .tool-call {
        background-color: #fff3e0;
        padding: 8px;
        border-radius: 5px;
        margin: 3px 0;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_agent_system():
    """Initialize MultiAgentSystem (cached for performance)"""
    try:
        return MultiAgentSystem()
    except Exception as e:
        st.error(f"Failed to initialize agent system: {handle_error(e, 'agent_init')}")
        return None


def render_sidebar():
    """Render sidebar with session management and quick actions"""
    with st.sidebar:
        st.title("📅 My Life in Blocks")
        
        # Session info
        st.subheader("Current Session")
        st.text(f"ID: {st.session_state.session_id[:20]}...")
        st.text(f"Messages: {len(st.session_state.messages)}")
        
        # New session button
        if st.button("🆕 New Session", use_container_width=True):
            st.session_state.session_id = create_new_session()
            st.session_state.messages = []
            st.session_state.tool_calls = []
            st.session_state.current_agent = None
            st.rerun()
        
        st.divider()
        
        # Quick actions
        st.subheader("Quick Actions")
        for action in QUICK_ACTIONS:
            if st.button(action['label'], use_container_width=True):
                # Set a flag to process this query
                st.session_state.pending_query = action['query']
                st.rerun()
        
        st.divider()
        
        # Agent legend
        st.subheader("Agents")
        for agent_type, config in AGENT_CONFIG.items():
            st.markdown(f"{config['icon']} **{config['name']}**: {config['description']}")
        
        st.divider()
        
        # Adaptive Control Metrics
        if st.session_state.agent_system:
            st.subheader("📊 Performance")
            try:
                cache_stats = st.session_state.agent_system.get_cache_stats()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cache Hit Rate", f"{cache_stats['hit_rate']:.1%}")
                with col2:
                    st.metric("Cached Items", cache_stats['entries'])
                
                # Show detailed metrics in expander
                with st.expander("Detailed Metrics"):
                    metrics = st.session_state.agent_system.get_adaptive_metrics()
                    st.text(metrics)
            except Exception as e:
                st.caption(f"Metrics unavailable: {e}")


def render_message(message: Dict[str, Any]):
    """Render individual message with styling"""
    role = message.get('role', 'user')
    content = message.get('content', '')
    agent_type = message.get('agent_type')
    timestamp = message.get('timestamp', '')
    
    if role == 'user':
        # User message - use chat_message for better styling
        with st.chat_message("user"):
            st.markdown(content)
            if timestamp:
                st.caption(format_timestamp(datetime.fromisoformat(timestamp)))
    else:
        # Agent message - use chat_message with agent icon
        agent_config = AGENT_CONFIG.get(agent_type, {
            'icon': '🤖',
            'name': 'Assistant',
            'color': '#666666'
        })
        
        with st.chat_message("assistant", avatar=agent_config['icon']):
            # Remove the agent identification from content if it's already there
            # (since process_query adds it)
            clean_content = content
            if '**' in content and 'AGENT RESPONSE:**' in content:
                # Extract just the response part after the header
                parts = content.split('\n\n', 1)
                if len(parts) > 1:
                    clean_content = parts[1]
            
            st.markdown(clean_content)
            if timestamp:
                st.caption(format_timestamp(datetime.fromisoformat(timestamp)))
        
        # Show tool calls if present
        if message.get('tool_calls'):
            with st.expander("🔧 Tool Usage"):
                for tool_call in message['tool_calls']:
                    st.markdown(f"**{tool_call.get('tool_name', 'Unknown Tool')}**")
                    if tool_call.get('tool_input'):
                        st.json(tool_call['tool_input'])
                    if tool_call.get('tool_output'):
                        output = truncate_tool_output(str(tool_call['tool_output']), MAX_TOOL_OUTPUT_LENGTH)
                        st.text(output)


def process_user_message(query: str) -> Optional[Dict[str, Any]]:
    """
    Process user message through agent system.
    
    Args:
        query: User query string
    
    Returns:
        Response dictionary with content and agent_type
    """
    try:
        agent_system = st.session_state.agent_system
        if not agent_system:
            return {
                'content': "⚠️ Agent system not initialized. Please refresh the page.",
                'agent_type': None,
                'tool_calls': []
            }
        
        # Process query
        st.write("🔄 Processing query...")  # Debug
        response, agent_type = agent_system.process_query(query)
        st.write(f"✅ Got response from agent: {agent_type}")  # Debug
        st.write(f"📝 Response length: {len(response)} characters")  # Debug
        
        # Extract tool calls if available
        tool_calls = []
        if hasattr(agent_system, 'memory') and hasattr(agent_system.memory, 'get_recent_tool_usage'):
            try:
                recent_tools = agent_system.memory.get_recent_tool_usage(limit=5)
                for tool in recent_tools:
                    tool_calls.append({
                        'tool_name': tool.get('tool_name', 'Unknown'),
                        'tool_input': tool.get('input_params', {}),
                        'tool_output': tool.get('output_result', '')
                    })
            except Exception as tool_error:
                st.write(f"⚠️ Could not extract tool calls: {tool_error}")  # Debug
        
        return {
            'content': response,
            'agent_type': agent_type.value if agent_type else None,
            'tool_calls': tool_calls
        }
    
    except Exception as e:
        st.error(f"Error processing message: {str(e)}")  # Debug
        log_error(e, 'process_user_message', {'query': query})
        return {
            'content': handle_error(e, 'query_processing'),
            'agent_type': None,
            'tool_calls': []
        }


def stream_response(response_text: str, placeholder):
    """Stream response text token-by-token"""
    displayed_text = ""
    for i in range(0, len(response_text), 10):
        displayed_text = response_text[:i+10]
        placeholder.markdown(displayed_text)
        time.sleep(0.01)
    placeholder.markdown(response_text)


def main():
    """Main application logic"""
    # Initialize session state
    initialize_session_state()
    
    # Initialize pending_query if not exists
    if 'pending_query' not in st.session_state:
        st.session_state.pending_query = None
    
    # Initialize agent system
    if st.session_state.agent_system is None:
        with st.spinner("Initializing agent system..."):
            st.session_state.agent_system = initialize_agent_system()
    
    # Render sidebar
    render_sidebar()
    
    # Main chat area
    st.title("💬 Chat with Your Calendar Assistant")
    
    # Display chat messages
    for message in st.session_state.messages:
        render_message(message)
    
    # Process pending query from quick actions
    if st.session_state.pending_query:
        prompt = st.session_state.pending_query
        st.session_state.pending_query = None
        
        # Add user message
        user_message = {
            'role': 'user',
            'content': prompt,
            'timestamp': datetime.now().isoformat()
        }
        st.session_state.messages.append(user_message)
        
        # Process and get response
        with st.spinner("Processing..."):
            response_data = process_user_message(prompt)
            
            if response_data:
                # Add agent message
                agent_message = {
                    'role': 'assistant',
                    'content': response_data['content'],
                    'agent_type': response_data['agent_type'],
                    'tool_calls': response_data.get('tool_calls', []),
                    'timestamp': datetime.now().isoformat()
                }
                st.session_state.messages.append(agent_message)
        
        # Rerun to display messages
        st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask about your schedule, book meetings, or request reviews..."):
        # Add user message
        user_message = {
            'role': 'user',
            'content': prompt,
            'timestamp': datetime.now().isoformat()
        }
        st.session_state.messages.append(user_message)
        
        # Process and display agent response
        with st.spinner("Processing..."):
            st.session_state.is_processing = True
            
            # Get response
            response_data = process_user_message(prompt)
            
            if response_data:
                # Add agent message
                agent_message = {
                    'role': 'assistant',
                    'content': response_data['content'],
                    'agent_type': response_data['agent_type'],
                    'tool_calls': response_data.get('tool_calls', []),
                    'timestamp': datetime.now().isoformat()
                }
                st.session_state.messages.append(agent_message)
                
                st.session_state.is_processing = False
                
                # Rerun to display new message
                st.rerun()


if __name__ == "__main__":
    main()
