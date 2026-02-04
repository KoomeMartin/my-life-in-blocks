# Multi-Agent React System v2 - Complete Guide

## Overview

The `multi_agent_react_2.py` file contains a completely reorganized multi-agent system with proper Google Calendar Toolkit integration and clear agent specialization using the ReAct (Reasoning + Acting) pattern.

## System Architecture

### 🎯 **ReAct Pattern Implementation**

Each agent follows the ReAct pattern:
1. **Reason**: Analyze the user query and determine what tools to use
2. **Act**: Execute the appropriate tools based on reasoning
3. **Observe**: Process tool results and provide intelligent responses

### 🤖 **Agent Specialization**

#### **Orchestrator Agent**
- **Purpose**: Handle simple calendar queries and intelligent routing
- **Tools**: `calendar_search_events`, `get_calendars_info`, `get_current_datetime`
- **No RAG Access**: Focuses purely on calendar operations
- **Handles**: "What's my schedule today?", "Am I free at 2 PM?"

#### **Planner Agent**
- **Purpose**: Complex scheduling with energy-aware planning
- **Tools**: `search_user_profile_and_policies` (RAG) + ALL calendar tools
- **Unique Capability**: Only agent with RAG access for user profile/energy patterns
- **Handles**: "Find me 2 hours for deep work", "Schedule considering my energy levels"

#### **Executor Agent**
- **Purpose**: Event creation and calendar modifications
- **Tools**: `create_calendar_event`, `calendar_update_event`, `calendar_delete_event`
- **No RAG Access**: Focuses purely on execution
- **Handles**: Creating confirmed events after user approval

## Key Features

### ✅ **Proper Google Calendar Toolkit Integration**

```python
def get_calendar_toolkit():
    """Initialize Google Calendar Toolkit with proper error handling."""
    from langchain_google_community import CalendarToolkit
    from langchain_google_community.calendar.utils import (
        build_resource_service,
        get_google_credentials,
    )
    
    credentials = get_google_credentials(
        token_file="token.json",
        scopes=["https://www.googleapis.com/auth/calendar"],
        client_secrets_file="credentials.json",
    )
    
    api_resource = build_resource_service(credentials=credentials)
    toolkit = CalendarToolkit(api_resource=api_resource)
    
    return toolkit.get_tools()
```

### ✅ **Intelligent Intent Classification**

```python
def classify_intent(self, user_query: str) -> str:
    """Classify user intent for proper routing."""
    
    # COMPLEX_SCHEDULING keywords
    complex_keywords = ['schedule', 'plan', 'optimize', 'find time', 'energy']
    
    # SIMPLE_CALENDAR keywords  
    simple_keywords = ['what is', 'check', 'today', 'tomorrow', 'meetings']
    
    # Automatic routing based on detected intent
```

### ✅ **Clean Tool Distribution**

- **Orchestrator Tools**: Calendar search only, no RAG
- **Planner Tools**: RAG + full calendar access for intelligent planning
- **Executor Tools**: Event creation only

### ✅ **Conversation State Management**

- Persistent conversation history (last 20 turns)
- Context-aware responses
- Session tracking and summaries

## Installation & Setup

### 1. Install Dependencies

```bash
pip install langchain-google-community[calendar]
pip install langchain-openai
pip install langchain-chroma
pip install python-dotenv
```

### 2. Setup Credentials

**Google Calendar Setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Download `credentials.json` to project root

**Environment Variables:**
```bash
# .env file
OPENAI_API_KEY=your_openai_api_key_here
```

**Required Files:**
- `credentials.json` - Google OAuth2 credentials
- `token.json` - Will be generated on first run
- `.env` - OpenAI API key
- `profile.json` - User profile data
- `chroma_db/` - RAG vector database

### 3. Initialize RAG Database

```bash
python rag.py  # Run this first to create the vector database
```

## Usage Examples

### Simple Calendar Queries (→ Orchestrator)

```python
# These queries go directly to Orchestrator Agent
"What's my schedule today?"
"Am I free at 2 PM tomorrow?"
"What meetings do I have this week?"
"Show me my calendar for Friday"
```

