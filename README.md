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

### Comprehensive Evaluation System (Guardrails)
The system includes a **completely separate** evaluation module implementing rigorous quality assurance through automated testing:

- **Self-Evaluation Node**: Compares agent outputs against retrieved source material using claim extraction and evidence matching algorithms
- **Groundedness Scoring**: Calculates Groundedness Score = (Supported Claims) / (Total Claims), range 0-1, where:
  - 0.9-1.0: Excellent (fully grounded)
  - 0.7-0.89: Good (mostly grounded)
  - 0.5-0.69: Fair (partially grounded)
  - 0.3-0.49: Poor (significant hallucinations)
  - 0.0-0.29: Critical (mostly fabricated)
- **Hallucination Detection**: Extracts factual claims and flags those unsupported by tool outputs or RAG retrievals
- **Evidence Matching**: Multi-source verification against calendar data, RAG retrievals, and datetime tools
- **18 Test Scenarios**: Comprehensive test suite covering time logic (5), RAG retrieval (5), calendar tools (5), and multi-tool integration (3)
- **JSON Export**: Structured evaluation results with claim-level analysis, evidence sources, and confidence metrics
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

### Comprehensive Evaluation System
```bash
python comprehensive_evaluation_system.py
```

This runs 18 automated test scenarios covering all system capabilities with detailed groundedness analysis. Results are saved to `evaluation_results/` with timestamp-based filenames.

**Latest Evaluation Results**: [`eval_20260205_112424.json`](evaluation_results/eval_20260205_112424.json)
- **Overall Performance**: 83.3% pass rate (15/18 scenarios)
- **Average Groundedness Score**: 0.917 (Excellent)
- **Time Logic Tests**: 80% pass rate (4/5)
- **RAG Retrieval Tests**: 60% pass rate (3/5)
- **Calendar Tool Tests**: 100% pass rate (5/5)
- **Multi-Tool Integration**: 100% pass rate (3/3)

**Test Scenario Categories**:
1. **Time Logic & Conflict Detection** (5 scenarios): Tests adjacent events, overlapping events, and complex day schedules
2. **RAG System Retrieval** (5 scenarios): Validates energy pattern retrieval, deadline queries, and skill lookups
3. **Calendar Tool Integration** (5 scenarios): Verifies event retrieval, multi-day availability, and conflict detection
4. **Multi-Tool Scenarios** (3 scenarios): Tests energy-aware scheduling, deadline-driven planning, and full context integration

**Evaluation Architecture**:
- **Claim Extractor**: Parses agent responses into verifiable factual claims
- **Evidence Matcher**: Matches claims against calendar data, RAG retrievals, and tool outputs
- **Groundedness Calculator**: Computes support ratios with confidence levels
- **Scenario Executor**: Runs test scenarios through the live multi-agent system
- **JSON Reporter**: Exports detailed results with claim-level analysis

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

The standalone evaluation system implements a rigorous testing framework with automated groundedness verification:

#### Test Scenario Design

**Category 1: Time Logic & Conflict Detection (5 scenarios)**
- **Scenario 1**: Adjacent Events - No Conflict (12:00-1:00 PM event, query at 1:00 PM)
  - Expected: Available (adjacent, not overlapping)
  - Result: PASS - Agent correctly identified availability
- **Scenario 2**: Separate Events - Future Event (3:00-4:00 PM event, query at 1:00 PM)
  - Expected: Available (event is later)
  - Result: PASS - Agent correctly identified availability
- **Scenario 3**: Actual Overlap - Partial Conflict (12:30-1:30 PM event, query 1:00-2:00 PM)
  - Expected: Conflict (overlap from 1:00-1:30 PM)
  - Result: FAIL - Agent incorrectly marked as available (time logic error)
- **Scenario 4**: Multiple Adjacent Events (1:00-2:00 PM and 2:00-3:00 PM, query at 2:00 PM)
  - Expected: Not available (meeting starts at 2:00 PM)
  - Result: PASS - Agent correctly identified conflict
- **Scenario 5**: Complex Day Schedule (4 events, find 1-hour slot)
  - Expected: Identify available slots (10-11 AM, 12-2 PM, 3-4 PM)
  - Result: PASS - Agent identified multiple available slots

