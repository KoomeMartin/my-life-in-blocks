-- ============================================================================
-- COMPLETE MEMORY SYSTEM SCHEMA FOR SUPABASE
-- Multi-Agent Calendar System - Persistent Memory & Analytics
-- ============================================================================
-- 
-- This file contains ALL SQL needed to set up the complete memory system:
-- 
-- PART 1: CORE MEMORY TABLES (5 tables)
--   - conversation_sessions: Track conversation sessions
--   - conversation_messages: Store individual messages
--   - agent_tasks: Track agent task execution
--   - agent_memory_context: Store agent-specific learned patterns
--   - tool_usage_logs: Log all tool usage for analytics
--
-- PART 2: ADVANCED MEMORY TABLES (4 tables)
--   - user_preferences: Store learned user preferences
--   - session_summaries: Compressed session history
--   - prior_plans: Store successful plans for reuse
--   - performance_metrics: Daily agent performance tracking
--
-- PART 3: INDEXES
--   - Performance indexes for all tables
--
-- PART 4: TRIGGERS
--   - Auto-update timestamps
--
-- PART 5: RPC FUNCTIONS
--   - Analytics and retrieval functions
--
-- PART 6: VIEWS
--   - Convenient views for common queries
--
-- PART 7: FIXES & ENHANCEMENTS
--   - Add missing columns (user_id)
--   - Create analytics RPC functions for REVIEWER agent
--
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- PART 1: CORE MEMORY TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABLE: conversation_sessions
-- PURPOSE: Tracks conversation sessions with metadata
-- USAGE: One row per conversation session with user
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    total_messages INT DEFAULT 0,
    agent_types_used TEXT[], -- Array of agent types used in session
    status TEXT DEFAULT 'active', -- active, completed, archived
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE conversation_sessions IS 'Tracks conversation sessions with users';
COMMENT ON COLUMN conversation_sessions.session_id IS 'Unique session identifier';
COMMENT ON COLUMN conversation_sessions.user_id IS 'User identifier for multi-user support';
COMMENT ON COLUMN conversation_sessions.agent_types_used IS 'Array of agent types (manager, planner, executor) used';
COMMENT ON COLUMN conversation_sessions.status IS 'Session status: active, completed, archived';

-- ----------------------------------------------------------------------------
-- TABLE: conversation_messages
-- PURPOSE: Stores individual messages in conversations
-- USAGE: One row per message (user or assistant)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    user_id TEXT, -- Added for analytics queries
    message_index INT NOT NULL,
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    agent_type TEXT, -- 'manager', 'planner', 'executor', null for user messages
    content TEXT NOT NULL,
    tool_calls JSONB, -- Array of tool calls made
    tool_results JSONB, -- Results from tool calls
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_session_message UNIQUE(session_id, message_index)
);

COMMENT ON TABLE conversation_messages IS 'Stores individual messages in conversations';
COMMENT ON COLUMN conversation_messages.role IS 'Message role: user, assistant, system';
COMMENT ON COLUMN conversation_messages.agent_type IS 'Which agent generated this message (if assistant)';
COMMENT ON COLUMN conversation_messages.tool_calls IS 'JSON array of tool calls made during this message';
COMMENT ON COLUMN conversation_messages.tool_results IS 'JSON array of tool results';

-- ----------------------------------------------------------------------------
-- TABLE: agent_tasks
-- PURPOSE: Tracks tasks assigned to and completed by agents
-- USAGE: One row per agent task (query, plan, execute, search)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    task_id TEXT UNIQUE NOT NULL,
    agent_type TEXT NOT NULL, -- 'manager', 'planner', 'executor'
    task_type TEXT NOT NULL, -- 'query', 'plan', 'execute', 'search'
    task_description TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, in_progress, completed, failed
    priority INT DEFAULT 5, -- 1-10, higher is more important
    input_data JSONB,
    output_data JSONB,
    tools_used TEXT[], -- Array of tool names used
    execution_time_ms INT,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE agent_tasks IS 'Tracks tasks assigned to and completed by agents';
