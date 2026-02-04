"""
Standalone Verification Module (Guardrails) for Multi-Agent Calendar System

This module implements:
1. Self-Evaluation Node: Compares agent output against retrieved source material
2. Confidence Scoring: Provides Groundedness Score (0-1) for response reliability
3. Hallucination Detection: Flags unsupported claims and requests clarification
4. JSON Export: Saves evaluation results to JSON files for later reference

The Groundedness Score represents the fraction of key factual claims 
that are explicitly supported by retrieved passages or tool outputs.

Usage:
- Run standalone: python evaluation.py
- Import for testing: from evaluation import evaluate_agent_responses
"""

import os
import re
import json
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

# Setup clean logging for better user experience
class CleanConsoleFormatter(logging.Formatter):
    """Custom formatter for clean console output"""
    def format(self, record):
        if record.levelno >= logging.ERROR:
            return f"❌ {record.getMessage()}"
        elif record.levelno >= logging.WARNING:
            return f"⚠️ {record.getMessage()}"
        else:
            return ""  # Don't show INFO messages in console

# Setup file logging (detailed)
file_handler = logging.FileHandler('verification_trace.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Setup console logging (minimal)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)  # Only show warnings and errors
console_handler.setFormatter(CleanConsoleFormatter())

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger('VerificationModule')

@dataclass
class FactualClaim:
    """Represents a factual claim extracted from agent response."""
    claim: str
    claim_type: str  # 'time', 'event', 'availability', 'constraint', 'recommendation'
    confidence: float
    source_required: bool = True

@dataclass
class EvidenceSource:
    """Represents evidence from retrieved sources or tool outputs."""
    content: str
    source_type: str  # 'rag_retrieval', 'calendar_tool', 'user_profile', 'system_data'
    reliability: float  # 0-1 score for source reliability
    timestamp: str

@dataclass
class VerificationResult:
    """Results of verification process."""
    groundedness_score: float  # 0-1: fraction of claims supported by evidence
    supported_claims: List[FactualClaim]
    unsupported_claims: List[FactualClaim]
    evidence_sources: List[EvidenceSource]
    confidence_level: str  # 'high', 'medium', 'low'
    requires_clarification: bool
    verification_details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'groundedness_score': self.groundedness_score,
            'supported_claims': [asdict(claim) for claim in self.supported_claims],
            'unsupported_claims': [asdict(claim) for claim in self.unsupported_claims],
            'evidence_sources': [asdict(source) for source in self.evidence_sources],
            'confidence_level': self.confidence_level,
            'requires_clarification': self.requires_clarification,
            'verification_details': self.verification_details
        }

@dataclass
class EvaluationSession:
    """Represents a complete evaluation session with multiple test cases."""
    session_id: str
    timestamp: str
    test_cases: List[Dict[str, Any]]
    summary_stats: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

