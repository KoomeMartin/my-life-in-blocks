# My Life in Blocks - Repository Overview

## 🎯 What This Project Does

This is an intelligent multi-agent calendar scheduling system that uses AI to optimize your time management based on:
- Personal energy patterns and productivity cycles
- Calendar constraints and existing commitments
- Project deadlines and work preferences
- Smart conflict detection and resolution

## 🏗️ How It's Organized

### Core Files
- **`main.py`** - 🚀 Main entry point with multiple modes (interactive, traces, setup)
- **`agents.py`** - 🤖 Multi-agent system with Manager, Planner, and Executor agents
- **`rag.py`** - 🧠 RAG system for personalized scheduling based on user profiles

### Configuration & Data
- **`requirements.txt`** - 📦 Python dependencies
- **`profile.json`** - 👤 User preferences, energy patterns, and constraints
- **`.env`** - 🔑 API keys and environment variables
- **`credentials.json`** - 🔐 Google Calendar API credentials

### Generated Files (Not in Git)
- **`chroma_db/`** - 💾 Vector database for RAG
- **`token.json`** - 🎫 OAuth tokens for Google Calendar
- **`implementation_trace.log`** - 📋 Detailed execution traces

## 🚀 Quick Start Commands

```bash
# Check if everything is set up
python main.py check

# Run interactive scheduling agent
python main.py

# Generate implementation traces for documentation
python main.py traces

# Setup RAG system
python main.py rag
```

## 🤖 Agent Roles

1. **Manager Agent** - Calendar queries and availability checks
2. **Planner Agent** - Strategic scheduling with conflict resolution
3. **Executor Agent** - Calendar event creation and execution

## 📊 Key Features

- Multi-agent collaboration with context sharing
- ReAct framework for reasoning and tool usage
- Google Calendar integration
- RAG-powered personalization
- Comprehensive implementation traces
- Interactive command-line interface

## 🔧 Development

The system is built with:
- **LangChain** for agent orchestration
- **OpenAI GPT-4** for reasoning
- **ChromaDB** for vector search
- **Google Calendar API** for calendar integration

All agents follow the ReAct pattern: Observe → Think → Act → Reason → Respond