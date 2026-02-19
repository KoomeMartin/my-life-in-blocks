"""
Adaptive Control System for Multi-Agent Calendar Scheduling
Implements: Observe → Reason → Decide → Act → Evaluate → Update → Repeat

Features:
- Tool result caching (30-50% token savings)
- Retry logic with exponential backoff
- Groundedness checking
- Confidence-based clarification
- Closed-loop feedback
"""

import hashlib
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ==============================================================================
# CACHE CONFIGURATION
# ==============================================================================

# Different TTLs for different tool types
CACHE_TTL = {
    'search_events': 300,        # 5 minutes (calendar changes frequently)
    'calendars_info': 600,       # 10 minutes (calendar list rarely changes)
    'search_user_profile': 3600, # 1 hour (profile rarely changes)
    'get_current_datetime': 60,  # 1 minute (time changes)
    'create_event': 0,           # Never cache (side effects)
    'update_event': 0,           # Never cache (side effects)
    'delete_event': 0,           # Never cache (side effects)
    'send_review_email': 0,      # Never cache (side effects)
}


def get_ttl_for_tool(tool_name: str) -> int:
    """Get appropriate TTL for tool"""
    return CACHE_TTL.get(tool_name, 300)  # Default 5 minutes


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class CacheEntry:
    """Cache entry with TTL"""
    result: Any
    cached_at: datetime
    expires_at: datetime
    tool_name: str


@dataclass
class GroundednessResult:
    """Result of groundedness evaluation"""
    score: float
    supported_claims: int
    total_claims: int
    unsupported_claims: List[str]
    action: str  # "ACCEPT" or "RE_RETRIEVE"


@dataclass
class ConfidenceResult:
    """Result of confidence evaluation"""
    confidence: float
    clarity_score: float
    tool_score: float
    result_score: float
    action: str  # "PROCEED" or "REQUEST_CLARIFICATION"
    clarification_needed: Optional[str]


# ==============================================================================
# TOOL RESULT CACHE
# ==============================================================================