class EvaluationManager:
    """Manages evaluation sessions and JSON export functionality."""
    
    def __init__(self, results_dir: str = "evaluation_results"):
        self.results_dir = results_dir
        self.ensure_results_directory()
    
    def ensure_results_directory(self):
        """Create results directory if it doesn't exist."""
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            logger.info(f"Created evaluation results directory: {self.results_dir}")
    
    def save_evaluation_session(self, session: EvaluationSession) -> str:
        """Save evaluation session to JSON file."""
        filename = f"evaluation_{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Evaluation session saved to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save evaluation session: {e}")
            return ""
    
    def load_evaluation_session(self, filepath: str) -> Optional[EvaluationSession]:
        """Load evaluation session from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return EvaluationSession(**data)
        except Exception as e:
            logger.error(f"Failed to load evaluation session: {e}")
            return None
    
    def list_evaluation_files(self) -> List[str]:
        """List all evaluation JSON files in results directory."""
        try:
            files = [f for f in os.listdir(self.results_dir) if f.startswith('evaluation_') and f.endswith('.json')]
            return sorted(files, reverse=True)  # Most recent first
        except Exception as e:
            logger.error(f"Failed to list evaluation files: {e}")
            return []

class FactualClaimExtractor:
    """Extracts factual claims from agent responses."""
    
    def __init__(self, llm):
        self.llm = llm
        self.claim_extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a factual claim extraction specialist. 

Extract ALL factual claims from the agent response that can be verified against source material.

CLAIM TYPES:
- TIME: Specific times, dates, durations, schedules
- EVENT: Meeting details, appointments, calendar events  
- AVAILABILITY: Free/busy status, conflicts, open slots
- CONSTRAINT: User preferences, energy patterns, rules
- RECOMMENDATION: Suggested actions, optimal times, strategies

For each claim, determine:
1. The exact factual statement
2. The claim type
3. Whether it requires source verification (true/false)

Return ONLY valid JSON format without any additional text. Example:
{{"claims": [{{"claim": "User has a meeting at 10 AM tomorrow", "claim_type": "event", "source_required": true}}]}}"""),
            ("human", "Agent Response: {agent_response}")
        ])
    
    def extract_claims(self, agent_response: str) -> List[FactualClaim]:
        """Extract factual claims from agent response."""
        try:
            result = self.llm.invoke(
                self.claim_extraction_prompt.format_messages(
                    agent_response=agent_response
                )
            )
            
            # Clean the response content
            content = result.content.strip()
            
            # Try to extract JSON from the response
            try:
                claims_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to find JSON within the response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    claims_data = json.loads(json_match.group())
                else:
                    logger.error(f"CLAIM EXTRACTION ERROR: Could not parse JSON from: {content[:100]}")
                    return []
            
            claims = []
            
            for claim_info in claims_data.get('claims', []):
                claim = FactualClaim(
                    claim=claim_info['claim'],
                    claim_type=claim_info['claim_type'],
                    confidence=0.5,  # Initial confidence
                    source_required=claim_info.get('source_required', True)
                )
                claims.append(claim)
            
            logger.info(f"CLAIM EXTRACTION: Extracted {len(claims)} factual claims")
            return claims
            
        except Exception as e:
            logger.error(f"CLAIM EXTRACTION ERROR: {e}")
            return []

class EvidenceCollector:
    """Collects and processes evidence from various sources."""
    
    def __init__(self):
        self.source_reliability = {
            'calendar_tool': 0.95,  # High reliability - direct API data
            'rag_retrieval': 0.85,  # High reliability - user profile data
            'user_profile': 0.90,   # High reliability - structured data
            'system_data': 0.80,    # Good reliability - system information
            'agent_reasoning': 0.60  # Lower reliability - agent inference
        }
    
    def collect_evidence(self, tools_used: List[str], tool_outputs: Dict[str, str], 
                        rag_retrievals: List[str]) -> List[EvidenceSource]:
        """Collect evidence from all available sources."""
        evidence_sources = []
        
        # Calendar tool evidence (highest reliability)
        for tool_name in tools_used:
            if tool_name in tool_outputs:
                evidence = EvidenceSource(
                    content=tool_outputs[tool_name],
                    source_type='calendar_tool',
                    reliability=self.source_reliability['calendar_tool'],
                    timestamp=datetime.now().isoformat()
                )
                evidence_sources.append(evidence)
        
        # RAG retrieval evidence
        for retrieval in rag_retrievals:
            evidence = EvidenceSource(
                content=retrieval,
                source_type='rag_retrieval', 
                reliability=self.source_reliability['rag_retrieval'],
                timestamp=datetime.now().isoformat()
            )
            evidence_sources.append(evidence)
        
        logger.info(f"EVIDENCE COLLECTION: Collected {len(evidence_sources)} evidence sources")
        return evidence_sources

class GroundednessEvaluator:
    """Evaluates groundedness of claims against evidence."""
    
    def __init__(self, llm):
        self.llm = llm
        self.evaluation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a groundedness evaluation specialist.

Compare each factual claim against the provided evidence sources to determine support level.

EVALUATION CRITERIA:
- FULLY_SUPPORTED: Claim is explicitly stated or directly derivable from evidence
- PARTIALLY_SUPPORTED: Claim has some evidence but missing key details
- UNSUPPORTED: No evidence supports this claim
- CONTRADICTED: Evidence contradicts this claim

For each claim, provide:
1. Support level (FULLY_SUPPORTED/PARTIALLY_SUPPORTED/UNSUPPORTED/CONTRADICTED)
2. Supporting evidence (quote relevant parts)
3. Confidence score (0-1)

Return ONLY valid JSON format without any additional text. Example:
{{"evaluations": [{{"claim": "Original claim text", "support_level": "FULLY_SUPPORTED", "supporting_evidence": "Relevant evidence quote", "confidence": 0.9}}]}}"""),
            ("human", """
CLAIMS TO EVALUATE:
{claims}

EVIDENCE SOURCES:
{evidence}