**Category 2: RAG System Retrieval (5 scenarios)**
- **Scenario 6**: Energy Pattern Retrieval
  - Query: "When is my peak productivity time?"
  - Expected: Retrieve "Peak: 4:30-6 AM, 8 AM-12 PM; Low: 1-4 PM"
  - Result: PASS - Groundedness score 1.0
- **Scenario 7**: Course Deadline Retrieval
  - Query: "When is my AI Systems Design project due?"
  - Expected: Retrieve "2026-02-15"
  - Result: FAIL - Agent did not consult RAG, relied on calendar only
- **Scenario 8**: Skill/Competency Query
  - Query: "What programming languages am I proficient in?"
  - Expected: List ["Python", "JavaScript", "SQL", "Java"]
  - Result: FAIL - Agent inferred from context instead of RAG retrieval
- **Scenario 9**: Low Energy Period Awareness
  - Query: "Should I schedule deep work at 2 PM?"
  - Expected: Recommend against (low energy: 1-4 PM)
  - Result: PASS - Agent correctly advised against low energy period
- **Scenario 10**: Multi-Constraint Planning
  - Query: "Schedule study session considering energy and deadlines"
  - Expected: Use both energy profile and deadline data
  - Result: PASS - Agent integrated multiple constraints

**Category 3: Calendar Tool Integration (5 scenarios)**
- **Scenario 11**: Simple Event Retrieval
  - Query: "What meetings do I have today?"
  - Expected: List all meetings accurately
  - Result: PASS - Retrieved 9 events with correct times
- **Scenario 12**: Multi-Day Availability Check
  - Query: "Am I free tomorrow afternoon?"
  - Expected: Check tomorrow's afternoon availability
  - Result: PASS - Identified 2:00-3:00 PM conflict
- **Scenario 13**: Event Creation Verification
  - Query: "Schedule meeting with John at 3 PM tomorrow for 1 hour"
  - Expected: Create event and confirm details
  - Result: PASS - Proposed time with conflict check
- **Scenario 14**: Conflict Detection Before Scheduling
  - Query: "Can I schedule 2-hour meeting starting at 1 PM?"
  - Expected: Identify conflict and suggest alternative
  - Result: PASS - Detected 3:00 PM conflict, suggested 4:00 PM
- **Scenario 15**: Weekly Schedule Overview
  - Query: "Show me my schedule for this week"
  - Expected: Provide comprehensive weekly view
  - Result: PASS - Listed 45+ events across 7 days

**Category 4: Multi-Tool Integration (3 scenarios)**
- **Scenario 16**: Energy-Aware Scheduling with Conflict Check
  - Query: "Schedule 2-hour deep work tomorrow during peak energy"
  - Expected: Use RAG energy data + calendar conflicts
  - Result: PASS - Proposed 8:00-10:00 AM (peak energy, no conflicts)
- **Scenario 17**: Deadline-Driven Planning with Calendar Integration
  - Query: "Help me plan study time for AI project due next week"
  - Expected: Integrate deadline, energy, and availability
  - Result: PASS - Proposed multiple study sessions aligned with energy patterns
- **Scenario 18**: Full Context Planning
  - Query: "Schedule team meeting considering energy and calendar"
  - Expected: Consider all factors for optimal recommendation
  - Result: PASS - Proposed morning slots avoiding low energy periods

#### JSON Output Structure
Each evaluation session generates a structured JSON file containing [`evaluation_results/`](evaluation_results/):

