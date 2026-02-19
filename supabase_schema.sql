       -- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create semantic_memory table
CREATE TABLE IF NOT EXISTS semantic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_name TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    chunk_type TEXT,
    semantic_unit TEXT,
    retrieval_priority TEXT,
    importance_score FLOAT DEFAULT 0.5,
    content_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_content_hash UNIQUE(content_hash, collection_name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS semantic_memory_embedding_idx 
ON semantic_memory USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS semantic_memory_collection_idx 
ON semantic_memory(collection_name);

CREATE INDEX IF NOT EXISTS semantic_memory_chunk_type_idx 
ON semantic_memory(chunk_type);

CREATE INDEX IF NOT EXISTS semantic_memory_priority_idx 
ON semantic_memory(retrieval_priority);

CREATE INDEX IF NOT EXISTS semantic_memory_importance_idx 
ON semantic_memory(importance_score DESC);

CREATE INDEX IF NOT EXISTS semantic_memory_metadata_idx 
ON semantic_memory USING gin(metadata);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_semantic_memory_updated_at ON semantic_memory;
CREATE TRIGGER update_semantic_memory_updated_at
    BEFORE UPDATE ON semantic_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