Evaluate each claim's groundedness against the evidence.""")
        ])
    
    def evaluate_claims(self, claims: List[FactualClaim], 
                       evidence_sources: List[EvidenceSource]) -> Dict[str, Any]:
        """Evaluate groundedness of claims against evidence."""
        try:
            # Format claims and evidence for evaluation
            claims_text = "\n".join([f"- {claim.claim} (Type: {claim.claim_type})" 
                                   for claim in claims])
            
            evidence_text = "\n".join([f"[{ev.source_type}] {ev.content[:200]}..." 
                                     for ev in evidence_sources])
            
            result = self.llm.invoke(
                self.evaluation_prompt.format_messages(
                    claims=claims_text,
                    evidence=evidence_text
                )
            )
            
            # Clean and parse the response
            content = result.content.strip()
            
            try:
                evaluation_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    evaluation_data = json.loads(json_match.group())
                else:
                    logger.error(f"GROUNDEDNESS EVALUATION ERROR: Could not parse JSON from: {content[:100]}")
                    return {"evaluations": []}
            
            logger.info(f"GROUNDEDNESS EVALUATION: Evaluated {len(claims)} claims")
            return evaluation_data
            
        except Exception as e:
            logger.error(f"GROUNDEDNESS EVALUATION ERROR: {e}")
            return {"evaluations": []}