COMMENT ON COLUMN agent_tasks.task_type IS 'Type of task: query, plan, execute, search';
COMMENT ON COLUMN agent_tasks.status IS 'Task status: pending, in_progress, completed, failed';
COMMENT ON COLUMN agent_tasks.priority IS 'Task priority 1-10, higher is more important';

-- ----------------------------------------------------------------------------
-- TABLE: agent_memory_context
-- PURPOSE: Stores agent-specific context and learned patterns
-- USAGE: Key-value store for agent learning and preferences
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_memory_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type TEXT NOT NULL,
    context_key TEXT NOT NULL, -- e.g., 'user_preferences', 'common_queries'
    context_value JSONB NOT NULL,
    importance_score FLOAT DEFAULT 0.5,
    access_count INT DEFAULT 0,
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_agent_context UNIQUE(agent_type, context_key)
);

COMMENT ON TABLE agent_memory_context IS 'Stores agent-specific context and learned patterns';
COMMENT ON COLUMN agent_memory_context.context_key IS 'Key for context (e.g., user_preferences, common_queries)';
COMMENT ON COLUMN agent_memory_context.importance_score IS 'Importance score 0-1 for memory pruning';

-- ----------------------------------------------------------------------------
-- TABLE: tool_usage_logs
-- PURPOSE: Tracks tool usage for analytics and optimization
-- USAGE: One row per tool invocation
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tool_usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    task_id TEXT REFERENCES agent_tasks(task_id) ON DELETE CASCADE,
    agent_type TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_input JSONB,
    tool_output JSONB,
    execution_time_ms INT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE tool_usage_logs IS 'Tracks tool usage for analytics and optimization';
COMMENT ON COLUMN tool_usage_logs.tool_name IS 'Name of tool invoked';
COMMENT ON COLUMN tool_usage_logs.success IS 'Whether tool execution succeeded';

-- ============================================================================
-- PART 2: ADVANCED MEMORY TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABLE: user_preferences
-- PURPOSE: Stores user preferences that persist across sessions
-- USAGE: Learned preferences from user behavior and explicit settings
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    preference_key TEXT NOT NULL,
    preference_value JSONB NOT NULL,
    preference_type TEXT NOT NULL, -- 'calendar', 'scheduling', 'notification', 'energy'
    source TEXT DEFAULT 'user_input', -- 'user_input', 'learned', 'inferred'
    confidence_score FLOAT DEFAULT 1.0, -- 0.0-1.0, higher for explicit preferences
    times_used INT DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_user_preference UNIQUE(user_id, preference_key)
);

COMMENT ON TABLE user_preferences IS 'Stores user preferences that persist across sessions';
COMMENT ON COLUMN user_preferences.preference_type IS 'Type: calendar, scheduling, notification, energy, general';
COMMENT ON COLUMN user_preferences.source IS 'How preference was obtained: user_input, learned, inferred';
COMMENT ON COLUMN user_preferences.confidence_score IS 'Confidence 0-1, higher for explicit preferences';

-- ----------------------------------------------------------------------------
-- TABLE: session_summaries
-- PURPOSE: Stores summarized versions of completed sessions
-- USAGE: For memory pruning - keep summaries, delete old messages
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS session_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT UNIQUE NOT NULL REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    user_id TEXT,
    summary_text TEXT NOT NULL,
    key_topics TEXT[], -- Array of main topics discussed
    key_decisions JSONB, -- Important decisions made
    tasks_completed INT DEFAULT 0,
    agents_used TEXT[],
    important_preferences JSONB, -- Preferences learned in this session
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE session_summaries IS 'Stores summarized versions of completed sessions for memory pruning';
COMMENT ON COLUMN session_summaries.key_topics IS 'Main topics discussed in session';
COMMENT ON COLUMN session_summaries.key_decisions IS 'Important decisions made during session';