class ToolResultCache:
    """
    Cache tool results to avoid redundant API calls.
    Implements TTL (time-to-live) and invalidation strategies.
    """
    
    def __init__(self):
        self.cache: Dict[str, CacheEntry] = {}
        self.hit_count = 0
        self.miss_count = 0
    
    def get_cache_key(self, tool_name: str, tool_input: dict) -> str:
        """Generate cache key from tool name and input"""
        # Sort dict for consistent hashing
        input_str = json.dumps(tool_input, sort_keys=True, default=str)
        hash_value = hashlib.md5(input_str.encode()).hexdigest()
        return f"{tool_name}:{hash_value}"
    
    def get(self, tool_name: str, tool_input: dict) -> Optional[Any]:
        """Get cached result if valid"""
        cache_key = self.get_cache_key(tool_name, tool_input)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Check if expired
            if datetime.now() < entry.expires_at:
                self.hit_count += 1
                logger.info(f"🎯 CACHE HIT: {tool_name} (saved API call)")
                logger.info(f"📊 CACHE STATS: {self.hit_count} hits, {self.miss_count} misses, {self.hit_rate():.1%} hit rate")
                return entry.result
            else:
                # Expired - remove from cache
                del self.cache[cache_key]
                logger.info(f"⏰ CACHE EXPIRED: {tool_name}")
        
        self.miss_count += 1
        logger.info(f"❌ CACHE MISS: {tool_name} (will call tool)")
        return None
    
    def set(self, tool_name: str, tool_input: dict, result: Any, ttl_seconds: int = 300):
        """Cache tool result with TTL"""
        cache_key = self.get_cache_key(tool_name, tool_input)
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        
        self.cache[cache_key] = CacheEntry(
            result=result,
            cached_at=datetime.now(),
            expires_at=expires_at,
            tool_name=tool_name
        )
        
        logger.info(f"💾 CACHE SET: {tool_name} (TTL: {ttl_seconds}s, expires: {expires_at.strftime('%H:%M:%S')})")
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern"""
        if pattern is None:
            # Clear all
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"🗑️ CACHE INVALIDATED: All entries ({count} cleared)")
        else:
            # Clear matching pattern
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
            logger.info(f"🗑️ CACHE INVALIDATED: {len(keys_to_delete)} entries matching '{pattern}'")
    
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            'hits': self.hit_count,
            'misses': self.miss_count,
            'hit_rate': self.hit_rate(),
            'entries': len(self.cache)
        }


# ==============================================================================
# RETRY STRATEGY
# ==============================================================================

class ToolExecutionError(Exception):
    """Raised when tool execution fails after retries"""
    pass


class RetryStrategy:
    """
    Implement retry logic with exponential backoff for tool failures.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def execute_with_retry(self, tool_func, tool_name: str, *args, **kwargs) -> Any:
        """
        Execute tool with retry logic.
        
        Implements: Observe → Reason → Decide → Act → Evaluate → Update → Repeat
        """
        attempt = 0
        last_error = None
        
        while attempt < self.max_retries:
            try:
                # OBSERVE
                logger.info(f"👁️ OBSERVE: Attempting {tool_name} (attempt {attempt + 1}/{self.max_retries})")
                
                # ACT
                result = tool_func(*args, **kwargs)
                
                # EVALUATE
                if self.is_valid_result(result):
                    logger.info(f"✅ EVALUATE: {tool_name} succeeded on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"⚠️ EVALUATE: {tool_name} returned invalid result")
                    raise ValueError("Invalid tool result")
                
            except Exception as e:
                last_error = e
                attempt += 1
                
                # REASON
                logger.error(f"🤔 REASON: {tool_name} failed - {str(e)}")
                
                if attempt < self.max_retries:
                    # DECIDE
                    delay = self.base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"🎯 DECIDE: Will retry after {delay}s delay")
                    
                    # UPDATE
                    time.sleep(delay)
                    
                    # REPEAT
                    logger.info(f"🔄 REPEAT: Retrying {tool_name}...")
                else:
                    # ESCALATE
                    logger.error(f"🚨 ESCALATE: {tool_name} failed after {self.max_retries} attempts")
                    raise ToolExecutionError(f"{tool_name} failed: {last_error}")
    
    def is_valid_result(self, result: Any) -> bool:
        """Validate tool result"""
        if result is None:
            return False
        if isinstance(result, str) and len(result) == 0:
            return False
        if isinstance(result, list) and len(result) == 0:
            # Empty list might be valid (no events found)
            return True
        return True


# ==============================================================================
# GROUNDEDNESS EVALUATOR
# ==============================================================================

