#!/usr/bin/env python3
"""
My Life in Blocks - Multi-Agent Calendar Scheduling System
Main entry point for the intelligent scheduling agent system.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_requirements():
    """Check if all required dependencies and credentials are available."""
    print("🔍 Checking system requirements...")

    # Check OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("   Please set your OpenAI API key in .env file")
        return False
    print("✅ OpenAI API key configured")
    
    # Check Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found in environment variables")
        print("   Please set SUPABASE_URL and SUPABASE_ANON_KEY in .env file")
        return False
    print("✅ Supabase credentials configured")

    # Check profile.json
    if not os.path.exists('profile.json'):
        print("❌ profile.json not found")
        print("   Please ensure your profile data is available")
        return False
    print("✅ Profile data available")

    # Check Supabase connection
    try:
        from supabase_rag import SupabaseVectorStore
        store = SupabaseVectorStore("advanced_agentic_brain")
        print("✅ Supabase vector store connection successful")
    except Exception as e:
        print(f"⚠️  Supabase connection warning: {e}")
        print("   System will attempt to connect during runtime")

    return True

def interactive_mode():
    """Run the system in interactive mode."""
    print("\n🤖 My Life in Blocks - Interactive Mode")
    print("=" * 50)
    print("Type your scheduling requests or commands:")
    print("📅 Scheduling: 'What meetings do I have today?', 'Schedule meeting with John'")
    print("❓ Help: 'help' for commands, 'quit' to exit")
    print("=" * 50)

    try:
        from agents import MultiAgentSystem
        
        # Suppress HTTP request logging for cleaner output
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        
        system = MultiAgentSystem()
        print("✅ Multi-Agent System initialized successfully!")
        print("🤖 Agents: Manager (Calendar Query) | Planner (Strategic Planning) | Executor (Calendar Execution) | Reviewer (Progress & Analytics)")
        print()

        while True:
            try:
                user_input = input("💬 You: ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                # Handle special commands
                if user_input.lower() in ['help', 'h']:
                    print("\n📋 **AVAILABLE COMMANDS:**")
                    print("📊 conversation summary - Show conversation statistics")
                    print("❓ help - Show this help message")
                    print("🚪 quit - Exit the system")
                    print("\n📅 **SCHEDULING EXAMPLES:**")
                    print("• 'What meetings do I have today?'")
                    print("• 'Schedule a meeting with John tomorrow at 2 PM'")
                    print("• 'Check my availability next week'")
                    print("• 'Find time for a 1-hour meeting with Sarah'")
                    continue
                
                if user_input.lower() in ['conversation summary', 'summary', 'stats']:
                    print("\n" + system.get_conversation_summary())
                    continue

                # Show processing indicator
                print("🤖 Processing your request...")
                
                # Process the query
                response, agent_type = system.process_query(user_input)

                # Clear the processing line and show response
                print(f"\n{response}")
                print("-" * 50)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print("Please try again or check your configuration.")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        print("Please check your configuration and try again.")

def trace_mode():
    """Generate implementation traces for documentation."""
    print("\n📊 Implementation Trace Generation")
    print("=" * 50)

    try:
        from generate_traces import generate_implementation_traces
        generate_implementation_traces()
        print("\n✅ Implementation traces generated successfully!")
        print("📄 Check 'implementation_trace.log' for detailed traces")

    except ImportError:
        print("❌ generate_traces.py not found")
        print("   Please ensure the trace generation script is available")
    except Exception as e:
        print(f"❌ Trace generation failed: {e}")

def rag_setup():
    """Set up the RAG system in Supabase (deprecated - data already migrated)."""
    print("\n🧠 RAG System Setup")
    print("=" * 50)
    print("ℹ️  RAG data has been migrated to Supabase")
    print("✅ Using Supabase vector store for all retrieval operations")
    print("📚 Collection: advanced_agentic_brain")
    print("🎯 33 unique documents with importance scoring")

def advanced_rag_setup():
    """Set up the advanced RAG system with semantic chunking in Supabase."""
    print("\n🧠 Advanced RAG System Setup (Supabase)")
    print("=" * 50)

    try:
        import advanced_rag
        print("✅ Advanced RAG system setup completed!")
        print("📚 Data ingested into Supabase vector store")
        print("🎯 Semantic chunking strategy implemented")
        print("☁️  Cloud-based storage with pgvector")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure advanced_rag.py is available")
    except Exception as e:
        print(f"❌ Advanced RAG setup failed: {e}")

def main():
    """Main entry point."""
    print("🎯 My Life in Blocks - Multi-Agent Calendar Scheduling System")
    print("=" * 60)

    parser = argparse.ArgumentParser(description="Intelligent calendar scheduling agent")
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['interactive', 'traces', 'rag', 'advanced-rag', 'check'],
        default='interactive',
        help='Mode to run: interactive (default), traces, rag, advanced-rag, or check'
    )

    args = parser.parse_args()

    # Check requirements for all modes except 'check'
    if args.mode != 'check' and not check_requirements():
        print("\n❌ System requirements not met. Please fix the issues above.")
        sys.exit(1)

    # Execute requested mode
    if args.mode == 'interactive':
        interactive_mode()
    elif args.mode == 'traces':
        trace_mode()
    elif args.mode == 'rag':
        rag_setup()
    elif args.mode == 'advanced-rag':
        advanced_rag_setup()
    elif args.mode == 'check':
        if check_requirements():
            print("\n✅ All system requirements met!")
        else:
            print("\n❌ System requirements not met.")
            sys.exit(1)

if __name__ == "__main__":
    main()