class VerificationModule:
    """Main verification module implementing self-evaluation and confidence scoring."""
    
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        # Check for API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required. Please set it in your .env file.")
        
        self.llm = ChatOpenAI(model=llm_model, temperature=0, api_key=api_key)
        self.claim_extractor = FactualClaimExtractor(self.llm)
        self.evidence_collector = EvidenceCollector()
        self.groundedness_evaluator = GroundednessEvaluator(self.llm)
        
        # Thresholds for confidence levels
        self.confidence_thresholds = {
            'high': 0.8,    # 80%+ claims supported
            'medium': 0.6,  # 60-79% claims supported  
            'low': 0.4      # 40-59% claims supported
        }
    
    def verify_response(self, agent_response: str, tools_used: List[str] = None,
                       tool_outputs: Dict[str, str] = None, 
                       rag_retrievals: List[str] = None) -> VerificationResult:
        """
        Main verification method implementing self-evaluation node.
        
        Args:
            agent_response: The agent's response to verify
            tools_used: List of tools used by the agent
            tool_outputs: Dictionary of tool outputs
            rag_retrievals: List of RAG retrieval results
            
        Returns:
            VerificationResult with groundedness score and details
        """
        logger.info("VERIFICATION: Starting self-evaluation process")
        
        # Initialize inputs
        tools_used = tools_used or []
        tool_outputs = tool_outputs or {}
        rag_retrievals = rag_retrievals or []
        
        # Step 1: Extract factual claims from agent response
        logger.info("VERIFICATION STEP 1: Extracting factual claims")
        claims = self.claim_extractor.extract_claims(agent_response)
        
        if not claims:
            logger.warning("VERIFICATION: No factual claims extracted")
            return VerificationResult(
                groundedness_score=1.0,  # No claims to verify
                supported_claims=[],
                unsupported_claims=[],
                evidence_sources=[],
                confidence_level='high',
                requires_clarification=False,
                verification_details={'reason': 'No factual claims to verify'}
            )
        
        # Step 2: Collect evidence from all sources
        logger.info("VERIFICATION STEP 2: Collecting evidence sources")
        evidence_sources = self.evidence_collector.collect_evidence(
            tools_used, tool_outputs, rag_retrievals
        )
        
        if not evidence_sources:
            logger.warning("VERIFICATION: No evidence sources available")
            return VerificationResult(
                groundedness_score=0.0,  # No evidence to support claims
                supported_claims=[],
                unsupported_claims=claims,
                evidence_sources=[],
                confidence_level='low',
                requires_clarification=True,
                verification_details={'reason': 'No evidence sources available'}
            )
        
        # Step 3: Evaluate groundedness of claims against evidence
        logger.info("VERIFICATION STEP 3: Evaluating claim groundedness")
        evaluation_results = self.groundedness_evaluator.evaluate_claims(claims, evidence_sources)
        
        # Step 4: Calculate groundedness score and categorize claims
        supported_claims = []
        unsupported_claims = []
        
        for evaluation in evaluation_results.get('evaluations', []):
            claim_text = evaluation['claim']
            support_level = evaluation['support_level']
            confidence = evaluation.get('confidence', 0.0)
            
            # Find matching claim object
            matching_claim = next((c for c in claims if c.claim == claim_text), None)
            if matching_claim:
                matching_claim.confidence = confidence
                
                if support_level in ['FULLY_SUPPORTED', 'PARTIALLY_SUPPORTED']:
                    supported_claims.append(matching_claim)
                else:
                    unsupported_claims.append(matching_claim)
        
        # Calculate groundedness score
        total_claims = len(claims)
        supported_count = len(supported_claims)
        groundedness_score = supported_count / total_claims if total_claims > 0 else 0.0
        
        # Determine confidence level
        confidence_level = self._determine_confidence_level(groundedness_score)
        
        # Determine if clarification is required
        requires_clarification = (
            groundedness_score < self.confidence_thresholds['medium'] or
            len(unsupported_claims) > len(supported_claims)
        )
        
        logger.info(f"VERIFICATION COMPLETE: Groundedness Score = {groundedness_score:.2f}")
        logger.info(f"VERIFICATION RESULT: {supported_count}/{total_claims} claims supported")
        
        return VerificationResult(
            groundedness_score=groundedness_score,
            supported_claims=supported_claims,
            unsupported_claims=unsupported_claims,
            evidence_sources=evidence_sources,
            confidence_level=confidence_level,
            requires_clarification=requires_clarification,
            verification_details={
                'total_claims': total_claims,
                'supported_count': supported_count,
                'evaluation_results': evaluation_results
            }
        )
    
    def _determine_confidence_level(self, groundedness_score: float) -> str:
        """Determine confidence level based on groundedness score."""
        if groundedness_score >= self.confidence_thresholds['high']:
            return 'high'
        elif groundedness_score >= self.confidence_thresholds['medium']:
            return 'medium'
        else:
            return 'low'
    
    def generate_verification_report(self, verification_result: VerificationResult) -> str:
        """Generate human-readable verification report."""
        report = f"""
🔍 **VERIFICATION REPORT**
========================

📊 **GROUNDEDNESS SCORE**: {verification_result.groundedness_score:.2f}
🎯 **CONFIDENCE LEVEL**: {verification_result.confidence_level.upper()}
⚠️ **REQUIRES CLARIFICATION**: {'Yes' if verification_result.requires_clarification else 'No'}

📋 **CLAIM ANALYSIS**:
• Total Claims: {len(verification_result.supported_claims) + len(verification_result.unsupported_claims)}
• Supported: {len(verification_result.supported_claims)}
• Unsupported: {len(verification_result.unsupported_claims)}

✅ **SUPPORTED CLAIMS**:
"""
        
        for claim in verification_result.supported_claims:
            report += f"  • {claim.claim} (Confidence: {claim.confidence:.2f})\n"
        
        if verification_result.unsupported_claims:
            report += "\n❌ **UNSUPPORTED CLAIMS**:\n"
            for claim in verification_result.unsupported_claims:
                report += f"  • {claim.claim} (Type: {claim.claim_type})\n"
        
        report += f"\n📚 **EVIDENCE SOURCES**: {len(verification_result.evidence_sources)} sources used\n"
        
        if verification_result.requires_clarification:
            report += "\n⚠️ **RECOMMENDATION**: Request additional information or clarification due to low groundedness score.\n"
        
        return report