class GroundednessEvaluator:
    """
    Evaluate if agent response is grounded in retrieved evidence.
    Implements closed-loop feedback for re-retrieval.
    """
    
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
    
    def evaluate(self, response: str, tool_outputs: List[str]) -> GroundednessResult:
        """
        Evaluate groundedness of response against tool outputs.
        
        Returns:
            GroundednessResult with score and feedback
        """
        logger.info("🔍 EVALUATE: Checking response groundedness")
        
        # Extract claims from response
        claims = self.extract_claims(response)
        logger.info(f"📝 EVALUATE: Extracted {len(claims)} claims from response")
        
        if not claims:
            # No claims to verify - accept
            logger.info("✅ EVALUATE: No verifiable claims (conversational response)")
            return GroundednessResult(
                score=1.0,
                supported_claims=0,
                total_claims=0,
                unsupported_claims=[],
                action="ACCEPT"
            )
        
        # Check each claim against evidence
        supported_claims = 0
        unsupported_claims = []
        
        for claim in claims:
            if self.is_supported(claim, tool_outputs):
                supported_claims += 1
            else:
                unsupported_claims.append(claim)
        
        # Calculate groundedness score
        score = supported_claims / len(claims) if claims else 1.0
        
        logger.info(f"📊 EVALUATE: Groundedness score = {score:.2f} ({supported_claims}/{len(claims)} claims supported)")
        logger.info(f"🎯 EVALUATE: Threshold = {self.threshold}")
        
        # Determine action
        if score < self.threshold and len(unsupported_claims) > 0:
            logger.warning(f"⚠️ EVALUATE: Groundedness below threshold!")
            logger.warning(f"❌ EVALUATE: Unsupported claims: {unsupported_claims[:2]}")
            action = "RE_RETRIEVE"
        else:
            logger.info(f"✅ EVALUATE: Groundedness acceptable")
            action = "ACCEPT"
        
        return GroundednessResult(
            score=score,
            supported_claims=supported_claims,
            total_claims=len(claims),
            unsupported_claims=unsupported_claims,
            action=action
        )
    
    def extract_claims(self, response: str) -> List[str]:
        """Extract factual claims from response"""
        # Remove agent identification headers
        if '**' in response and 'AGENT RESPONSE:**' in response:
            parts = response.split('\n\n', 1)
            if len(parts) > 1:
                response = parts[1]
        
        # Split by sentences
        sentences = response.replace('!', '.').replace('?', '.').split('.')
        
        # Filter for factual claims (not questions, not greetings)
        claims = []
        for s in sentences:
            s = s.strip()
            # Skip short sentences, questions, greetings
            if len(s) > 20 and not s.lower().startswith(('how', 'what', 'when', 'where', 'why', 'hello', 'hi')):
                claims.append(s)
        
        return claims[:10]  # Limit to 10 claims for performance
    
    def is_supported(self, claim: str, evidence: List[str]) -> bool:
        """Check if claim is supported by evidence"""
        claim_lower = claim.lower()
        
        # Check if any evidence contains claim keywords
        for evidence_text in evidence:
            evidence_lower = str(evidence_text).lower()
            
            # Simple keyword matching
            claim_words = set(claim_lower.split())
            evidence_words = set(evidence_lower.split())
            
            # Remove common words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            claim_words -= stop_words
            evidence_words -= stop_words
            
            if not claim_words:
                continue
            
            # If >40% of claim words appear in evidence, consider supported
            overlap = len(claim_words & evidence_words)
            if overlap / len(claim_words) > 0.4:
                return True
        
        return False


# ==============================================================================
# CONFIDENCE EVALUATOR
# ==============================================================================

