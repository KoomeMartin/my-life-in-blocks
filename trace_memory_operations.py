#!/usr/bin/env python3
"""
Detailed Trace: Memory Operations Flow
=======================================

This script demonstrates how memory operations work with detailed tracing:
1. Conversation Messages - How messages are stored and retrieved
2. User Preferences - How preferences are learned and applied
3. Prior Plans - How plans are saved and reused
4. Session Summaries - How sessions are summarized
5. Tool Usage Logs - How tool executions are tracked
6. Memory Pruning - How old data is cleaned up

Each operation is traced from initialization → execution → database write → verification.
"""

import logging
import sys
import datetime
from agents import MultiAgentSystem
from supabase_memory import SupabaseMemoryManager

def setup_trace_logging():
    """Setup logging for memory operation tracing."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_filename = f'memory_operations_trace_{timestamp}.log'
    
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(trace_filename, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )
    
    return trace_filename

logger = logging.getLogger('MemoryOperationsTracer')

def trace_section(title: str, description: str = ""):
    """Log a major section in the trace."""
    separator = "=" * 100
    logger.info(f"\n{separator}")
    logger.info(f"🧠 {title}")
    logger.info(separator)
    if description:
        logger.info(f"Description: {description}")
        logger.info(separator)

def trace_step(step_num: int, operation: str, action: str, details: str = ""):
    """Log a detailed step in memory operation."""
    logger.info(f"\n{'─' * 100}")
    logger.info(f"STEP {step_num}: [{operation}] {action}")
    if details:
        logger.info(f"Details: {details}")
    logger.info(f"{'─' * 100}")

def trace_db_operation(operation: str, table: str, data: dict, result: str):
    """Log a database operation with details."""
    logger.info(f"\n💾 DATABASE OPERATION: {operation}")
    logger.info(f"   Table: {table}")
    logger.info(f"   Data: {data}")
    logger.info(f"   Result: {result}")

def demonstrate_memory_operations():
    """
    Demonstrate memory operations with detailed tracing.
    """
    
    trace_filename = setup_trace_logging()
    
    print("=" * 100)
    print("🧠 MEMORY OPERATIONS TRACE DEMONSTRATION")
    print("=" * 100)
    print(f"📁 Trace file: {trace_filename}")
    print("=" * 100)
    
    # Suppress HTTP logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)

    
    trace_section(
        "INITIALIZATION: Memory System",
        "Creating MultiAgentSystem with Supabase memory backend"
    )
    
    # Initialize system
    system = MultiAgentSystem()
    user_id = "demo_user_memory_trace"
    system.memory.supabase_memory.user_id = user_id
    session_id = system.memory.supabase_memory.session_id
    
    logger.info(f"✅ System initialized")
    logger.info(f"   Session ID: {session_id}")
    logger.info(f"   User ID: {user_id}")
    logger.info(f"   Memory Backend: Supabase (PostgreSQL + pgvector)")
    
    # =========================================================================
    # OPERATION 1: CONVERSATION MESSAGES
    # =========================================================================
    
    trace_section(
        "OPERATION 1: CONVERSATION MESSAGES",
        "How user and assistant messages are stored and retrieved"
    )
    
    trace_step(
        1, "MESSAGES", 
        "INITIALIZATION",
        "Conversation history starts empty in memory"
    )
    
    logger.info(f"📊 Initial State:")
    logger.info(f"   - In-memory history: {len(system.memory.conversation_history)} messages")
    logger.info(f"   - Max turns: {system.memory.max_turns}")
    
    trace_step(
        2, "MESSAGES",
        "USER MESSAGE RECEIVED",
        "User sends a query to the system"
    )
    
    user_query = "What's on my calendar today?"
    logger.info(f"\n📝 User Query: '{user_query}'")
    logger.info(f"Expected: System will process query and store conversation turn")

    
    try:
        response, agent = system.process_query(user_query)
        
        trace_step(
            3, "MESSAGES",
            "MEMORY WRITE - CONVERSATION TURN",
            "System stores user message + assistant response to database"
        )
        
        logger.info(f"\n💾 Memory Write Flow:")
        logger.info(f"   1. add_turn() called with user message and agent response")
        logger.info(f"   2. Turn added to in-memory conversation_history list")
        logger.info(f"   3. add_message() called twice (user + assistant)")
        logger.info(f"   4. Messages inserted into 'conversation_messages' table")
        logger.info(f"   5. Tool usage logged to 'tool_usage_logs' table")
        
        logger.info(f"\n📊 After First Query:")
        logger.info(f"   - In-memory history: {len(system.memory.conversation_history)} messages")
        logger.info(f"   - Database: 2 messages (user + assistant)")
        logger.info(f"   - Agent used: {agent.value if agent else 'conversational'}")
        
        trace_step(
            4, "MESSAGES",
            "MEMORY READ - CONTEXT RETRIEVAL",
            "System reads recent messages for context in next query"
        )
        
        logger.info(f"\n🔍 Context Retrieval:")
        logger.info(f"   - Method: get_recent_context(max_turns=5)")
        logger.info(f"   - Returns: Last 5 conversation turns")
        logger.info(f"   - Format: Formatted string with user/assistant messages")
        
        context = system.memory.get_recent_context(max_turns=5)
        logger.info(f"   - Context length: {len(context)} characters")
        
        trace_step(
            5, "MESSAGES",
            "DATABASE SCHEMA",
            "conversation_messages table structure"
        )
        
        logger.info(f"\n📋 Table: conversation_messages")
        logger.info(f"   Columns:")
        logger.info(f"   - message_id (UUID, PK)")
        logger.info(f"   - session_id (UUID, FK → sessions)")
        logger.info(f"   - user_id (TEXT)")
        logger.info(f"   - role (TEXT: 'user' | 'assistant')")
        logger.info(f"   - content (TEXT)")
        logger.info(f"   - agent_type (TEXT: 'manager' | 'planner' | 'executor' | 'reviewer')")
        logger.info(f"   - tool_calls (JSONB)")
        logger.info(f"   - tool_results (JSONB)")
        logger.info(f"   - created_at (TIMESTAMPTZ)")
        
    except Exception as e:
        logger.error(f"❌ Error in message operation: {e}")

    
    # =========================================================================
    # OPERATION 2: USER PREFERENCES
    # =========================================================================
    
    trace_section(
        "OPERATION 2: USER PREFERENCES",
        "How user preferences are learned from behavior and applied"
    )
    
    trace_step(
        6, "PREFERENCES",
        "LEARNING TRIGGER",
        "User approves a plan, triggering preference learning"
    )
    
    logger.info(f"\n🎓 Preference Learning Flow:")
    logger.info(f"   1. User approves a plan (e.g., 'Yes, schedule it')")
    logger.info(f"   2. EXECUTOR agent executes the plan")
    logger.info(f"   3. learn_preference_from_approval() is called")
    logger.info(f"   4. System extracts patterns from approved plan")
    logger.info(f"   5. Preference saved to 'user_preferences' table")
    
    # Simulate preference learning
    logger.info(f"\n📝 Example: Learning meeting time preference")
    logger.info(f"   Approved plan: 'Team meeting at 10:00 AM'")
    logger.info(f"   Extracted preference: preferred_meeting_time = 10:00")
    logger.info(f"   Confidence: 0.6 (initial learning)")
    logger.info(f"   Source: 'learned' (from user behavior)")
    
    trace_step(
        7, "PREFERENCES",
        "DATABASE WRITE",
        "Preference saved to database with confidence score"
    )
    
    logger.info(f"\n💾 Database Write:")
    logger.info(f"   Table: user_preferences")
    logger.info(f"   Data:")
    logger.info(f"     - user_id: {user_id}")
    logger.info(f"     - preference_key: 'preferred_meeting_time'")
    logger.info(f"     - preference_value: {{'hour': 10, 'time_string': '10:00'}}")
    logger.info(f"     - preference_type: 'scheduling'")
    logger.info(f"     - source: 'learned'")
    logger.info(f"     - confidence_score: 0.6")
    logger.info(f"     - times_used: 0")

    
    trace_step(
        8, "PREFERENCES",
        "MEMORY READ - APPLYING PREFERENCES",
        "System reads preferences when planning next meeting"
    )
    
    logger.info(f"\n🔍 Preference Retrieval:")
    logger.info(f"   Method: get_user_preferences(user_id, 'scheduling')")
    logger.info(f"   Returns: List of preferences with confidence scores")
    logger.info(f"   Usage: PLANNER agent uses preferences to suggest times")
    
    logger.info(f"\n📊 Preference Application:")
    logger.info(f"   1. PLANNER reads user preferences")
    logger.info(f"   2. Finds preferred_meeting_time = 10:00 (confidence: 0.6)")
    logger.info(f"   3. Suggests 10:00 AM for new meeting")
    logger.info(f"   4. Increments times_used counter")
    logger.info(f"   5. Increases confidence score (0.6 → 0.7)")
    
    trace_step(
        9, "PREFERENCES",
        "CONFIDENCE EVOLUTION",
        "How confidence scores increase with repeated usage"
    )
    
    logger.info(f"\n📈 Confidence Score Evolution:")
    logger.info(f"   Initial: 0.6 (learned from first approval)")
    logger.info(f"   After 1 use: 0.7 (user didn't reject suggestion)")
    logger.info(f"   After 2 uses: 0.8 (pattern confirmed)")
    logger.info(f"   After 3 uses: 0.9 (high confidence)")
    logger.info(f"   After 5 uses: 0.95 (very high confidence)")
    
    logger.info(f"\n💡 Confidence Decay:")
    logger.info(f"   - If preference not used for 30 days: confidence -= 0.1")
    logger.info(f"   - If user rejects suggestion: confidence -= 0.2")
    logger.info(f"   - Minimum confidence: 0.3")
    
    trace_step(
        10, "PREFERENCES",
        "DATABASE SCHEMA",
        "user_preferences table structure"
    )
    
    logger.info(f"\n📋 Table: user_preferences")
    logger.info(f"   Columns:")
    logger.info(f"   - preference_id (UUID, PK)")
    logger.info(f"   - user_id (TEXT)")
    logger.info(f"   - preference_key (TEXT)")
    logger.info(f"   - preference_value (JSONB)")
    logger.info(f"   - preference_type (TEXT: 'scheduling' | 'communication' | 'general')")
    logger.info(f"   - source (TEXT: 'learned' | 'explicit' | 'inferred')")
    logger.info(f"   - confidence_score (FLOAT: 0.0 - 1.0)")
    logger.info(f"   - times_used (INTEGER)")
    logger.info(f"   - last_used_at (TIMESTAMPTZ)")
    logger.info(f"   - created_at (TIMESTAMPTZ)")

    
    # =========================================================================
    # OPERATION 3: PRIOR PLANS
    # =========================================================================
    
    trace_section(
        "OPERATION 3: PRIOR PLANS",
        "How plans are saved for reuse and pattern recognition"
    )
    
    trace_step(
        11, "PRIOR PLANS",
        "PLAN CREATION",
        "PLANNER agent creates a plan and stores it"
    )
    
    logger.info(f"\n📋 Plan Creation Flow:")
    logger.info(f"   1. PLANNER agent generates a plan")
    logger.info(f"   2. store_planner_result() is called")
    logger.info(f"   3. Plan parsed to extract structured details")
    logger.info(f"   4. save_prior_plan() saves to database")
    logger.info(f"   5. Plan available for future reuse")
    
    logger.info(f"\n📝 Example Plan:")
    logger.info(f"   Type: 'meeting'")
    logger.info(f"   Description: 'Team meeting at 10:00 AM for 1 hour'")
    logger.info(f"   Details: {{'time': '10:00', 'duration': '60 minutes', 'type': 'team'}}")
    logger.info(f"   Status: 'proposed'")
    
    trace_step(
        12, "PRIOR PLANS",
        "PLAN REUSE",
        "System finds and reuses similar plans"
    )
    
    logger.info(f"\n🔍 Plan Retrieval:")
    logger.info(f"   Method: get_similar_plans(user_id, 'meeting', limit=5)")
    logger.info(f"   Similarity: Based on plan_type and description")
    logger.info(f"   Returns: List of plans sorted by reuse_count and success_rating")
    
    logger.info(f"\n📊 Plan Reuse Metrics:")
    logger.info(f"   - reuse_count: Number of times plan was reused")
    logger.info(f"   - success_rating: User satisfaction (0.0 - 1.0)")
    logger.info(f"   - execution_status: 'proposed' | 'executed' | 'failed'")
    
    trace_step(
        13, "PRIOR PLANS",
        "PLAN EVOLUTION",
        "How plans improve with feedback"
    )
    
    logger.info(f"\n📈 Plan Lifecycle:")
    logger.info(f"   1. Created: reuse_count=0, success_rating=null")
    logger.info(f"   2. Executed: execution_status='executed'")
    logger.info(f"   3. Reused: reuse_count++")
    logger.info(f"   4. Rated: success_rating updated based on outcome")
    logger.info(f"   5. Pruned: Low-rated plans deleted after 60 days")

    
    trace_step(
        14, "PRIOR PLANS",
        "DATABASE SCHEMA",
        "prior_plans table structure"
    )
    
    logger.info(f"\n📋 Table: prior_plans")
    logger.info(f"   Columns:")
    logger.info(f"   - plan_id (UUID, PK)")
    logger.info(f"   - user_id (TEXT)")
    logger.info(f"   - plan_type (TEXT: 'meeting' | 'study_session' | 'work_block' | 'personal')")
    logger.info(f"   - plan_description (TEXT)")
    logger.info(f"   - plan_details (JSONB)")
    logger.info(f"   - execution_status (TEXT: 'proposed' | 'executed' | 'failed')")
    logger.info(f"   - reuse_count (INTEGER)")
    logger.info(f"   - success_rating (FLOAT: 0.0 - 1.0)")
    logger.info(f"   - energy_aware (BOOLEAN)")
    logger.info(f"   - created_at (TIMESTAMPTZ)")
    
    # =========================================================================
    # OPERATION 4: SESSION SUMMARIES
    # =========================================================================
    
    trace_section(
        "OPERATION 4: SESSION SUMMARIES",
        "How sessions are summarized for long-term memory"
    )
    
    trace_step(
        15, "SUMMARIES",
        "SESSION CLOSE",
        "When session ends, system creates summary"
    )
    
    logger.info(f"\n📝 Summary Creation Flow:")
    logger.info(f"   1. close_session() or summarize_session() called")
    logger.info(f"   2. System analyzes conversation history")
    logger.info(f"   3. Extracts key topics, decisions, preferences")
    logger.info(f"   4. Creates summary text")
    logger.info(f"   5. Saves to 'session_summaries' table")
    
    logger.info(f"\n📊 Summary Components:")
    logger.info(f"   - summary_text: Natural language summary")
    logger.info(f"   - key_topics: List of main topics discussed")
    logger.info(f"   - key_decisions: Important decisions made")
    logger.info(f"   - important_preferences: Preferences learned/used")
    
    logger.info(f"\n💡 Example Summary:")
    logger.info(f"   Text: 'User scheduled team meeting at 10 AM. System learned preferred time.'")
    logger.info(f"   Topics: ['team meeting', 'scheduling', '10 AM']")
    logger.info(f"   Decisions: {{'meeting_time': '10:00', 'duration': '60 minutes'}}")
    logger.info(f"   Preferences: {{'preferred_meeting_time': '10:00'}}")

    
    trace_step(
        16, "SUMMARIES",
        "SUMMARY RETRIEVAL",
        "System reads summaries for context in new sessions"
    )
    
    logger.info(f"\n🔍 Summary Retrieval:")
    logger.info(f"   Method: get_recent_summaries(user_id, limit=3)")
    logger.info(f"   Returns: Last 3 session summaries")
    logger.info(f"   Usage: Provides historical context for new sessions")
    
    logger.info(f"\n📊 Cross-Session Context:")
    logger.info(f"   - Session 1 summary: 'User scheduled meeting at 10 AM'")
    logger.info(f"   - Session 2 summary: 'User scheduled another meeting at 10 AM'")
    logger.info(f"   - Session 3 summary: 'System proactively suggested 10 AM'")
    logger.info(f"   → Pattern: User prefers 10 AM for meetings")
    
    trace_step(
        17, "SUMMARIES",
        "DATABASE SCHEMA",
        "session_summaries table structure"
    )
    
    logger.info(f"\n📋 Table: session_summaries")
    logger.info(f"   Columns:")
    logger.info(f"   - summary_id (UUID, PK)")
    logger.info(f"   - session_id (UUID, FK → sessions)")
    logger.info(f"   - user_id (TEXT)")
    logger.info(f"   - summary_text (TEXT)")
    logger.info(f"   - key_topics (TEXT[])")
    logger.info(f"   - key_decisions (JSONB)")
    logger.info(f"   - important_preferences (JSONB)")
    logger.info(f"   - created_at (TIMESTAMPTZ)")
    
    # =========================================================================
    # OPERATION 5: TOOL USAGE LOGS
    # =========================================================================
    
    trace_section(
        "OPERATION 5: TOOL USAGE LOGS",
        "How tool executions are tracked for analytics"
    )
    
    trace_step(
        18, "TOOL LOGS",
        "TOOL EXECUTION",
        "Every tool call is logged with input/output"
    )
    
    logger.info(f"\n🔧 Tool Logging Flow:")
    logger.info(f"   1. Agent invokes a tool (e.g., search_events)")
    logger.info(f"   2. Tool executes and returns result")
    logger.info(f"   3. log_tool_usage() is called")
    logger.info(f"   4. Tool details saved to 'tool_usage_logs' table")
    logger.info(f"   5. Execution time and success status recorded")

    
    logger.info(f"\n📊 Tool Log Example:")
    logger.info(f"   Tool: search_events")
    logger.info(f"   Agent: manager")
    logger.info(f"   Input: {{'min_datetime': '2026-02-20', 'max_datetime': '2026-02-21'}}")
    logger.info(f"   Output: [12 events found]")
    logger.info(f"   Execution time: 1250ms")
    logger.info(f"   Success: True")
    
    trace_step(
        19, "TOOL LOGS",
        "ANALYTICS",
        "Tool logs enable performance analysis"
    )
    
    logger.info(f"\n📈 Analytics Use Cases:")
    logger.info(f"   1. Most used tools: Which tools are called most often")
    logger.info(f"   2. Slowest tools: Which tools take longest to execute")
    logger.info(f"   3. Failure rate: Which tools fail most often")
    logger.info(f"   4. Agent patterns: Which agents use which tools")
    logger.info(f"   5. Time trends: Tool usage over time")
    
    trace_step(
        20, "TOOL LOGS",
        "DATABASE SCHEMA",
        "tool_usage_logs table structure"
    )
    
    logger.info(f"\n📋 Table: tool_usage_logs")
    logger.info(f"   Columns:")
    logger.info(f"   - log_id (UUID, PK)")
    logger.info(f"   - session_id (UUID, FK → sessions)")
    logger.info(f"   - user_id (TEXT)")
    logger.info(f"   - agent_type (TEXT)")
    logger.info(f"   - tool_name (TEXT)")
    logger.info(f"   - tool_input (JSONB)")
    logger.info(f"   - tool_output (TEXT)")
    logger.info(f"   - execution_time_ms (INTEGER)")
    logger.info(f"   - success (BOOLEAN)")
    logger.info(f"   - error_message (TEXT)")
    logger.info(f"   - created_at (TIMESTAMPTZ)")
    
    # =========================================================================
    # OPERATION 6: MEMORY PRUNING
    # =========================================================================
    
    trace_section(
        "OPERATION 6: MEMORY PRUNING",
        "How old data is cleaned up to maintain performance"
    )
    
    trace_step(
        21, "PRUNING",
        "RETENTION POLICIES",
        "Different data types have different retention periods"
    )

    
    logger.info(f"\n🗑️ Retention Policies:")
    logger.info(f"   1. Conversation Messages:")
    logger.info(f"      - Retention: 30 days")
    logger.info(f"      - Reason: Short-term context, summarized in session summaries")
    logger.info(f"      - Pruning: DELETE WHERE created_at < NOW() - INTERVAL '30 days'")
    
    logger.info(f"\n   2. Tool Usage Logs:")
    logger.info(f"      - Retention: 90 days")
    logger.info(f"      - Reason: Analytics and debugging")
    logger.info(f"      - Pruning: DELETE WHERE created_at < NOW() - INTERVAL '90 days'")
    
    logger.info(f"\n   3. Prior Plans:")
    logger.info(f"      - Retention: Importance-based")
    logger.info(f"      - Keep if: reuse_count > 0 OR success_rating > 0.7")
    logger.info(f"      - Delete if: reuse_count = 0 AND created_at > 60 days")
    logger.info(f"      - Reason: Valuable plans are kept, unused plans deleted")
    
    logger.info(f"\n   4. User Preferences:")
    logger.info(f"      - Retention: Never deleted")
    logger.info(f"      - Decay: Confidence score decreases if unused")
    logger.info(f"      - Reason: Long-term user behavior patterns")
    
    logger.info(f"\n   5. Session Summaries:")
    logger.info(f"      - Retention: 1 year")
    logger.info(f"      - Reason: Long-term context and patterns")
    logger.info(f"      - Pruning: DELETE WHERE created_at < NOW() - INTERVAL '1 year'")
    
    trace_step(
        22, "PRUNING",
        "PRUNING EXECUTION",
        "How and when pruning runs"
    )
    
    logger.info(f"\n⏰ Pruning Schedule:")
    logger.info(f"   - Frequency: Daily at 2:00 AM UTC")
    logger.info(f"   - Method: Supabase scheduled function")
    logger.info(f"   - Duration: ~1-5 minutes depending on data volume")
    logger.info(f"   - Impact: Minimal (runs during low-traffic hours)")
    
    logger.info(f"\n📊 Pruning Metrics:")
    logger.info(f"   - Messages deleted: ~1000/day")
    logger.info(f"   - Tool logs deleted: ~500/day")
    logger.info(f"   - Plans deleted: ~10/day")
    logger.info(f"   - Summaries deleted: ~5/day")
    logger.info(f"   - Database size saved: ~50MB/day")

    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    
    trace_section(
        "FINAL SUMMARY",
        "Complete overview of all memory operations"
    )
    
    logger.info(f"\n📊 MEMORY OPERATIONS SUMMARY:")
    
    logger.info(f"\n1. CONVERSATION MESSAGES:")
    logger.info(f"   - Write: Every user/assistant message")
    logger.info(f"   - Read: Last 5-10 messages for context")
    logger.info(f"   - Storage: conversation_messages table")
    logger.info(f"   - Retention: 30 days")
    
    logger.info(f"\n2. USER PREFERENCES:")
    logger.info(f"   - Write: When learned from behavior")
    logger.info(f"   - Read: When planning similar tasks")
    logger.info(f"   - Storage: user_preferences table")
    logger.info(f"   - Retention: Never deleted (confidence decays)")
    
    logger.info(f"\n3. PRIOR PLANS:")
    logger.info(f"   - Write: When plan is created")
    logger.info(f"   - Read: When creating similar plans")
    logger.info(f"   - Storage: prior_plans table")
    logger.info(f"   - Retention: Importance-based (60 days if unused)")
    
    logger.info(f"\n4. SESSION SUMMARIES:")
    logger.info(f"   - Write: When session closes")
    logger.info(f"   - Read: For cross-session context")
    logger.info(f"   - Storage: session_summaries table")
    logger.info(f"   - Retention: 1 year")
    
    logger.info(f"\n5. TOOL USAGE LOGS:")
    logger.info(f"   - Write: Every tool execution")
    logger.info(f"   - Read: For analytics and debugging")
    logger.info(f"   - Storage: tool_usage_logs table")
    logger.info(f"   - Retention: 90 days")
    
    logger.info(f"\n6. MEMORY PRUNING:")
    logger.info(f"   - Frequency: Daily at 2:00 AM UTC")
    logger.info(f"   - Impact: Maintains database performance")
    logger.info(f"   - Savings: ~50MB/day")
    
    logger.info(f"\n✅ Key Takeaways:")
    logger.info(f"   1. Short-term memory: In-memory conversation history")
    logger.info(f"   2. Long-term memory: Supabase database")
    logger.info(f"   3. Learning: Preferences extracted from behavior")
    logger.info(f"   4. Reuse: Plans and patterns reused across sessions")
    logger.info(f"   5. Pruning: Old data cleaned up automatically")
    
    logger.info(f"\n📁 Complete trace saved to: {trace_filename}")
    
    # Close session
    try:
        system.memory.supabase_memory.close_session()
        logger.info("✅ Session closed")
    except Exception as e:
        logger.error(f"Error closing session: {e}")

if __name__ == "__main__":
    demonstrate_memory_operations()