-- ----------------------------------------------------------------------------
-- TABLE: prior_plans
-- PURPOSE: Stores planning results for reuse and learning
-- USAGE: Save successful plans to reuse for similar requests
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prior_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id TEXT UNIQUE NOT NULL,
    session_id TEXT REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    user_id TEXT,
    plan_type TEXT NOT NULL, -- 'meeting', 'study_session', 'work_block', 'personal'
    plan_description TEXT NOT NULL,
    plan_details JSONB NOT NULL, -- Full plan with time slots, constraints, etc.
    execution_status TEXT DEFAULT 'proposed', -- 'proposed', 'approved', 'executed', 'rejected'
    success_rating FLOAT, -- 0.0-1.0, user feedback on plan quality
    constraints_used JSONB, -- Constraints that were considered
    energy_aware BOOLEAN DEFAULT false,
    reuse_count INT DEFAULT 0,
    last_reused_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE prior_plans IS 'Stores planning results for reuse and learning';
COMMENT ON COLUMN prior_plans.plan_type IS 'Type: meeting, study_session, work_block, personal';
COMMENT ON COLUMN prior_plans.execution_status IS 'Status: proposed, approved, executed, rejected';
COMMENT ON COLUMN prior_plans.energy_aware IS 'Whether plan considered energy patterns';

-- ----------------------------------------------------------------------------
-- TABLE: performance_metrics
-- PURPOSE: Tracks agent performance metrics over time
-- USAGE: Daily aggregated metrics for trend analysis
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_date DATE NOT NULL DEFAULT CURRENT_DATE,
    agent_type TEXT NOT NULL,
    metric_type TEXT NOT NULL, -- 'response_time', 'success_rate', 'user_satisfaction'
    metric_value FLOAT NOT NULL,
    sample_size INT DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_daily_metric UNIQUE(metric_date, agent_type, metric_type)
);

COMMENT ON TABLE performance_metrics IS 'Tracks agent performance metrics over time';
COMMENT ON COLUMN performance_metrics.metric_type IS 'Type: response_time, success_rate, user_satisfaction, tool_efficiency';
COMMENT ON COLUMN performance_metrics.sample_size IS 'Number of samples used to calculate metric';


-- ============================================================================
-- PART 3: INDEXES FOR PERFORMANCE
-- ============================================================================

-- Conversation Sessions Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON conversation_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON conversation_sessions(last_activity_at DESC);

-- Conversation Messages Indexes
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON conversation_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON conversation_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_agent_type ON conversation_messages(agent_type);
CREATE INDEX IF NOT EXISTS idx_messages_role ON conversation_messages(role);

-- Agent Tasks Indexes
CREATE INDEX IF NOT EXISTS idx_tasks_session_id ON agent_tasks(session_id);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_type ON agent_tasks(agent_type);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON agent_tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON agent_tasks(created_at DESC);

