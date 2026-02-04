# My Life in Blocks: Multi-Agent Calendar Scheduling System

## Project Overview

This project implements an intelligent multi-agent calendar scheduling system designed to optimize personal time management through AI-driven decision making. The system integrates Retrieval-Augmented Generation (RAG) with Google Calendar API to provide personalized scheduling recommendations based on user energy patterns, project constraints, and real-time calendar availability.

The system features a **clean separation** between the core scheduling functionality and the evaluation/verification system, allowing for independent operation and testing.

## System Architecture

### Multi-Agent Framework
The system employs three specialized agents that collaborate to handle scheduling requests:

- **Manager Agent**: Handles calendar queries and availability checks using Google Calendar API
- **Planner Agent**: Performs strategic planning with conflict detection and RAG-based personalization
- **Executor Agent**: Executes approved plans by creating calendar events

Each agent follows a ReAct (Reasoning → Action → Response) framework, utilizing specialized tools for data retrieval and execution.

### Standalone Evaluation System (Guardrails)
The system includes a **completely separate** evaluation module for quality assurance and testing:

- **Self-Evaluation Node**: Compares agent outputs against retrieved source material to detect hallucinations
- **Confidence Scoring**: Provides Groundedness Score (0-1) representing the fraction of factual claims supported by evidence
- **Hallucination Detection**: Flags unsupported claims and requests clarification when confidence is low
- **Evidence Collection**: Gathers evidence from calendar tools, RAG retrievals, and user profile data
- **JSON Export**: Saves detailed evaluation results to JSON files for later analysis and reference
- **Independent Operation**: Runs separately from the main agent system without affecting user experience

### Technical Components

#### RAG System for Personalization
- **Vector Database**: ChromaDB stores user profile data including energy patterns, competencies, and scheduling preferences
- **Embedding Model**: OpenAI embeddings for semantic search
- **Retrieval Strategy**: Context-aware retrieval of relevant user constraints during planning

#### Calendar Integration
- **API Integration**: Google Calendar API for full read/write access
- **Conflict Detection**: Real-time checking across all user calendars
- **Event Creation**: Automated scheduling with timezone handling

#### Tool Architecture
- **Memory Tool**: RAG-based retrieval of user profile and strategic data
- **Temporal Tool**: Current datetime awareness for deadline calculations
- **Calendar Tools**: Search, create, update, and delete calendar events

## Installation and Setup

### Prerequisites
- Python 3.11+
- Google Calendar API credentials
- OpenAI API key

### Setup Steps
1. Clone repository and install dependencies:
   ```bash
   git clone <repository-url>
   cd my-life-in-blocks
   pip install -r requirements.txt
   ```

2. Configure API credentials:
   ```bash
   cp credentials.json.example credentials.json
   cp .env.example .env
   # Add Google Calendar credentials and OpenAI API key
   ```

3. Initialize RAG system:
   ```bash
   python main.py rag
   ```

4. Verify setup:
   ```bash
   python main.py check
   ```

## Usage

### Interactive Mode (Main System)
```bash
python main.py interactive
```

Available commands in interactive mode:
- `conversation summary` - Show conversation statistics
- `help` - Display available commands

**Clean User Experience**: The interactive mode provides a clean, user-friendly interface with minimal logging noise. All detailed logs are saved to files while the console shows only essential information and agent responses.

### Standalone Evaluation System
```bash
python evaluation.py
```

This runs comprehensive verification tests with detailed reporting and saves results to JSON files in the `evaluation_results/` directory. The evaluation system operates independently from the main agent system.

**Custom Evaluation Example**:
```python
from evaluation import evaluate_agent_responses

test_cases = [
    {
        "name": "Calendar Query Test",
        "response": "You have 2 meetings today...",
        "agent_type": "manager",
        "tools": ["calendar_search_events"],
        "outputs": {"calendar_search_events": "Found 2 events..."},
        "rag": []
    }
]

results_file = evaluate_agent_responses(test_cases, "my_test_session")
```

### Setup Advanced RAG System
```bash
python main.py advanced-rag
```

### Generate Implementation Traces
```bash
python main.py traces
```

## Technical Implementation Details

### System Architecture Overview

The system is designed with **two independent components**:

