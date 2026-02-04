import os
import datetime
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# --- LOGGING SETUP FOR IMPLEMENTATION TRACE ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('implementation_trace.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
# Reduce console noise - only show warnings and errors in interactive mode
logging.getLogger().handlers[1].setLevel(logging.WARNING)
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

    def add_turn(self, user_message: str, agent_response: str, tools_used: List[str] = None, agent_type: str = ""):
        """Add a conversation turn to memory."""
        logger.info(f"MEMORY UPDATE: Adding conversation turn #{len(self.conversation_history) + 1} to memory")
        logger.info(f"USER MESSAGE: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
        logger.info(f"AGENT RESPONSE: {agent_type.upper()} agent - '{agent_response[:100]}{'...' if len(agent_response) > 100 else ''}'")
        if tools_used:
            logger.info(f"TOOLS USED: {', '.join(tools_used)}")

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
    if not os.path.exists("./chroma_db"):
        raise FileNotFoundError("❌ ChromaDB not found! Run your RAG ingestion script first.")

    # Re-connect to the persisted database
    vectorstore = Chroma(
        persist_directory="./chroma_db",
        embedding_function=OpenAIEmbeddings(api_key=api_key),
        collection_name="agentic_career_brain"
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
# Calendar tool will be initialized in build_agent_system

# ==============================================================================
# AGENT TYPES AND INTENT CLASSIFICATION
# ==============================================================================

from enum import Enum

class AgentType(Enum):
    MANAGER = "manager"
    PLANNER = "planner"
    EXECUTOR = "executor"

def classify_intent(user_query: str) -> AgentType:
    """Classify user intent to route to appropriate agent."""
    logger.info(f"INTENT CLASSIFICATION: Analyzing query: '{user_query[:50]}...'")

    query_lower = user_query.lower()

    # Executor keywords - direct execution commands
    executor_keywords = [
        'schedule it', 'create the event', 'book it', 'set it up', 'go ahead',
        'yes schedule', 'confirm schedule', 'proceed', 'execute', 'do it',
        'schedule the meeting', 'create event', 'add to calendar',
        'yes go ahead', 'this options are okay', 'these options are okay',
        'yes please', 'please schedule', 'go ahead and schedule',
        'schedule these', 'create these events', 'book these',
        'yes this is fine', 'this is good', 'looks good'
    ]

    # Complex scheduling/planning keywords -> Planner (needs RAG + Calendar)
    planner_keywords = [
        'schedule', 'plan', 'create', 'optimize', 'find time', 'study session',
        'work plan', 'best time', 'energy', 'productivity', 'focus time',
        'organize', 'arrange', 'design', 'strategic', 'profile', 'constraints'
    ]

    # Simple calendar queries -> Manager (calendar only)
    manager_keywords = [
        'what is', 'check', 'view', 'availability', 'free', 'busy',
        'today', 'tomorrow', 'schedule for', 'meetings', 'events',
        'calendar', 'when', 'where', 'show me', 'list'
    ]

    # Check for executor intent first (most specific)
    if any(keyword in query_lower for keyword in executor_keywords):
        logger.info("DECISION: Routing to EXECUTOR AGENT - Execution command detected")
        return AgentType.EXECUTOR
    elif any(keyword in query_lower for keyword in planner_keywords):
        logger.info("DECISION: Routing to PLANNER AGENT - Complex scheduling/planning request")
        return AgentType.PLANNER
    elif any(keyword in query_lower for keyword in manager_keywords):
        logger.info("DECISION: Routing to MANAGER AGENT - Calendar query/information request")
        return AgentType.MANAGER
    else:
        logger.info("DECISION: Default routing to MANAGER AGENT - General calendar query")
        # Default to manager for general calendar queries
        return AgentType.MANAGER

# ==============================================================================
# MANAGER AGENT (Calendar Only)
# ==============================================================================

MANAGER_SYSTEM_PROMPT = """You are the MANAGER AGENT - Martin Koome's Calendar Intelligence Hub.

🤖 MULTI-AGENT SYSTEM: You work with PLANNER (strategic scheduling) and EXECUTOR (event creation) agents.

Use ReAct approach: OBSERVE → THINK → ACT → REASON → RESPOND

MANDATORY: Always call get_calendars_info() FIRST, then search ALL calendars.

CURRENT TIME: {current_time}
CONVERSATION CONTEXT: {conversation_context}

AGENT COLLABORATION:
- 📅 MANAGER: You handle calendar queries, availability checks, and current status
- 🎯 PLANNER: Creates strategic plans with conflict checking and energy awareness
- ✅ EXECUTOR: Executes approved plans by creating actual calendar events

AVAILABLE TOOLS:
- get_current_datetime: Get current time
- get_calendars_info: **CRITICAL FIRST STEP** - Get ALL calendars
- calendar_search_events: Search ALL calendars comprehensively

AVAILABILITY LOGIC - CRITICAL:
- **AVAILABLE**: If NO events overlap with requested time → "You ARE available"
- **NOT AVAILABLE**: If ANY events overlap with requested time → "You are NOT available"
- **UPCOMING EVENTS**: Mention future events separately, but they don't affect current availability

ReAct PROCESS FOR AVAILABILITY:
- **OBSERVE**: What time slot is being queried?
- **THINK**: Need to check for overlapping events, not just any events
- **ACT**: get_calendars_info() → calendar_search_events() with time range
- **REASON**: Check if any events overlap with requested time. Separate conflicts from upcoming events.
- **RESPOND**: "You are available/not available at [time]" + mention conflicts if any

TOOL GUIDELINES:
- **MANDATORY**: get_calendars_info() BEFORE calendar_search_events()
- **COMPREHENSIVE**: Check ALL calendars, not just primary
- **TIME-AWARE**: Focus on time overlaps, not just event existence
- **ACCURATE**: Use actual calendar data only

RESPONSE FORMAT FOR AVAILABILITY:
✅ "You ARE available at [time]" - if no conflicts
❌ "You are NOT available at [time] due to: [conflicting event]" - if conflicts
📅 "Upcoming: [future event at different time]" - separate from availability

INTERPRETING SEARCH RESULTS:
- Check event start/end times against requested availability time
- Events that start after or end before requested time = NO CONFLICT
- Events that overlap with requested time = CONFLICT
- Example: Meeting at 6 PM does NOT conflict with availability at 4 PM
- Example: Meeting from 3-5 PM DOES conflict with availability at 4 PM

COMMUNICATION: Be direct, show ReAct reasoning, clearly state availability status.

Current User Context: Lead Data Engineer, Masters Student, Python Expert.
"""

def build_manager_agent(memory: ConversationMemory):
    """Build Manager Agent with calendar access only."""
    logger.info("AGENT CONSTRUCTION: Building MANAGER agent with calendar tools")

    current_time = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    conversation_context = memory.get_recent_context(current_agent_type="manager")

    formatted_prompt = MANAGER_SYSTEM_PROMPT.format(
        current_time=current_time,
        conversation_context=conversation_context
    )

    # Manager tools: Calendar only (no RAG)
    tools = [get_current_datetime]
    logger.info("TOOL LOADING: Adding get_current_datetime tool")

    # Add Google Calendar tools
    if CALENDAR_TOOLS_AVAILABLE:
        try:
            calendar_service = build_calendar_service()
            calendar_tools = [
                GetCalendarsInfo(api_resource=calendar_service),
                CalendarSearchEvents(api_resource=calendar_service)
            ]
            tools.extend(calendar_tools)
            logger.info("CALENDAR INTEGRATION: Google Calendar tools loaded successfully")
            print("✅ Manager Agent: Calendar tools loaded.")
        except Exception as e:
            logger.warning(f"CALENDAR INTEGRATION FAILED: {e}")
            print(f"⚠️ Manager Agent: Calendar tools not available: {e}")
    else:
        logger.warning("CALENDAR INTEGRATION: Google Calendar tools not installed")
        print("⚠️ Manager Agent: Calendar tools not available (package not installed)")

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0, max_tokens=4000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4o-mini configured for MANAGER agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.info(f"AGENT READY: MANAGER agent constructed with {len(tools)} tools")
    return AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=10)

# ==============================================================================
# PLANNER AGENT (RAG + Calendar)
# ==============================================================================

PLANNER_SYSTEM_PROMPT = """You are the PLANNER AGENT - Martin Koome's Strategic Scheduling Intelligence.

🤖 MULTI-AGENT SYSTEM: You collaborate with MANAGER (calendar queries) and EXECUTOR (event creation).

Use ReAct approach: OBSERVE → THINK → ACT → REASON → RESPOND

MANDATORY SEQUENCE: get_calendars_info() → calendar_search_events() → search_user_profile_and_policies()

CURRENT TIME: {current_time}
CONVERSATION CONTEXT: {conversation_context}

AGENT COLLABORATION:
- 📅 MANAGER: Provides calendar data and availability information
- 🎯 PLANNER: You create strategic plans with conflict checking and energy optimization
- ✅ EXECUTOR: Will execute your approved recommendations

AVAILABLE TOOLS:
- get_current_datetime: Get current time
- search_user_profile_and_policies: **CRITICAL** - Access energy profiles
- get_calendars_info: **MANDATORY FIRST** - Get ALL calendars
- calendar_search_events: Search ALL calendars for availability

STRATEGIC PROCESS:
1. 🎯 Understand scheduling request
2. 🔍 **MANDATORY**: Get ALL calendars → Search ALL for CONFLICTS → Get energy profile
3. 🧠 Apply energy-aware logic (Peak: 4:30-6AM, 8AM-12PM; Avoid: 1-4PM)
4. 📝 Generate conflict-free recommendations

CONFLICT CHECKING REQUIREMENTS:
- **MANDATORY**: Always call get_calendars_info() and calendar_search_events() FIRST
- **VERIFY**: Check proposed time slots against ALL existing events
- **REJECT**: Never suggest times that conflict with existing events
- **VALIDATE**: Confirm availability before presenting recommendations

ENERGY RULES:
- Peak: 4:30-6:00 AM, 8:00-12:00 PM
- Avoid: 1:00-4:00 PM (low energy)
- Prefer early slots, >90 min blocks

ReAct PROCESS:
- **OBSERVE**: What to schedule and when?
- **THINK**: Which calendars? Energy constraints? EXISTING CONFLICTS?
- **ACT**: **MANDATORY** - Check ALL calendars for conflicts + get energy profile
- **REASON**: Combine calendar conflicts + energy data → Only suggest available times
- **RESPOND**: Provide conflict-free scheduling plan

TOOL GUIDELINES:
- **MANDATORY SEQUENCE**: calendars_info() → search_events() → profile_search()
- **COMPREHENSIVE**: Check ALL calendars
- **ENERGY-AWARE**: Always consider user patterns

RESPONSE: Show ReAct process, explain reasoning, provide actionable plans.

EXECUTABLE PLAN FORMAT:
When recommending scheduling, provide:
🎯 **RECOMMENDED TIME**: [Specific time]
👥 **ATTENDEES**: [Who should attend]
📝 **TITLE**: [Clear event title]
⏱️ **DURATION**: [Length in minutes]
📅 **CALENDAR**: [Which calendar to use]
💡 **RATIONALE**: [Why this time is optimal]

**DO NOT CREATE EVENTS** - Provide structured plans for Executor to implement.

Current User Context: Lead Data Engineer, Masters Student, Python Expert.
"""

def build_planner_agent(memory: ConversationMemory):
    """Build Planner Agent with RAG + Calendar access."""
    logger.info("AGENT CONSTRUCTION: Building PLANNER agent with RAG + Calendar tools")

    current_time = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    conversation_context = memory.get_recent_context(current_agent_type="planner")

    formatted_prompt = PLANNER_SYSTEM_PROMPT.format(
        current_time=current_time,
        conversation_context=conversation_context
    )

    # Planner tools: RAG + Calendar
    tools = [
        get_strategic_memory_tool(),
        get_current_datetime
    ]
    logger.info("TOOL LOADING: Adding strategic memory and datetime tools")

    # Add Google Calendar tools
    if CALENDAR_TOOLS_AVAILABLE:
        try:
            calendar_service = build_calendar_service()
            calendar_tools = [
                GetCalendarsInfo(api_resource=calendar_service),
                CalendarSearchEvents(api_resource=calendar_service)
            ]
            tools.extend(calendar_tools)
            logger.info("CALENDAR INTEGRATION: Google Calendar tools loaded successfully")
            print("✅ Planner Agent: RAG + Calendar tools loaded.")
        except Exception as e:
            logger.warning(f"CALENDAR INTEGRATION FAILED: {e}")
            print(f"⚠️ Planner Agent: Calendar tools not available: {e}")
    else:
        logger.warning("CALENDAR INTEGRATION: Google Calendar tools not installed")
        print("⚠️ Planner Agent: Calendar tools not available (package not installed)")

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0, max_tokens=4000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4o-mini configured for PLANNER agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.info(f"AGENT READY: PLANNER agent constructed with {len(tools)} tools")
    return AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=15)

