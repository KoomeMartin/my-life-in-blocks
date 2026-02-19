# Streamlit Web Interface - Quick Start Guide

## Overview

The Streamlit web interface provides a modern, chat-based UI for the multi-agent calendar scheduling system with:
- 💬 Real-time chat interface
- 🤖 Visual agent identification (Manager 🔍, Planner 📋, Executor ⚡, Reviewer 📊)
- 🔧 Tool usage transparency
- 📅 Calendar event display
- 💾 Session management
- ⚡ Quick actions for common tasks

## Installation

1. **Install Streamlit** (if not already installed):
```bash
pip install streamlit>=1.28.0
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

2. **Verify environment variables** are set in `.env`:
```bash
OPENAI_API_KEY=your_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

3. **Ensure database is set up**:
- Run `complete_memory_schema.sql` in Supabase SQL Editor
- Run `python advanced_rag.py` to ingest profile data
- Run `python reauth_gmail.py` to authenticate Calendar + Gmail

## Running the Interface

### Start the Streamlit app:
```bash
streamlit run app.py
```

The interface will open in your browser at `http://localhost:8501`

### Alternative: Specify port
```bash
streamlit run app.py --server.port 8502
```

## Using the Interface

### Chat Interface
- Type your query in the chat input at the bottom
- Press Enter or click Send
- Watch as the agent processes your request
- See which agent responds (Manager, Planner, Executor, or Reviewer)

### Quick Actions (Sidebar)
Click any quick action button to instantly:
- 📅 **Today's Schedule**: View all meetings today
- 📊 **Weekly Review**: Generate productivity review
- 🔍 **Check Availability**: Find free time slots

### Tool Usage
- Expand "🔧 Tool Usage" sections to see:
  - Which tools the agent used
  - Tool input parameters
  - Tool output results

### Session Management
- **New Session**: Click "🆕 New Session" to start fresh
- **Session Info**: View current session ID and message count
- Sessions are automatically saved to Supabase

## Example Queries

Try these queries to test the interface:

**Manager Agent** (Calendar queries):
- "What meetings do I have today?"
- "Am I free tomorrow afternoon?"
- "Show me my schedule for this week"

**Planner Agent** (Scheduling):
- "Schedule a 1-hour meeting tomorrow at 2pm"
- "Find time for a 2-hour study session this week"
- "When can I schedule a team meeting considering everyone's availability?"

**Executor Agent** (Event creation):
- After Planner creates a plan, say "yes" or "correct" to execute

**Reviewer Agent** (Analytics):
- "Generate my weekly review"
- "How productive was I this week?"
- "Show me my energy alignment metrics"

## Features

### Agent Identification
Each agent has a unique icon and color:
- 🔍 **Manager** (Blue): Calendar queries and availability
- 📋 **Planner** (Purple): Strategic scheduling and planning
- ⚡ **Executor** (Green): Event creation and execution
- 📊 **Reviewer** (Red): Progress tracking and analytics

### Tool Transparency
See exactly what the agents are doing:
- Calendar searches
- RAG retrievals (profile data)
- Event creation
- Analytics queries

### Persistent Memory
- All conversations saved to Supabase
- Cross-session learning
- Preference tracking
- Plan reuse

## Troubleshooting

### "Agent system not initialized"
- Check that `.env` file has all required variables
- Verify Supabase connection
- Ensure `complete_memory_schema.sql` was run

### "Database connection issue"
- Verify Supabase credentials in `.env`
- Check internet connection
- Ensure Supabase project is active

### "Calendar API error"
- Run `python reauth_gmail.py` to re-authenticate
- Verify `token.json` exists
- Check Calendar API permissions

### Slow responses
- First query may be slow (agent initialization)
- Subsequent queries should be faster (cached)
- Check OpenAI API status

## Configuration

### Customize Quick Actions
Edit `config.py` to add/modify quick actions:
```python
QUICK_ACTIONS = [
    {
        'label': '📅 Your Custom Action',
        'query': 'Your custom query here',
        'icon': '📅'
    }
]
```

### Adjust Styling
Edit `.streamlit/config.toml` to change colors:
```toml
[theme]
primaryColor = "#3498db"  # Change to your preferred color
```

### Modify Agent Colors
Edit `config.py` AGENT_CONFIG to change agent colors:
```python
AGENT_CONFIG = {
    'manager': {
        'color': '#3498db',  # Your custom color
        ...
    }
}
```

## Development

### Project Structure
```
.
├── app.py                      # Main Streamlit application
├── config.py                   # Configuration and constants
├── utils/
│   ├── session.py             # Session management
│   ├── formatting.py          # Text and time formatting
│   └── error_handling.py      # Error handling utilities
├── .streamlit/
│   └── config.toml            # Streamlit configuration
└── streamlit_requirements.txt  # Streamlit-specific dependencies
```

### Adding Features
1. Add new components in `utils/` or create `components/` directory
2. Import in `app.py`
3. Call from `main()` function
4. Test with `streamlit run app.py`