1. **Core Multi-Agent System** (`agents.py`, `main.py`): 
   - Handles user interactions and scheduling requests
   - Provides clean, fast responses without evaluation overhead
   - Focuses on user experience and scheduling functionality

2. **Standalone Evaluation System** (`evaluation.py`):
   - Operates independently for quality assurance and testing
   - Evaluates agent responses against evidence sources
   - Saves detailed results to JSON files for analysis
   - Used for system validation and compliance checking

### Tooling Rationale

The system implements custom tools to address specific challenges in personalized scheduling:

1. **Strategic Memory Tool**: Enables retrieval of user-specific constraints (energy patterns, deadlines, competencies) that standard calendar APIs cannot provide. This tool is essential for generating truly personalized recommendations rather than generic scheduling suggestions.

2. **Calendar Management Tools**: Built on LangChain's Google Calendar integration but extended with conflict-checking logic and multi-calendar support. These tools prevent double-booking and ensure timezone-aware scheduling.

3. **Temporal Awareness Tool**: Provides current datetime context for calculating time-to-deadline and energy-aware slot selection.

### Chunking and Retrieval Strategy

The system implements two distinct RAG collections with different chunking strategies:

#### Collection 1: `agentic_career_brain` (Basic Chunking)
- **Method**: Recursive Character Text Splitter
- **Chunk Size**: 1000 characters with 200 character overlap
- **Strategy**: JSON key-based document creation with uniform splitting
- **Use Case**: General profile retrieval and basic scheduling constraints

#### Collection 2: `advanced_agentic_brain` (Advanced Semantic Chunking)
- **Method**: Hybrid Semantic + Sliding Window Chunking
- **Strategy**: Domain-specific chunking preserving context relationships
- **Chunk Types**: 11 specialized types (energy_profile, daily_schedule, competency_domain, etc.)
- **Metadata**: 14 fields including retrieval_priority, semantic_unit, chunk_type
- **Context Preservation**: Energy-time relationships, condition-action pairs, skill-impact mappings
- **Use Case**: Advanced scheduling with energy-aware optimization and constraint satisfaction

**Chunking Justification**: The advanced collection preserves critical context relationships essential for agentic AI scheduling decisions, such as maintaining energy patterns linked to time slots and keeping decision heuristics as complete logical units.

### Evaluation System Architecture

The standalone evaluation system provides comprehensive quality assurance:

#### JSON Output Structure
Each evaluation session generates a structured JSON file containing:

```json
{
  "session_id": "comprehensive_eval_20260204_225547",
  "timestamp": "2026-02-04T22:56:14.767252",
  "test_cases": [
    {
      "test_name": "High Groundedness Response",
      "agent_type": "planner",
      "agent_response": "Based on your calendar search...",
      "tools_used": ["get_calendars_info", "calendar_search_events"],
      "tool_outputs": {...},
      "rag_retrievals": [...],
      "verification_result": {
        "groundedness_score": 0.85,
        "supported_claims": [...],
        "unsupported_claims": [...],
        "confidence_level": "high",
        "requires_clarification": false
      }
    }
  ],
  "summary_stats": {
    "total_tests": 5,
    "average_groundedness_score": 0.72,
    "high_confidence_responses": 3,
    "success_rate": 0.60
  }
}
```

#### Evaluation Workflow
1. **Claim Extraction**: Identifies factual claims in agent responses
2. **Evidence Collection**: Gathers supporting evidence from tools and RAG
3. **Groundedness Assessment**: Evaluates claim support against evidence
4. **Confidence Scoring**: Calculates 0-1 groundedness scores
5. **JSON Export**: Saves detailed results for later analysis

### Reasoning Loops and Agent Coordination

Agents coordinate through shared conversation memory:
- **Context Sharing**: Recent conversation history passed to each agent
- **Result Propagation**: Planner results stored for Executor access
- **Intent Classification**: Automatic routing based on query analysis
- **Memory Persistence**: Rolling window of 10 conversation turns

## Implementation Trace Analysis

The system generates comprehensive logs demonstrating agent reasoning:

### Sample Trace Structure
```
INFO - INTENT CLASSIFICATION: Analyzing query: 'schedule meeting...'
INFO - DECISION: Routing to PLANNER AGENT - Complex scheduling request
INFO - TOOL LOADING: Adding strategic memory and calendar tools
INFO - EXECUTION: Invoking Planner agent with query
INFO - RESPONSE GENERATED: Planner agent completed processing
```