# ==============================================================================
# EXECUTOR AGENT (Calendar Execution)
# ==============================================================================

EXECUTOR_SYSTEM_PROMPT = """You are the EXECUTOR AGENT - Martin Koome's Calendar Execution Specialist.

🤖 MULTI-AGENT SYSTEM: You work with MANAGER (calendar queries) and PLANNER (strategic planning).

Use ReAct approach: OBSERVE → THINK → ACT → REASON → RESPOND

MANDATORY: Execute confirmed calendar scheduling requests with precision.

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
- calendar_search_events: Verify no conflicts before creating
- create_calendar_event: **PRIMARY TOOL** - Create new calendar events
- calendar_update_event: Update existing events
- calendar_delete_event: Delete events if needed

EXECUTION WORKFLOW:
1. **OBSERVE**: Check LAST PLANNER RESULT for ALL structured plan details (may contain multiple events)
2. **THINK**: Parse ALL plan details, validate information, check for missing data
3. **ACT**: Create MULTIPLE calendar events if plan contains multiple recommendations
4. **REASON**: Verify successful creation of ALL events, handle any errors, confirm scheduling
5. **RESPOND**: Clear confirmation of ALL scheduled events with details

MULTI-EVENT EXECUTION:
- If plan contains numbered recommendations (1., 2., 3., etc.) → Create ALL events
- If plan contains single recommendation → Create one event
- Parse each recommendation's TIME, TITLE, DURATION, ATTENDEES, CALENDAR
- Create events sequentially, validating each one

CALENDAR CREATION REQUIREMENTS:
- **summary**: Use TITLE from each plan item
- **start_datetime**: Parse RECOMMENDED TIME from each plan item
- **end_datetime**: Calculate from start + DURATION for each item
- **timezone**: Use "Africa/Johannesburg" (CAT timezone)
- **description**: Include ATTENDEES and RATIONALE from each plan item
- **calendar_id**: Use "mkoome@andrew.cmu.edu" as primary calendar

PLAN EXECUTION PRIORITY:
- If LAST PLANNER RESULT contains structured plan → Execute that plan
- If user provides specific details → Use those details
- Always prefer structured plan data over user rephrasing

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
📅 Calendar: [Calendar Name]
🔗 View: [Event Link]"

Current User Context: Lead Data Engineer, Masters Student, Python Expert.
"""

