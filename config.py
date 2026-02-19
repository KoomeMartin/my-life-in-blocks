# Streamlit Web Interface Configuration

# Agent Configuration
AGENT_CONFIG = {
    'manager': {
        'name': 'Manager',
        'icon': '🔍',
        'color': '#3498db',  # Blue
        'description': 'Calendar queries and availability'
    },
    'planner': {
        'name': 'Planner',
        'icon': '📋',
        'color': '#9b59b6',  # Purple
        'description': 'Strategic scheduling'
    },
    'executor': {
        'name': 'Executor',
        'icon': '⚡',
        'color': '#2ecc71',  # Green
        'description': 'Calendar event creation'
    },
    'reviewer': {
        'name': 'Reviewer',
        'icon': '📊',
        'color': '#e74c3c',  # Red
        'description': 'Progress tracking and analytics'
    }
}

# Quick Actions
QUICK_ACTIONS = [
    {
        'label': '📅 Today\'s Schedule',
        'query': 'What meetings do I have today?',
        'icon': '📅'
    },
    {
        'label': '📊 Weekly Review',
        'query': 'Generate my weekly review',
        'icon': '📊'
    },
    {
        'label': '🔍 Check Availability',
        'query': 'When am I available today?',
        'icon': '🔍'
    }
]

# UI Constants
MAX_TOOL_OUTPUT_LENGTH = 500
MESSAGE_PAGINATION_SIZE = 50
STREAMING_CHUNK_SIZE = 10
STREAMING_DELAY_MS = 10

# Streamlit Page Configuration
PAGE_CONFIG = {
    'page_title': 'My Life in Blocks',
    'page_icon': '📅',
    'layout': 'wide',
    'initial_sidebar_state': 'expanded'
}
