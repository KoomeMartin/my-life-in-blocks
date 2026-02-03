import os
import datetime
from dotenv import load_dotenv

# --- LANGCHAIN IMPORTS ---
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import tool
from langchain_core.tools import create_retriever_tool
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# --- GOOGLE CALENDAR IMPORTS ---
from langchain_google_community.calendar.search_events import CalendarSearchEvents
from langchain_google_community.calendar.get_calendars_info import GetCalendarsInfo
from langchain_google_community.calendar.utils import build_calendar_service

# Load Environment Variables (API Keys)
load_dotenv()

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
        embedding_function=OpenAIEmbeddings(),
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
# 4. TOOL: COMMUNICATION (Mocked for safety)
# ==============================================================================
@tool
def send_email_notification(recipient: str, subject: str, body: str) -> str:
    """
    Sends the finalized schedule to the user.
    ONLY use this after the user has confirmed the plan.
    """
    # In a real app, use Gmail API here.
    return f"✅ EMAIL SENT to {recipient} | Subject: {subject}"

# ==============================================================================
# 5. THE AGENT ORCHESTRATOR
# ==============================================================================

SYSTEM_PROMPT = """You are Martin Koome's Personal Scheduling Assistant.

CURRENT TIME: {current_time}

Your task: Schedule time blocks based on my energy profile and calendar constraints.

REQUIRED STEPS (follow in order):
1. ✅ Get current date/time (already provided above)
2. 🔍 Retrieve my energy profile and scheduling constraints from memory
3. 📅 Get my calendar information using get_calendars_info
4. 🔎 Check existing events for the requested time period using search_events
5. 🎯 Find available slots that match my energy profile:
   - Peak: 4:30-6:00 AM, 8:00-12:00 PM (preferred)
   - Avoid: 1:00-4:00 PM (low energy valley)
   - Morning preference: Early slots when possible
6. 📝 Select the best time block for the requested task
7. 📧 Send email confirmation with scheduled time

ENERGY PROFILE RULES:
- Peak cognitive time: 4:30-6:00 AM, 8:00-12:00 PM
- Avoid: 1:00-4:00 PM (low energy valley)
- Morning Lark: Prefer early slots
- Deep work blocks: >90 minutes preferred

CONSTRAINTS:
- No conflicts with existing calendar events
- Respect commute/prep time before classes
- Consider due dates and urgency

IMPORTANT: Always call get_calendars_info BEFORE search_events.
If no suitable slot found, suggest alternatives.

Current User Context: Lead Data Engineer, Masters Student, Python Expert.
"""

def build_agent_system():
    # Get current time for the prompt
    current_time = datetime.datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
    
    # Format the system prompt with current time
    formatted_prompt = SYSTEM_PROMPT.format(current_time=current_time)
    
    # 1. Define Tools
    tools = [
        get_strategic_memory_tool(),
        get_current_datetime,
        send_email_notification
    ]
    
    # Try to add Google Calendar tool
    try:
        calendar_service = build_calendar_service()
        calendar_tools = [
            GetCalendarsInfo(api_resource=calendar_service),
            CalendarSearchEvents(api_resource=calendar_service)
        ]
        tools.extend(calendar_tools)
        print("✅ Google Calendar tools loaded.")
    except Exception as e:
        print(f"⚠️ Google Calendar tools not available: {e}")
        print("Tip: Ensure credentials.json is set up and complete OAuth flow.")

    # 2. Initialize Brain
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # 3. Create Prompt Wrapper
    prompt = ChatPromptTemplate.from_messages([
        ("system", formatted_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"), 
    ])

    # 4. Construct Agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # 5. Return Executor
    return AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=10)

# ==============================================================================
# MAIN EXECUTION LOOP
# ==============================================================================
if __name__ == "__main__":
    print("🤖 Booting up Agentic System...")
    
    # Initialize
    try:
        agent_executor = build_agent_system()
        print("✅ System Online. Connected to RAG & Google Calendar.")
        print("\n💡 Type your scheduling requests below. Type 'quit' or 'exit' to stop.\n")
        
        while True:
            user_query = input("💬 You: ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_query:
                continue
                
            print(f"\n🤖 Processing: {user_query}\n")
            
            response = agent_executor.invoke({"input": user_query})
            
            print("🏁 RESPONSE ----------------\n")
            print(response["output"])
            print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"\n❌ SYSTEM ERROR: {e}")
        print("Tip: Did you run the RAG ingestion script first? Is credentials.json present?")