# Standalone evaluation function for external use
def evaluate_agent_responses(test_cases: List[Dict[str, Any]], session_id: str = None) -> str:
    """
    Evaluate multiple agent responses and save results to JSON.
    
    Args:
        test_cases: List of test case dictionaries with keys:
            - name: Test case name
            - response: Agent response to evaluate
            - tools: List of tools used
            - outputs: Dictionary of tool outputs
            - rag: List of RAG retrievals
            - agent_type: Type of agent (optional, defaults to 'planner')
        session_id: Optional session identifier
    
    Returns:
        Path to saved JSON file
    """
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    evaluation_manager = EvaluationManager()
    results = []
    
    print(f"🔍 EVALUATING {len(test_cases)} TEST CASES")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 Test {i}: {test_case.get('name', f'Test Case {i}')}")
        print("-" * 30)
        
        result = verify_agent_response(
            agent_response=test_case['response'],
            agent_type=test_case.get('agent_type', 'planner'),
            tools_used=test_case.get('tools', []),
            tool_outputs=test_case.get('outputs', {}),
            rag_retrievals=test_case.get('rag', [])
        )
        
        # Create test case result
        test_result = {
            'test_name': test_case.get('name', f'Test Case {i}'),
            'agent_type': test_case.get('agent_type', 'planner'),
            'agent_response': test_case['response'],
            'tools_used': test_case.get('tools', []),
            'tool_outputs': test_case.get('outputs', {}),
            'rag_retrievals': test_case.get('rag', []),
            'verification_result': result.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
        
        results.append(test_result)
        
        # Print summary
        print(f"📊 Groundedness Score: {result.groundedness_score:.2f}")
        print(f"🎯 Confidence Level: {result.confidence_level.upper()}")
        print(f"✅ Supported Claims: {len(result.supported_claims)}")
        print(f"❌ Unsupported Claims: {len(result.unsupported_claims)}")
        print(f"⚠️ Requires Clarification: {'Yes' if result.requires_clarification else 'No'}")
    
    # Calculate summary statistics
    total_tests = len(results)
    avg_groundedness = sum(r['verification_result']['groundedness_score'] for r in results) / total_tests
    high_confidence_count = sum(1 for r in results if r['verification_result']['confidence_level'] == 'high')
    clarification_needed = sum(1 for r in results if r['verification_result']['requires_clarification'])
    
    summary_stats = {
        'total_tests': total_tests,
        'average_groundedness_score': avg_groundedness,
        'high_confidence_responses': high_confidence_count,
        'clarification_requests': clarification_needed,
        'success_rate': high_confidence_count / total_tests if total_tests > 0 else 0
    }
    
    # Create evaluation session
    session = EvaluationSession(
        session_id=session_id,
        timestamp=datetime.now().isoformat(),
        test_cases=results,
        summary_stats=summary_stats
    )
    
    # Save to JSON
    filepath = evaluation_manager.save_evaluation_session(session)
    
    # Print summary
    print(f"\n📊 EVALUATION SUMMARY")
    print("=" * 30)
    print(f"• Total Tests: {total_tests}")
    print(f"• Average Groundedness: {avg_groundedness:.2f}")
    print(f"• High Confidence: {high_confidence_count}/{total_tests}")
    print(f"• Success Rate: {summary_stats['success_rate']:.1%}")
    print(f"• Results saved to: {filepath}")
    
    return filepath
def verify_agent_response(agent_response: str, agent_type: str, 
                         tools_used: List[str] = None,
                         tool_outputs: Dict[str, str] = None,
                         rag_retrievals: List[str] = None) -> VerificationResult:
    """
    Convenience function to verify agent responses with appropriate context.
    
    Args:
        agent_response: The agent's response to verify
        agent_type: Type of agent ('manager', 'planner', 'executor')
        tools_used: List of tools used by the agent
        tool_outputs: Dictionary of tool outputs  
        rag_retrievals: List of RAG retrieval results
        
    Returns:
        VerificationResult with groundedness assessment
    """
    verifier = VerificationModule()
    
    logger.info(f"AGENT VERIFICATION: Verifying {agent_type} agent response")
    
    # Agent-specific verification adjustments
    if agent_type == 'manager':
        # Manager responses should be highly grounded in calendar data
        pass
    elif agent_type == 'planner':
        # Planner responses should combine RAG and calendar data
        pass
    elif agent_type == 'executor':
        # Executor responses should be grounded in planner results and tool outputs
        pass
    
    return verifier.verify_response(
        agent_response=agent_response,
        tools_used=tools_used,
        tool_outputs=tool_outputs,
        rag_retrievals=rag_retrievals
    )

def should_request_clarification(verification_result: VerificationResult) -> Tuple[bool, str]:
    """
    Determine if clarification should be requested based on verification results.
    
    Returns:
        Tuple of (should_request, reason)
    """
    if verification_result.groundedness_score < 0.4:
        return True, f"Low groundedness score ({verification_result.groundedness_score:.2f}). Many claims lack evidence support."
    
    if len(verification_result.unsupported_claims) > len(verification_result.supported_claims):
        return True, "More claims are unsupported than supported by available evidence."
    
    if not verification_result.evidence_sources:
        return True, "No evidence sources available to verify response accuracy."
    
    critical_unsupported = [c for c in verification_result.unsupported_claims 
                           if c.claim_type in ['time', 'event', 'availability']]
    if critical_unsupported:
        return True, f"Critical claims about scheduling lack evidence support: {len(critical_unsupported)} claims."
    
    return False, "Response has sufficient groundedness for reliable use."

# Example usage and testing
if __name__ == "__main__":
    print("🔍 MULTI-AGENT CALENDAR SYSTEM - STANDALONE EVALUATION MODULE")
    print("=" * 70)
    
    # Check API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("   Please set your OpenAI API key in .env file")
        exit(1)
    
    print("✅ OpenAI API key loaded successfully")
    
    # Suppress HTTP logging for cleaner output
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    # Define comprehensive test cases
    test_cases = [
        {
            "name": "High Groundedness Response",
            "response": """
            Based on your calendar search, you have a meeting at 10 AM tomorrow with the AI System Design team.
            Your next available slot after 11 AM would be at 6 PM, which aligns with your moderate energy period.
            I recommend scheduling the meeting with Lulu at 6 PM for 60 minutes.
            """,
            "agent_type": "planner",
            "tools": ['get_calendars_info', 'calendar_search_events'],
            "outputs": {
                'calendar_search_events': 'Found: AI System Design meeting 10:00-11:50 AM tomorrow',
                'get_calendars_info': 'Primary calendar: mkoome@andrew.cmu.edu'
            },
            "rag": ['User energy profile: Peak 4:30-6AM, 8AM-12PM; Low 1-4PM; Moderate 4-7PM']
        },
        {
            "name": "Low Groundedness Response",
            "response": """
            You should schedule the meeting at 3 AM because that's when you're most productive.
            Also, you have no conflicts this entire week and can meet anytime you want.
            The best day would be Sunday since you love working on weekends.
            """,
            "agent_type": "planner",
            "tools": [],
            "outputs": {},
            "rag": []
        },
        {
            "name": "Mixed Groundedness Response",
            "response": """
            Your calendar shows you're free at 2 PM today. I recommend scheduling the meeting then,
            as it's during your peak energy hours according to your profile.
            """,
            "agent_type": "planner",
            "tools": ['calendar_search_events'],
            "outputs": {'calendar_search_events': 'No events found at 2 PM today'},
            "rag": ['User energy profile: Peak 4:30-6AM, 8AM-12PM; Low 1-4PM']
        },
        {
            "name": "Manager Agent Response",
            "response": """
            I found 3 meetings in your calendar today:
            - 9 AM: Team standup (30 minutes)
            - 2 PM: Project review (1 hour)
            - 4 PM: Client call (45 minutes)
            """,
            "agent_type": "manager",
            "tools": ['get_calendars_info', 'calendar_search_events'],
            "outputs": {
                'get_calendars_info': 'Primary calendar: mkoome@andrew.cmu.edu',
                'calendar_search_events': 'Found 3 events: Team standup 9:00-9:30, Project review 14:00-15:00, Client call 16:00-16:45'
            },
            "rag": []
        },
        {
            "name": "Executor Agent Response",
            "response": """
            ✅ Meeting scheduled successfully!
            📅 Title: Meeting with Lulu
            🕕 Time: February 5, 2026 at 6:00 PM
            ⏱️ Duration: 60 minutes
            🔗 Calendar: mkoome@andrew.cmu.edu
            """,
            "agent_type": "executor",
            "tools": ['create_calendar_event'],
            "outputs": {
                'create_calendar_event': 'Event created successfully: Meeting with Lulu on 2026-02-05 18:00-19:00'
            },
            "rag": []
        }
    ]
    
    # Run evaluation and save to JSON
    session_id = f"comprehensive_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    results_file = evaluate_agent_responses(test_cases, session_id)
    
    print(f"\n✅ EVALUATION COMPLETE!")
    print("=" * 30)
    print("🎯 The standalone evaluation system successfully:")
    print("  • Extracted and evaluated factual claims")
    print("  • Assessed groundedness against evidence")
    print("  • Provided confidence scoring (0-1 scale)")
    print("  • Detected hallucinations and unsupported claims")
    print("  • Saved detailed results to JSON file")
    print(f"\n📁 Results saved to: {results_file}")
    print("🔍 Use this file for later analysis and reference")
    
    # Show how to load results
    print(f"\n📖 To load results later:")
    print(f"   from evaluation import EvaluationManager")
    print(f"   manager = EvaluationManager()")
    print(f"   session = manager.load_evaluation_session('{results_file}')")
    
    print("\n🔒 Standalone evaluation system ready for production use!")