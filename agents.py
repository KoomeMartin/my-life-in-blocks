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
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from supabase_rag import SupabaseVectorStore
from supabase_memory import SupabaseMemoryManager

# --- EMAIL SERVICE IMPORTS ---
try:
    from email_service import GmailEmailService
    from email_templates import weekly_review_template, progress_report_template, simple_notification_template
    EMAIL_SERVICE_AVAILABLE = True
    logger.info("✅ EMAIL SERVICE: Gmail email service imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ EMAIL SERVICE: Not available - {e}")
    EMAIL_SERVICE_AVAILABLE = False
    GmailEmailService = None
    weekly_review_template = None
    progress_report_template = None
    simple_notification_template = None

# --- ADAPTIVE CONTROL IMPORTS ---
try:
    from adaptive_control import (
        ToolResultCache,
        RetryStrategy,
        GroundednessEvaluator,
        ConfidenceEvaluator,
        AdaptiveMetrics,
        get_ttl_for_tool,
        ToolExecutionError
    )
    ADAPTIVE_CONTROL_AVAILABLE = True
    logger.info("✅ ADAPTIVE CONTROL: Imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ ADAPTIVE CONTROL: Not available - {e}")
    ADAPTIVE_CONTROL_AVAILABLE = False
    ToolResultCache = None
    RetryStrategy = None
    GroundednessEvaluator = None
    ConfidenceEvaluator = None
    AdaptiveMetrics = None
    get_ttl_for_tool = None
    ToolExecutionError = None

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
# CONVERSATION MEMORY SYSTEM (Supabase-backed)
# ==============================================================================