**Expected Flow:**
1. Intent classified as `SIMPLE_CALENDAR`
2. Routed to Orchestrator Agent
3. Uses `calendar_search_events` tool
4. Returns actual calendar data

### Complex Scheduling (→ Planner)

```python
# These queries go to Planner Agent (has RAG access)
"Find me 2 hours for deep work this week"
"Schedule a study session considering my energy levels"
"Plan my week optimally"
"When is the best time for complex tasks?"
```

**Expected Flow:**
1. Intent classified as `COMPLEX_SCHEDULING`
2. Routed to Planner Agent
3. Uses RAG to get energy patterns
4. Uses calendar tools to check availability
5. Combines insights for optimal recommendations

### General Queries (→ Orchestrator)

```python
# These queries go to Orchestrator for general assistance
"What can you help me with?"
"How does this system work?"
"Tell me about your capabilities"
```

## Running the System

### Command Line Interface

```bash
python multi_agent_react_2.py
```

### Sample Interaction

```
🤖 Initializing Multi-Agent React System v2...
🔧 Orchestrator Tools: ✅ Google Calendar Toolkit loaded successfully.
🔧 Planner Tools: ✅ Google Calendar Toolkit loaded successfully.
🔧 Executor Tools: ✅ Google Calendar Toolkit loaded successfully.
✅ Multi-Agent System initialized successfully!
✅ System Online. Ready for queries.

💬 You: What's my schedule today?

🎯 Intent classified as: SIMPLE_CALENDAR

🤖 Processing: What's my schedule today?

🏁 RESPONSE ----------------
Based on your calendar, here are your events for today:

📅 EVENTS FOR 2026-02-04 (Wednesday)
• 09:00 - 10:30: Machine Learning Lecture
• 14:00 - 15:00: Team Meeting
• 16:30 - 17:30: Office Hours

==================================================

💬 You: Find me 2 hours for deep work this week

🎯 Intent classified as: COMPLEX_SCHEDULING

🤖 Processing: Find me 2 hours for deep work this week

🏁 RESPONSE ----------------
Based on your energy profile and calendar analysis:

🧠 OPTIMAL DEEP WORK SLOTS:
• Thursday 08:00 - 10:00 (Peak energy period)
• Friday 04:30 - 06:30 (Early morning peak)

These times align with your peak cognitive hours and have no conflicts.

==================================================
```

## System Benefits

### ✅ **Clear Agent Specialization**
- Each agent has a specific, focused purpose
- No overlap in responsibilities
- Efficient tool usage

### ✅ **Proper Calendar Integration**
- Official Google Calendar Toolkit
- Real calendar data, not mock responses
- Proper OAuth2 authentication

### ✅ **Intelligent Routing**
- Automatic intent classification
- Context-aware agent selection
- Efficient query processing

### ✅ **RAG Integration**
- Energy-aware scheduling
- User profile consideration
- Historical pattern analysis

### ✅ **Scalable Architecture**
- Easy to add new agents
- Modular tool distribution
- Clean separation of concerns

## Troubleshooting

### Common Issues

1. **Calendar Tools Not Available**
   - Check `credentials.json` exists
   - Verify Google Calendar API is enabled
   - Ensure proper OAuth2 scopes

2. **RAG Database Missing**
   - Run `python rag.py` to create vector database
   - Check `profile.json` exists
   - Verify ChromaDB installation

3. **API Key Issues**
   - Check `.env` file has `OPENAI_API_KEY`
   - Verify API key is valid and has credits

### Debug Mode

Add verbose logging:
```python
# In agent initialization
self.executor = AgentExecutor(
    agent=agent,
    tools=self.tools,
    verbose=True,  # Enable debug output
    max_iterations=10
)
```

## Next Steps

1. **Test the System**: Run `python multi_agent_react_2.py`
2. **Try Different Queries**: Test both simple and complex scheduling
3. **Monitor Agent Routing**: Verify correct intent classification
4. **Check Calendar Integration**: Ensure real calendar data is used
5. **Validate RAG Access**: Confirm only Planner has profile access

The React-based multi-agent system is now properly configured with clean tool schemas, intelligent routing, and specialized agent responsibilities! 🚀