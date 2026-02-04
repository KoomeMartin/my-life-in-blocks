#!/usr/bin/env python3
"""
Example script showing how to use the standalone evaluation system.
"""

from evaluation import evaluate_agent_responses, EvaluationManager

def run_custom_evaluation():
    """Example of running custom evaluation tests."""
    
    # Define your test cases
    test_cases = [
        {
            "name": "Calendar Query Test",
            "response": "You have 2 meetings today: Team standup at 9 AM and Project review at 2 PM.",
            "agent_type": "manager",
            "tools": ["calendar_search_events"],
            "outputs": {
                "calendar_search_events": "Found 2 events: Team standup 09:00-09:30, Project review 14:00-15:00"
            },
            "rag": []
        },
        {
            "name": "Scheduling Recommendation Test", 
            "response": "I recommend scheduling your meeting at 10 AM tomorrow, during your peak energy hours.",
            "agent_type": "planner",
            "tools": ["calendar_search_events", "search_user_profile_and_policies"],
            "outputs": {
                "calendar_search_events": "No conflicts found at 10 AM tomorrow"
            },
            "rag": ["User energy profile: Peak 8AM-12PM, Low 1-4PM"]
        }
    ]
    
    # Run evaluation and save to JSON
    results_file = evaluate_agent_responses(test_cases, "custom_test_session")
    
    print(f"\n📁 Evaluation results saved to: {results_file}")
    
    # Example of loading results later
    manager = EvaluationManager()
    session = manager.load_evaluation_session(results_file)
    
    if session:
        print(f"\n📊 Loaded session: {session.session_id}")
        print(f"📈 Summary stats: {session.summary_stats}")
    
    return results_file

if __name__ == "__main__":
    print("🧪 CUSTOM EVALUATION EXAMPLE")
    print("=" * 40)
    
    results_file = run_custom_evaluation()
    
    print(f"\n✅ Example complete!")
    print(f"🔍 Check the JSON file for detailed results: {results_file}")