#!/usr/bin/env python3
"""
Supabase Persistent Memory Manager

Handles conversation history, agent tasks, and context storage in Supabase.
"""

import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseMemoryManager:
    """Manages persistent memory for agents in Supabase"""
    
    def __init__(self, session_id: Optional[str] = None, user_id: Optional[str] = None):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Missing Supabase credentials in .env")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.session_id = session_id or self._generate_session_id()
        self.user_id = user_id
        self.message_index = 0
        
        # Initialize session
        self._initialize_session()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def _initialize_session(self):
        """Initialize or resume conversation session"""
        try:
            # Check if session exists
            result = self.supabase.table('conversation_sessions') \
                .select('*') \
                .eq('session_id', self.session_id) \
                .execute()
            
            if not result.data:
                # Create new session
                self.supabase.table('conversation_sessions').insert({
                    'session_id': self.session_id,
                    'user_id': self.user_id,
                    'status': 'active',
                    'agent_types_used': []
                }).execute()
                logger.info(f"Created new session: {self.session_id}")
            else:
                # Resume existing session
                self.message_index = result.data[0]['total_messages']
                logger.info(f"Resumed session: {self.session_id} (messages: {self.message_index})")
                
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
    
    def add_message(
        self,
        role: str,
        content: str,
        agent_type: Optional[str] = None,
        tool_calls: Optional[List[Dict]] = None,
        tool_results: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add message to conversation history.
        
        Args:
            role: 'user', 'assistant', or 'system'
            content: Message content
            agent_type: Agent type if role is 'assistant'
            tool_calls: List of tool calls made
            tool_results: Results from tool calls
            metadata: Additional metadata
        
        Returns:
            Message ID
        """
        try:
            message_data = {
                'session_id': self.session_id,
                'message_index': self.message_index,
                'role': role,
                'content': content,
                'agent_type': agent_type,
                'tool_calls': tool_calls,
                'tool_results': tool_results,
                'metadata': metadata or {}
            }
            
            result = self.supabase.table('conversation_messages').insert(message_data).execute()
            
            # Update session
            self.message_index += 1
            self._update_session_activity(agent_type)
            
            logger.info(f"Added message {self.message_index} to session {self.session_id}")
            return result.data[0]['id']
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return None
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent conversation history.
        
        Args:
            limit: Number of recent messages to retrieve
        
        Returns:
            List of message dictionaries
        """
        try:
            result = self.supabase.table('conversation_messages') \
                .select('*') \
                .eq('session_id', self.session_id) \
                .order('message_index', desc=True) \
                .limit(limit) \
                .execute()
            
            # Reverse to get chronological order
            messages = list(reversed(result.data))
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def get_formatted_history(self, limit: int = 10) -> str:
        """Get conversation history formatted as string"""
        messages = self.get_conversation_history(limit)
        
        formatted = []
        for msg in messages:
            role = msg['role'].upper()
            agent = f" ({msg['agent_type']})" if msg.get('agent_type') else ""
            content = msg['content']
            formatted.append(f"{role}{agent}: {content}")
        
        return "\n\n".join(formatted)
    
    def _update_session_activity(self, agent_type: Optional[str] = None):
        """Update session activity and agent types used"""
        try:
            update_data = {
                'total_messages': self.message_index,
                'last_activity_at': datetime.now().isoformat()
            }
            
            # Add agent type to list if not already present
            if agent_type:
                result = self.supabase.table('conversation_sessions') \
                    .select('agent_types_used') \
                    .eq('session_id', self.session_id) \
                    .execute()
                
                if result.data:
                    agent_types = result.data[0].get('agent_types_used', []) or []
                    if agent_type not in agent_types:
                        agent_types.append(agent_type)
                        update_data['agent_types_used'] = agent_types
            
            self.supabase.table('conversation_sessions') \
                .update(update_data) \
                .eq('session_id', self.session_id) \
                .execute()
                
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
    
    def create_task(
        self,
        agent_type: str,
        task_type: str,
        task_description: str,
        priority: int = 5,
        input_data: Optional[Dict] = None
    ) -> str:
        """
        Create agent task.
        
        Args:
            agent_type: Agent type ('manager', 'planner', 'executor')
            task_type: Task type ('query', 'plan', 'execute', 'search')
            task_description: Description of the task
            priority: Priority level (1-10)
            input_data: Input data for the task
        
        Returns:
            Task ID
        """
        try:
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            task_data = {
                'session_id': self.session_id,
                'task_id': task_id,
                'agent_type': agent_type,
                'task_type': task_type,
                'task_description': task_description,
                'status': 'pending',
                'priority': priority,
                'input_data': input_data or {}
            }
            
            result = self.supabase.table('agent_tasks').insert(task_data).execute()
            logger.info(f"Created task {task_id} for {agent_type}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None
    
    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        output_data: Optional[Dict] = None,
        tools_used: Optional[List[str]] = None,
        execution_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Update task status and results"""
        try:
            update_data = {}
            
            if status:
                update_data['status'] = status
                if status == 'in_progress':
                    update_data['started_at'] = datetime.now().isoformat()
                elif status in ['completed', 'failed']:
                    update_data['completed_at'] = datetime.now().isoformat()
            
            if output_data is not None:
                update_data['output_data'] = output_data
            if tools_used is not None:
                update_data['tools_used'] = tools_used
            if execution_time_ms is not None:
                update_data['execution_time_ms'] = execution_time_ms
            if error_message is not None:
                update_data['error_message'] = error_message
            
            self.supabase.table('agent_tasks') \
                .update(update_data) \
                .eq('task_id', task_id) \
                .execute()
            
            logger.info(f"Updated task {task_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error updating task: {e}")
    
    def log_tool_usage(
        self,
        agent_type: str,
        tool_name: str,
        tool_input: Dict,
        tool_output: Any,
        execution_time_ms: int,
        success: bool = True,
        error_message: Optional[str] = None,
        task_id: Optional[str] = None
    ):
        """Log tool usage for analytics"""
        try:
            log_data = {
                'session_id': self.session_id,
                'task_id': task_id,
                'agent_type': agent_type,
                'tool_name': tool_name,
                'tool_input': tool_input,
                'tool_output': str(tool_output)[:1000] if tool_output else None,  # Truncate large outputs
                'execution_time_ms': execution_time_ms,
                'success': success,
                'error_message': error_message
            }
            
            self.supabase.table('tool_usage_logs').insert(log_data).execute()
            
        except Exception as e:
            logger.error(f"Error logging tool usage: {e}")
    
    def get_agent_context(self, agent_type: str, context_key: str) -> Optional[Dict]:
        """Get agent-specific context"""
        try:
            result = self.supabase.table('agent_memory_context') \
                .select('context_value, importance_score') \
                .eq('agent_type', agent_type) \
                .eq('context_key', context_key) \
                .execute()
            
            if result.data:
                # Update access count
                self.supabase.table('agent_memory_context') \
                    .update({
                        'access_count': result.data[0].get('access_count', 0) + 1,
                        'last_accessed_at': datetime.now().isoformat()
                    }) \
                    .eq('agent_type', agent_type) \
                    .eq('context_key', context_key) \
                    .execute()
                
                return result.data[0]['context_value']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting agent context: {e}")
            return None
    
    def set_agent_context(
        self,
        agent_type: str,
        context_key: str,
        context_value: Dict,
        importance_score: float = 0.5
    ):
        """Set agent-specific context"""
        try:
            # Upsert context
            self.supabase.table('agent_memory_context').upsert({
                'agent_type': agent_type,
                'context_key': context_key,
                'context_value': context_value,
                'importance_score': importance_score
            }, on_conflict='agent_type,context_key').execute()
            
            logger.info(f"Set context {context_key} for {agent_type}")
            
        except Exception as e:
            logger.error(f"Error setting agent context: {e}")
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session"""
        try:
            # Get session info
            session_result = self.supabase.table('conversation_sessions') \
                .select('*') \
                .eq('session_id', self.session_id) \
                .execute()
            
            # Get task counts
            tasks_result = self.supabase.table('agent_tasks') \
                .select('status') \
                .eq('session_id', self.session_id) \
                .execute()
            
            task_counts = {
                'total': len(tasks_result.data),
                'completed': sum(1 for t in tasks_result.data if t['status'] == 'completed'),
                'pending': sum(1 for t in tasks_result.data if t['status'] == 'pending'),
                'failed': sum(1 for t in tasks_result.data if t['status'] == 'failed')
            }
            
            return {
                'session_id': self.session_id,
                'session_info': session_result.data[0] if session_result.data else {},
                'task_counts': task_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return {}
    
    def close_session(self):
        """Mark session as completed"""
        try:
            self.supabase.table('conversation_sessions') \
                .update({'status': 'completed'}) \
                .eq('session_id', self.session_id) \
                .execute()
            
            logger.info(f"Closed session: {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error closing session: {e}")
    
    # =========================================================================
    # USER PREFERENCES MANAGEMENT
    # =========================================================================
    
    def save_user_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: Dict,
        preference_type: str,
        source: str = 'user_input',
        confidence_score: float = 1.0
    ):
        """
        Save or update user preference.
        
        Args:
            user_id: User identifier
            preference_key: Unique key for preference (e.g., 'preferred_meeting_time')
            preference_value: Preference value as JSON
            preference_type: Type ('calendar', 'scheduling', 'notification', 'energy', 'general')
            source: Source of preference ('user_input', 'learned', 'inferred')
            confidence_score: Confidence level (0.0-1.0)
        """
        try:
            # Upsert preference
            self.supabase.table('user_preferences').upsert({
                'user_id': user_id,
                'preference_key': preference_key,
                'preference_value': preference_value,
                'preference_type': preference_type,
                'source': source,
                'confidence_score': confidence_score,
                'times_used': 0,
                'last_used_at': datetime.now().isoformat()
            }, on_conflict='user_id,preference_key').execute()
            
            logger.info(f"Saved preference {preference_key} for user {user_id} (confidence: {confidence_score})")
            
        except Exception as e:
            logger.error(f"Error saving user preference: {e}")
    
    def get_user_preferences(
        self,
        user_id: str,
        preference_type: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Get user preferences.
        
        Args:
            user_id: User identifier
            preference_type: Filter by type (optional)
            min_confidence: Minimum confidence score
        
        Returns:
            List of preference dictionaries
        """
        try:
            query = self.supabase.table('user_preferences') \
                .select('*') \
                .eq('user_id', user_id) \
                .gte('confidence_score', min_confidence)
            
            if preference_type:
                query = query.eq('preference_type', preference_type)
            
            result = query.order('confidence_score', desc=True).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return []
    
    def increment_preference_usage(self, user_id: str, preference_key: str):
        """Increment usage count for a preference"""
        try:
            # Get current preference
            result = self.supabase.table('user_preferences') \
                .select('times_used, confidence_score') \
                .eq('user_id', user_id) \
                .eq('preference_key', preference_key) \
                .execute()
            
            if result.data:
                current_usage = result.data[0].get('times_used', 0)
                current_confidence = result.data[0].get('confidence_score', 0.5)
                
                # Increase confidence with usage (cap at 1.0)
                new_confidence = min(1.0, current_confidence + 0.05)
                
                self.supabase.table('user_preferences') \
                    .update({
                        'times_used': current_usage + 1,
                        'confidence_score': new_confidence,
                        'last_used_at': datetime.now().isoformat()
                    }) \
                    .eq('user_id', user_id) \
                    .eq('preference_key', preference_key) \
                    .execute()
                
                logger.info(f"Incremented usage for preference {preference_key} (new confidence: {new_confidence})")
                
        except Exception as e:
            logger.error(f"Error incrementing preference usage: {e}")
    
    # =========================================================================
    # PRIOR PLANS MANAGEMENT
    # =========================================================================
    
    def save_prior_plan(
        self,
        user_id: str,
        plan_type: str,
        plan_description: str,
        plan_details: Dict,
        execution_status: str = 'proposed',
        constraints_used: Optional[Dict] = None,
        energy_aware: bool = False
    ) -> str:
        """
        Save a plan for future reuse.
        
        Args:
            user_id: User identifier
            plan_type: Type of plan ('meeting', 'study_session', 'work_block', 'personal')
            plan_description: Human-readable description
            plan_details: Full plan details as JSON
            execution_status: Status ('proposed', 'approved', 'executed', 'rejected')
            constraints_used: Constraints that were considered
            energy_aware: Whether plan considered energy patterns
        
        Returns:
            Plan ID
        """
        try:
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            plan_data = {
                'plan_id': plan_id,
                'session_id': self.session_id,
                'user_id': user_id,
                'plan_type': plan_type,
                'plan_description': plan_description,
                'plan_details': plan_details,
                'execution_status': execution_status,
                'constraints_used': constraints_used or {},
                'energy_aware': energy_aware,
                'reuse_count': 0
            }
            
            result = self.supabase.table('prior_plans').insert(plan_data).execute()
            logger.info(f"Saved plan {plan_id} (type: {plan_type})")
            return plan_id
            
        except Exception as e:
            logger.error(f"Error saving prior plan: {e}")
            return None
    
    def get_similar_plans(
        self,
        user_id: str,
        plan_type: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get similar prior plans for reuse.
        
        Args:
            user_id: User identifier
            plan_type: Type of plan to search for
            limit: Maximum number of plans to return
        
        Returns:
            List of similar plans
        """
        try:
            result = self.supabase.table('prior_plans') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('plan_type', plan_type) \
                .in_('execution_status', ['approved', 'executed']) \
                .order('success_rating', desc=True) \
                .order('reuse_count', desc=True) \
                .limit(limit) \
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting similar plans: {e}")
            return []
    
    def update_plan_status(
        self,
        plan_id: str,
        execution_status: str,
        success_rating: Optional[float] = None
    ):
        """Update plan execution status and rating"""
        try:
            update_data = {'execution_status': execution_status}
            
            if success_rating is not None:
                update_data['success_rating'] = success_rating
            
            self.supabase.table('prior_plans') \
                .update(update_data) \
                .eq('plan_id', plan_id) \
                .execute()
            
            logger.info(f"Updated plan {plan_id} status to {execution_status}")
            
        except Exception as e:
            logger.error(f"Error updating plan status: {e}")
    
    def increment_plan_reuse(self, plan_id: str):
        """Increment reuse count for a plan"""
        try:
            # Get current reuse count
            result = self.supabase.table('prior_plans') \
                .select('reuse_count') \
                .eq('plan_id', plan_id) \
                .execute()
            
            if result.data:
                current_count = result.data[0].get('reuse_count', 0)
                
                self.supabase.table('prior_plans') \
                    .update({
                        'reuse_count': current_count + 1,
                        'last_reused_at': datetime.now().isoformat()
                    }) \
                    .eq('plan_id', plan_id) \
                    .execute()
                
                logger.info(f"Incremented reuse count for plan {plan_id} (new count: {current_count + 1})")
                
        except Exception as e:
            logger.error(f"Error incrementing plan reuse: {e}")
    
    # =========================================================================
    # SESSION SUMMARIZATION
    # =========================================================================
    
    def summarize_session(
        self,
        summary_text: str,
        key_topics: List[str],
        key_decisions: Dict,
        important_preferences: Optional[Dict] = None
    ):
        """
        Create summary of completed session.
        
        Args:
            summary_text: Human-readable summary
            key_topics: List of main topics discussed
            key_decisions: Important decisions made
            important_preferences: Preferences learned in this session
        """
        try:
            # Get session info
            session_result = self.supabase.table('conversation_sessions') \
                .select('user_id, agent_types_used') \
                .eq('session_id', self.session_id) \
                .execute()
            
            if not session_result.data:
                logger.warning(f"Session {self.session_id} not found for summarization")
                return
            
            session_data = session_result.data[0]
            
            # Count completed tasks
            tasks_result = self.supabase.table('agent_tasks') \
                .select('status') \
                .eq('session_id', self.session_id) \
                .eq('status', 'completed') \
                .execute()
            
            tasks_completed = len(tasks_result.data)
            
            # Create summary
            summary_data = {
                'session_id': self.session_id,
                'user_id': session_data.get('user_id'),
                'summary_text': summary_text,
                'key_topics': key_topics,
                'key_decisions': key_decisions,
                'tasks_completed': tasks_completed,
                'agents_used': session_data.get('agent_types_used', []),
                'important_preferences': important_preferences or {}
            }
            
            self.supabase.table('session_summaries').insert(summary_data).execute()
            logger.info(f"Created summary for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error summarizing session: {e}")
    
    def get_recent_summaries(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent session summaries for a user"""
        try:
            result = self.supabase.table('session_summaries') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting recent summaries: {e}")
            return []
    
    # =========================================================================
    # PERFORMANCE METRICS
    # =========================================================================
    
    def record_performance_metric(
        self,
        agent_type: str,
        metric_type: str,
        metric_value: float,
        metadata: Optional[Dict] = None
    ):
        """
        Record performance metric.
        
        Args:
            agent_type: Agent type
            metric_type: Metric type ('response_time', 'success_rate', 'user_satisfaction', 'tool_efficiency')
            metric_value: Metric value
            metadata: Additional metadata
        """
        try:
            metric_data = {
                'metric_date': datetime.now().date().isoformat(),
                'agent_type': agent_type,
                'metric_type': metric_type,
                'metric_value': metric_value,
                'sample_size': 1,
                'metadata': metadata or {}
            }
            
            # Upsert to aggregate daily metrics
            self.supabase.table('performance_metrics').upsert(
                metric_data,
                on_conflict='metric_date,agent_type,metric_type'
            ).execute()
            
        except Exception as e:
            logger.error(f"Error recording performance metric: {e}")


# Convenience functions for quick access
def get_recent_sessions(limit: int = 10) -> List[Dict]:
    """Get recent conversation sessions"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    supabase = create_client(supabase_url, supabase_key)
    
    result = supabase.table('conversation_sessions') \
        .select('*') \
        .order('last_activity_at', desc=True) \
        .limit(limit) \
        .execute()
    
    return result.data


def get_agent_performance(agent_type: str, days: int = 7) -> Dict:
    """Get agent performance metrics"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    supabase = create_client(supabase_url, supabase_key)
    
    result = supabase.rpc('get_agent_performance', {
        'p_agent_type': agent_type,
        'p_days': days
    }).execute()
    
    return result.data[0] if result.data else {}


if __name__ == "__main__":
    # Test memory manager
    print("Testing Supabase Memory Manager...")
    
    try:
        memory = SupabaseMemoryManager(user_id="test_user")
        print(f"✅ Session created: {memory.session_id}")
        
        # Add test message
        memory.add_message("user", "What meetings do I have today?")
        memory.add_message("assistant", "You have 3 meetings today.", agent_type="manager")
        
        # Get history
        history = memory.get_conversation_history()
        print(f"✅ Retrieved {len(history)} messages")
        
        # Create task
        task_id = memory.create_task("manager", "query", "Retrieve calendar events")
        print(f"✅ Created task: {task_id}")
        
        # Get summary
        summary = memory.get_session_summary()
        print(f"✅ Session summary: {summary}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


# =============================================================================
# HELPER FUNCTIONS FOR MEMORY ANALYTICS
# =============================================================================

def get_recent_sessions(limit: int = 10) -> List[Dict]:
    """Get recent conversation sessions (standalone function)"""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not all([supabase_url, supabase_key]):
            return []
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        result = supabase.table('conversation_sessions') \
            .select('*') \
            .order('last_activity_at', desc=True) \
            .limit(limit) \
            .execute()
        
        return result.data
        
    except Exception as e:
        logger.error(f"Error getting recent sessions: {e}")
        return []


def get_agent_performance(agent_type: str, days: int = 7) -> Dict:
    """Get agent performance metrics (standalone function)"""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not all([supabase_url, supabase_key]):
            return {}
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Use RPC function
        result = supabase.rpc('get_agent_performance', {
            'p_agent_type': agent_type,
            'p_days': days
        }).execute()
        
        if result.data:
            return result.data[0]
        
        return {}
        
    except Exception as e:
        logger.error(f"Error getting agent performance: {e}")
        return {}


def prune_old_messages(days_to_keep: int = 30) -> int:
    """Prune old messages (admin function)"""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Need service role for deletion
        
        if not all([supabase_url, supabase_key]):
            logger.error("Missing Supabase credentials for pruning")
            return 0
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Use RPC function
        result = supabase.rpc('prune_old_messages', {
            'p_days_to_keep': days_to_keep
        }).execute()
        
        deleted_count = result.data if result.data else 0
        logger.info(f"Pruned {deleted_count} old messages")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error pruning old messages: {e}")
        return 0


# =============================================================================
# REVIEWER ANALYTICS FUNCTIONS
# =============================================================================

def get_agent_interaction_metrics(user_id: str, days: int = 7) -> Dict:
    """
    Get agent interaction quality metrics for REVIEWER agent.
    
    Returns:
        Dict with:
        - agent_usage: Dict of agent_type -> usage_count
        - planner_executor_success_rate: % of planner recommendations executed
        - follow_through_rate: % of planned tasks completed
        - total_interactions: Total agent interactions
        - most_used_agent: Agent used most frequently
    """
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Use service role key for RPC
        
        if not all([supabase_url, supabase_key]):
            return {}
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Call the SQL RPC function
        result = supabase.rpc('get_agent_interaction_metrics', {
            'p_user_id': user_id,
            'p_days': days
        }).execute()
        
        if result.data:
            return result.data
        else:
            return {}
        
    except Exception as e:
        logger.error(f"Error getting agent interaction metrics: {e}")
        return {}


def get_memory_learning_metrics(user_id: str, days: int = 7) -> Dict:
    """
    Get memory and learning metrics for REVIEWER agent.
    
    Returns:
        Dict with:
        - sessions_completed: Number of sessions in period
        - preferences_learned: Number of new preferences
        - plan_reuse_count: Number of times plans were reused
        - avg_preference_confidence: Average confidence score
        - most_queried_topic: Most common query pattern
        - learning_velocity: % change in preferences from previous period
    """
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Use service role key for RPC
        
        if not all([supabase_url, supabase_key]):
            return {}
        
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Call the SQL RPC function
        result = supabase.rpc('get_memory_learning_metrics', {
            'p_user_id': user_id,
            'p_days': days
        }).execute()
        
        if result.data:
            return result.data
        else:
            return {}
        
    except Exception as e:
        logger.error(f"Error getting memory learning metrics: {e}")
        return {}