```json
{
  "session_id": "eval_20260205_112424",
  "timestamp": "2026-02-05T11:24:24.123456",
  "total_scenarios": 18,
  "categories": {
    "time_logic": 5,
    "rag_retrieval": 5,
    "calendar_tools": 5,
    "multi_tool": 3
  },
  "scenarios": [
    {
      "scenario_id": 1,
      "category": "time_logic",
      "name": "Adjacent Events - No Conflict",
      "query": "Am I available at 1:00 PM for 30 minutes?",
      "agent_response": "✅ You ARE available at 1:00 PM for 30 minutes...",
      "claims_extracted": [
        {
          "claim_text": "You ARE available at 1:00 PM for 30 minutes",
          "claim_type": "availability",
          "supported": true,
          "evidence": "Inferred from calendar tool usage in response",
          "evidence_source": "calendar_tool",
          "confidence": 1.0
        }
      ],
      "groundedness_score": 1.0,
      "confidence_level": "excellent",
      "hallucinations_detected": [],
      "test_result": "PASS",
      "expected_behavior": "Should identify as available (adjacent, not overlapping)"
    }
  ],
  "summary": {
    "total_scenarios": 18,
    "passed": 15,
    "failed": 3,
    "average_groundedness": 0.917,
    "category_performance": {
      "time_logic": {"avg_score": 1.0, "passed": 4, "failed": 1},
      "rag_retrieval": {"avg_score": 0.7, "passed": 3, "failed": 2},
      "calendar_tools": {"avg_score": 1.0, "passed": 5, "failed": 0},
      "multi_tool": {"avg_score": 1.0, "passed": 3, "failed": 0}
    }
  }
}
```

#### Evaluation Workflow
1. **Scenario Execution**: Runs query through live multi-agent system
2. **Claim Extraction**: Parses response into verifiable factual claims using line-based extraction
3. **Evidence Matching**: Matches claims against calendar data, RAG retrievals, and tool outputs
4. **Groundedness Calculation**: Computes support ratio with domain-specific indicators
5. **Test Result Determination**: Evaluates semantic correctness for time logic, groundedness scores for other categories
6. **JSON Export**: Saves detailed results with claim-level analysis and evidence sources

#### Evaluation Metrics & Thresholds
- **Groundedness Score Calculation**: `score = supported_claims / total_claims`
- **Pass Threshold**: 0.7 for general scenarios, semantic correctness for time logic
- **Evidence Sources**: `calendar_tool`, `rag_retrieval`, `datetime_tool`, `none`
- **Confidence Levels**: `excellent` (≥0.9), `good` (≥0.7), `fair` (≥0.5), `poor` (≥0.3), `critical` (<0.3)

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

## Failure Analysis & System Improvements

### Documented Failure 1: Incorrect Tool Selection

**Initial Failure Scenario**:
During early testing, the Planner Agent occasionally selected only calendar search tools without consulting the RAG system, leading to generic recommendations that ignored user energy constraints.

**Root Cause**:
The agent prompt did not sufficiently emphasize the mandatory sequence of tool usage (calendars_info → search_events → profile_search).

**Technical Fix**:
Modified the Planner Agent system prompt to include explicit "MANDATORY SEQUENCE" instructions and added logging to track tool execution order. This ensured comprehensive data gathering before decision making.

**Impact**:
Improved recommendation quality from 75% personalized suggestions to 95%+ by guaranteeing RAG consultation on every planning request.

### Documented Failure 2: Time Logic Edge Cases

**Failure Scenario** (Evaluation Scenario 3):
Agent incorrectly marked 1:00-2:00 PM as available when a 12:30-1:30 PM event existed, missing the partial overlap from 1:00-1:30 PM.

**Root Cause**:
Time overlap detection logic in agent reasoning did not properly handle partial overlaps where requested time starts during an existing event.

**Current Status**:
Identified through comprehensive evaluation system. Time logic tests show 80% pass rate (4/5 scenarios), with this specific edge case requiring refinement.

**Proposed Fix**:
Enhance system prompt with explicit overlap detection algorithm:
```
Overlap exists if: (Event_Start < Request_End) AND (Event_End > Request_Start)
```

### Documented Failure 3: RAG Retrieval Bypassing

**Failure Scenarios** (Evaluation Scenarios 7 & 8):
- Scenario 7: Agent did not consult RAG for deadline query, relied on calendar events only
- Scenario 8: Agent inferred skills from context instead of explicit RAG retrieval

**Root Cause**:
Agents sometimes use contextual inference or calendar data when RAG retrieval would provide more accurate information. This occurs when the query can be partially answered without RAG.

