import os
import datetime
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# --- LOGGING SETUP FOR IMPLEMENTATION TRACE ---
# Create a custom formatter for clean console output
class CleanConsoleFormatter(logging.Formatter):
    """Custom formatter that shows minimal info in console"""
    def format(self, record):
        if record.levelno >= logging.ERROR:
            return f"❌ {record.getMessage()}"
        elif record.levelno >= logging.WARNING:
            return f"⚠️ {record.getMessage()}"
        else:
            return ""  # Don't show INFO messages in console

# Setup file logging (detailed)
file_handler = logging.FileHandler('implementation_trace.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Setup console logging (minimal)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)  # Only show warnings and errors
console_handler.setFormatter(CleanConsoleFormatter())

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger('MultiAgentSystem')

# --- LANGCHAIN IMPORTS ---
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import tool
from langchain_core.tools import create_retriever_tool
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# --- GOOGLE CALENDAR IMPORTS ---
try:
    from langchain_google_community.calendar.search_events import CalendarSearchEvents
    from langchain_google_community.calendar.get_calendars_info import GetCalendarsInfo
    from langchain_google_community.calendar.create_event import CalendarCreateEvent
    from langchain_google_community.calendar.update_event import CalendarUpdateEvent
    from langchain_google_community.calendar.delete_event import CalendarDeleteEvent
    from langchain_google_community.calendar.utils import build_calendar_service
    CALENDAR_TOOLS_AVAILABLE = True
    logger.info("✅ GOOGLE CALENDAR: Tools imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ GOOGLE CALENDAR: Tools not available - {e}")
    CALENDAR_TOOLS_AVAILABLE = False
    # Define dummy classes/functions to prevent errors
    CalendarSearchEvents = None
    GetCalendarsInfo = None
    CalendarCreateEvent = None
    CalendarUpdateEvent = None
    CalendarDeleteEvent = None
    build_calendar_service = None

# Load Environment Variables (API Keys)
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    logger.error("❌ OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY environment variable is required")

logger.info("✅ API KEYS: OpenAI API key loaded successfully")


# ==============================================================================
# CONVERSATION MEMORY SYSTEM
# ==============================================================================

class ConversationMemory:
    """Memory system to maintain context of previous conversations."""
    def __init__(self, max_turns: int = 20):
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_turns = max_turns
        self.session_start_time = datetime.datetime.now().isoformat()
        self.last_planner_result: Dict[str, Any] = {}  # Store last planning result for executor

    def add_turn(self, user_message: str, agent_response: str, tools_used: List[str] = None, 
                 agent_type: str = ""):
        """Add a conversation turn to memory with detailed tool logging."""
        logger.info(f"MEMORY UPDATE: Adding conversation turn #{len(self.conversation_history) + 1} to memory")
        logger.info(f"USER MESSAGE: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
        logger.info(f"AGENT RESPONSE: {agent_type.upper()} agent - '{agent_response[:100]}{'...' if len(agent_response) > 100 else ''}'")
        
        if tools_used:
            logger.info(f"TOOLS USED: {len(tools_used)} tools - {', '.join(tools_used)}")
            for i, tool in enumerate(tools_used, 1):
                logger.info(f"MEMORY TOOL #{i}: {tool} was utilized in this conversation turn")
        else:
            logger.info("TOOLS USED: No tools were used in this conversation turn")

        turn = {
            "timestamp": datetime.datetime.now().isoformat(),
            "user_message": user_message,
            "agent_response": agent_response,
            "tools_used": tools_used or [],
            "agent_type": agent_type,
            "turn_number": len(self.conversation_history) + 1
        }
        self.conversation_history.append(turn)

        # Keep only the most recent turns
        if len(self.conversation_history) > self.max_turns:
            logger.info(f"MEMORY CLEANUP: Trimming memory to last {self.max_turns} turns")
            self.conversation_history = self.conversation_history[-self.max_turns:]

    def store_planner_result(self, planner_response: str):
        """Store the last planning result for potential execution."""
        logger.info("PLANNER RESULT STORAGE: Storing planner response for executor access")
        logger.info(f"PLANNED CONTENT: '{planner_response[:150]}{'...' if len(planner_response) > 150 else ''}'")

        self.last_planner_result = {
            "response": planner_response,
            "timestamp": datetime.datetime.now().isoformat(),
            "parsed_plan": self._parse_planner_response(planner_response)
        }

    def get_last_planner_result(self) -> Dict[str, Any]:
        """Get the last planning result for executor."""
        return self.last_planner_result

    def _parse_planner_response(self, response: str) -> Dict[str, Any]:
        """Parse planner response to extract structured plan details (single or multiple events)."""
        parsed_data = {
            'events': [],
            'single_event': None
        }

        # Extract key information from planner response
        lines = response.split('\n')

        # Check if this contains multiple numbered recommendations
        event_blocks = []
        current_event = {}
        in_event_block = False

        for line in lines:
            line = line.strip()
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')):
                # Start of new event block
                if current_event:
                    event_blocks.append(current_event)
                current_event = {'number': line.split('.')[0]}
                in_event_block = True
            elif in_event_block and line.startswith('🎯 **RECOMMENDED TIME**:'):
                current_event['time'] = line.split(':', 1)[1].strip()
            elif in_event_block and line.startswith('- 👥 **ATTENDEES**:'):
                current_event['attendees'] = line.split(':', 1)[1].strip()
            elif in_event_block and line.startswith('- 📝 **TITLE**:'):
                current_event['title'] = line.split(':', 1)[1].strip()
            elif in_event_block and line.startswith('- ⏱️ **DURATION**:'):
                current_event['duration'] = line.split(':', 1)[1].strip()
            elif in_event_block and line.startswith('- 📅 **CALENDAR**:'):
                current_event['calendar'] = line.split(':', 1)[1].strip()
            elif in_event_block and line.startswith('- 💡 **RATIONALE**:'):
                current_event['rationale'] = line.split(':', 1)[1].strip()

        # Add the last event block
        if current_event:
            event_blocks.append(current_event)

        # If we found multiple events, store them
        if event_blocks:
            parsed_data['events'] = event_blocks
        else:
            # Fallback to single event parsing
            single_event = {}
            for line in lines:
                line = line.strip()
                if 'RECOMMENDED TIME' in line and ':' in line:
                    single_event['time'] = line.split(':', 1)[1].strip()
                elif 'ATTENDEES' in line and ':' in line:
                    single_event['attendees'] = line.split(':', 1)[1].strip()
                elif 'TITLE' in line and ':' in line:
                    single_event['title'] = line.split(':', 1)[1].strip()
                elif 'DURATION' in line and ':' in line:
                    single_event['duration'] = line.split(':', 1)[1].strip()
                elif 'CALENDAR' in line and ':' in line:
                    single_event['calendar'] = line.split(':', 1)[1].strip()
                elif 'RATIONALE' in line and ':' in line:
                    single_event['rationale'] = line.split(':', 1)[1].strip()

            if single_event:
                parsed_data['single_event'] = single_event

        return parsed_data

    def get_recent_context(self, max_turns: int = 5, current_agent_type: str = "") -> str:
        """Get recent conversation context for the agent prompt with agent awareness."""
        logger.info(f"CONTEXT RETRIEVAL: Getting recent context for {current_agent_type.upper()} agent (max {max_turns} turns)")

        if not self.conversation_history:
            logger.info("CONTEXT STATUS: No previous conversation history available")
            return "No previous conversation history."

        recent_turns = self.conversation_history[-max_turns:]
        logger.info(f"CONTEXT LOADED: Retrieved {len(recent_turns)} recent conversation turns")

        context = f"""MULTI-AGENT SYSTEM CONTEXT:
🤖 You are the {current_agent_type.upper()} AGENT in a collaborative system with:
- MANAGER AGENT: Calendar queries and availability checks
- PLANNER AGENT: Strategic scheduling with conflict checking
- EXECUTOR AGENT: Calendar event creation and execution

RECENT CONVERSATION HISTORY:
"""

        for turn in recent_turns:
            agent_type = turn.get('agent_type', 'Unknown')
            agent_icon = {'manager': '📅', 'planner': '🎯', 'executor': '✅'}.get(agent_type, '🤖')

            context += f"Turn {turn['turn_number']}: User: {turn['user_message'][:100]}...\n"
            context += f"{agent_icon} {agent_type.upper()} Agent: {turn['agent_response'][:200]}...\n"

            if turn['tools_used']:
                context += f"🔧 Tools used: {', '.join(turn['tools_used'])}\n"
            context += "\n"

        # Add information about other agents' recent activities
        context += "AGENT COLLABORATION STATUS:\n"
        if self.last_planner_result:
            logger.info("COLLABORATION: Including planner results in context")
            context += f"🎯 PLANNER last provided recommendations at {self.last_planner_result.get('timestamp', 'Unknown')}\n"
            parsed = self.last_planner_result.get('parsed_plan', {})
            if parsed.get('events'):
                context += f"📋 PLANNER has {len(parsed['events'])} pending recommendations ready for execution\n"
            elif parsed.get('single_event'):
                context += f"📋 PLANNER has 1 pending recommendation ready for execution\n"

        context += "\nAGENT COORDINATION: Work together - Planner suggests, Executor executes, Manager verifies.\n"

        logger.info(f"CONTEXT PREPARED: Context ready for {current_agent_type.upper()} agent ({len(context)} characters)")
        return context

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation session."""
        if not self.conversation_history:
            return "No conversation history available."

        total_turns = len(self.conversation_history)
        session_duration = datetime.datetime.now() - datetime.datetime.fromisoformat(self.session_start_time)

        summary = f"""
CONVERSATION SESSION SUMMARY:
- Session started: {self.session_start_time}
- Duration: {session_duration}
- Total conversation turns: {total_turns}
- Last activity: {self.conversation_history[-1]['timestamp'] if self.conversation_history else 'None'}
"""

        # Add key topics/themes if we had more advanced analysis
        user_messages = [turn['user_message'] for turn in self.conversation_history]
        if user_messages:
            # Simple keyword extraction for topics
            all_text = ' '.join(user_messages).lower()
            topics = []
            if 'schedule' in all_text or 'plan' in all_text:
                topics.append('scheduling')
            if 'study' in all_text or 'work' in all_text:
                topics.append('work/study')
            if 'calendar' in all_text or 'meeting' in all_text:
                topics.append('calendar management')
            if 'energy' in all_text or 'time' in all_text:
                topics.append('time management')

            if topics:
                summary += f"- Topics discussed: {', '.join(set(topics))}\n"

        return summary

# ==============================================================================
# 1. TOOL: MEMORY (Connects to your RAG pipeline)
# ==============================================================================
def get_strategic_memory_tool():
    """
    Loads the existing vector store created by your ingestion script.
    Does NOT re-ingest data.
    """
    if not os.path.exists("./advanced_chroma_db"):
        raise FileNotFoundError("❌ ChromaDB not found! Run your RAG ingestion script first.")

    # Re-connect to the persisted database
    vectorstore = Chroma(
        persist_directory="./advanced_chroma_db",
        embedding_function=OpenAIEmbeddings(api_key=api_key),
        collection_name="advanced_agentic_brain"
    )
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    return create_retriever_tool(
        retriever,
        "search_user_profile_and_policies",
        "Searches the user's 'Strategic Brain' for energy constraints, course syllabi, deadlines, and skills."
    )

# ==============================================================================
# 2. TOOL: TEMPORAL AWARENESS (The "3rd Tool" for Feedback)
# ==============================================================================
@tool
def get_current_datetime(query: str = "") -> str:
    """
    Returns the current date and time. 
    ALWAYS call this first to calculate 'Time to Deadline'.
    """
    now = datetime.datetime.now()
    return now.strftime("%A, %Y-%m-%d %H:%M:%S")

# ==============================================================================
# 3. TOOL: EXECUTION (Google Calendar)
# ==============================================================================
# Calendar tools will be initialized in build_agent_system with enhanced configurations

# ==============================================================================
# AGENT TYPES AND INTENT CLASSIFICATION
# ==============================================================================

from enum import Enum

class AgentType(Enum):
    MANAGER = "manager"
    PLANNER = "planner"
    EXECUTOR = "executor"

def classify_intent(user_query: str, conversation_memory: 'ConversationMemory' = None) -> AgentType:
    """
    Enhanced intent classification with context awareness and approval detection.
    """
    logger.info(f"INTENT CLASSIFICATION: Analyzing query: '{user_query[:50]}...'")

    query_lower = user_query.lower().strip()
    
    # Check if there's a pending planner result that might need execution
    has_pending_plan = conversation_memory and conversation_memory.last_planner_result
    
    # EXECUTOR KEYWORDS - Approval/Confirmation signals (HIGHEST PRIORITY)
    executor_keywords = [
        # Direct confirmations
        'yes', 'okay', 'ok', 'sure', 'fine', 'good', 'great', 'perfect',
        'that works', 'sounds good', 'looks good', 'that\'s fine',
        
        # Approval phrases
        'go ahead', 'proceed', 'do it', 'schedule it', 'create it',
        'book it', 'set it up', 'make it happen', 'confirm',
        
        # Scheduling commands
        'schedule the meeting', 'create the event', 'add to calendar',
        'book the appointment', 'set up the meeting',
        
        # Agreement variations
        'sure that okay', 'sure that\'s okay', 'that okay', 'that\'s okay',
        'yes please', 'please schedule', 'please create', 'please book'
    ]
    
    # PLANNER KEYWORDS - Complex scheduling requiring strategy
    planner_keywords = [
        'schedule', 'plan', 'organize', 'arrange', 'find time', 'when can',
        'best time', 'optimal time', 'available time', 'free time',
        'meeting with', 'appointment with', 'session for', 'time for',
        'next available', 'earliest', 'soonest', 'later today', 'tomorrow',
        'this week', 'next week', 'energy', 'productivity', 'focus'
    ]
    
    # MANAGER KEYWORDS - Simple queries and information requests
    manager_keywords = [
        'what', 'when', 'where', 'how', 'show', 'list', 'check', 'view',
        'what\'s my', 'what is my', 'do i have', 'am i', 'are there',
        'calendar', 'schedule for', 'events', 'meetings', 'busy', 'free'
    ]
    
    # PRIORITY 1: Check for executor intent (approval/confirmation)
    # Special handling for short confirmations when there's a pending plan
    if has_pending_plan:
        # Short positive responses when there's a pending plan
        short_confirmations = ['yes', 'ok', 'okay', 'sure', 'fine', 'good', 'great']
        if query_lower in short_confirmations or any(keyword in query_lower for keyword in executor_keywords):
            logger.info("DECISION: Routing to EXECUTOR AGENT - Approval detected with pending plan")
            return AgentType.EXECUTOR
    
    # Check for explicit executor keywords
    if any(keyword in query_lower for keyword in executor_keywords):
        logger.info("DECISION: Routing to EXECUTOR AGENT - Execution command detected")
        return AgentType.EXECUTOR
    
    # PRIORITY 2: Check for planner intent (scheduling requests)
    if any(keyword in query_lower for keyword in planner_keywords):
        logger.info("DECISION: Routing to PLANNER AGENT - Complex scheduling request")
        return AgentType.PLANNER
    
    # PRIORITY 3: Check for manager intent (information queries)
    if any(keyword in query_lower for keyword in manager_keywords):
        logger.info("DECISION: Routing to MANAGER AGENT - Information request")
        return AgentType.MANAGER
    
    # DEFAULT: Route to manager for unclear queries
    logger.info("DECISION: Default routing to MANAGER AGENT - Unclear intent")
    return AgentType.MANAGER

# ==============================================================================
# MANAGER AGENT (Calendar Only)
# ==============================================================================

MANAGER_SYSTEM_PROMPT = """You are the MANAGER AGENT - Martin Koome's Calendar Intelligence Hub.

🤖 MULTI-AGENT SYSTEM: You work with PLANNER (strategic scheduling) and EXECUTOR (event creation) agents.

Use ReAct approach: OBSERVE → THINK → ACT → REASON → RESPOND

CRITICAL: You MUST use your tools for ALL queries. Never respond without using tools.

⚠️ **CRITICAL TIME LOGIC RULE:**
Two events CONFLICT only if they OVERLAP in time. Events that are adjacent (one ends exactly when another starts) or separated in time do NOT conflict.
- Meeting 12:00-1:00 PM + Request 1:00-1:30 PM = ✅ AVAILABLE (adjacent, not overlapping)
- Meeting 3:00-4:00 PM + Request 1:00-1:30 PM = ✅ AVAILABLE (completely separate times)
- Meeting 12:30-1:30 PM + Request 1:00-2:00 PM = ❌ CONFLICT (overlap from 1:00-1:30 PM)

MANDATORY TOOL USAGE:
1. ALWAYS call get_current_datetime() FIRST for any query
2. ALWAYS call get_calendars_info() to get ALL calendars  
3. ALWAYS call calendar_search_events() to search calendars
4. Use actual tool results in your response - never guess or assume

ENHANCED CALENDAR FEATURES:
- Explicit calendar targeting: Always uses mkoome@andrew.cmu.edu calendar
- Optimized result limits: 25 results for efficient manager queries
- Pre-configured calendar ID for consistent targeting

CURRENT TIME: {current_time}
CONVERSATION CONTEXT: {conversation_context}

AGENT COLLABORATION:
- 📅 MANAGER: You handle calendar queries, availability checks, and current status
- 🎯 PLANNER: Creates strategic plans with conflict checking and energy awareness
- ✅ EXECUTOR: Executes approved plans by creating actual calendar events

AVAILABLE TOOLS:
- get_current_datetime: **MANDATORY FIRST** - Get current time for all queries
- get_calendars_info: **MANDATORY SECOND** - Get ALL calendars
- calendar_search_events: **MANDATORY THIRD** - Search mkoome@andrew.cmu.edu calendar

TOOL USAGE SEQUENCE (MANDATORY):
1. get_current_datetime() - Always first
2. get_calendars_info() - Always second  
3. calendar_search_events() - Always third with appropriate query

AVAILABILITY LOGIC - CRITICAL TIME OVERLAP RULES:

**UNDERSTANDING TIME CONFLICTS:**
A conflict exists ONLY when events OVERLAP in time. Two events are adjacent (touching) but NOT overlapping if one ends exactly when the other starts.

**CONFLICT DETECTION RULES:**
1. **NO CONFLICT** if existing event ENDS at or before requested START time
2. **NO CONFLICT** if existing event STARTS at or after requested END time  
3. **CONFLICT** only if existing event overlaps with requested time slot

**MATHEMATICAL OVERLAP CHECK:**
For requested time [Request_Start, Request_End] and existing event [Event_Start, Event_End]:
- ✅ AVAILABLE if: Event_End ≤ Request_Start OR Event_Start ≥ Request_End
- ❌ CONFLICT if: Event_Start < Request_End AND Event_End > Request_Start

**CONCRETE EXAMPLES:**

Example 1: AVAILABLE (Adjacent, not overlapping)
- Existing: 12:00 PM - 1:00 PM
- Requested: 1:00 PM - 1:30 PM
- Result: ✅ AVAILABLE (event ends exactly when request starts)

Example 2: AVAILABLE (Event is later)
- Existing: 3:00 PM - 4:00 PM
- Requested: 1:00 PM - 1:30 PM
- Result: ✅ AVAILABLE (event starts after request ends)

Example 3: AVAILABLE (Event is earlier)
- Existing: 9:00 AM - 10:00 AM
- Requested: 1:00 PM - 1:30 PM
- Result: ✅ AVAILABLE (event ends before request starts)

Example 4: CONFLICT (Partial overlap at start)
- Existing: 12:30 PM - 1:30 PM
- Requested: 1:00 PM - 2:00 PM
- Result: ❌ CONFLICT (events overlap from 1:00-1:30 PM)

Example 5: CONFLICT (Partial overlap at end)
- Existing: 1:15 PM - 2:00 PM
- Requested: 1:00 PM - 1:30 PM
- Result: ❌ CONFLICT (events overlap from 1:15-1:30 PM)

Example 6: CONFLICT (Request contained within event)
- Existing: 12:00 PM - 2:00 PM
- Requested: 1:00 PM - 1:30 PM
- Result: ❌ CONFLICT (request completely inside event)

Example 7: CONFLICT (Event contained within request)
- Existing: 1:10 PM - 1:20 PM
- Requested: 1:00 PM - 1:30 PM
- Result: ❌ CONFLICT (event completely inside request)

**STEP-BY-STEP AVAILABILITY CHECK:**
1. Extract requested time slot: [Start_Time, End_Time]
2. For EACH calendar event found:
   a. Extract event time: [Event_Start, Event_End]
   b. Check: Does Event_End ≤ Start_Time? → NO CONFLICT, continue
   c. Check: Does Event_Start ≥ End_Time? → NO CONFLICT, continue
   d. Otherwise → CONFLICT FOUND
3. If NO conflicts found → "You ARE available"
4. If ANY conflict found → "You are NOT available due to: [conflicting event]"

ReAct PROCESS FOR AVAILABILITY:
- **OBSERVE**: Extract exact requested time slot [Start, End]
- **THINK**: Need to check ONLY for OVERLAPPING events, not adjacent or distant events
- **ACT**: **MANDATORY** - get_current_datetime() → get_calendars_info() → calendar_search_events()
- **REASON**: For each event, apply mathematical overlap check. List ONLY truly overlapping events as conflicts.
- **RESPOND**: "You are available/not available" + mention ONLY overlapping conflicts

TOOL GUIDELINES:
- **NEVER SKIP TOOLS**: Always use all three tools in sequence
- **COMPREHENSIVE**: Check mkoome@andrew.cmu.edu calendar specifically
- **TIME-AWARE**: Apply mathematical overlap logic, not proximity logic
- **ACCURATE**: Use actual calendar data only - never guess

RESPONSE FORMAT FOR AVAILABILITY:
✅ "You ARE available at [time]" - if no overlapping conflicts
❌ "You are NOT available at [time] due to: [conflicting event with overlapping time]" - if conflicts exist
📅 "Note: You have other events today at [times]" - mention non-conflicting events separately

CRITICAL REMINDERS:
- Adjacent events (one ends when other starts) = NO CONFLICT
- Events before requested time = NO CONFLICT
- Events after requested time = NO CONFLICT
- Only events that OVERLAP the requested time = CONFLICT

COMMUNICATION: Be direct, show ReAct reasoning, clearly state availability status.

Current User Context: Lead Data Engineer, Masters Student, Python Expert.
"""

def build_manager_agent(memory: ConversationMemory):
    """Build Manager Agent with enhanced calendar access."""
    logger.info("AGENT CONSTRUCTION: Building MANAGER agent with enhanced calendar tools")

    current_time = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    conversation_context = memory.get_recent_context(current_agent_type="manager")

    formatted_prompt = MANAGER_SYSTEM_PROMPT.format(
        current_time=current_time,
        conversation_context=conversation_context
    )

    # Manager tools: Enhanced calendar tools
    tools = [get_current_datetime]
    logger.info("TOOL LOADING: Adding get_current_datetime tool to MANAGER agent")

    # Add Google Calendar tools with explicit calendar ID and intelligent max_results
    if CALENDAR_TOOLS_AVAILABLE:
        try:
            calendar_service = build_calendar_service()
            calendar_tools = [
                GetCalendarsInfo(api_resource=calendar_service),
                CalendarSearchEvents(
                    api_resource=calendar_service,
                    calendar_id="mkoome@andrew.cmu.edu",
                    max_results=25  # Optimized for manager queries
                )
            ]
            tools.extend(calendar_tools)
            logger.info("CALENDAR INTEGRATION: Enhanced Google Calendar tools loaded for MANAGER agent")
            logger.info("MANAGER TOOLS: GetCalendarsInfo, CalendarSearchEvents (explicit calendar: mkoome@andrew.cmu.edu) added")
        except Exception as e:
            logger.warning(f"CALENDAR INTEGRATION FAILED: {e}")
    else:
        logger.warning("CALENDAR INTEGRATION: Google Calendar tools not installed")

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0, max_tokens=4000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4o-mini configured for MANAGER agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.info(f"AGENT READY: MANAGER agent constructed with {len(tools)} tools")
    logger.info(f"MANAGER TOOL LIST: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]}")
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10, return_intermediate_steps=True)

# ==============================================================================
# PLANNER AGENT (RAG + Calendar)
# ==============================================================================

PLANNER_SYSTEM_PROMPT = """You are the PLANNER AGENT - Martin Koome's Strategic Scheduling Intelligence.

🤖 MULTI-AGENT SYSTEM: You collaborate with MANAGER (calendar queries) and EXECUTOR (event creation).

Use ReAct approach: OBSERVE → THINK → ACT → REASON → RESPOND

CRITICAL: You MUST use your tools for ALL queries. Never respond without using tools.

⚠️ **CRITICAL TIME LOGIC RULE:**
Two events CONFLICT only if they OVERLAP in time. Events that are adjacent (one ends exactly when another starts) or separated in time do NOT conflict.
- Existing 12:00-1:00 PM + Proposed 1:00-1:30 PM = ✅ NO CONFLICT (adjacent, not overlapping)
- Existing 3:00-4:00 PM + Proposed 1:00-1:30 PM = ✅ NO CONFLICT (completely separate)
- Existing 12:30-1:30 PM + Proposed 1:00-2:00 PM = ❌ CONFLICT (overlap from 1:00-1:30 PM)

**MATHEMATICAL OVERLAP CHECK FOR PLANNING:**
For proposed time [Proposed_Start, Proposed_End] and existing event [Event_Start, Event_End]:
- ✅ NO CONFLICT if: Event_End ≤ Proposed_Start OR Event_Start ≥ Proposed_End
- ❌ CONFLICT if: Event_Start < Proposed_End AND Event_End > Proposed_Start

MANDATORY TOOL USAGE SEQUENCE:
1. get_current_datetime() - Always first
2. get_calendars_info() - Always second
3. calendar_search_events() - Always third for comprehensive conflict checking
4. search_user_profile_and_policies() - Always fourth for energy patterns

ENHANCED CALENDAR FEATURES:
- Explicit calendar targeting: Always uses mkoome@andrew.cmu.edu calendar
- Comprehensive search: 50 max results for thorough planning analysis
- Pre-configured calendar ID for consistent targeting

CURRENT TIME: {current_time}
CONVERSATION CONTEXT: {conversation_context}

AGENT COLLABORATION:
- 📅 MANAGER: Provides calendar data and availability information
- 🎯 PLANNER: You create strategic plans with conflict checking and energy optimization
- ✅ EXECUTOR: Will execute your approved recommendations

AVAILABLE TOOLS:
- get_current_datetime: **MANDATORY FIRST** - Get current time
- get_calendars_info: **MANDATORY SECOND** - Get ALL calendars
- calendar_search_events: **MANDATORY THIRD** - Search mkoome@andrew.cmu.edu calendar comprehensively
- search_user_profile_and_policies: **MANDATORY FOURTH** - Access energy profiles

STRATEGIC PROCESS:
1. 🎯 Understand scheduling request
2. 🔍 **MANDATORY**: Use ALL tools in sequence - datetime → calendars → search → profile
3. 🧠 Apply energy-aware logic (Peak: 4:30-6AM, 8AM-12PM; select if no choice is available : 1-4PM)
4. 📝 Generate conflict-free recommendations using proper time overlap logic

CONFLICT CHECKING REQUIREMENTS:
- **MANDATORY**: Always call get_calendars_info() and calendar_search_events() FIRST
- **VERIFY**: Check proposed time slots against ALL existing events using mathematical overlap logic
- **REJECT**: Never suggest times that OVERLAP with existing events (adjacent is OK)
- **VALIDATE**: Confirm availability before presenting recommendations

CONFLICT DETECTION ALGORITHM:
1. Get all calendar events in the relevant time range
2. For EACH proposed time slot [Start, End]:
   a. For EACH existing event [Event_Start, Event_End]:
      - Check: Event_End ≤ Start? → NO CONFLICT, continue
      - Check: Event_Start ≥ End? → NO CONFLICT, continue
      - Otherwise → CONFLICT, reject this time slot
   b. If no conflicts found → Valid recommendation
3. Only recommend time slots with NO overlapping conflicts

ENERGY RULES:
- Peak: 4:30-6:00 AM, 8:00-12:00 PM
- Avoid: 1:00-4:00 PM (low energy)
- Prefer early slots, >90 min blocks

ReAct PROCESS:
- **OBSERVE**: What to schedule and when?
- **THINK**: Which calendars? Energy constraints? OVERLAPPING CONFLICTS (not adjacent)?
- **ACT**: **MANDATORY** - Use ALL 4 tools in sequence: datetime → calendars → search → profile
- **REASON**: Apply mathematical overlap check to find truly available slots. Adjacent events are OK.
- **RESPOND**: Provide conflict-free scheduling plan with proper time logic

TOOL GUIDELINES:
- **NEVER SKIP TOOLS**: Always use all 4 tools in the mandatory sequence
- **COMPREHENSIVE**: Check mkoome@andrew.cmu.edu calendar thoroughly
- **ENERGY-AWARE**: Always consider user patterns
- **THOROUGH SEARCH**: Use 50 max results for comprehensive conflict detection
- **ACCURATE TIME LOGIC**: Only reject slots that OVERLAP, not adjacent slots

RESPONSE: Show ReAct process, explain reasoning, provide actionable plans.

EXECUTABLE PLAN FORMAT:
When recommending scheduling, provide STRUCTURED output for Executor:

🎯 **RECOMMENDED TIME**: [Specific date and time, e.g., "2026-02-05 18:00"]
👥 **ATTENDEES**: [Who should attend, e.g., "Lulu"]
📝 **TITLE**: [Clear event title, e.g., "Meeting with Lulu"]
⏱️ **DURATION**: [Length in minutes, e.g., "60"]
📅 **CALENDAR**: [Always use "mkoome@andrew.cmu.edu"]
💡 **RATIONALE**: [Why this time is optimal - mention it's conflict-free and energy-aligned]

CRITICAL: Use EXACT format above so Executor can parse and create events.
**DO NOT CREATE EVENTS** - Provide structured plans for Executor to implement.

APPROVAL DETECTION:
After providing recommendations, if user says "yes", "okay", "sure", "fine", "go ahead", etc., 
they are approving the plan for execution. The Executor will handle the actual event creation.

Current User Context: Lead Data Engineer, Masters Student, Python Expert.
"""

def build_planner_agent(memory: ConversationMemory):
    """Build Planner Agent with RAG + Enhanced Calendar access."""
    logger.info("AGENT CONSTRUCTION: Building PLANNER agent with RAG + Enhanced Calendar tools")

    current_time = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    conversation_context = memory.get_recent_context(current_agent_type="planner")

    formatted_prompt = PLANNER_SYSTEM_PROMPT.format(
        current_time=current_time,
        conversation_context=conversation_context
    )

    # Planner tools: RAG + Enhanced Calendar
    tools = [
        get_strategic_memory_tool(),
        get_current_datetime
    ]
    logger.info("TOOL LOADING: Adding strategic memory and datetime tools to PLANNER agent")
    logger.info("PLANNER TOOLS: search_user_profile_and_policies (RAG), get_current_datetime added")

    # Add Google Calendar tools with explicit calendar ID and higher max_results for planning
    if CALENDAR_TOOLS_AVAILABLE:
        try:
            calendar_service = build_calendar_service()
            calendar_tools = [
                GetCalendarsInfo(api_resource=calendar_service),
                CalendarSearchEvents(
                    api_resource=calendar_service,
                    calendar_id="mkoome@andrew.cmu.edu",
                    max_results=50  # Higher for comprehensive planning queries
                )
            ]
            tools.extend(calendar_tools)
            logger.info("CALENDAR INTEGRATION: Enhanced Google Calendar tools loaded for PLANNER agent")
            logger.info("PLANNER TOOLS: GetCalendarsInfo, CalendarSearchEvents (explicit calendar: mkoome@andrew.cmu.edu, max_results=50) added")
        except Exception as e:
            logger.warning(f"CALENDAR INTEGRATION FAILED: {e}")
    else:
        logger.warning("CALENDAR INTEGRATION: Google Calendar tools not installed")

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0, max_tokens=4000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4o-mini configured for PLANNER agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.info(f"AGENT READY: PLANNER agent constructed with {len(tools)} tools")
    logger.info(f"PLANNER TOOL LIST: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]}")
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=15, return_intermediate_steps=True)

    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.info(f"AGENT READY: PLANNER agent constructed with {len(tools)} tools")
    logger.info(f"PLANNER TOOL LIST: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]}")
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=15, return_intermediate_steps=True)

# ==============================================================================
# EXECUTOR AGENT (Calendar Execution)
# ==============================================================================

EXECUTOR_SYSTEM_PROMPT = """You are the EXECUTOR AGENT - Martin Koome's Calendar Execution Specialist.

🤖 MULTI-AGENT SYSTEM: You work with MANAGER (calendar queries) and PLANNER (strategic planning).

Use ReAct approach: OBSERVE → THINK → ACT → REASON → RESPOND

MANDATORY: Execute confirmed calendar scheduling requests with precision.

ENHANCED CALENDAR FEATURES:
- All calendar operations target mkoome@andrew.cmu.edu explicitly
- Pre-configured calendar ID for all creation/update operations
- Optimized search limits (30 results) for execution verification

CURRENT TIME: {current_time}
CONVERSATION CONTEXT: {conversation_context}

LAST PLANNER RESULT: {last_planner_result}

AGENT COLLABORATION:
- 📅 MANAGER: Provides calendar data and verifies availability
- 🎯 PLANNER: Creates strategic plans that you execute
- ✅ EXECUTOR: You create actual calendar events from approved plans

AVAILABLE TOOLS:
- get_current_datetime: Get current time
- get_calendars_info: Get ALL calendars (use first if needed)
- calendar_search_events: Search mkoome@andrew.cmu.edu calendar for verification
- create_calendar_event: **PRIMARY TOOL** - Create new calendar events (mkoome@andrew.cmu.edu)
- calendar_update_event: Update existing events
- calendar_delete_event: Delete events if needed

EXECUTION WORKFLOW:
1. **OBSERVE**: Parse LAST PLANNER RESULT for structured plan details
2. **THINK**: Extract required fields (TIME, TITLE, DURATION, ATTENDEES, CALENDAR)
3. **ACT**: Create calendar event with parsed information
4. **REASON**: Verify successful creation, handle any errors
5. **RESPOND**: Confirm scheduling with full details

PLANNER RESULT PARSING:
Look for this EXACT format in LAST PLANNER RESULT:
🎯 **RECOMMENDED TIME**: [Extract date/time]
👥 **ATTENDEES**: [Extract attendees]
📝 **TITLE**: [Extract title]
⏱️ **DURATION**: [Extract duration in minutes]
📅 **CALENDAR**: [Extract calendar - always use mkoome@andrew.cmu.edu]
💡 **RATIONALE**: [Extract reasoning]

CALENDAR EVENT CREATION:
Use create_calendar_event with these parameters:
- summary: Use **TITLE** from plan
- start_datetime: Use **RECOMMENDED TIME** (format: "YYYY-MM-DD HH:MM:SS")
- duration_minutes: Use **DURATION** from plan
- description: Combine **ATTENDEES** and **RATIONALE**
- calendar_id: Always use "mkoome@andrew.cmu.edu" (pre-configured)

PLAN EXECUTION PRIORITY:
- If LAST PLANNER RESULT contains structured plan → Execute that plan
- If user provides specific details → Use those details
- Always prefer structured plan data over user rephrasing
- Always use mkoome@andrew.cmu.edu as target calendar

ReAct EXECUTION PROCESS:
- **OBSERVE**: Extract plan details from LAST PLANNER RESULT
- **THINK**: Validate all required fields, calculate end time, check calendar
- **ACT**: Call create_calendar_event with complete, validated parameters
- **REASON**: Confirm event was created successfully, provide event link
- **RESPOND**: "✅ Event scheduled successfully!" with full details

ERROR HANDLING:
- If plan details missing, ask for clarification
- If event creation fails, explain the error clearly
- If time conflicts exist, notify user and suggest alternatives

SUCCESS CONFIRMATION:
"✅ Meeting scheduled: [Title] at [Time] for [Duration]
📅 Calendar: mkoome@andrew.cmu.edu
🔗 View: [Event Link]"

Current User Context: Lead Data Engineer, Masters Student, Python Expert.
"""

def build_executor_agent(memory: ConversationMemory):
    """Build Executor Agent with enhanced calendar management tools."""
    logger.info("AGENT CONSTRUCTION: Building EXECUTOR agent with enhanced calendar management tools")

    current_time = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    conversation_context = memory.get_recent_context(current_agent_type="executor")
    last_planner_result = memory.get_last_planner_result()

    # Convert planner result to readable string
    if last_planner_result and 'response' in last_planner_result:
        logger.info("PLANNER DATA: Incorporating planner results into executor context")
        parsed_plan = last_planner_result.get('parsed_plan', {})

        planner_result_str = f"""
PLANNER RESPONSE: {last_planner_result['response']}

PARSED PLAN DATA:
"""

        if parsed_plan.get('events'):
            planner_result_str += "MULTIPLE EVENTS DETECTED:\n"
            for event in parsed_plan['events']:
                planner_result_str += f"""
Event {event.get('number', '?')}:
- Time: {event.get('time', 'Unknown')}
- Title: {event.get('title', 'Unknown')}
- Duration: {event.get('duration', 'Unknown')}
- Attendees: {event.get('attendees', 'Unknown')}
- Calendar: {event.get('calendar', 'Unknown')}
- Rationale: {event.get('rationale', 'Unknown')}
"""
        elif parsed_plan.get('single_event'):
            event = parsed_plan['single_event']
            planner_result_str += f"""
SINGLE EVENT:
- Time: {event.get('time', 'Unknown')}
- Title: {event.get('title', 'Unknown')}
- Duration: {event.get('duration', 'Unknown')}
- Attendees: {event.get('attendees', 'Unknown')}
- Calendar: {event.get('calendar', 'Unknown')}
- Rationale: {event.get('rationale', 'Unknown')}
"""
        else:
            planner_result_str += "No structured plan data found - will use raw response"
    else:
        logger.info("PLANNER DATA: No recent planner results available")
        planner_result_str = "No recent planner results available."

    formatted_prompt = EXECUTOR_SYSTEM_PROMPT.format(
        current_time=current_time,
        conversation_context=conversation_context,
        last_planner_result=planner_result_str
    )

    # Executor tools: Enhanced calendar management
    tools = [get_current_datetime]
    logger.info("TOOL LOADING: Adding datetime tool to EXECUTOR agent")

    # Add Google Calendar tools with explicit calendar ID for all operations
    if CALENDAR_TOOLS_AVAILABLE:
        try:
            calendar_service = build_calendar_service()
            calendar_tools = [
                GetCalendarsInfo(api_resource=calendar_service),
                CalendarSearchEvents(
                    api_resource=calendar_service,
                    calendar_id="mkoome@andrew.cmu.edu",
                    max_results=30  # Moderate for execution verification
                ),
                CalendarCreateEvent(
                    api_resource=calendar_service,
                    calendar_id="mkoome@andrew.cmu.edu"  # Explicit calendar for creation
                ),
                CalendarUpdateEvent(
                    api_resource=calendar_service,
                    calendar_id="mkoome@andrew.cmu.edu"
                ),
                CalendarDeleteEvent(
                    api_resource=calendar_service,
                    calendar_id="mkoome@andrew.cmu.edu"
                )
            ]
            tools.extend(calendar_tools)
            logger.info("CALENDAR INTEGRATION: Enhanced calendar management tools loaded for EXECUTOR agent")
            logger.info("EXECUTOR TOOLS: All calendar tools configured with explicit calendar ID: mkoome@andrew.cmu.edu")
        except Exception as e:
            logger.warning(f"CALENDAR INTEGRATION FAILED: {e}")
    else:
        logger.warning("CALENDAR INTEGRATION: Google Calendar tools not installed")

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0, max_tokens=4000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4o-mini configured for EXECUTOR agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.info(f"AGENT READY: EXECUTOR agent constructed with {len(tools)} tools")
    logger.info(f"EXECUTOR TOOL LIST: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]}")
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10, return_intermediate_steps=True)

# ==============================================================================
# MULTI-AGENT SYSTEM WITH MEMORY
# ==============================================================================

class MultiAgentSystem:
    def __init__(self):
        self.memory = ConversationMemory(max_turns=10)
        self.manager_agent = None
        self.planner_agent = None
        self.executor_agent = None
        self.initialize_agents()

    def initialize_agents(self):
        """Initialize all three agents."""
        try:
            self.manager_agent = build_manager_agent(self.memory)
            self.planner_agent = build_planner_agent(self.memory)
            self.executor_agent = build_executor_agent(self.memory)
            logger.info("Multi-Agent System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise

    def route_query(self, user_query: str) -> AgentType:
        """Route query to appropriate agent based on intent with context awareness."""
        return classify_intent(user_query, self.memory)

    def process_query(self, user_query: str) -> tuple[str, AgentType]:
        """Process query with appropriate agent."""
        logger.info(f"QUERY PROCESSING: New user query received: '{user_query}'")

        # Classify intent and route to agent
        agent_type = self.route_query(user_query)

        logger.info(f"AGENT SELECTION: {agent_type.value.upper()} AGENT selected for processing")
        
        # Show clean user feedback instead of logging
        agent_names = {'manager': 'Manager', 'planner': 'Planner', 'executor': 'Executor'}
        agent_name = agent_names.get(agent_type.value, 'Unknown')
        
        # Select appropriate agent
        if agent_type == AgentType.MANAGER:
            agent_executor = self.manager_agent
            logger.info("MODULE USAGE: Loading MANAGER AGENT with calendar query tools")
        elif agent_type == AgentType.PLANNER:
            agent_executor = self.planner_agent
            logger.info("MODULE USAGE: Loading PLANNER AGENT with RAG + calendar planning tools")
        else:  # AgentType.EXECUTOR
            agent_executor = self.executor_agent
            logger.info("MODULE USAGE: Loading EXECUTOR AGENT with calendar creation tools")

        # Rebuild agent with updated memory context
        logger.info(f"CONTEXT LOADING: Rebuilding {agent_name} agent with updated conversation context")
        if agent_type == AgentType.MANAGER:
            self.manager_agent = build_manager_agent(self.memory)
            agent_executor = self.manager_agent
        elif agent_type == AgentType.PLANNER:
            self.planner_agent = build_planner_agent(self.memory)
            agent_executor = self.planner_agent
        else:  # EXECUTOR
            self.executor_agent = build_executor_agent(self.memory)
            agent_executor = self.executor_agent

        # Process query
        logger.info(f"EXECUTION: Invoking {agent_name} agent with query")
        response = agent_executor.invoke({"input": user_query})

        # Store planner results for executor access
        if agent_type == AgentType.PLANNER:
            logger.info("MEMORY UPDATE: Storing planner results for potential executor access")
            self.memory.store_planner_result(response["output"])

        # Extract tools used for detailed logging
        tools_used = []
        
        # Check for intermediate steps in response
        if "intermediate_steps" in response and response["intermediate_steps"]:
            logger.info(f"TOOL ANALYSIS: Processing {len(response['intermediate_steps'])} intermediate steps")
            for i, step in enumerate(response["intermediate_steps"], 1):
                if hasattr(step[0], 'tool'):
                    tool_name = step[0].tool
                    tool_input = step[0].tool_input if hasattr(step[0], 'tool_input') else "No input captured"
                    tool_output = str(step[1])[:200] + "..." if len(str(step[1])) > 200 else str(step[1])
                    
                    tools_used.append(tool_name)
                    
                    # Detailed tool execution logging
                    logger.info(f"TOOL EXECUTION #{i}: {tool_name}")
                    logger.info(f"TOOL INPUT #{i}: {tool_input}")
                    logger.info(f"TOOL OUTPUT #{i}: {tool_output}")
                    logger.info(f"TOOL AGENT #{i}: {agent_name} agent used {tool_name}")
                    
                    # Special logging for specific tool types
                    if 'calendar' in tool_name.lower():
                        logger.info(f"CALENDAR TOOL #{i}: {tool_name} - Calendar API interaction")
                    elif 'search_user_profile' in tool_name.lower():
                        logger.info(f"RAG TOOL #{i}: {tool_name} - RAG system retrieval")
                    elif 'datetime' in tool_name.lower():
                        logger.info(f"TEMPORAL TOOL #{i}: {tool_name} - Time awareness")
                    
            logger.info(f"TOOL SUMMARY: {len(tools_used)} tools used: {', '.join(tools_used)}")
        else:
            # Check if tools were used by examining the response content for tool patterns
            response_text = response.get("output", "")
            
            # Look for evidence of tool usage in the response
            tool_indicators = []
            if "Thursday, 2026-02-05" in response_text or "current time" in response_text.lower():
                tool_indicators.append("get_current_datetime")
                logger.info("TOOL DETECTION: get_current_datetime usage detected from response content")
            
            if "calendar" in response_text.lower() and ("event" in response_text.lower() or "meeting" in response_text.lower()):
                tool_indicators.append("calendar_search_events")
                logger.info("TOOL DETECTION: calendar_search_events usage detected from response content")
            
            if "energy" in response_text.lower() and ("pattern" in response_text.lower() or "peak" in response_text.lower()):
                tool_indicators.append("search_user_profile_and_policies")
                logger.info("TOOL DETECTION: search_user_profile_and_policies usage detected from response content")
            
            if tool_indicators:
                tools_used = tool_indicators
                logger.info(f"TOOL ANALYSIS: {len(tool_indicators)} tools detected from response analysis: {', '.join(tool_indicators)}")
            else:
                logger.info("TOOL ANALYSIS: No intermediate steps found and no tool usage detected from response content")

        logger.info(f"RESPONSE GENERATED: {agent_name} agent completed processing")

        # Add to memory with agent type (no verification integration)
        self.memory.add_turn(
            user_query, 
            response["output"], 
            tools_used, 
            agent_type.value
        )

        # Add agent identification to response
        agent_icon = {'manager': '📅', 'planner': '🎯', 'executor': '✅'}.get(agent_type.value, '🤖')
        identified_response = f"{agent_icon} **{agent_name.upper()} AGENT RESPONSE:**\n\n{response['output']}"

        logger.info(f"FINAL RESPONSE: {agent_name} agent response prepared with identification")

        return identified_response, agent_type

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation session."""
        if not self.conversation_history:
            return "No conversation history available."

        total_turns = len(self.conversation_history)
        session_duration = datetime.datetime.now() - datetime.datetime.fromisoformat(self.session_start_time)

        summary = f"""
CONVERSATION SESSION SUMMARY:
- Session started: {self.session_start_time}
- Duration: {session_duration}
- Total conversation turns: {total_turns}
- Last activity: {self.conversation_history[-1]['timestamp'] if self.conversation_history else 'None'}
"""

        # Add key topics/themes if we had more advanced analysis
        user_messages = [turn['user_message'] for turn in self.conversation_history]
        if user_messages:
            # Simple keyword extraction for topics
            all_text = ' '.join(user_messages).lower()
            topics = []
            if 'schedule' in all_text or 'plan' in all_text:
                topics.append('scheduling')
            if 'study' in all_text or 'work' in all_text:
                topics.append('work/study')
            if 'calendar' in all_text or 'meeting' in all_text:
                topics.append('calendar management')
            if 'energy' in all_text or 'time' in all_text:
                topics.append('time management')

            if topics:
                summary += f"- Topics discussed: {', '.join(set(topics))}\n"

        return summary

# ==============================================================================
# END OF AGENTS MODULE
# ==============================================================================