class ConversationMemory:
    """Memory system to maintain context of previous conversations using Supabase."""
    def __init__(self, max_turns: int = 20, session_id: str = None, user_id: str = None):
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_turns = max_turns
        self.session_start_time = datetime.datetime.now().isoformat()
        self.last_planner_result: Dict[str, Any] = {}  # Store last planning result for executor
        
        # Initialize Supabase memory manager
        self.supabase_memory = SupabaseMemoryManager(session_id=session_id, user_id=user_id)
        logger.info(f"✅ SUPABASE MEMORY: Initialized with session_id={self.supabase_memory.session_id}")

    def add_turn(self, user_message: str, agent_response: str, tools_used: List[str] = None, 
                 agent_type: str = "", tool_calls: List[Dict] = None, tool_results: List[Dict] = None):
        """Add a conversation turn to memory with detailed tool logging and Supabase persistence."""
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
        
        # Persist to Supabase
        try:
            # Add user message
            self.supabase_memory.add_message(
                role="user",
                content=user_message,
                agent_type=None
            )
            
            # Add assistant response with tool information
            self.supabase_memory.add_message(
                role="assistant",
                content=agent_response,
                agent_type=agent_type,
                tool_calls=tool_calls,
                tool_results=tool_results
            )
            
            # Log tool usage (with minimal data since we don't have detailed tool info here)
            if tools_used and tool_calls and tool_results:
                # If we have detailed tool information, log it
                for i, tool_name in enumerate(tools_used):
                    tool_input = tool_calls[i] if i < len(tool_calls) else {}
                    tool_output = tool_results[i] if i < len(tool_results) else {}
                    
                    self.supabase_memory.log_tool_usage(
                        agent_type=agent_type,
                        tool_name=tool_name,
                        tool_input=tool_input if isinstance(tool_input, dict) else {'raw': str(tool_input)},
                        tool_output=tool_output,
                        execution_time_ms=0,  # Not tracked at this level
                        success=True
                    )
            elif tools_used:
                # If we only have tool names, log with minimal data
                for tool_name in tools_used:
                    self.supabase_memory.log_tool_usage(
                        agent_type=agent_type,
                        tool_name=tool_name,
                        tool_input={},
                        tool_output="Tool executed successfully",
                        execution_time_ms=0,
                        success=True
                    )
            
            logger.info("✅ SUPABASE MEMORY: Conversation turn persisted to database")
        except Exception as e:
            logger.warning(f"⚠️ SUPABASE MEMORY: Failed to persist turn - {e}")

        # Keep only the most recent turns in local memory
        if len(self.conversation_history) > self.max_turns:
            logger.info(f"MEMORY CLEANUP: Trimming memory to last {self.max_turns} turns")
            self.conversation_history = self.conversation_history[-self.max_turns:]

    def store_planner_result(self, planner_response: str, user_id: str = "default_user"):
        """Store the last planning result for potential execution and learning."""
        logger.info("PLANNER RESULT STORAGE: Storing planner response for executor access")
        logger.info(f"PLANNED CONTENT: '{planner_response[:150]}{'...' if len(planner_response) > 150 else ''}'")

        parsed_plan = self._parse_planner_response(planner_response)
        
        self.last_planner_result = {
            "response": planner_response,
            "timestamp": datetime.datetime.now().isoformat(),
            "parsed_plan": parsed_plan
        }
        
        # Save plan to persistent memory for future reuse
        try:
            if parsed_plan.get('events') or parsed_plan.get('single_event'):
                plan_type = self._infer_plan_type(planner_response)
                
                self.supabase_memory.save_prior_plan(
                    user_id=user_id,
                    plan_type=plan_type,
                    plan_description=planner_response[:200],
                    plan_details=parsed_plan,
                    execution_status='proposed',
                    energy_aware='energy' in planner_response.lower() or 'peak' in planner_response.lower()
                )
                logger.info(f"✅ MEMORY: Saved plan to persistent memory (type: {plan_type})")
        except Exception as e:
            logger.warning(f"⚠️ MEMORY: Failed to save plan - {e}")
    
    def _infer_plan_type(self, response: str) -> str:
        """Infer plan type from response content"""
        response_lower = response.lower()
        
        if 'meeting' in response_lower or 'attendees' in response_lower:
            return 'meeting'
        elif 'study' in response_lower or 'exam' in response_lower:
            return 'study_session'
        elif 'work' in response_lower or 'project' in response_lower:
            return 'work_block'
        else:
            return 'personal'
    
    def learn_preference_from_approval(self, user_id: str = "default_user"):
        """Learn user preferences when they approve a plan"""
        try:
            if not self.last_planner_result:
                return
            
            parsed_plan = self.last_planner_result.get('parsed_plan', {})
            
            # Extract time preferences from approved plan
            if parsed_plan.get('single_event'):
                event = parsed_plan['single_event']
                if 'time' in event:
                    time_str = event['time']
                    
                    # Extract hour from time string
                    # Handle different formats:
                    # - "10:00 AM" -> 10
                    # - "14:00" -> 14
                    # - "2026-02-17 20:00" -> 20
                    # - "2026-02-17 20" -> 20
                    
                    hour = None
                    try:
                        # If it contains a date (YYYY-MM-DD), extract just the time part
                        if '-' in time_str and len(time_str) > 10:
                            # Format: "2026-02-17 20:00" or "2026-02-17 20"
                            time_part = time_str.split(' ', 1)[1] if ' ' in time_str else time_str
                            if ':' in time_part:
                                hour = int(time_part.split(':')[0])
                            else:
                                hour = int(time_part)
                        elif ':' in time_str:
                            # Format: "10:00 AM" or "14:00"
                            hour = int(time_str.split(':')[0])
                        else:
                            # Format: just a number "20"
                            hour = int(time_str)
                        
                        if hour is not None and 0 <= hour <= 23:
                            # Save as preference
                            plan_type = self._infer_plan_type(self.last_planner_result['response'])
                            preference_key = f"preferred_{plan_type}_time"
                            
                            self.supabase_memory.save_user_preference(
                                user_id=user_id,
                                preference_key=preference_key,
                                preference_value={'hour': hour, 'time_string': time_str},
                                preference_type='scheduling',
                                source='learned',
                                confidence_score=0.6  # Start with moderate confidence
                            )
                            logger.info(f"✅ LEARNING: Learned preference {preference_key} = hour {hour} (from '{time_str}')")
                        else:
                            logger.warning(f"⚠️ LEARNING: Invalid hour {hour} extracted from '{time_str}'")
                    
                    except (ValueError, IndexError) as e:
                        logger.warning(f"⚠️ LEARNING: Could not parse time from '{time_str}': {e}")
            
        except Exception as e:
            logger.warning(f"⚠️ LEARNING: Failed to learn preference - {e}")

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
            agent_icon = {'manager': '📅', 'planner': '🎯', 'executor': '✅', 'reviewer': '📊'}.get(agent_type, '🤖')

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

    def get_chat_history_for_langchain(self, max_turns: int = 5) -> List:
        """Get recent conversation history in LangChain message format."""
        from langchain_core.messages import HumanMessage, AIMessage
        
        if not self.conversation_history:
            return []
        
        recent_turns = self.conversation_history[-max_turns:]
        messages = []
        
        for turn in recent_turns:
            messages.append(HumanMessage(content=turn['user_message']))
            messages.append(AIMessage(content=turn['agent_response']))
        
        return messages

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
    Loads the existing Supabase vector store.
    Connects to the migrated data in Supabase (PostgreSQL + pgvector).
    """
    logger.info("🔧 TOOL LOADING: Initializing Supabase vector store connection")
    
    try:
        # Connect to Supabase vector store
        vectorstore = SupabaseVectorStore(
            collection_name="advanced_agentic_brain"
        )
        
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        
        logger.info("✅ SUPABASE: Successfully connected to vector store")
        
        return create_retriever_tool(
            retriever,
            "search_user_profile_and_policies",
            "Searches the user's 'Strategic Brain' for energy constraints, course syllabi, deadlines, and skills."
        )
    except Exception as e:
        logger.error(f"❌ SUPABASE: Failed to load vector store - {e}")
        raise

# ==============================================================================
# 2. TOOL: TEMPORAL AWARENESS (The "3rd Tool" for Feedback)
# ==============================================================================
@tool
def get_current_datetime(query: str = "") -> str:
    """
    Returns the current date and time in Africa/Maputo timezone (UTC+2).
    ALWAYS call this first to get timezone-aware current time.
    
    Returns format: "Tuesday, 2026-02-17 18:44:58 CAT (UTC+0200)"
    """
    import pytz
    tz = pytz.timezone('Africa/Maputo')
    now = datetime.datetime.now(tz)
    return now.strftime("%A, %Y-%m-%d %H:%M:%S %Z (UTC%z)")


@tool
def send_review_email(
    recipient_email: str,
    review_content: str,
    date_range: str = "",
    email_type: str = "weekly_review"
) -> str:
    """
    Send a review report via email using Gmail API.
    
    Use this tool when user asks to:
    - "Email me my review"
    - "Send me my weekly review"
    - "Email my progress report"
    
    Args:
        recipient_email: Email address to send to (e.g., "user@example.com")
        review_content: The review content/report to send (plain text format)
        date_range: Date range for the review (e.g., "Feb 11-18, 2026")
        email_type: Type of email - "weekly_review", "progress_report", or "simple"
    
    Returns:
        str: Success or error message
    
    Example:
        send_review_email(
            recipient_email="mkoome@andrew.cmu.edu",
            review_content="Your weekly review content here...",
            date_range="Feb 11-18, 2026",
            email_type="weekly_review"
        )
    """
    try:
        if not EMAIL_SERVICE_AVAILABLE:
            return "❌ Email service not available. Please check email_service.py is installed."
        
        # Initialize email service
        email_service = GmailEmailService()
        
        # Parse review content to extract structured data
        # For now, send as simple notification
        # TODO: Parse review_content to extract metrics for beautiful template
        
        if email_type == "weekly_review":
            subject = f"📊 Your Weekly Review - {date_range}" if date_range else "📊 Your Weekly Review"
            
            # Create simple HTML for now (can be enhanced to parse metrics)
            html_body = simple_notification_template(
                title="Weekly Review",
                message=review_content,
                emoji="📊"
            )
        elif email_type == "progress_report":
            subject = "📈 Your Progress Report"
            html_body = simple_notification_template(
                title="Progress Report",
                message=review_content,
                emoji="📈"
            )
        else:
            subject = "📧 Review from Your REVIEWER Agent"
            html_body = simple_notification_template(
                title="Review Report",
                message=review_content,
                emoji="📧"
            )
        
        # Send email
        success = email_service.send_email(
            to=recipient_email,
            subject=subject,
            body=review_content,
            html_body=html_body
        )
        
        if success:
            return f"✅ Email sent successfully to {recipient_email}! Check your inbox."
        else:
            return f"❌ Failed to send email to {recipient_email}. Check logs for details."
            
    except Exception as e:
        logger.error(f"❌ Email tool error: {e}")
        return f"❌ Error sending email: {str(e)}"


@tool
def get_agent_interaction_analytics(user_id: str = "default_user", days: int = 7) -> str:
    """
    Get agent interaction quality metrics for weekly reviews.
    
    Use this tool to analyze:
    - How often each agent (MANAGER, PLANNER, EXECUTOR) was used
    - Success rate of PLANNER → EXECUTOR workflow
    - Follow-through rate on planned tasks
    - Most used agent
    
    Args:
        user_id: User identifier (default: "default_user")
        days: Number of days to analyze (default: 7 for weekly)
    
    Returns:
        str: Formatted analytics report with agent interaction metrics
    
    Example:
        get_agent_interaction_analytics(user_id="default_user", days=7)
    """
    try:
        from supabase_memory import get_agent_interaction_metrics
        
        metrics = get_agent_interaction_metrics(user_id, days)
        
        if not metrics:
            return "❌ No agent interaction data available for this period."
        
        # Format the response
        report = f"""🤖 AGENT INTERACTION ANALYTICS ({days} days)

📊 Agent Usage:
"""
        for agent, count in metrics.get('agent_usage', {}).items():
            report += f"  • {agent.upper()}: {count} interactions\n"
        
        report += f"""
✅ Workflow Success:
  • Planner → Executor Success: {metrics.get('executor_count', 0)}/{metrics.get('planner_count', 0)} ({metrics.get('planner_executor_success_rate', 0)}%)
  • Follow-through Rate: {metrics.get('completed_tasks', 0)}/{metrics.get('total_tasks', 0)} ({metrics.get('follow_through_rate', 0)}%)

📈 Summary:
  • Total Interactions: {metrics.get('total_interactions', 0)}
  • Most Used Agent: {metrics.get('most_used_agent', 'N/A').upper() if metrics.get('most_used_agent') else 'N/A'}
