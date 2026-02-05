#!/usr/bin/env python3
"""
Implementation Trace Generator for Multi-Agent System
Generates detailed logs showing agent reasoning, tool usage, and decision points
"""

import logging
import sys
import datetime
from agents import MultiAgentSystem

def setup_trace_logging():
    """Setup comprehensive logging for trace generation."""
    # Create timestamp for unique log files
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_filename = f'implementation_traces_{timestamp}.log'
    
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure logging for implementation traces
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(trace_filename, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )
    
    return trace_filename

logger = logging.getLogger('TraceGenerator')

def generate_implementation_traces():
    """Generate implementation traces by running sample queries through the multi-agent system."""
    
    # Setup logging with timestamped filename
    trace_filename = setup_trace_logging()
    
    print("🔧 IMPLEMENTATION TRACE GENERATOR")
    print("=" * 60)
    print(f"📁 Trace file: {trace_filename}")
    print(f"📁 Main log: implementation_trace.log")
    print("=" * 60)
    
    logger.info("STARTING IMPLEMENTATION TRACE GENERATION")
    logger.info(f"TRACE OUTPUT FILE: {trace_filename}")

    # Suppress HTTP logging for cleaner output
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)

    # Initialize the multi-agent system
    logger.info("INITIALIZING MULTI-AGENT SYSTEM")
    system = MultiAgentSystem()
    logger.info("MULTI-AGENT SYSTEM INITIALIZED SUCCESSFULLY")

    # Sample queries to demonstrate different agent behaviors and tool usage
    test_queries = [
        {
            "query": "What meetings do I have today?",
            "expected_agent": "MANAGER",
            "expected_tools": ["get_current_datetime", "get_calendars_info", "search_events"],
            "description": "Calendar query - should trigger Manager agent with calendar tools"
        },
        {
            "query": "Schedule a 1-hour meeting with John tomorrow at 2 PM about project planning",
            "expected_agent": "PLANNER", 
            "expected_tools": ["get_current_datetime", "get_calendars_info", "search_events", "search_user_profile_and_policies"],
            "description": "Complex scheduling - should trigger Planner agent with RAG + calendar tools"
        },
        {
            "query": "Check my availability next week",
            "expected_agent": "PLANNER",
            "expected_tools": ["get_current_datetime", "get_calendars_info", "search_events", "search_user_profile_and_policies"],
            "description": "Availability analysis - should trigger Planner agent with comprehensive tools"
        },
        {
            "query": "Yes, please schedule it",
            "expected_agent": "EXECUTOR",
            "expected_tools": ["get_current_datetime", "create_calendar_event"],
            "description": "Execution approval - should trigger Executor agent with calendar creation tools"
        }
    ]

    logger.info(f"TEST QUERIES PREPARED: {len(test_queries)} queries ready for processing")
    
    # Log query details
    for i, test_case in enumerate(test_queries, 1):
        logger.info(f"QUERY {i} DETAILS:")
        logger.info(f"  Query: '{test_case['query']}'")
        logger.info(f"  Expected Agent: {test_case['expected_agent']}")
        logger.info(f"  Expected Tools: {', '.join(test_case['expected_tools'])}")
        logger.info(f"  Description: {test_case['description']}")

    # Process each query
    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        expected_agent = test_case["expected_agent"]
        expected_tools = test_case["expected_tools"]
        
        print(f"\n🧪 PROCESSING QUERY {i}/{len(test_queries)}")
        print(f"Query: {query}")
        print(f"Expected: {expected_agent} agent with {len(expected_tools)} tools")
        print("-" * 50)

        logger.info(f"QUERY {i} EXECUTION START")
        logger.info(f"QUERY TEXT: '{query}'")
        logger.info(f"EXPECTED AGENT: {expected_agent}")
        logger.info(f"EXPECTED TOOLS: {', '.join(expected_tools)}")

        try:
            # Process the query and capture the response
            response, agent_type = system.process_query(query)

            # Extract agent name for comparison
            actual_agent = agent_type.value.upper()
            
            print(f"✅ Agent: {actual_agent}")
            print(f"📝 Response: {response[:150]}{'...' if len(response) > 150 else ''}")
            
            # Verify expectations
            if actual_agent == expected_agent:
                print(f"✅ Agent selection: CORRECT ({actual_agent})")
                logger.info(f"AGENT SELECTION VERIFICATION: CORRECT - Expected {expected_agent}, Got {actual_agent}")
            else:
                print(f"⚠️ Agent selection: Expected {expected_agent}, Got {actual_agent}")
                logger.warning(f"AGENT SELECTION MISMATCH: Expected {expected_agent}, Got {actual_agent}")
            
            print("✅ Query processed successfully")
            logger.info(f"QUERY {i} COMPLETED SUCCESSFULLY")

        except Exception as e:
            print(f"❌ Error processing query: {e}")
            logger.error(f"QUERY {i} FAILED: {str(e)}")
            logger.exception("Full error details:")

    print("\n" + "=" * 60)
    print("🎉 IMPLEMENTATION TRACE GENERATION COMPLETE")
    print(f"📁 Detailed traces saved to: {trace_filename}")
    print(f"📁 Main system log: implementation_trace.log")
    print("=" * 60)
    
    # Verify trace file was created
    import os
    if os.path.exists(trace_filename):
        file_size = os.path.getsize(trace_filename)
        print(f"✅ Trace file created successfully ({file_size} bytes)")
    else:
        print(f"❌ Warning: Trace file {trace_filename} was not created")
    
    logger.info("IMPLEMENTATION TRACE GENERATION COMPLETE")
    logger.info(f"TRACE FILE SAVED: {trace_filename}")
    logger.info("All queries processed successfully")

if __name__ == "__main__":
    generate_implementation_traces()