class ConfidenceEvaluator:
    """
    Evaluate confidence in agent's ability to answer query.
    Request clarification if confidence is low.
    """
    
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
    
    def evaluate_confidence(self, query: str, available_tools: List[str], 
                          tool_results: List[Any]) -> ConfidenceResult:
        """
        Evaluate confidence in answering query.
        
        Factors:
        - Query clarity (ambiguous terms?)
        - Tool availability (have right tools?)
        - Tool results quality (got good data?)
        """
        logger.info("🔍 EVALUATE: Checking confidence in response")
        
        # Factor 1: Query clarity (0-1)
        clarity_score = self.assess_query_clarity(query)
        logger.info(f"📝 EVALUATE: Query clarity = {clarity_score:.2f}")
        
        # Factor 2: Tool availability (0-1)
        tool_score = self.assess_tool_availability(query, available_tools)
        logger.info(f"🔧 EVALUATE: Tool availability = {tool_score:.2f}")
        
        # Factor 3: Result quality (0-1)
        result_score = self.assess_result_quality(tool_results)
        logger.info(f"📊 EVALUATE: Result quality = {result_score:.2f}")
        
        # Overall confidence (weighted average)
        confidence = (clarity_score * 0.3 + tool_score * 0.3 + result_score * 0.4)
        logger.info(f"🎯 EVALUATE: Overall confidence = {confidence:.2f}")
        
        # DECIDE
        if confidence < self.threshold:
            logger.warning(f"⚠️ EVALUATE: Confidence below threshold ({self.threshold})")
            action = "REQUEST_CLARIFICATION"
            clarification_needed = self.generate_clarification_request(
                query, clarity_score, tool_score, result_score
            )
        else:
            logger.info(f"✅ EVALUATE: Confidence acceptable")
            action = "PROCEED"
            clarification_needed = None
        
        return ConfidenceResult(
            confidence=confidence,
            clarity_score=clarity_score,
            tool_score=tool_score,
            result_score=result_score,
            action=action,
            clarification_needed=clarification_needed
        )
    
    def assess_query_clarity(self, query: str) -> float:
        """Assess how clear/unambiguous the query is"""
        ambiguous_terms = ['it', 'that', 'this', 'them', 'those', 'something', 'stuff', 'thing']
        query_lower = query.lower()
        
        # Penalize for ambiguous terms
        ambiguity_count = sum(1 for term in ambiguous_terms if f' {term} ' in f' {query_lower} ')
        
        # Penalize for very short queries
        word_count = len(query.split())
        if word_count < 3:
            return 0.6
        
        # Calculate clarity score
        clarity = 1.0 - (ambiguity_count * 0.15)
        return max(0.3, min(1.0, clarity))
    
    def assess_tool_availability(self, query: str, available_tools: List[str]) -> float:
        """Assess if we have the right tools for this query"""
        query_lower = query.lower()
        
        # Check for calendar-related queries
        if any(word in query_lower for word in ['meeting', 'calendar', 'schedule', 'event', 'appointment']):
            has_calendar_tools = any('calendar' in tool or 'event' in tool for tool in available_tools)
            return 1.0 if has_calendar_tools else 0.4
        
        # Check for profile-related queries
        if any(word in query_lower for word in ['energy', 'productivity', 'skill', 'preference']):
            has_profile_tools = any('profile' in tool for tool in available_tools)
            return 1.0 if has_profile_tools else 0.5
        
        return 0.8  # Default: assume we have what we need
    
    def assess_result_quality(self, tool_results: List[Any]) -> float:
        """Assess quality of tool results"""
        if not tool_results:
            return 0.5  # No results = medium confidence (might be conversational)
        
        # Check if results are meaningful
        non_empty_results = [r for r in tool_results if r and len(str(r)) > 10]
        
        if not non_empty_results:
            return 0.5  # Empty results = medium confidence
        
        return 0.9  # Good results
    
    def generate_clarification_request(self, query: str, clarity: float, 
                                      tools: float, results: float) -> str:
        """Generate clarification request based on low confidence factors"""
        if clarity < 0.5:
            return "I need more details. Could you be more specific about what you're asking?"
        elif tools < 0.5:
            return "I don't have the right information to answer that. Could you rephrase your question?"
        elif results < 0.5:
            return "I couldn't find enough information. Could you provide more context?"
        else:
            return "I'm not confident in my answer. Could you clarify your question?"


# ==============================================================================
# ADAPTIVE METRICS
# ==============================================================================

class AdaptiveMetrics:
    """Track adaptive control metrics"""
    
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
        self.retries_attempted = 0
        self.retries_succeeded = 0
        self.re_retrievals = 0
        self.clarifications_requested = 0
        self.tokens_saved_estimate = 0
    
    def update_from_cache(self, cache: ToolResultCache):
        """Update metrics from cache"""
        self.cache_hits = cache.hit_count
        self.cache_misses = cache.miss_count
        # Estimate tokens saved (assume 100 tokens per API call)
        self.tokens_saved_estimate = self.cache_hits * 100
    
    def report(self) -> str:
        """Generate metrics report"""
        total_cache = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_cache if total_cache > 0 else 0
        
        return f"""
📊 ADAPTIVE CONTROL METRICS:
- Cache hit rate: {hit_rate:.1%} ({self.cache_hits}/{total_cache})
- Tokens saved (est): {self.tokens_saved_estimate}
- Retries attempted: {self.retries_attempted}
- Retries succeeded: {self.retries_succeeded}
- Re-retrievals: {self.re_retrievals}
- Clarifications: {self.clarifications_requested}
        """.strip()