"""
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Agent interaction analytics error: {e}")
        return f"❌ Error getting agent interaction analytics: {str(e)}"


@tool
def get_memory_learning_analytics(user_id: str = "default_user", days: int = 7) -> str:
    """
    Get memory and learning metrics for weekly reviews.
    
    Use this tool to analyze:
    - Number of conversation sessions
    - New preferences learned
    - Plan reuse patterns
    - Learning velocity (improvement rate)
    - Most queried topics
    
    Args:
        user_id: User identifier (default: "default_user")
        days: Number of days to analyze (default: 7 for weekly)
    
    Returns:
        str: Formatted analytics report with memory and learning metrics
    
    Example:
        get_memory_learning_analytics(user_id="default_user", days=7)
    """
    try:
        from supabase_memory import get_memory_learning_metrics
        
        metrics = get_memory_learning_metrics(user_id, days)
        
        if not metrics:
            return "❌ No memory/learning data available for this period."
        
        # Format the response
        report = f"""🧠 MEMORY & LEARNING ANALYTICS ({days} days)

📚 Session Activity:
  • Sessions Completed: {metrics.get('sessions_completed', 0)}
  • Most Queried Topic: "{metrics.get('most_queried_topic', 'N/A')}"

💡 Learning Progress:
  • New Preferences Learned: {metrics.get('preferences_learned', 0)}
  • Previous Period: {metrics.get('prev_preferences_count', 0)}
  • Learning Velocity: {metrics.get('learning_velocity', 0):+.1f}%

🎯 Pattern Recognition:
  • Plan Reuse Count: {metrics.get('plan_reuse_count', 0)}
  • Avg Preference Confidence: {metrics.get('avg_preference_confidence', 0):.1f}/10

📈 Insight:
"""
        
        # Add contextual insight
        velocity = metrics.get('learning_velocity', 0)
        if velocity > 20:
            report += "  • Excellent learning rate! System is rapidly adapting to your patterns.\n"
        elif velocity > 0:
            report += "  • Good progress! System is learning your preferences steadily.\n"
        elif velocity == 0:
            report += "  • Stable patterns. System has established your preferences.\n"
        else:
            report += "  • Fewer new patterns this period. Existing preferences are working well.\n"
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Memory learning analytics error: {e}")
        return f"❌ Error getting memory learning analytics: {str(e)}"


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
    REVIEWER = "reviewer"

def classify_intent(user_query: str, conversation_memory: 'ConversationMemory' = None) -> AgentType:
    """
    Enhanced intent classification with context awareness and conversational handling.
    Routes queries to appropriate agents or handles simple conversations directly.
    """
    logger.info(f"INTENT CLASSIFICATION: Analyzing query: '{user_query[:100]}...'")

    query_lower = user_query.lower().strip()
    
    # Check if there's a pending planner result that might need execution
    has_pending_plan = conversation_memory and conversation_memory.last_planner_result
    
    # CONVERSATIONAL KEYWORDS - Simple greetings and small talk (NO AGENT NEEDED)
    conversational_keywords = [
        'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 
        'good evening', 'how are you', 'what\'s up', 'sup', 'yo',
        'thanks', 'thank you', 'bye', 'goodbye', 'see you', 'later',
        'nice', 'cool', 'awesome', 'great job', 'well done'
    ]
    
    # EXECUTOR KEYWORDS - Approval/Confirmation signals + Update/Modify operations (HIGHEST PRIORITY)
    executor_keywords = [
        # Direct confirmations
        'yes', 'okay', 'ok', 'sure', 'fine', 'good', 'great', 'perfect',
        'that works', 'sounds good', 'looks good', 'that\'s fine',
        
        # Approval phrases (specific to executing a plan)
        'go ahead', 'proceed', 'do it', 'schedule it', 'create it',
        'book it', 'set it up', 'make it happen', 'confirm',
        
        # Scheduling commands (specific - with "the" or "that")
        'schedule the meeting', 'create the event', 'add to calendar',
        'book the appointment', 'set up the meeting', 'schedule that',
        'create that', 'book that',
        
        # Update/Modify operations
        'update', 'modify', 'change', 'edit', 'reschedule', 'move',
        'update the meeting', 'change the time', 'move the event',
        'reschedule the meeting', 'edit the event', 'modify the meeting',
        
        # Attendee management
        'add attendees', 'invite', 'add people', 'include',
        'add to the meeting', 'invite to', 'include in',
        
        # Agreement variations
        'sure that okay', 'sure that\'s okay', 'that okay', 'that\'s okay',
        'yes please', 'please do'
    ]
    
    # PLANNER KEYWORDS - Complex scheduling requiring strategy
    planner_keywords = [
        'schedule', 'plan', 'organize', 'arrange', 'find time', 'when can',
        'best time', 'optimal time', 'available time', 'free time',
        'meeting with', 'appointment with', 'session for', 'time for',
        'next available', 'earliest', 'soonest', 'later today', 'tomorrow',
        'this week', 'next week', 'energy', 'productivity', 'focus',
        'book', 'booking', 'reserve', 'set up', 'create meeting', 'create event',
        'invite', 'attendees', 'group meeting', 'team meeting'
    ]
    
    # MANAGER KEYWORDS - Simple queries and information requests
    manager_keywords = [
        'what', 'when', 'where', 'how', 'show', 'list', 'check', 'view',
        'what\'s my', 'what is my', 'do i have', 'am i', 'are there',
        'calendar', 'schedule for', 'events', 'meetings', 'busy', 'free',
        'available', 'today', 'this week', 'next week'
    ]
    
    # REVIEWER KEYWORDS - Analytics, progress tracking, accountability, and email reports
    reviewer_keywords = [
        'review', 'weekly review', 'monthly review', 'progress', 'how am i doing',
        'how did i do', 'performance', 'metrics', 'analytics', 'report',
        'summary', 'insights', 'patterns', 'trends', 'statistics', 'stats',
        'accountability', 'track', 'tracking', 'achievement', 'achievements',
        'email me', 'send me', 'email my review', 'send my review',
        'email me my review', 'send me my review', 'email weekly review',
        'send weekly review', 'email progress', 'send progress report'
        'goals', 'goal progress', 'completion rate', 'productivity',
        'how productive', 'energy alignment', 'behavioral patterns',
        'weekly summary', 'monthly summary', 'what patterns', 'analyze',
        'analysis', 'how have i been', 'am i on track', 'progress report'
    ]
    
    # PRIORITY 0: Check for simple conversational queries (NO AGENT ROUTING)
    # These should be handled directly without tool usage
    # STRICT CHECK: Only pure greetings/thanks with NO scheduling keywords
    query_words = query_lower.split()
    
    # First check if there's ANY scheduling intent
    has_scheduling_intent = any(keyword in query_lower for keyword in planner_keywords + manager_keywords + executor_keywords)
    has_review_intent = any(keyword in query_lower for keyword in reviewer_keywords)
    
    logger.info(f"INTENT CHECK: Query has {len(query_words)} words, scheduling_intent={has_scheduling_intent}, review_intent={has_review_intent}")
    
    # PRIORITY 0.5: Check for REVIEWER intent FIRST (highest priority for analytics queries)
    if has_review_intent:
        logger.info("DECISION: Routing to REVIEWER AGENT - Analytics/progress tracking request")
        return AgentType.REVIEWER
    
    # CRITICAL: If there's ANY scheduling intent, NEVER treat as conversational
    if has_scheduling_intent:
        matched_planner = [kw for kw in planner_keywords if kw in query_lower]
        matched_manager = [kw for kw in manager_keywords if kw in query_lower]
        matched_executor = [kw for kw in executor_keywords if kw in query_lower]
        logger.info(f"SCHEDULING KEYWORDS FOUND: planner={matched_planner[:3]}, manager={matched_manager[:3]}, executor={matched_executor[:3]}")
        # Continue to agent routing below
    else:
        # Only treat as conversational if NO scheduling keywords AND it's a short greeting
        if len(query_words) <= 3:
            starts_with_greeting = len(query_words) > 0 and query_words[0] in conversational_keywords
            if starts_with_greeting:
                logger.info("DECISION: CONVERSATIONAL - Pure greeting/small talk (no agent routing)")
                return None  # Signal to handle conversationally
    
    # PRIORITY 1: Check for numeric selection (choosing from options)
    # If user responds with just a number (1-10), it's likely selecting from options
    # Route to PLANNER to create a plan for that time slot
    if len(query_words) == 1 and query_lower.isdigit():
        option_number = int(query_lower)
        if 1 <= option_number <= 10:
            logger.info(f"DECISION: Routing to PLANNER AGENT - Numeric selection ({option_number}) from options")
            return AgentType.PLANNER
    
    # PRIORITY 2: Check for executor intent (approval/confirmation)
    # Executor should only trigger for:
    # 1. Short confirmations (1-5 words) when there's a pending PLANNER plan
    # 2. Explicit execution phrases like "schedule it", "book it" (with "it" or "the")
    
    if has_pending_plan:
        # Short positive responses when there's a pending plan
        short_confirmations = [
            'yes', 'ok', 'okay', 'sure', 'fine', 'good', 'great', 'perfect',
            'correct', 'right', 'exactly', 'yep', 'yup', 'yeah', 'affirmative',
            'approved', 'agree', 'confirmed'
        ]
        
        # Check for single-word confirmations
        if query_lower in short_confirmations:
            logger.info("DECISION: Routing to EXECUTOR AGENT - Short approval with pending plan")
            return AgentType.EXECUTOR
        
        # Check for short phrases (2-5 words) that are clearly confirmations
        if len(query_words) <= 5:
            confirmation_phrases = [
                'yes please', 'sounds good', 'looks good', 'that works',
                'go ahead', 'do it', 'make it', 'that\'s right', 'that\'s correct',
                'yes do it', 'yes go ahead', 'please proceed', 'let\'s do it',
                'that will do', 'that\'ll do', 'that works for me'
            ]
            if any(phrase in query_lower for phrase in confirmation_phrases):
                logger.info("DECISION: Routing to EXECUTOR AGENT - Confirmation phrase with pending plan")
                return AgentType.EXECUTOR
    
    # Check for explicit executor keywords (phrases with "it", "the", "that")
    explicit_executor_phrases = [
        'schedule it', 'create it', 'book it', 'schedule the', 'create the', 
        'book the', 'schedule that', 'create that', 'book that',
        'go ahead', 'proceed', 'do it', 'make it happen', 'confirm'
    ]
    if any(phrase in query_lower for phrase in explicit_executor_phrases):
        logger.info("DECISION: Routing to EXECUTOR AGENT - Explicit execution command")
        return AgentType.EXECUTOR
    
    # PRIORITY 2: Check for MANAGER intent FIRST for availability/information queries
    # These are simpler queries that don't require planning
    availability_query_patterns = [
        'my availability', 'am i available', 'am i free', 'am i busy',
        'do i have', 'what\'s my', 'what is my', 'show me', 'check my',
        'list my', 'view my', 'when am i', 'where am i'
    ]
    
    # Check if this is an availability/information query (not a scheduling request)
    is_availability_query = any(pattern in query_lower for pattern in availability_query_patterns)
    
    if is_availability_query or (any(keyword in query_lower for keyword in manager_keywords) and 
                                  not any(kw in query_lower for kw in ['schedule', 'plan', 'book', 'create', 'organize', 'arrange'])):
        logger.info("DECISION: Routing to MANAGER AGENT - Information/availability request")
        return AgentType.MANAGER
    
    # PRIORITY 3: Check for planner intent (scheduling requests)
    if any(keyword in query_lower for keyword in planner_keywords):
        logger.info("DECISION: Routing to PLANNER AGENT - Complex scheduling request")
        return AgentType.PLANNER
    
    # INTELLIGENT FALLBACK: If there's a pending plan and query is short/ambiguous,
    # assume it's a confirmation (context-aware routing)
    if has_pending_plan and len(query_words) <= 5:
        # Check if query contains NEW scheduling keywords (new request)
        has_new_scheduling_request = any(kw in query_lower for kw in [
            'schedule', 'plan', 'book', 'create', 'meeting', 'appointment',
            'find time', 'when', 'what', 'show', 'list'
        ])
        
        if not has_new_scheduling_request:
            # Short, ambiguous query with pending plan → likely a confirmation
            logger.info("DECISION: Routing to EXECUTOR AGENT - Context-aware: short query with pending plan (likely confirmation)")
            return AgentType.EXECUTOR
    
    # DEFAULT: Route to MANAGER for unclear queries
    logger.info("DECISION: Routing to MANAGER AGENT - Unclear intent, defaulting to manager")
    return AgentType.MANAGER

# ==============================================================================
# MANAGER AGENT (Calendar Only)
# ==============================================================================

MANAGER_SYSTEM_PROMPT = """You are the MANAGER AGENT - Martin Koome's Calendar Intelligence Hub.

