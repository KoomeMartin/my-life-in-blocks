# Multi-Agent Calendar System - Organized Workflow Architecture

## Overview

This document outlines the completely reorganized multi-agent workflow using proper Google Calendar Toolkit integration and clear agent responsibilities.

## Section 1: Tool Schema Configuration

### Google Calendar Toolkit Integration

```python
def get_calendar_toolkit():
    """Initialize Google Calendar Toolkit with proper error handling."""
    from langchain_google_community import CalendarToolkit
    from langchain_google_community.calendar.utils import (
        build_resource_service,
        get_google_credentials,
    )
    
    # Proper credential management
    credentials = get_google_credentials(
        token_file="token.json",
        scopes=["https://www.googleapis.com/auth/calendar"],
        client_secrets_file="credentials.json",
    )
    
    api_resource = build_resource_service(credentials=credentials)
    toolkit = CalendarToolkit(api_resource=api_resource)
    
    return toolkit.get_tools()
```

### Available Calendar Tools

From the Google Calendar Toolkit:
- `CalendarCreateEvent` - Create new events
- `CalendarSearchEvents` - Search for events
- `CalendarUpdateEvent` - Update existing events  
- `GetCalendarsInfo` - Get calendar information
- `CalendarMoveEvent` - Move events between calendars
- `CalendarDeleteEvent` - Delete events
- `GetCurrentDatetime` - Get current date/time

## Section 2: Agent Tool Distribution

### 🔧 Orchestrator Agent Tools
**Purpose**: Handle simple calendar queries and routing

**Tools Available**:
- `get_current_datetime` - Temporal awareness
- `calendar_search_events` - Search calendar events
- `get_calendars_info` - Get available calendars

**NO RAG ACCESS** - Focuses purely on calendar operations

### 🧠 Planner Agent Tools  
**Purpose**: Complex scheduling with energy-aware planning

**Tools Available**:
- `get_current_datetime` - Temporal awareness
- `get_strategic_memory_tool` - **RAG ACCESS** for user profile/energy patterns
- **ALL Calendar Tools** - Full calendar functionality for comprehensive planning

**UNIQUE CAPABILITY**: Only agent with RAG access for energy-aware scheduling

### ⚡ Executor Agent Tools
**Purpose**: Event creation and calendar modifications

**Tools Available**:
- `get_current_datetime` - Temporal awareness  
- `create_calendar_event` - Create new events
- `calendar_update_event` - Update events
- `calendar_delete_event` - Delete events

**NO RAG ACCESS** - Focuses purely on execution

## Section 3: Workflow Logic

### Intent Classification System

```python
def classify_intent(self, user_query: str) -> str:
    """Classify user intent for proper routing."""
    
    # SIMPLE_CALENDAR: Direct calendar queries
    simple_keywords = ['what is', 'check', 'view', 'today', 'tomorrow', 'meetings']
    
    # COMPLEX_SCHEDULING: Planning and optimization
    complex_keywords = ['schedule', 'plan', 'optimize', 'find time', 'energy', 'best time']
    
    # Route accordingly
```

### Agent Routing Strategy

1. **Simple Calendar Queries** → **Orchestrator Agent**
   - "What's my schedule today?"
   - "Am I free at 2 PM?"
   - "What meetings do I have tomorrow?"

2. **Complex Scheduling** → **Planner Agent**  
   - "Schedule a 2-hour study session this week"
   - "Find the best time for deep work"
   - "Plan my week considering my energy levels"

3. **Event Creation** → **Executor Agent**
   - After user confirms a plan
   - Direct event creation requests

## Section 4: Key Improvements

### ✅ Proper Tool Schema Management

- **Google Calendar Toolkit**: Official LangChain integration
- **Credential Management**: Proper OAuth2 flow with token.json
- **Error Handling**: Graceful degradation when tools unavailable
- **Tool Filtering**: Each agent gets only relevant tools

### ✅ Clear Agent Responsibilities

- **Orchestrator**: Calendar search + routing (NO RAG)
- **Planner**: RAG + full calendar access for intelligent planning  
- **Executor**: Event creation only

### ✅ Organized Workflow

- **Intent Classification**: Automatic routing based on query type
- **Conversation State**: Persistent context across interactions
- **Human-in-the-Loop**: Confirmation before event creation
- **Error Recovery**: Proper exception handling throughout

## Section 5: Usage Examples

### Simple Calendar Query Flow
```
User: "What's my schedule tomorrow?"
↓
Intent: SIMPLE_CALENDAR
↓  
Orchestrator Agent:
- Uses calendar_search_events
- Returns actual calendar data
- No RAG needed
```

### Complex Scheduling Flow
```
User: "Find me 2 hours for deep work this week"
↓
Intent: COMPLEX_SCHEDULING
↓
Planner Agent:
- Uses RAG to get energy patterns
- Uses calendar tools to check availability
- Combines insights for optimal scheduling
- Returns energy-aware recommendations
```

### Event Creation Flow
```
User confirms plan
↓
Executor Agent:
- Uses create_calendar_event
- Creates actual calendar entry
- Returns confirmation
```

## Section 6: Configuration Requirements

### Dependencies
```bash
pip install langchain-google-community[calendar]
pip install langchain-openai
pip install langchain-chroma
```

### Required Files
- `credentials.json` - Google OAuth2 credentials
- `token.json` - Generated OAuth2 token
- `.env` - OpenAI API key
- `profile.json` - User profile data
- `chroma_db/` - RAG vector database

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key
```

## Section 7: Testing the System

### Quick Test Commands
```python
# Test calendar toolkit
python -c "from multi_agent_system import get_calendar_toolkit; print(get_calendar_toolkit())"

# Test agent initialization  
python multi_agent_system.py
```

### Sample Queries to Test
1. **Simple**: "What's my schedule today?"
2. **Complex**: "Schedule a study session considering my energy levels"
3. **General**: "What can you help me with?"

## Benefits of This Architecture

✅ **Clear Separation of Concerns**: Each agent has specific responsibilities
✅ **Proper Tool Management**: Using official Google Calendar Toolkit
✅ **Intelligent Routing**: Automatic intent classification and agent selection
✅ **RAG Integration**: Only Planner has access to user profile for energy-aware scheduling
✅ **Scalable Design**: Easy to add new agents or tools
✅ **Error Handling**: Robust exception management throughout
✅ **Real Calendar Integration**: Actual Google Calendar API usage

This architecture provides a clean, organized, and scalable foundation for intelligent calendar management with proper tool calling and agent specialization.