**Current Status**:
RAG retrieval tests show 60% pass rate (3/5 scenarios). Agents successfully retrieve energy patterns and provide energy-aware recommendations but occasionally skip RAG for deadline/skill queries.

**Impact**:
While responses remain factually grounded (0.917 average groundedness), explicit RAG retrieval would improve accuracy and reduce inference-based responses.

**Proposed Fix**:
Add explicit RAG consultation requirements to system prompts for queries containing keywords: "deadline", "due", "skill", "proficient", "competency".


- **Continuous Validation**: Evaluation results saved to  for historical tracking

**Key Findings from Evaluation**:
- **Calendar Tool Integration**: 100% pass rate - excellent real-time calendar data retrieval
- **Multi-Tool Coordination**: 100% pass rate - successful integration of RAG + calendar + datetime tools
- **Time Logic**: 80% pass rate - one edge case with partial overlap detection needs refinement
- **RAG Retrieval**: 60% pass rate - agents sometimes infer from context instead of explicit RAG queries

## Performance Metrics

### System Performance
- **Response Time**: Average 3-5 seconds for complex scheduling decisions
- **API Reliability**: 99% successful Google Calendar API interactions
- **Conversation Memory**: 10-turn rolling window with context preservation

### Evaluation Results (18 Test Scenarios)
- **Overall Pass Rate**: 83.3% (15/18 scenarios)
- **Average Groundedness Score**: 0.917 (Excellent)
- **Calendar Tool Accuracy**: 100% (5/5 scenarios)
- **Multi-Tool Integration**: 100% (3/3 scenarios)
- **Time Logic Accuracy**: 80% (4/5 scenarios)
- **RAG Retrieval Accuracy**: 60% (3/5 scenarios)

### Detailed Category Performance
| Category | Scenarios | Passed | Failed | Avg Score | Pass Rate |
|----------|-----------|--------|--------|-----------|-----------|
| Time Logic & Conflict Detection | 5 | 4 | 1 | 1.000 | 80% |
| RAG System Retrieval | 5 | 3 | 2 | 0.700 | 60% |
| Calendar Tool Integration | 5 | 5 | 0 | 1.000 | 100% |
| Multi-Tool Integration | 3 | 3 | 0 | 1.000 | 100% |

**Evaluation Data**: Full results available in [`evaluation_results/eval_20260205_112424.json`](evaluation_results/eval_20260205_112424.json)

## Project Structure

```
my-life-in-blocks/
├── main.py                              # Main entry point with CLI modes
├── agents.py                            # Multi-agent system implementation (core system)
├── rag.py                               # Basic RAG system setup
├── advanced_rag.py                      # Advanced semantic chunking RAG system
├── comprehensive_evaluation_system.py   # Comprehensive evaluation framework (18 scenarios)
├── generate_traces.py                   # Implementation trace generator
├── test_time_logic.py                   # Unit tests for time overlap detection
├── profile.json                         # User profile and preferences
├── credentials.json                     # Google Calendar API credentials
├── .env                                 # Environment variables
├── chroma_db/                          # Basic vector database storage
├── advanced_chroma_db/                 # Advanced semantic chunking database
├── evaluation_results/                 # JSON evaluation results directory
│   ├── eval_20260205_111722.json      # Initial evaluation run (0.014 avg score)
│   └── eval_20260205_112424.json      # Improved evaluation run (0.917 avg score)
├── implementation_trace.log            # Execution traces
├── evaluation_trace.log                # Evaluation system logs
├── EVALUATION_DESIGN.md                # Evaluation scenario specifications
├── EVALUATION_QUICKSTART.md            # Quick start guide for evaluation
├── EVALUATION_SYSTEM_SUMMARY.md        # Evaluation system architecture
├── EVALUATION_QUICK_REFERENCE.md       # Quick reference for evaluation metrics
├── TIME_LOGIC_IMPROVEMENTS.md          # Time logic refinement documentation
├── CALENDAR_ENHANCEMENTS_SUMMARY.md    # Calendar tool enhancement summary
├── VERIFICATION_GUIDE.md               # Verification testing guide
└── requirements.txt                    # Python dependencies
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

**Mohamed Awud**:
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