🤖 MULTI-AGENT SYSTEM: You work with PLANNER (strategic scheduling) and EXECUTOR (event creation) agents.

Use ReAct approach: OBSERVE → THINK → ACT → REASON → RESPOND

**INTELLIGENT TOOL USAGE:**
- Use tools ONLY when the query requires calendar data or current time
- For simple greetings or acknowledgments, respond directly without tools
- Examples of NO TOOL NEEDED: "Hello", "Thanks", "Got it", "Okay"
- Examples of TOOLS NEEDED: "What meetings do I have?", "Am I free at 2 PM?", "Check my calendar"

⚠️ **CRITICAL TIME LOGIC RULE:**
Two events CONFLICT only if they OVERLAP in time. Events that are adjacent (one ends exactly when another starts) or separated in time do NOT conflict.
- Meeting 12:00-1:00 PM + Request 1:00-1:30 PM = ✅ AVAILABLE (adjacent, not overlapping)
- Meeting 3:00-4:00 PM + Request 1:00-1:30 PM = ✅ AVAILABLE (completely separate times)
- Meeting 12:30-1:30 PM + Request 1:00-2:00 PM = ❌ CONFLICT (overlap from 1:00-1:30 PM)

**CRITICAL AVAILABILITY CHECK PROCESS:**
When checking if user is available at a specific time (e.g., "Am I available at 9 AM?"):
1. Determine the time window to check (e.g., 9:00 AM for 1 hour = 9:00-10:00 AM)
2. Search for ALL events that could overlap with this window:
   - Events that START BEFORE the requested time (e.g., 8:00 AM event might extend past 9:00 AM)
   - Events that START DURING the requested time (e.g., 9:30 AM event)
   - Events that START AFTER but BEFORE the end time (e.g., 9:45 AM event)
3. For EACH event found, check if it overlaps:
   - Event 8:00-9:50 AM overlaps with 9:00-10:00 AM request ❌ CONFLICT
   - Event 10:00-11:00 AM does NOT overlap with 9:00-10:00 AM request ✅ NO CONFLICT
4. If ANY event overlaps, user is NOT available

**SEARCH STRATEGY FOR AVAILABILITY:**
To find ALL potentially conflicting events, search a WIDER time range:
- If checking 9:00 AM availability, search from 7:00 AM to 11:00 AM
- This catches events that start before, during, or shortly after the requested time
- Then apply overlap logic to each event found

