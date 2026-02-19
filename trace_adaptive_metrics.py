#!/usr/bin/env python3
"""
Detailed Trace: Adaptive Control Metrics Flow
==============================================

This script demonstrates how each adaptive control metric is computed and tracked:
1. Cache Hit Rate - How tool results are cached and reused
2. Tokens Saved - Estimated tokens saved by avoiding redundant API calls
3. Retries Attempted - How many times tools failed and were retried
4. Retries Succeeded - How many retries eventually succeeded
5. Re-retrievals - How many times groundedness check triggered re-retrieval
6. Clarifications - How many times system requested user clarification

Each metric is traced from initialization → update → final computation.
"""

import logging
import sys
import datetime
from agents import MultiAgentSystem

def setup_trace_logging():
    """Setup logging for metric tracing."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_filename = f'adaptive_metrics_trace_{timestamp}.log'
    
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

logger = logging.getLogger('AdaptiveMetricsTracer')

def trace_section(title: str, description: str = ""):
    """Log a major section in the trace."""
    separator = "=" * 100
    logger.info(f"\n{separator}")
    logger.info(f"📊 {title}")
    logger.info(separator)
    if description:
        logger.info(f"Description: {description}")
        logger.info(separator)

def trace_step(step_num: int, metric: str, action: str, details: str = ""):
    """Log a detailed step in metric computation."""
    logger.info(f"\n{'─' * 100}")
    logger.info(f"STEP {step_num}: [{metric}] {action}")
    if details:
        logger.info(f"Details: {details}")
    logger.info(f"{'─' * 100}")

def trace_metric_update(metric_name: str, old_value, new_value, reason: str):
    """Log a metric update with before/after values."""
    logger.info(f"\n🔄 METRIC UPDATE: {metric_name}")
    logger.info(f"   Before: {old_value}")
    logger.info(f"   After:  {new_value}")
    logger.info(f"   Reason: {reason}")

def demonstrate_adaptive_metrics():
    """
    Demonstrate adaptive control metrics with detailed tracing.
    """
    
    trace_filename = setup_trace_logging()
    
    print("=" * 100)
    print("📊 ADAPTIVE CONTROL METRICS TRACE DEMONSTRATION")
    print("=" * 100)
    print(f"📁 Trace file: {trace_filename}")
    print("=" * 100)
    
    # Suppress HTTP logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)
    
    trace_section(
        "INITIALIZATION: Adaptive Control System",
        "Creating MultiAgentSystem with adaptive control components"
    )
    
    # Initialize system
    system = MultiAgentSystem()
    user_id = "demo_user_metrics"
    system.memory.supabase_memory.user_id = user_id
    session_id = system.memory.supabase_memory.session_id
    
    logger.info(f"✅ System initialized")
    logger.info(f"   Session ID: {session_id}")
    logger.info(f"   User ID: {user_id}")
    
    # Check if adaptive control is available
    if not hasattr(system, 'metrics') or system.metrics is None:
        logger.error("❌ Adaptive control not available - cannot demonstrate metrics")
        return
    
    trace_section(
        "METRIC 1: CACHE HIT RATE",
        "Tracks how often tool results are served from cache vs. fresh API calls"
    )
    
    trace_step(
        1, "CACHE HIT RATE", 
        "INITIALIZATION",
        "Cache starts empty with 0 hits and 0 misses"
    )
    
    logger.info(f"📊 Initial Cache State:")
    logger.info(f"   - cache.hit_count = {system.cache.hit_count}")
    logger.info(f"   - cache.miss_count = {system.cache.miss_count}")
    logger.info(f"   - cache.hit_rate() = {system.cache.hit_rate():.1%}")
    logger.info(f"   - cache entries = {len(system.cache.cache)}")
    
    trace_step(
        2, "CACHE HIT RATE",
        "FIRST QUERY - All Cache Misses",
        "First query will miss cache for all tools (get_current_datetime, search_events, etc.)"
    )
    
    logger.info("\n🔍 Executing first query: 'What's on my calendar tomorrow?'")
    logger.info("Expected: All tools will MISS cache (no cached results yet)")
    
    try:
        response1, agent1 = system.process_query("What's on my calendar tomorrow?")
        
        trace_step(
            3, "CACHE HIT RATE",
            "AFTER FIRST QUERY - Cache Populated",
            "Cache now contains results from first query"
        )
        
        logger.info(f"\n📊 Cache State After First Query:")
        logger.info(f"   - cache.hit_count = {system.cache.hit_count}")
        logger.info(f"   - cache.miss_count = {system.cache.miss_count}")
        logger.info(f"   - cache.hit_rate() = {system.cache.hit_rate():.1%}")
        logger.info(f"   - cache entries = {len(system.cache.cache)}")
        
        # Show what's in cache
        logger.info(f"\n📦 Cached Tools:")
        for cache_key, entry in system.cache.cache.items():
            tool_name = entry.tool_name
            expires_in = (entry.expires_at - datetime.datetime.now()).total_seconds()
            logger.info(f"   - {tool_name}: expires in {expires_in:.0f}s")
        
        trace_step(
            4, "CACHE HIT RATE",
            "SECOND QUERY - Cache Hits Expected",
            "Similar query should hit cache for some tools (get_current_datetime, search_events)"
        )
        
        logger.info("\n🔍 Executing second query: 'Show me tomorrow's schedule'")
        logger.info("Expected: Some tools will HIT cache (get_current_datetime, search_events)")
        
        old_hits = system.cache.hit_count
        old_misses = system.cache.miss_count
        
        response2, agent2 = system.process_query("Show me tomorrow's schedule")
        
        new_hits = system.cache.hit_count
        new_misses = system.cache.miss_count
        
        trace_metric_update(
            "cache.hit_count",
            old_hits,
            new_hits,
            f"Tools served from cache: {new_hits - old_hits}"
        )
        
        trace_metric_update(
            "cache.miss_count",
            old_misses,
            new_misses,
            f"Tools called fresh: {new_misses - old_misses}"
        )
        
        logger.info(f"\n📊 Cache State After Second Query:")
        logger.info(f"   - cache.hit_count = {system.cache.hit_count}")
        logger.info(f"   - cache.miss_count = {system.cache.miss_count}")
        logger.info(f"   - cache.hit_rate() = {system.cache.hit_rate():.1%}")
        
        trace_step(
            5, "CACHE HIT RATE",
            "COMPUTATION FORMULA",
            "hit_rate = hit_count / (hit_count + miss_count)"
        )
        
        total_calls = system.cache.hit_count + system.cache.miss_count
        hit_rate = system.cache.hit_count / total_calls if total_calls > 0 else 0
        
        logger.info(f"\n🧮 Cache Hit Rate Calculation:")
        logger.info(f"   Formula: hit_rate = hit_count / (hit_count + miss_count)")
        logger.info(f"   Calculation: {system.cache.hit_count} / ({system.cache.hit_count} + {system.cache.miss_count})")
        logger.info(f"   Result: {hit_rate:.1%}")
        
    except Exception as e:
        logger.error(f"❌ Error during cache demonstration: {e}")
    
    # =========================================================================
    # METRIC 2: TOKENS SAVED
    # =========================================================================
    
    trace_section(
        "METRIC 2: TOKENS SAVED (ESTIMATED)",
        "Estimates tokens saved by serving results from cache instead of making API calls"
    )
    
    trace_step(
        6, "TOKENS SAVED",
        "COMPUTATION FORMULA",
        "tokens_saved = cache_hits * 100 (assumes 100 tokens per API call)"
    )
    
    logger.info(f"\n🧮 Tokens Saved Calculation:")
    logger.info(f"   Formula: tokens_saved = cache_hits * 100")
    logger.info(f"   Calculation: {system.cache.hit_count} * 100")
    logger.info(f"   Result: {system.cache.hit_count * 100} tokens")
    logger.info(f"\n💡 Explanation:")
    logger.info(f"   - Each cache hit avoids an API call")
    logger.info(f"   - Average API call uses ~100 tokens (input + output)")
    logger.info(f"   - This is a conservative estimate")
    
    # Update metrics from cache
    old_tokens = system.metrics.tokens_saved_estimate
    system.metrics.update_from_cache(system.cache)
    new_tokens = system.metrics.tokens_saved_estimate
    
    trace_metric_update(
        "metrics.tokens_saved_estimate",
        old_tokens,
        new_tokens,
        f"Updated from cache stats: {system.cache.hit_count} hits * 100 tokens/hit"
    )
    
    # =========================================================================
    # METRIC 3: RETRIES ATTEMPTED & SUCCEEDED
    # =========================================================================
    
    trace_section(
        "METRIC 3: RETRIES ATTEMPTED & SUCCEEDED",
        "Tracks tool execution failures and retry attempts with exponential backoff"
    )
    
    trace_step(
        7, "RETRIES",
        "RETRY MECHANISM OVERVIEW",
        "When a tool fails, RetryStrategy attempts up to 3 retries with exponential backoff"
    )
    
    logger.info(f"\n🔄 Retry Strategy Configuration:")
    logger.info(f"   - max_retries = {system.retry_strategy.max_retries}")
    logger.info(f"   - base_delay = {system.retry_strategy.base_delay}s")
    logger.info(f"   - backoff = exponential (1s, 2s, 4s)")
    
    logger.info(f"\n📊 Current Retry Metrics:")
    logger.info(f"   - metrics.retries_attempted = {system.metrics.retries_attempted}")
    logger.info(f"   - metrics.retries_succeeded = {system.metrics.retries_succeeded}")
    
    trace_step(
        8, "RETRIES",
        "RETRY FLOW EXAMPLE",
        "Observe → Reason → Decide → Act → Evaluate → Update → Repeat"
    )
    
    logger.info(f"\n🔄 Retry Flow (when tool fails):")
    logger.info(f"   1. OBSERVE: Tool execution failed (e.g., network error)")
    logger.info(f"   2. REASON: Analyze error type (transient vs. permanent)")
    logger.info(f"   3. DECIDE: Determine if retry is appropriate")
    logger.info(f"   4. ACT: Wait with exponential backoff (1s → 2s → 4s)")
    logger.info(f"   5. EVALUATE: Check if retry succeeded")
    logger.info(f"   6. UPDATE: Increment retry counters")
    logger.info(f"   7. REPEAT: Try again or escalate failure")
    
    logger.info(f"\n💡 Retry Tracking:")
    logger.info(f"   - retries_attempted: Incremented when tool fails after all retries")
    logger.info(f"   - retries_succeeded: Incremented when retry eventually succeeds")
    logger.info(f"   - Success rate = retries_succeeded / retries_attempted")
    
    # =========================================================================
    # METRIC 4: RE-RETRIEVALS
    # =========================================================================
    
    trace_section(
        "METRIC 4: RE-RETRIEVALS",
        "Tracks when groundedness check detects unsupported claims and triggers re-retrieval"
    )
    
    trace_step(
        9, "RE-RETRIEVALS",
        "GROUNDEDNESS EVALUATION OVERVIEW",
        "Checks if agent response is grounded in retrieved evidence"
    )
    
    logger.info(f"\n🔍 Groundedness Evaluator Configuration:")
    logger.info(f"   - threshold = {system.groundedness_evaluator.threshold}")
    logger.info(f"   - action = RE_RETRIEVE if score < threshold")
    
    logger.info(f"\n📊 Current Re-retrieval Metrics:")
    logger.info(f"   - metrics.re_retrievals = {system.metrics.re_retrievals}")
    
    trace_step(
        10, "RE-RETRIEVALS",
        "GROUNDEDNESS CHECK FLOW",
        "Extract claims → Check evidence → Compute score → Decide action"
    )
    
    logger.info(f"\n🔍 Groundedness Check Flow:")
    logger.info(f"   1. Extract claims from agent response (split by sentences)")
    logger.info(f"   2. For each claim, check if supported by tool outputs")
    logger.info(f"   3. Compute groundedness score = supported_claims / total_claims")
    logger.info(f"   4. If score < {system.groundedness_evaluator.threshold}:")
    logger.info(f"      - Action = RE_RETRIEVE")
    logger.info(f"      - Increment metrics.re_retrievals")
    logger.info(f"      - (Currently logs warning but continues)")
    
    logger.info(f"\n💡 Re-retrieval Tracking:")
    logger.info(f"   - Incremented when groundedness score < threshold")
    logger.info(f"   - Indicates agent made unsupported claims")
    logger.info(f"   - Triggers additional RAG retrieval (when implemented)")
    
    # =========================================================================
    # METRIC 5: CLARIFICATIONS
    # =========================================================================
    
    trace_section(
        "METRIC 5: CLARIFICATIONS REQUESTED",
        "Tracks when confidence evaluator detects ambiguous queries and requests clarification"
    )
    
    trace_step(
        11, "CLARIFICATIONS",
        "CONFIDENCE EVALUATION OVERVIEW",
        "Assesses query clarity, tool availability, and result quality"
    )
    
    logger.info(f"\n🎯 Confidence Evaluator Configuration:")
    logger.info(f"   - threshold = {system.confidence_evaluator.threshold}")
    logger.info(f"   - action = REQUEST_CLARIFICATION if confidence < threshold")
    
    logger.info(f"\n📊 Current Clarification Metrics:")
    logger.info(f"   - metrics.clarifications_requested = {system.metrics.clarifications_requested}")
    
    trace_step(
        12, "CLARIFICATIONS",
        "CONFIDENCE CHECK FLOW",
        "Assess clarity → Check tools → Evaluate results → Compute confidence"
    )
    
    logger.info(f"\n🎯 Confidence Check Flow:")
    logger.info(f"   1. Assess query clarity (0.0 - 1.0):")
    logger.info(f"      - Check for ambiguous terms (tomorrow, next week)")
    logger.info(f"      - Check for missing details (time, duration)")
    logger.info(f"   2. Assess tool availability (0.0 - 1.0):")
    logger.info(f"      - Check if required tools are available")
    logger.info(f"   3. Assess result quality (0.0 - 1.0):")
    logger.info(f"      - Check if tool results are valid")
    logger.info(f"   4. Compute overall confidence = (clarity + tools + quality) / 3")
    logger.info(f"   5. If confidence < {system.confidence_evaluator.threshold}:")
    logger.info(f"      - Action = REQUEST_CLARIFICATION")
    logger.info(f"      - Increment metrics.clarifications_requested")
    
    logger.info(f"\n💡 Clarification Tracking:")
    logger.info(f"   - Incremented when confidence score < threshold")
    logger.info(f"   - Indicates query is ambiguous or incomplete")
    logger.info(f"   - Triggers clarification request to user")
    
    # =========================================================================
    # FINAL METRICS REPORT
    # =========================================================================
    
    trace_section(
        "FINAL METRICS REPORT",
        "Complete summary of all adaptive control metrics"
    )
    
    trace_step(
        13, "ALL METRICS",
        "FINAL COMPUTATION",
        "Aggregating all metrics for final report"
    )
    
    # Update metrics one final time
    system.metrics.update_from_cache(system.cache)
    
    logger.info(f"\n📊 COMPLETE METRICS BREAKDOWN:")
    logger.info(f"\n1. CACHE HIT RATE:")
    logger.info(f"   - Formula: hit_count / (hit_count + miss_count)")
    logger.info(f"   - Calculation: {system.cache.hit_count} / {system.cache.hit_count + system.cache.miss_count}")
    logger.info(f"   - Result: {system.cache.hit_rate():.1%}")
    
    logger.info(f"\n2. TOKENS SAVED:")
    logger.info(f"   - Formula: cache_hits * 100")
    logger.info(f"   - Calculation: {system.cache.hit_count} * 100")
    logger.info(f"   - Result: {system.metrics.tokens_saved_estimate} tokens")
    
    logger.info(f"\n3. RETRIES ATTEMPTED:")
    logger.info(f"   - Value: {system.metrics.retries_attempted}")
    logger.info(f"   - Meaning: Tools that failed after all retry attempts")
    
    logger.info(f"\n4. RETRIES SUCCEEDED:")
    logger.info(f"   - Value: {system.metrics.retries_succeeded}")
    logger.info(f"   - Meaning: Retries that eventually succeeded")
    
    logger.info(f"\n5. RE-RETRIEVALS:")
    logger.info(f"   - Value: {system.metrics.re_retrievals}")
    logger.info(f"   - Meaning: Times groundedness check triggered re-retrieval")
    
    logger.info(f"\n6. CLARIFICATIONS:")
    logger.info(f"   - Value: {system.metrics.clarifications_requested}")
    logger.info(f"   - Meaning: Times system requested user clarification")
    
    # Show the formatted report
    logger.info(f"\n{system.metrics.report()}")
    
    trace_section(
        "DEMONSTRATION COMPLETE",
        "All adaptive control metrics have been traced and explained"
    )
    
    logger.info(f"\n✅ Key Takeaways:")
    logger.info(f"   1. Cache Hit Rate: Measures efficiency of result caching")
    logger.info(f"   2. Tokens Saved: Estimates cost savings from caching")
    logger.info(f"   3. Retries: Tracks reliability and error recovery")
    logger.info(f"   4. Re-retrievals: Measures response groundedness")
    logger.info(f"   5. Clarifications: Tracks query ambiguity")
    
    logger.info(f"\n📁 Complete trace saved to: {trace_filename}")
    
    # Close session
    try:
        system.memory.supabase_memory.close_session()
        logger.info("✅ Session closed")
    except Exception as e:
        logger.error(f"Error closing session: {e}")

if __name__ == "__main__":
    demonstrate_adaptive_metrics()
