-- =============================================================================
-- Legal Council API Database Schema
-- Additional tables for deliberation sessions, messages, and legal opinions
-- Run this after extraction-job/schema.sql
-- =============================================================================

-- =============================================================================
-- Users Table (optional - for authenticated sessions)
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Deliberation Sessions Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS deliberation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'concluded', 'archived')),

    -- Case input stored as JSONB for flexibility
    case_input JSONB NOT NULL,

    -- References to similar cases found
    similar_case_ids UUID[],

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    concluded_at TIMESTAMPTZ
);

-- =============================================================================
-- Deliberation Messages Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS deliberation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES deliberation_sessions(id) ON DELETE CASCADE,

    -- Sender information
    sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('user', 'agent', 'system')),
    agent_id VARCHAR(20) CHECK (agent_id IN ('strict', 'humanist', 'historian')),

    -- Message content
    content TEXT NOT NULL,
    intent VARCHAR(50),

    -- References
    cited_case_ids UUID[],
    cited_laws TEXT[],

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Legal Opinions Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS legal_opinions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID UNIQUE NOT NULL REFERENCES deliberation_sessions(id) ON DELETE CASCADE,

    -- Opinion stored as JSONB
    opinion_data JSONB NOT NULL,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON deliberation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON deliberation_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON deliberation_sessions(created_at DESC);

-- Messages indexes
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON deliberation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON deliberation_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_sender_type ON deliberation_messages(sender_type);

-- Legal opinions index
CREATE INDEX IF NOT EXISTS idx_opinions_session_id ON legal_opinions(session_id);

-- =============================================================================
-- Triggers for updated_at
-- =============================================================================

-- Reuse the trigger function from extraction-job schema if it exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Sessions trigger
DROP TRIGGER IF EXISTS update_deliberation_sessions_updated_at ON deliberation_sessions;
CREATE TRIGGER update_deliberation_sessions_updated_at
    BEFORE UPDATE ON deliberation_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Users trigger
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