MANDATORY TOOL USAGE:
1. ALWAYS call get_current_datetime() FIRST for any query
2. ALWAYS call get_calendars_info() to get ALL calendars  
3. ALWAYS call calendar_search_events() to search calendars
4. Use actual tool results in your response - never guess or assume

ENHANCED CALENDAR FEATURES:
- Explicit calendar targeting: Always uses mkoome@andrew.cmu.edu calendar
- Optimized result limits: 25 results for efficient manager queries
- Pre-configured calendar ID for consistent targeting

CONVERSATION HISTORY:
- Previous conversation turns are automatically available in chat history
- Use get_current_datetime() tool to get current time with timezone

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
4. **STOP AFTER ONE SEARCH** - Do NOT repeatedly search the same time ranges

**CRITICAL: AVOID INFINITE LOOPS**
- Search the calendar ONCE for the relevant time period
- Analyze the results and provide your answer
- DO NOT search multiple overlapping time ranges
- DO NOT repeat the same search with different parameters
- If you've already searched a time range, use those results
- Make a decision and respond - do not keep searching

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

def build_manager_agent():
    """Build Manager Agent with enhanced calendar access (built once, reused)."""
    logger.info("AGENT CONSTRUCTION: Building MANAGER agent with enhanced calendar tools")

    # No context formatting - agent will use tools for current time
    # Conversation history handled by LangChain automatically

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

    llm = ChatOpenAI(model="gpt-5.2-2025-12-11", api_key=api_key, temperature=0, max_tokens=100000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4 configured for MANAGER agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", MANAGER_SYSTEM_PROMPT),  # Static prompt, no formatting
        MessagesPlaceholder(variable_name="chat_history", optional=True),  # Conversation history
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

**HANDLING NUMERIC SELECTIONS:**
If the user responds with just a number (e.g., "4", "2", "1"), they are selecting from options provided by MANAGER.
- Look at the conversation history to see what options were presented
- The number corresponds to the option number (1 = first option, 2 = second option, etc.)
- Extract the time slot from that option
- Create a structured plan for that specific time slot
- DO NOT search for availability again - the MANAGER already verified it
- Proceed directly to creating the plan with proper format

🧠 **MEMORY & LEARNING**: You have access to prior successful plans. When creating similar plans, consider what worked before and adapt those patterns.

⏰ **TIMEZONE HANDLING - CRITICAL**:
Your calendar uses Africa/Maputo timezone (UTC+2). ALL times must be timezone-aware!

WHEN USER SAYS A TIME:
- "10 AM tomorrow" means 10:00 AM in Africa/Maputo timezone (UTC+2)
- "2 PM today" means 14:00 PM in Africa/Maputo timezone (UTC+2)

CALENDAR SEARCH FORMAT - IMPORTANT:
The calendar tools expect datetime in this format: "YYYY-MM-DD HH:MM:SS" (without timezone suffix)
- ❌ WRONG: "2026-02-18T10:00:00+02:00" (ISO format with timezone - will cause errors!)
- ✅ CORRECT: "2026-02-18 10:00:00" (simple format without timezone)
- ✅ CORRECT: "2026-02-18 14:00:00" (simple format without timezone)

EXAMPLES:
- For "10 AM on Feb 18": use "2026-02-18 10:00:00"
- For "2 PM today": use "2026-02-17 14:00:00"
- For "all day Friday": use "2026-02-21 00:00:00" to "2026-02-21 23:59:59"

CONFLICT DETECTION:
- Calendar events are returned with timezone info
- Your searches use simple format
- The tool handles timezone conversion internally
- Focus on the time values for conflict detection

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

CONVERSATION HISTORY:
- Previous conversation turns are automatically available in chat history
- Use get_current_datetime() tool to get current time with timezone

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

def build_planner_agent():
    """Build Planner Agent with RAG + Enhanced Calendar access (built once, reused)."""
    logger.info("AGENT CONSTRUCTION: Building PLANNER agent with RAG + Enhanced Calendar tools")

    # No context formatting - agent will use tools for current time
    # Conversation history handled by LangChain automatically

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

    llm = ChatOpenAI(model="gpt-5.2-2025-12-11", api_key=api_key, temperature=0, max_tokens=100000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4 configured for PLANNER agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", PLANNER_SYSTEM_PROMPT),  # Static prompt, no formatting
        MessagesPlaceholder(variable_name="chat_history", optional=True),  # Conversation history
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

CONVERSATION HISTORY:
- Previous conversation turns are automatically available in chat history
- Use get_current_datetime() tool to get current time with timezone

PLANNER RECOMMENDATIONS:
- Previous planner recommendations are available in conversation history
- Look for structured plans with time, attendees, title, duration, calendar

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
- **If event not found (404 error)**: The event may have been deleted or doesn't exist. Inform user and offer to create a new event or check calendar
- **If update/delete fails**: Verify the event still exists before retrying. Suggest searching for the event first

SUCCESS CONFIRMATION:
"✅ Meeting scheduled: [Title] at [Time] for [Duration]
📅 Calendar: mkoome@andrew.cmu.edu
🔗 View: [Event Link]"

Current User Context: Lead Data Engineer, Masters Student, Python Expert.
"""

# ==============================================================================
# REVIEWER AGENT (Analytics & Accountability)
# ==============================================================================

REVIEWER_SYSTEM_PROMPT = """You are the REVIEWER AGENT - Martin Koome's Accountability & Progress Tracking Specialist.

🤖 MULTI-AGENT SYSTEM: You work alongside MANAGER (calendar queries), PLANNER (strategic planning), and EXECUTOR (event creation).

🎯 YOUR MISSION: Analyze user's scheduling behavior, track progress, provide insights, and generate accountability reports.

Use ReAct approach: OBSERVE → THINK → ACT → REASON → RESPOND

CORE RESPONSIBILITIES:

1. **PROGRESS TRACKING**
   - Analyze completed vs planned tasks
   - Track goal achievement rates
   - Monitor deadline adherence
   - Measure productivity patterns

2. **BEHAVIORAL ANALYSIS**
   - Identify scheduling patterns
   - Detect energy alignment trends
   - Track meeting attendance
   - Analyze rescheduling frequency

3. **ACCOUNTABILITY REPORTING**
   - Generate weekly/monthly summaries
   - Provide actionable insights
   - Highlight achievements and gaps
   - Suggest improvements

4. **CONTEXT AWARENESS**
   - Full access to conversation history
   - Aware of PLANNER recommendations
   - Tracks EXECUTOR actions
   - Monitors MANAGER queries

CONVERSATION HISTORY:
- Previous conversation turns are automatically available in chat history
- You can see all agent interactions (MANAGER, PLANNER, EXECUTOR)
- Use get_current_datetime() tool to get current time with timezone

AVAILABLE TOOLS:
- get_current_datetime: **MANDATORY FIRST** - Get current time for analysis
- get_calendars_info: **MANDATORY SECOND** - Get ALL calendars for comprehensive review
- calendar_search_events: **MANDATORY THIRD** - Search calendar for completed/upcoming events
  - CRITICAL: Use calendar ID "mkoome@andrew.cmu.edu" in calendars_info parameter
  - Format: calendars_info='mkoome@andrew.cmu.edu'
- search_user_profile_and_policies: Access user energy patterns and preferences
- get_agent_interaction_analytics: **NEW** - Get agent usage and workflow success metrics
- get_memory_learning_analytics: **NEW** - Get learning progress and pattern recognition metrics
- send_review_email: **EMAIL CAPABILITY** - Send review reports via email
  - Use when user asks to "email me my review", "send me my weekly review", etc.
  - Parameters: recipient_email, review_content, date_range, email_type
  - Default email: mkoome@andrew.cmu.edu or koomemartin43@gmail.com

EMAIL WORKFLOW:
When user requests email:
1. Generate the review report first (using calendar + RAG data)
2. Call send_review_email with:
   - recipient_email: "koomemartin43@gmail.com" (user's preferred email)
   - review_content: Your complete review text
   - date_range: The date range analyzed (e.g., "Feb 11-18, 2026")
   - email_type: "weekly_review", "progress_report", or "simple"
3. Confirm email was sent successfully

TOOL USAGE SEQUENCE (MANDATORY):
1. get_current_datetime() - Get current time
2. get_calendars_info() - Get all calendars (for reference)
3. calendar_search_events(calendars_info='mkoome@andrew.cmu.edu', min_datetime='YYYY-MM-DD HH:MM:SS', max_datetime='YYYY-MM-DD HH:MM:SS', max_results=100)
4. search_user_profile_and_policies(query='energy patterns') - Get user profile
5. get_agent_interaction_analytics(user_id='default_user', days=7) - **NEW** Get agent workflow metrics
6. get_memory_learning_analytics(user_id='default_user', days=7) - **NEW** Get learning progress
7. send_review_email(...) - If user requested email

SUPABASE MEMORY ACCESS:
You have FULL access to persistent memory through the conversation context:
- Session history (all conversations)
- User preferences (learned patterns)
- Prior plans (successful schedules)
- Performance metrics (agent effectiveness)
- Tool usage logs (what tools were used when)
- Task completion data (what was accomplished)

ANALYSIS WORKFLOW:

**For Weekly Reviews:**
1. **OBSERVE**: Get current date, determine review period (last 7 days)
2. **THINK**: What metrics matter? (completion rate, energy alignment, goals met, agent interactions, learning progress)
3. **ACT**: 
   - Call get_current_datetime() to get current time
   - Call get_calendars_info() to see available calendars
   - Call calendar_search_events with:
     * calendars_info='mkoome@andrew.cmu.edu'
     * min_datetime = current_date - 7 days (format: 'YYYY-MM-DD HH:MM:SS')
     * max_datetime = current_date (format: 'YYYY-MM-DD HH:MM:SS')
     * max_results=100
   - Call search_user_profile_and_policies(query='energy patterns')
   - Call get_agent_interaction_analytics(user_id='default_user', days=7) - **NEW**
   - Call get_memory_learning_analytics(user_id='default_user', days=7) - **NEW**
4. **REASON**: Calculate metrics, identify patterns, generate insights with agent interaction and learning data
5. **RESPOND**: Provide structured report with actionable recommendations

CRITICAL CALENDAR SEARCH FORMAT:
```
calendar_search_events(
    calendars_info='mkoome@andrew.cmu.edu',
    min_datetime='2026-02-11 00:00:00',
    max_datetime='2026-02-18 23:59:59',
    max_results=100
)
```

DO NOT pass empty string or JSON to calendars_info - use the calendar ID directly!

**For Progress Checks:**
1. **OBSERVE**: Review conversation history for goals/commitments
2. **THINK**: What was promised? What was delivered?
3. **ACT**: Search calendar for evidence of completion
4. **REASON**: Compare planned vs actual, calculate progress
5. **RESPOND**: Clear progress update with next steps

**For Behavioral Insights:**
1. **OBSERVE**: Analyze patterns in conversation and calendar
2. **THINK**: What trends emerge? What's working? What's not?
3. **ACT**: Query calendar for pattern evidence
4. **REASON**: Identify correlations and causations
5. **RESPOND**: Insights with data-backed recommendations

REPORT STRUCTURE:

📊 **WEEKLY REVIEW TEMPLATE:**
```
📊 WEEKLY REVIEW: [Date Range]

🎯 PRODUCTIVITY METRICS
✅ Tasks Completed: X/Y (Z%)
⏰ Time Utilization: X/Y hours (Z%)
📅 Events Attended: X/Y (Z%)
🎓 Study Sessions: X/Y planned (Z%)

⚡ ENERGY ALIGNMENT
✅ Peak Hour Usage: X/Y hours (Z%)
⚠️ Low Energy Usage: X/Y hours (Z%)
📈 Alignment Score: X/10

🤖 AGENT INTERACTION QUALITY (NEW - Use get_agent_interaction_analytics)
✅ Planner → Executor Success: X/Y (Z%)
📊 Follow-through Rate: Z%
🔄 Plan Reuse: X similar plans executed
💡 Most Used Agent: [AGENT_NAME]
📈 Total Interactions: X

🧠 MEMORY & LEARNING (NEW - Use get_memory_learning_analytics)
📚 Sessions Completed: X
🎯 Preferences Learned: X (Previous: Y)
💡 Learning Velocity: +/-X%
🔍 Most Queried: "[topic]"
📈 Preference Confidence: X/10

🔍 KEY INSIGHTS
• [Pattern 1 with data - include agent interaction insights]
• [Pattern 2 with data - include learning progress insights]
• [Pattern 3 with data - include behavioral patterns]

📈 WEEK-OVER-WEEK TRENDS
[Metric]: +/-X% | [Metric]: +/-X%

🎯 RECOMMENDATIONS
• [Actionable recommendation 1]
• [Actionable recommendation 2]
• [Actionable recommendation 3]

💪 ACHIEVEMENTS
• [Notable achievement 1 - can include agent workflow success]
• [Notable achievement 2 - can include learning milestones]

⚠️ AREAS FOR IMPROVEMENT
• [Area 1 with specific suggestion]
• [Area 2 with specific suggestion]
```

METRICS TO TRACK:

**Completion Metrics:**
- Tasks completed vs planned
- Events attended vs scheduled
- Deadlines met vs missed
- Study hours actual vs target

**Energy Metrics:**
- % of tasks in peak hours (4:30-6 AM, 8 AM-12 PM)
- % of tasks in low energy hours (1-4 PM)
- Energy alignment score (0-10)
- Optimal time slot utilization

**Behavioral Metrics:**
- Most common meeting times
- Average meeting duration
- Rescheduling frequency
- Response time to requests

**Progress Metrics:**
- Goals achieved this week/month
- Improvement trends
- Consistency scores
- Productivity velocity

CRITICAL ANALYSIS RULES:

1. **BE DATA-DRIVEN**: Every insight must be backed by calendar data or conversation history
2. **BE SPECIFIC**: Use exact numbers, percentages, and dates
3. **BE ACTIONABLE**: Every recommendation must be implementable
4. **BE HONEST**: Highlight both achievements and gaps
5. **BE CONTEXTUAL**: Consider user's energy patterns and constraints
6. **BE ENCOURAGING**: Frame feedback positively while being truthful

CONVERSATION CONTEXT AWARENESS:

You can see in chat history:
- What PLANNER recommended
- What EXECUTOR created
- What MANAGER reported
- What user requested vs what happened

Use this to:
- Track if plans were executed
- Identify dropped commitments
- Measure follow-through rate
- Detect pattern changes

EXAMPLE INTERACTIONS:

**User: "Give me my weekly review"**
Response:
1. Get current date
2. Search calendar for last 7 days
3. Analyze conversation history
4. Calculate all metrics
5. Generate structured report

**User: "How am I doing with my goals?"**
Response:
1. Review conversation history for stated goals
2. Search calendar for evidence
3. Calculate progress percentage
4. Provide specific feedback

**User: "What patterns do you see in my scheduling?"**
Response:
1. Analyze calendar events over time
2. Identify recurring patterns
3. Compare with energy profile
4. Provide insights with recommendations

TONE & STYLE:
- Professional but encouraging
- Data-driven but empathetic
- Honest but constructive
- Specific but concise
- Motivating but realistic

REMEMBER:
- You have FULL context from all agents
- You can see EVERYTHING in conversation history
- You have access to ALL Supabase memory data
- Your role is ACCOUNTABILITY and INSIGHTS
- Be the agent that helps user stay on track

Current User Context: Lead Data Engineer, Masters Student, Python Expert.
"""

def build_reviewer_agent():
    """Build Reviewer Agent with analytics and memory access (built once, reused)."""
    logger.info("AGENT CONSTRUCTION: Building REVIEWER agent with analytics and memory access")

    # Reviewer tools: RAG + Calendar + DateTime + Email + Analytics
    tools = [
        get_strategic_memory_tool(),
        get_current_datetime,
        send_review_email,
        get_agent_interaction_analytics,
        get_memory_learning_analytics
    ]
    logger.info("TOOL LOADING: Adding strategic memory, datetime, email, and analytics tools to REVIEWER agent")
    logger.info("REVIEWER TOOLS: search_user_profile_and_policies (RAG), get_current_datetime, send_review_email, get_agent_interaction_analytics, get_memory_learning_analytics added")

    # Add Google Calendar tools for comprehensive analysis
    if CALENDAR_TOOLS_AVAILABLE:
        try:
            calendar_service = build_calendar_service()
            calendar_tools = [
                GetCalendarsInfo(api_resource=calendar_service),
                CalendarSearchEvents(
                    api_resource=calendar_service,
                    calendar_id="mkoome@andrew.cmu.edu",
                    max_results=100  # Higher for comprehensive review
                )
            ]
            tools.extend(calendar_tools)
            logger.info("CALENDAR INTEGRATION: Enhanced Google Calendar tools loaded for REVIEWER agent")
            logger.info("REVIEWER TOOLS: GetCalendarsInfo, CalendarSearchEvents (explicit calendar: mkoome@andrew.cmu.edu, max_results=100) added")
        except Exception as e:
            logger.warning(f"CALENDAR INTEGRATION FAILED: {e}")
    else:
        logger.warning("CALENDAR INTEGRATION: Google Calendar tools not installed")

    llm = ChatOpenAI(model="gpt-5.2-2025-12-11", api_key=api_key, temperature=0, max_tokens=100000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4 configured for REVIEWER agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", REVIEWER_SYSTEM_PROMPT),  # Static prompt, no formatting
        MessagesPlaceholder(variable_name="chat_history", optional=True),  # Conversation history
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.info(f"AGENT READY: REVIEWER agent constructed with {len(tools)} tools")
    logger.info(f"REVIEWER TOOL LIST: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]}")
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=15, return_intermediate_steps=True)

def build_executor_agent():
    """Build Executor Agent with enhanced calendar management tools (built once, reused)."""
    logger.info("AGENT CONSTRUCTION: Building EXECUTOR agent with enhanced calendar management tools")

    # No context formatting - agent will use tools for current time
    # Planner results will be available in conversation history
    # Conversation history handled by LangChain automatically

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

    llm = ChatOpenAI(model="gpt-5.2-2025-12-11", api_key=api_key, temperature=0, max_tokens=100000)
    logger.info("LLM CONFIGURATION: ChatOpenAI gpt-4 configured for EXECUTOR agent")

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXECUTOR_SYSTEM_PROMPT),  # Static prompt, no formatting
        MessagesPlaceholder(variable_name="chat_history", optional=True),  # Conversation history
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
        self.reviewer_agent = None
        
        # Initialize adaptive control components (if available)
        if ADAPTIVE_CONTROL_AVAILABLE:
            self.cache = ToolResultCache()
            self.retry_strategy = RetryStrategy(max_retries=3, base_delay=1.0)
            self.groundedness_evaluator = GroundednessEvaluator(threshold=0.7)
            self.confidence_evaluator = ConfidenceEvaluator(threshold=0.6)
            self.metrics = AdaptiveMetrics()
            logger.info("🎯 ADAPTIVE CONTROL: Initialized (caching, retry, groundedness, confidence)")
        else:
            self.cache = None
            self.retry_strategy = None
            self.groundedness_evaluator = None
            self.confidence_evaluator = None
            self.metrics = None
            logger.warning("⚠️ ADAPTIVE CONTROL: Not available - running without optimization")
        
        self.initialize_agents()

    def initialize_agents(self):
        """Initialize all four agents once (no rebuilding on each query)."""
        try:
            logger.info("� Building agents (one-time initialization)...")
            self.manager_agent = build_manager_agent()
            self.planner_agent = build_planner_agent()
            self.executor_agent = build_executor_agent()
            self.reviewer_agent = build_reviewer_agent()
            logger.info("✅ Multi-Agent System initialized - all agents built and ready")
            logger.info("📊 Agents: Manager, Planner, Executor, Reviewer")
            logger.info("📊 Agents will be reused for all queries (no rebuilding)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize agents: {e}")
            raise

    def route_query(self, user_query: str) -> AgentType:
        """Route query to appropriate agent based on intent with context awareness."""
        return classify_intent(user_query, self.memory)
    
    def execute_agent_with_adaptive_control(self, agent_executor, agent_type: AgentType, 
                                           user_query: str, chat_history: List) -> dict:
        """
        Execute agent with adaptive control: caching, retry, groundedness checking.
        Implements: Observe → Reason → Decide → Act → Evaluate → Update → Repeat
        """
        logger.info("🎯 ADAPTIVE CONTROL: Starting adaptive execution loop")
        
        # OBSERVE
        logger.info(f"👁️ OBSERVE: Query='{user_query[:100]}', Agent={agent_type.value}")
        logger.info(f"📊 OBSERVE: Cache stats - {self.cache.hit_rate():.1%} hit rate, {len(self.cache.cache)} entries")
        
        # Wrap tools with caching (temporarily)
        original_tools = agent_executor.tools
        cached_tools = []
        
        for tool in original_tools:
            cached_tool = self._wrap_tool_with_cache(tool)
            cached_tools.append(cached_tool)
        
        agent_executor.tools = cached_tools
        
        try:
            # ACT - Execute agent
            logger.info("🚀 ACT: Executing agent with cached tools")
            response = agent_executor.invoke({
                "input": user_query,
                "chat_history": chat_history
            })
            
            # EVALUATE - Extract tool outputs
            tool_outputs = []
            if "intermediate_steps" in response and response["intermediate_steps"]:
                for step in response["intermediate_steps"]:
                    if len(step) > 1:
                        tool_outputs.append(str(step[1]))
            
            # EVALUATE - Groundedness (skip for conversational responses)
            if tool_outputs:
                groundedness = self.groundedness_evaluator.evaluate(
                    response["output"], tool_outputs
                )
                
                if groundedness.action == "RE_RETRIEVE":
                    logger.warning("⚠️ UPDATE: Low groundedness detected, but continuing (re-retrieval not implemented yet)")
                    self.metrics.re_retrievals += 1
            
            # EVALUATE - Confidence (optional, can be enabled later)
            # available_tools = [t.name for t in original_tools]
            # confidence = self.confidence_evaluator.evaluate_confidence(
            #     user_query, available_tools, tool_outputs
            # )
            
            # UPDATE - Metrics
            self.metrics.update_from_cache(self.cache)
            
            logger.info("✅ EVALUATE: Adaptive execution completed successfully")
            logger.info(self.metrics.report())
            
            return response
            
        finally:
            # Restore original tools
            agent_executor.tools = original_tools
    
    def _wrap_tool_with_cache(self, tool):
        """Wrap tool function with caching and retry logic"""
        # Get the original function - handle different tool types
        if hasattr(tool, 'func'):
            original_func = tool.func
        elif hasattr(tool, '_run'):
            original_func = tool._run
        elif hasattr(tool, 'run'):
            original_func = tool.run
        elif callable(tool):
            original_func = tool
        else:
            # Can't wrap this tool - return as is
            logger.warning(f"⚠️ Cannot wrap tool {tool.name if hasattr(tool, 'name') else 'unknown'} - no callable found")
            return tool
        
        tool_name = tool.name if hasattr(tool, 'name') else str(tool)
        
        def cached_and_retried_func(*args, **kwargs):
            # Check cache first
            cache_key_input = {'args': args, 'kwargs': kwargs}
            cached_result = self.cache.get(tool_name, cache_key_input)
            
            if cached_result is not None:
                return cached_result
            
            # Cache miss - execute tool with retry
            try:
                result = self.retry_strategy.execute_with_retry(
                    original_func, tool_name, *args, **kwargs
                )
                
                # Cache result if appropriate
                ttl = get_ttl_for_tool(tool_name)
                if ttl > 0:  # Don't cache side-effect tools
                    self.cache.set(tool_name, cache_key_input, result, ttl)
                
                # Invalidate related cache if this is a write operation
                if tool_name in ['create_event', 'update_event', 'delete_event']:
                    logger.info("🗑️ CACHE INVALIDATION: Calendar modified, clearing calendar cache")
                    self.cache.invalidate('search_events')
                    self.cache.invalidate('calendars_info')
                
                return result
                
            except ToolExecutionError as e:
                logger.error(f"🚨 TOOL FAILURE: {tool_name} failed after retries: {e}")
                self.metrics.retries_attempted += 1
                # Return error message instead of raising
                return f"Error: {str(e)}"
        
        # Create new tool with wrapped function - handle different tool types
        from copy import copy
        wrapped_tool = copy(tool)
        
        # Set the wrapped function based on tool type
        if hasattr(wrapped_tool, 'func'):
            wrapped_tool.func = cached_and_retried_func
        elif hasattr(wrapped_tool, '_run'):
            wrapped_tool._run = cached_and_retried_func
        elif hasattr(wrapped_tool, 'run'):
            wrapped_tool.run = cached_and_retried_func
        
        return wrapped_tool

    def process_query(self, user_query: str) -> tuple[str, AgentType]:
        """Process query with appropriate agent or handle conversationally."""
        logger.info(f"QUERY PROCESSING: New user query received: '{user_query}'")

        # Classify intent and route to agent
        agent_type = self.route_query(user_query)
        
        # Handle conversational queries directly (no agent needed)
        if agent_type is None:
            logger.info("CONVERSATIONAL HANDLING: Simple greeting/small talk detected")
            conversational_responses = {
                'hello': "Hello! I'm your calendar assistant. How can I help you with your schedule today?",
                'hi': "Hi there! Ready to help with your calendar. What would you like to know?",
                'hey': "Hey! What can I do for you today?",
                'good morning': "Good morning! How can I assist with your schedule today?",
                'good afternoon': "Good afternoon! What scheduling needs do you have?",
                'good evening': "Good evening! How can I help you?",
                'thanks': "You're welcome! Let me know if you need anything else.",
                'thank you': "You're very welcome! Happy to help anytime.",
                'bye': "Goodbye! Have a great day!",
                'goodbye': "Goodbye! Feel free to come back anytime you need scheduling help.",
            }
            
            query_lower = user_query.lower().strip()
            response = conversational_responses.get(query_lower, 
                "I'm here to help with your calendar and scheduling. What would you like to know?")
            
            # Add to memory without agent type
            self.memory.add_turn(user_query, response, [], "conversational")
            
            return f"💬 {response}", None

        logger.info(f"AGENT SELECTION: {agent_type.value.upper()} AGENT selected for processing")
        
        # Show clean user feedback instead of logging
        agent_names = {'manager': 'Manager', 'planner': 'Planner', 'executor': 'Executor', 'reviewer': 'Reviewer'}
        agent_name = agent_names.get(agent_type.value, 'Unknown')
        
        # Select pre-built agent (NO REBUILDING!)
        if agent_type == AgentType.MANAGER:
            agent_executor = self.manager_agent
            logger.info(f"✅ Using pre-built MANAGER agent (no rebuild)")
        elif agent_type == AgentType.PLANNER:
            agent_executor = self.planner_agent
            logger.info(f"✅ Using pre-built PLANNER agent (no rebuild)")
        elif agent_type == AgentType.REVIEWER:
            agent_executor = self.reviewer_agent
            logger.info(f"✅ Using pre-built REVIEWER agent (no rebuild)")
        else:  # AgentType.EXECUTOR
            agent_executor = self.executor_agent
            logger.info(f"✅ Using pre-built EXECUTOR agent (no rebuild)")

        # Process query with pre-built agent
        logger.info(f"EXECUTION: Invoking {agent_name} agent with query")
        
        # Get conversation history for context
        chat_history = self.memory.get_chat_history_for_langchain(max_turns=5)
        
        # Invoke agent with adaptive control (if available) or direct execution
        if ADAPTIVE_CONTROL_AVAILABLE and self.cache:
            response = self.execute_agent_with_adaptive_control(
                agent_executor, agent_type, user_query, chat_history
            )
        else:
            # Direct execution without adaptive control
            logger.info("🚀 EXECUTION: Direct agent execution (adaptive control not available)")
            response = agent_executor.invoke({
                "input": user_query,
                "chat_history": chat_history
            })

        # Store planner results for executor access
        if agent_type == AgentType.PLANNER:
            logger.info("MEMORY UPDATE: Storing planner results for potential executor access")
            self.memory.store_planner_result(response["output"], user_id=self.memory.supabase_memory.user_id)
        
        # Learn from executor approvals
        if agent_type == AgentType.EXECUTOR:
            logger.info("LEARNING: User approved plan, learning preferences")
            self.memory.learn_preference_from_approval(user_id=self.memory.supabase_memory.user_id)
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
            logger.info("TOOL ANALYSIS: No intermediate steps found - agent responded without tools")

        logger.info(f"RESPONSE GENERATED: {agent_name} agent completed processing")

        # Add to memory with agent type
        self.memory.add_turn(
            user_query, 
            response["output"], 
            tools_used, 
            agent_type.value
        )

        # Add agent identification to response
        agent_icon = {'manager': '📅', 'planner': '🎯', 'executor': '✅', 'reviewer': '📊'}.get(agent_type.value, '🤖')
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

    def get_adaptive_metrics(self) -> str:
        """Get adaptive control metrics for display"""
        if self.metrics:
            return self.metrics.report()
        return "Adaptive control not available"
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {'hit_rate': 0.0, 'entries': 0, 'hits': 0, 'misses': 0}