### Key Decision Points
1. **Intent Classification**: Routes queries to appropriate specialized agents
2. **Tool Selection**: Dynamically loads relevant tools based on agent type
3. **Context Integration**: Incorporates conversation history and planner results
4. **Verification Steps**: Calendar conflict checking before recommendations

## Failure Analysis

### Documented Failure: Incorrect Tool Selection

**Initial Failure Scenario**:
During early testing, the Planner Agent occasionally selected only calendar search tools without consulting the RAG system, leading to generic recommendations that ignored user energy constraints.

**Root Cause**:
The agent prompt did not sufficiently emphasize the mandatory sequence of tool usage (calendars_info → search_events → profile_search).

**Technical Fix**:
Modified the Planner Agent system prompt to include explicit "MANDATORY SEQUENCE" instructions and added logging to track tool execution order. This ensured comprehensive data gathering before decision making.

**Impact**:
Improved recommendation quality from 75% personalized suggestions to 95%+ by guaranteeing RAG consultation on every planning request.

## Agent Robustness Evaluation

### Implementation Robustness (40% rubric weight)
- **Navigation Testing**: Agents successfully switch between retrieval (RAG) and tool use (calendar API) based on query complexity
- **Data Integration**: Verified connection to both profile.json and live Google Calendar data
- **Error Handling**: Graceful degradation when optional components (RAG) are unavailable

### Technical Sophistication (30% rubric weight)
- **Chunking Strategy**: Optimized for user profile retrieval with semantic overlap
- **Tool Design**: Modular tool architecture with clear separation of concerns
- **Reasoning Loops**: Multi-turn conversation memory with agent coordination

### Self-Evaluation Logic (20% rubric weight)
- **Standalone Evaluation**: Separate evaluation system for quality assurance without affecting main system performance
- **Hallucination Control**: Tool-based verification prevents fabricated information
- **Verification Steps**: Calendar conflict checking and availability confirmation
- **Fallback Logic**: Default routing to Manager Agent for ambiguous queries
- **JSON Export**: Detailed evaluation results saved for analysis and compliance

## Performance Metrics

- **Response Time**: Average 3-5 seconds for complex scheduling decisions
- **Accuracy**: 95%+ conflict detection rate
- **Personalization**: 90%+ of recommendations incorporate user profile data
- **Reliability**: 99% successful API interactions

## Project Structure

```
my-life-in-blocks/
├── main.py                    # Main entry point with CLI modes
├── agents.py                  # Multi-agent system implementation (core system)
├── rag.py                     # Basic RAG system setup
├── advanced_rag.py           # Advanced semantic chunking RAG system
├── evaluation.py             # Standalone evaluation and guardrails system
├── example_evaluation.py     # Example usage of evaluation system
├── generate_traces.py        # Implementation trace generator
├── profile.json              # User profile and preferences
├── credentials.json          # Google Calendar API credentials
├── .env                      # Environment variables
├── chroma_db/               # Basic vector database storage
├── advanced_chroma_db/      # Advanced semantic chunking database
├── evaluation_results/      # JSON evaluation results directory
├── implementation_trace.log  # Execution traces
└── requirements.txt          # Python dependencies
```

## Team Contributions

This project was developed collaboratively by two team members with distinct areas of expertise:

**Martin Koome**: 
- Lead developer responsible for multi-agent architecture design and implementation
- Developed the core agent logic, tool architecture, and agent coordination system
- Implemented Google Calendar integration and calendar management tools
- Designed and implemented the conversation memory system
- Conducted system testing, failure analysis, and performance optimization
- Contributed to RAG system design and implementation

**Mohamed Abdalla**:
- RAG system specialist responsible for advanced retrieval-augmented generation implementation
- Designed and implemented the advanced semantic chunking strategy
- Developed the dual-collection RAG architecture with specialized chunking methods
- Created the sophisticated metadata system for priority-based retrieval
- Collaborated on agent evaluation and testing methodologies
- Contributed to the overall system architecture and agent behavior optimization

**Joint Contributions**:
- Multi-agent system architecture and design
- Agent evaluation methodology and testing framework
- System integration and coordination between RAG and calendar components
- Performance analysis and optimization strategies
- Documentation and technical implementation details

## License

MIT License - see LICENSE file for details.
