#!/usr/bin/env python3
"""
Implementation Trace Generator for Multi-Agent System
Generates detailed logs showing agent reasoning, tool usage, and decision points
"""

import logging
import sys
from agents import MultiAgentSystem

# Configure logging for implementation traces
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('implementation_traces.log', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def generate_implementation_traces():
    """Generate implementation traces by running sample queries through the multi-agent system."""

    print("IMPLEMENTATION TRACE GENERATOR")
    print("=" * 50)
    logger.info("STARTING IMPLEMENTATION TRACE GENERATION")

    # Initialize the multi-agent system
    system = MultiAgentSystem()
    logger.info("MULTI-AGENT SYSTEM INITIALIZED")

    # Sample queries to demonstrate different agent behaviors
    test_queries = [
        "What meetings do I have today?",
        "Schedule a 1-hour meeting with John tomorrow at 2 PM about project planning",
        "Check my availability next week",
        "Create a weekly team standup every Monday at 9 AM"
    ]

    logger.info(f"TEST QUERIES PREPARED: {len(test_queries)} queries ready for processing")

    for i, query in enumerate(test_queries, 1):
        print(f"\nPROCESSING QUERY {i}/{len(test_queries)}")
        print(f"Query: {query}")
        print("-" * 40)

        logger.info(f"QUERY {i}: Processing '{query}'")

        try:
            # Process the query and capture the response
            response, agent_type = system.process_query(query)

            print(f"Agent: {agent_type.value.upper()}")
            print(f"Response: {response[:200]}...")
            print("Query processed successfully")

            logger.info(f"QUERY {i} COMPLETED: {agent_type.value.upper()} agent processed successfully")

        except Exception as e:
            print(f"Error processing query: {e}")
            logger.error(f"QUERY {i} FAILED: {e}")

    print("\n" + "=" * 50)
    print("IMPLEMENTATION TRACE GENERATION COMPLETE")
    print("Check 'implementation_traces.log' for detailed traces")
    logger.info("IMPLEMENTATION TRACE GENERATION COMPLETE")

if __name__ == "__main__":
    generate_implementation_traces()