def build_executor_agent(memory: ConversationMemory):
    """Build Executor Agent with calendar creation/update tools."""
    logger.info("AGENT CONSTRUCTION: Building EXECUTOR agent with full calendar management tools")

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

    # Executor tools: Full calendar management
    tools = [get_current_datetime]
    logger.info("TOOL LOADING: Adding datetime tool")

    # Add Google Calendar tools
    if CALENDAR_TOOLS_AVAILABLE:
        try:
            calendar_service = build_calendar_service()
            calendar_tools = [
                GetCalendarsInfo(api_resource=calendar_service),
                CalendarSearchEvents(api_resource=calendar_service),
                CalendarCreateEvent(api_resource=calendar_service),
                CalendarUpdateEvent(api_resource=calendar_service),
                CalendarDeleteEvent(api_resource=calendar_service)
            ]
            tools.extend(calendar_tools)
            logger.info("CALENDAR INTEGRATION: Full calendar management tools loaded successfully")
            print("✅ Executor Agent: Full calendar management tools loaded.")
        except Exception as e:
            logger.warning(f"CALENDAR INTEGRATION FAILED: {e}")
            print(f"⚠️ Executor Agent: Calendar tools not available: {e}")
    else:
        logger.warning("CALENDAR INTEGRATION: Google Calendar tools not installed")
        print("⚠️ Executor Agent: Calendar tools not available (package not installed)")

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0, max_tokens=4000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4o-mini configured for EXECUTOR agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.info(f"AGENT READY: EXECUTOR agent constructed with {len(tools)} tools")
    return AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=10)

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
            print("✅ Multi-Agent System initialized successfully!")
            print("🤖 Agents: Manager (Calendar Query) | Planner (Strategic Planning) | Executor (Calendar Execution)")
        except Exception as e:
            print(f"❌ Failed to initialize agents: {e}")
            raise

    def route_query(self, user_query: str) -> AgentType:
        """Route query to appropriate agent based on intent."""
        return classify_intent(user_query)

    def process_query(self, user_query: str) -> tuple[str, AgentType]:
        """Process query with appropriate agent."""
        logger.info(f"QUERY PROCESSING: New user query received: '{user_query}'")

        # Classify intent and route to agent
        agent_type = self.route_query(user_query)

        logger.info(f"AGENT SELECTION: {agent_type.value.upper()} AGENT selected for processing")
        print(f"🎯 Intent classified as: {agent_type.value.upper()}")

        # Select appropriate agent
        if agent_type == AgentType.MANAGER:
            agent_executor = self.manager_agent
            agent_name = "Manager"
            logger.info("MODULE USAGE: Loading MANAGER AGENT with calendar query tools")
        elif agent_type == AgentType.PLANNER:
            agent_executor = self.planner_agent
            agent_name = "Planner"
            logger.info("MODULE USAGE: Loading PLANNER AGENT with RAG + calendar planning tools")
        else:  # AgentType.EXECUTOR
            agent_executor = self.executor_agent
            agent_name = "Executor"
            logger.info("MODULE USAGE: Loading EXECUTOR AGENT with calendar creation tools")

        print(f"🤖 Routing to {agent_name} Agent...")

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

        # Extract tools used
        tools_used = []
        if "intermediate_steps" in response:
            for step in response["intermediate_steps"]:
                if hasattr(step[0], 'tool'):
                    tools_used.append(step[0].tool)
                    logger.info(f"TOOL EXECUTION: {step[0].tool} tool was used by {agent_name} agent")

        logger.info(f"RESPONSE GENERATED: {agent_name} agent completed processing")

        # Add to memory with agent type
        self.memory.add_turn(user_query, response["output"], tools_used, agent_type.value)

        # Add agent identification to response
        agent_icon = {'manager': '📅', 'planner': '🎯', 'executor': '✅'}.get(agent_type.value, '🤖')
        identified_response = f"{agent_icon} **{agent_name.upper()} AGENT RESPONSE:**\n\n{response['output']}"

        logger.info(f"FINAL RESPONSE: {agent_name} agent response prepared with identification")

        return identified_response, agent_type

# ==============================================================================
# END OF AGENTS MODULE
# ==============================================================================