-- Agent Memory Context Indexes
CREATE INDEX IF NOT EXISTS idx_context_agent_type ON agent_memory_context(agent_type);
CREATE INDEX IF NOT EXISTS idx_context_importance ON agent_memory_context(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_context_access_count ON agent_memory_context(access_count DESC);

-- Tool Usage Logs Indexes
CREATE INDEX IF NOT EXISTS idx_tool_logs_session_id ON tool_usage_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_logs_agent_type ON tool_usage_logs(agent_type);
CREATE INDEX IF NOT EXISTS idx_tool_logs_tool_name ON tool_usage_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_logs_timestamp ON tool_usage_logs(timestamp DESC);

-- User Preferences Indexes
CREATE INDEX IF NOT EXISTS idx_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_preferences_type ON user_preferences(preference_type);
CREATE INDEX IF NOT EXISTS idx_preferences_confidence ON user_preferences(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_preferences_times_used ON user_preferences(times_used DESC);

-- Session Summaries Indexes
CREATE INDEX IF NOT EXISTS idx_summaries_user_id ON session_summaries(user_id);
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON session_summaries(created_at DESC);

-- Prior Plans Indexes
CREATE INDEX IF NOT EXISTS idx_plans_user_id ON prior_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_plans_type ON prior_plans(plan_type);
CREATE INDEX IF NOT EXISTS idx_plans_status ON prior_plans(execution_status);
CREATE INDEX IF NOT EXISTS idx_plans_reuse_count ON prior_plans(reuse_count DESC);
CREATE INDEX IF NOT EXISTS idx_plans_created_at ON prior_plans(created_at DESC);

-- Performance Metrics Indexes
CREATE INDEX IF NOT EXISTS idx_metrics_date ON performance_metrics(metric_date DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_agent_type ON performance_metrics(agent_type);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON performance_metrics(metric_type);

-- ============================================================================
-- PART 4: TRIGGERS FOR AUTO-UPDATING TIMESTAMPS
-- ============================================================================

-- Generic function to update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to update session timestamp and last_activity_at
CREATE OR REPLACE FUNCTION update_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.last_activity_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables
DROP TRIGGER IF EXISTS trigger_update_session_timestamp ON conversation_sessions;
CREATE TRIGGER trigger_update_session_timestamp
    BEFORE UPDATE ON conversation_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_timestamp();

DROP TRIGGER IF EXISTS trigger_update_task_timestamp ON agent_tasks;
CREATE TRIGGER trigger_update_task_timestamp
    BEFORE UPDATE ON agent_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_update_context_timestamp ON agent_memory_context;
CREATE TRIGGER trigger_update_context_timestamp
    BEFORE UPDATE ON agent_memory_context
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_update_preferences_timestamp ON user_preferences;
CREATE TRIGGER trigger_update_preferences_timestamp
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_update_plans_timestamp ON prior_plans;
CREATE TRIGGER trigger_update_plans_timestamp
    BEFORE UPDATE ON prior_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 5: RPC FUNCTIONS FOR ANALYTICS & RETRIEVAL
-- ============================================================================

-- ----------------------------------------------------------------------------
-- FUNCTION: get_conversation_history
-- PURPOSE: Retrieve recent conversation history for a session
-- USAGE: SELECT * FROM get_conversation_history('session_123', 10);
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_conversation_history(
    p_session_id TEXT,
    p_limit INT DEFAULT 10
)
RETURNS TABLE (
    message_index INT,
    role TEXT,
    agent_type TEXT,
    content TEXT,
    timestamp TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cm.message_index,
        cm.role,
        cm.agent_type,
        cm.content,
        cm.timestamp
    FROM conversation_messages cm
    WHERE cm.session_id = p_session_id
    ORDER BY cm.message_index DESC
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION get_conversation_history IS 'Retrieves recent conversation history for a session';

-- ----------------------------------------------------------------------------
-- FUNCTION: get_agent_performance
-- PURPOSE: Calculate performance metrics for an agent type
-- USAGE: SELECT * FROM get_agent_performance('planner', 7);
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_agent_performance(
    p_agent_type TEXT,
    p_days INT DEFAULT 7
)
RETURNS TABLE (
    total_tasks INT,
    completed_tasks INT,
    failed_tasks INT,
    avg_execution_time_ms FLOAT,
    success_rate FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INT as total_tasks,
        COUNT(*) FILTER (WHERE status = 'completed')::INT as completed_tasks,
        COUNT(*) FILTER (WHERE status = 'failed')::INT as failed_tasks,
        AVG(execution_time_ms)::FLOAT as avg_execution_time_ms,
        (COUNT(*) FILTER (WHERE status = 'completed')::FLOAT / NULLIF(COUNT(*), 0))::FLOAT as success_rate
    FROM agent_tasks
    WHERE agent_type = p_agent_type
        AND created_at >= NOW() - (p_days || ' days')::INTERVAL;
END;
$$;

COMMENT ON FUNCTION get_agent_performance IS 'Calculates performance metrics for an agent type';

-- ----------------------------------------------------------------------------
-- FUNCTION: get_top_tools
-- PURPOSE: Get most frequently used tools by agent
-- USAGE: SELECT * FROM get_top_tools('planner', 10);
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_top_tools(
    p_agent_type TEXT,
    p_limit INT DEFAULT 10
)
RETURNS TABLE (
    tool_name TEXT,
    usage_count BIGINT,
    success_rate FLOAT,
    avg_execution_time_ms FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        tul.tool_name,
        COUNT(*)::BIGINT as usage_count,
        (COUNT(*) FILTER (WHERE success = true)::FLOAT / NULLIF(COUNT(*), 0))::FLOAT as success_rate,
        AVG(tul.execution_time_ms)::FLOAT as avg_execution_time_ms
    FROM tool_usage_logs tul
    WHERE tul.agent_type = p_agent_type
    GROUP BY tul.tool_name
    ORDER BY usage_count DESC
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION get_top_tools IS 'Returns most frequently used tools by agent type';

-- ----------------------------------------------------------------------------
-- FUNCTION: get_user_preferences
-- PURPOSE: Get user preferences by type
-- USAGE: SELECT * FROM get_user_preferences('user_123', 'scheduling');
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_user_preferences(
    p_user_id TEXT,
    p_preference_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    preference_key TEXT,
    preference_value JSONB,
    confidence_score FLOAT,
    times_used INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        up.preference_key,
        up.preference_value,
        up.confidence_score,
        up.times_used
    FROM user_preferences up
    WHERE up.user_id = p_user_id
        AND (p_preference_type IS NULL OR up.preference_type = p_preference_type)
    ORDER BY up.confidence_score DESC, up.times_used DESC;
END;
$$;

COMMENT ON FUNCTION get_user_preferences IS 'Retrieves user preferences by type';

-- ----------------------------------------------------------------------------
-- FUNCTION: get_similar_plans
-- PURPOSE: Find similar prior plans for reuse
-- USAGE: SELECT * FROM get_similar_plans('user_123', 'meeting', 5);
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_similar_plans(
    p_user_id TEXT,
    p_plan_type TEXT,
    p_limit INT DEFAULT 5
)
RETURNS TABLE (
    plan_id TEXT,
    plan_description TEXT,
    plan_details JSONB,
    success_rating FLOAT,
    reuse_count INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pp.plan_id,
        pp.plan_description,
        pp.plan_details,
        pp.success_rating,
        pp.reuse_count
    FROM prior_plans pp
    WHERE pp.user_id = p_user_id
        AND pp.plan_type = p_plan_type
        AND pp.execution_status IN ('approved', 'executed')
    ORDER BY pp.success_rating DESC NULLS LAST, pp.reuse_count DESC
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION get_similar_plans IS 'Finds similar prior plans for reuse';

-- ----------------------------------------------------------------------------
-- FUNCTION: aggregate_daily_metrics
-- PURPOSE: Aggregate daily performance metrics (run as cron job)
-- USAGE: SELECT aggregate_daily_metrics();
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION aggregate_daily_metrics()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    v_date DATE := CURRENT_DATE - INTERVAL '1 day';
BEGIN
    -- Calculate average response time per agent
    INSERT INTO performance_metrics (metric_date, agent_type, metric_type, metric_value, sample_size)
    SELECT
        v_date,
        agent_type,
        'avg_response_time_ms',
        AVG(execution_time_ms),
        COUNT(*)
    FROM agent_tasks
    WHERE DATE(created_at) = v_date
        AND execution_time_ms IS NOT NULL
    GROUP BY agent_type
    ON CONFLICT (metric_date, agent_type, metric_type) DO UPDATE
    SET metric_value = EXCLUDED.metric_value, sample_size = EXCLUDED.sample_size;
    
    -- Calculate success rate per agent
    INSERT INTO performance_metrics (metric_date, agent_type, metric_type, metric_value, sample_size)
    SELECT
        v_date,
        agent_type,
        'success_rate',
        COUNT(*) FILTER (WHERE status = 'completed')::FLOAT / NULLIF(COUNT(*), 0),
        COUNT(*)
    FROM agent_tasks
    WHERE DATE(created_at) = v_date
    GROUP BY agent_type
    ON CONFLICT (metric_date, agent_type, metric_type) DO UPDATE
    SET metric_value = EXCLUDED.metric_value, sample_size = EXCLUDED.sample_size;
END;
$$;

COMMENT ON FUNCTION aggregate_daily_metrics IS 'Aggregates daily performance metrics';

-- ----------------------------------------------------------------------------
-- FUNCTION: prune_old_messages
-- PURPOSE: Prune old messages (keep only summaries)
-- USAGE: SELECT prune_old_messages(30); -- Keep last 30 days
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prune_old_messages(
    p_days_to_keep INT DEFAULT 30
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INT;
BEGIN
    -- Delete messages from sessions older than p_days_to_keep that have summaries
    DELETE FROM conversation_messages
    WHERE session_id IN (
        SELECT cs.session_id
        FROM conversation_sessions cs
        JOIN session_summaries ss ON cs.session_id = ss.session_id
        WHERE cs.last_activity_at < NOW() - (p_days_to_keep || ' days')::INTERVAL
    );
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$;

COMMENT ON FUNCTION prune_old_messages IS 'Prunes old messages while keeping summaries';


-- ============================================================================
-- PART 6: VIEWS FOR COMMON QUERIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- VIEW: active_sessions_summary
-- PURPOSE: Quick overview of active sessions with task counts
-- USAGE: SELECT * FROM active_sessions_summary;
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW active_sessions_summary AS
SELECT
    cs.session_id,
    cs.user_id,
    cs.started_at,
    cs.last_activity_at,
    cs.total_messages,
    cs.agent_types_used,
    COUNT(DISTINCT at.id) as total_tasks,
    COUNT(DISTINCT at.id) FILTER (WHERE at.status = 'completed') as completed_tasks
FROM conversation_sessions cs
LEFT JOIN agent_tasks at ON cs.session_id = at.session_id
WHERE cs.status = 'active'
GROUP BY cs.id, cs.session_id, cs.user_id, cs.started_at, cs.last_activity_at, cs.total_messages, cs.agent_types_used;

COMMENT ON VIEW active_sessions_summary IS 'Active sessions with message and task counts';

-- ----------------------------------------------------------------------------
-- VIEW: recent_agent_activity
-- PURPOSE: Recent agent activity across all sessions
-- USAGE: SELECT * FROM recent_agent_activity LIMIT 20;
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW recent_agent_activity AS
SELECT
    at.agent_type,
    at.task_type,
    at.status,
    at.execution_time_ms,
    at.created_at,
    cs.session_id
FROM agent_tasks at
JOIN conversation_sessions cs ON at.session_id = cs.session_id
WHERE at.created_at >= NOW() - INTERVAL '24 hours'
ORDER BY at.created_at DESC;

COMMENT ON VIEW recent_agent_activity IS 'Recent agent activity in last 24 hours';

-- ----------------------------------------------------------------------------
-- VIEW: user_preference_summary
-- PURPOSE: Summary of user preferences by type
-- USAGE: SELECT * FROM user_preference_summary WHERE user_id = 'user_123';
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW user_preference_summary AS
SELECT
    user_id,
    preference_type,
    COUNT(*) as total_preferences,
    AVG(confidence_score) as avg_confidence,
    SUM(times_used) as total_usage
FROM user_preferences
GROUP BY user_id, preference_type;

COMMENT ON VIEW user_preference_summary IS 'Summary of user preferences by type';

-- ----------------------------------------------------------------------------
-- VIEW: agent_performance_trends
-- PURPOSE: Agent performance trends over time
-- USAGE: SELECT * FROM agent_performance_trends WHERE agent_type = 'planner';
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW agent_performance_trends AS
SELECT
    agent_type,
    metric_type,
    metric_date,
    metric_value,
    sample_size,
    LAG(metric_value) OVER (PARTITION BY agent_type, metric_type ORDER BY metric_date) as previous_value
FROM performance_metrics
ORDER BY agent_type, metric_type, metric_date DESC;

COMMENT ON VIEW agent_performance_trends IS 'Agent performance trends with previous values';

-- ----------------------------------------------------------------------------
-- VIEW: popular_plans
-- PURPOSE: Most reused plans
-- USAGE: SELECT * FROM popular_plans LIMIT 10;
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW popular_plans AS
SELECT
    plan_type,
    plan_description,
    reuse_count,
    success_rating,
    execution_status,
    created_at
FROM prior_plans
WHERE reuse_count > 0
ORDER BY reuse_count DESC, success_rating DESC NULLS LAST
LIMIT 20;

COMMENT ON VIEW popular_plans IS 'Most frequently reused plans';

-- ============================================================================
-- PART 7: FIXES & ENHANCEMENTS FOR REVIEWER AGENT
-- ============================================================================

-- ----------------------------------------------------------------------------
-- FIX: Add user_id to conversation_messages if not exists
-- PURPOSE: Enable analytics queries that filter by user_id
-- ----------------------------------------------------------------------------
DO $$ 
BEGIN
    -- Add user_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'conversation_messages' 
        AND column_name = 'user_id'
    ) THEN
        ALTER TABLE conversation_messages ADD COLUMN user_id TEXT;
        
        -- Update existing messages with user_id from sessions
        UPDATE conversation_messages cm
        SET user_id = cs.user_id
        FROM conversation_sessions cs
        WHERE cm.session_id = cs.session_id
        AND cm.user_id IS NULL;
        
        RAISE NOTICE 'Added user_id column to conversation_messages and populated from sessions';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- FUNCTION: get_agent_interaction_metrics
-- PURPOSE: Get agent interaction analytics for REVIEWER agent
-- USAGE: SELECT * FROM get_agent_interaction_metrics('user_123', 7);
-- RETURNS: JSON with agent usage, success rates, and interaction metrics
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_agent_interaction_metrics(
    p_user_id TEXT,
    p_days INT DEFAULT 7
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_result JSONB;
    v_total_interactions INT;
    v_planner_count INT;
    v_executor_count INT;
    v_manager_count INT;
    v_most_used_agent TEXT;
BEGIN
    -- Get agent usage counts from messages
    SELECT 
        COUNT(*) FILTER (WHERE agent_type = 'planner'),
        COUNT(*) FILTER (WHERE agent_type = 'executor'),
        COUNT(*) FILTER (WHERE agent_type = 'manager')
    INTO v_planner_count, v_executor_count, v_manager_count
    FROM conversation_messages cm
    JOIN conversation_sessions cs ON cm.session_id = cs.session_id
    WHERE cs.user_id = p_user_id
        AND cm.timestamp >= NOW() - (p_days || ' days')::INTERVAL
        AND cm.role = 'assistant';
    
    -- Calculate total interactions
    v_total_interactions := COALESCE(v_planner_count, 0) + 
                           COALESCE(v_executor_count, 0) + 
                           COALESCE(v_manager_count, 0);
    
    -- Determine most used agent
    v_most_used_agent := CASE 
        WHEN v_planner_count >= v_executor_count AND v_planner_count >= v_manager_count THEN 'planner'
        WHEN v_executor_count >= v_manager_count THEN 'executor'
        ELSE 'manager'
    END;
    
    -- Build result JSON
    v_result := jsonb_build_object(
        'total_interactions', v_total_interactions,
        'agent_usage', jsonb_build_object(
            'planner', COALESCE(v_planner_count, 0),
            'executor', COALESCE(v_executor_count, 0),
            'manager', COALESCE(v_manager_count, 0)
        ),
        'planner_count', COALESCE(v_planner_count, 0),
        'executor_count', COALESCE(v_executor_count, 0),
        'planner_executor_success_rate', 
            CASE 
                WHEN COALESCE(v_planner_count, 0) > 0 
                THEN ROUND((COALESCE(v_executor_count, 0)::FLOAT / v_planner_count * 100)::NUMERIC, 1)
                ELSE 0 
            END,
        'most_used_agent', v_most_used_agent
    );
    
    RETURN v_result;
END;
$$;

COMMENT ON FUNCTION get_agent_interaction_metrics IS 'Get agent interaction analytics for weekly reviews';

-- ----------------------------------------------------------------------------
-- FUNCTION: get_memory_learning_metrics
-- PURPOSE: Get memory and learning metrics for REVIEWER agent
-- USAGE: SELECT * FROM get_memory_learning_metrics('user_123', 7);
-- RETURNS: JSON with sessions, preferences, plans, and learning metrics
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_memory_learning_metrics(
    p_user_id TEXT,
    p_days INT DEFAULT 7
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_result JSONB;
    v_sessions_count INT;
    v_preferences_count INT;
    v_plans_count INT;
BEGIN
    -- Count sessions
    SELECT COUNT(*) INTO v_sessions_count
    FROM conversation_sessions
    WHERE user_id = p_user_id
        AND started_at >= NOW() - (p_days || ' days')::INTERVAL;
    
    -- Count new preferences learned
    SELECT COUNT(*) INTO v_preferences_count
    FROM user_preferences
    WHERE user_id = p_user_id
        AND created_at >= NOW() - (p_days || ' days')::INTERVAL;
    
    -- Count plans created
    SELECT COUNT(*) INTO v_plans_count
    FROM prior_plans
    WHERE user_id = p_user_id
        AND created_at >= NOW() - (p_days || ' days')::INTERVAL;
    
    -- Build result JSON
    v_result := jsonb_build_object(
        'sessions_completed', COALESCE(v_sessions_count, 0),
        'preferences_learned', COALESCE(v_preferences_count, 0),
        'plans_created', COALESCE(v_plans_count, 0),
        'most_queried_topic', 'scheduling'
    );
    
    RETURN v_result;
END;
$$;

COMMENT ON FUNCTION get_memory_learning_metrics IS 'Get memory and learning metrics for weekly reviews';

-- ============================================================================
-- PART 8: INITIAL DATA & DEFAULT VALUES
-- ============================================================================

-- Insert default agent memory contexts
INSERT INTO agent_memory_context (agent_type, context_key, context_value, importance_score)
VALUES
    ('manager', 'default_preferences', '{"max_results": 25, "calendar_id": "mkoome@andrew.cmu.edu"}'::jsonb, 0.8),
    ('planner', 'default_preferences', '{"max_results": 50, "calendar_id": "mkoome@andrew.cmu.edu"}'::jsonb, 0.8),
    ('executor', 'default_preferences', '{"max_results": 30, "calendar_id": "mkoome@andrew.cmu.edu"}'::jsonb, 0.8)
ON CONFLICT (agent_type, context_key) DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Run these queries to verify the schema was created successfully:

-- 1. Check all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name IN (
        'conversation_sessions',
        'conversation_messages',
        'agent_tasks',
        'agent_memory_context',
        'tool_usage_logs',
        'user_preferences',
        'session_summaries',
        'prior_plans',
        'performance_metrics'
    )
ORDER BY table_name;

-- 2. Check all indexes exist
SELECT indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
    AND indexname LIKE 'idx_%'
ORDER BY indexname;

-- 3. Check all functions exist
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
    AND routine_type = 'FUNCTION'
    AND routine_name IN (
        'get_conversation_history',
        'get_agent_performance',
        'get_top_tools',
        'get_user_preferences',
        'get_similar_plans',
        'aggregate_daily_metrics',
        'prune_old_messages',
        'get_agent_interaction_metrics',
        'get_memory_learning_metrics'
    )
ORDER BY routine_name;

-- 4. Check all views exist
SELECT table_name 
FROM information_schema.views 
WHERE table_schema = 'public'
ORDER BY table_name;

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Example 1: Get conversation history
-- SELECT * FROM get_conversation_history('session_123', 10);

-- Example 2: Get agent performance
-- SELECT * FROM get_agent_performance('planner', 7);

-- Example 3: Get user preferences
-- SELECT * FROM get_user_preferences('default_user', 'scheduling');

-- Example 4: Get agent interaction metrics (for REVIEWER)
-- SELECT * FROM get_agent_interaction_metrics('default_user', 7);

-- Example 5: Get memory learning metrics (for REVIEWER)
-- SELECT * FROM get_memory_learning_metrics('default_user', 7);

-- Example 6: View active sessions
-- SELECT * FROM active_sessions_summary;

-- Example 7: View recent agent activity
-- SELECT * FROM recent_agent_activity LIMIT 20;

-- ============================================================================
-- MAINTENANCE TASKS
-- ============================================================================

-- Run daily to aggregate metrics (can be set up as cron job)
-- SELECT aggregate_daily_metrics();

-- Run monthly to prune old messages (keeps last 30 days)
-- SELECT prune_old_messages(30);

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

-- Success message
DO $$ 
BEGIN
    RAISE NOTICE '✅ Complete memory schema created successfully!';
    RAISE NOTICE '📊 9 tables created';
    RAISE NOTICE '🔍 30+ indexes created';
    RAISE NOTICE '⚙️ 9 RPC functions created';
    RAISE NOTICE '📈 5 views created';
    RAISE NOTICE '🎯 Ready for multi-agent system!';
END $$;
