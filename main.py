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

    # Check profile.json
    if not os.path.exists('profile.json'):
        print("❌ profile.json not found")
        print("   Please ensure your profile data is available")
        return False
    print("✅ Profile data available")

    # Check RAG database
    if not os.path.exists('chroma_db'):
        print("⚠️  RAG database not found - run rag.py first")
        print("   This is optional but recommended for better personalization")
    else:
        print("✅ RAG database available")

    return True

def interactive_mode():
    """Run the system in interactive mode."""
    print("\n🤖 My Life in Blocks - Interactive Mode")
    print("=" * 50)
    print("Type your scheduling requests or 'quit' to exit")
    print("Examples:")
    print("  - 'What meetings do I have today?'")
    print("  - 'Schedule a meeting with John tomorrow at 2 PM'")
    print("  - 'Check my availability next week'")
    print("=" * 50)

    try:
        from agents import MultiAgentSystem
        system = MultiAgentSystem()
        print("✅ Multi-Agent System initialized successfully!")
        print("🤖 Agents: Manager (Calendar Query) | Planner (Strategic Planning) | Executor (Calendar Execution)")
        print()

        while True:
            try:
                user_input = input("💬 You: ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break

                print("🤖 Processing...")
                response, agent_type = system.process_query(user_input)

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
    """Set up the RAG system."""
    print("\n🧠 RAG System Setup")
    print("=" * 50)

    try:
        import rag
        print("✅ RAG system setup completed!")
        print("📚 Vector database created/updated in chroma_db/")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed")
    except Exception as e:
        print(f"❌ RAG setup failed: {e}")

def main():
    """Main entry point."""
    print("🎯 My Life in Blocks - Multi-Agent Calendar Scheduling System")
    print("=" * 60)

    parser = argparse.ArgumentParser(description="Intelligent calendar scheduling agent")
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['interactive', 'traces', 'rag', 'check'],
        default='interactive',
        help='Mode to run: interactive (default), traces, rag, or check'
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
    elif args.mode == 'check':
        if check_requirements():
            print("\n✅ All system requirements met!")
        else:
            print("\n❌ System requirements not met.")
            sys.exit(1)

if __name__ == "__main__":
    main()