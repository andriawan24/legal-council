-- =============================================================================
-- Legal Council Database Schema
-- Cloud SQL PostgreSQL with pgvector extension
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- LLM Extractions Table
-- Stores extraction results from LLM processing of court case documents
-- =============================================================================

CREATE TABLE llm_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id VARCHAR(255),  -- Can be NULL if LLM fails to extract decision number
    extraction_result JSONB,
    summary_en TEXT,
    summary_id TEXT,
    extraction_confidence FLOAT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,  -- Store error details if extraction fails
    source_file VARCHAR(500),  -- Original filename for tracking failed extractions
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Vector embeddings for semantic search (3072 dimensions - full Gemini precision)
    extraction_embedding vector(3072),
    summary_embedding vector(3072)
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Index on extraction_id for lookups (partial - only non-null values)
CREATE INDEX idx_llm_extractions_extraction_id ON llm_extractions(extraction_id)
    WHERE extraction_id IS NOT NULL;

CREATE INDEX idx_llm_extractions_status ON llm_extractions(status);
CREATE INDEX idx_llm_extractions_source_file ON llm_extractions(source_file);

-- Vector similarity search (IVFFlat for approximate nearest neighbor)
CREATE INDEX idx_llm_extractions_embedding
    ON llm_extractions USING ivfflat (extraction_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_llm_extractions_summary_embedding
    ON llm_extractions USING ivfflat (summary_embedding vector_cosine_ops)
    WITH (lists = 100);

-- JSONB index for querying extraction_result
CREATE INDEX idx_llm_extractions_result ON llm_extractions USING GIN (extraction_result);

-- =============================================================================
-- Trigger for updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_llm_extractions_updated_at
    BEFORE UPDATE ON llm_extractions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();