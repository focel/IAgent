-- Migration: 001_create_interview_conversations_table
-- Description: Tabla principal para almacenar conversaciones completas de entrevistas
-- Author: System Migration  
-- Date: 2025-01-27
-- Dependencies: Requiere tabla interviews existente

-- Simple table for complete conversation storage
CREATE TABLE IF NOT EXISTS public.interview_full_conversations (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL,
    
    -- Complete conversation data
    full_text TEXT NOT NULL,
    context_data JSONB, -- {prompt, qa_context, metadata}
    
    -- Basic metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key
    CONSTRAINT fk_full_conversation_interview 
        FOREIGN KEY (interview_id) 
        REFERENCES public.interviews(id_interview) 
        ON DELETE CASCADE,
        
    -- One conversation per interview
    CONSTRAINT unique_interview_full_conversation 
        UNIQUE (interview_id)
);

-- Basic indexes
CREATE INDEX IF NOT EXISTS idx_full_conversations_interview ON public.interview_full_conversations(interview_id);
CREATE INDEX IF NOT EXISTS idx_full_conversations_created ON public.interview_full_conversations(created_at);

-- Full-text search
CREATE INDEX IF NOT EXISTS idx_full_conversations_search 
    ON public.interview_full_conversations 
    USING gin(to_tsvector('spanish', full_text));

-- JSONB search
CREATE INDEX IF NOT EXISTS idx_full_conversations_context 
    ON public.interview_full_conversations 
    USING gin(context_data);

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_full_conversations_updated_at 
    BEFORE UPDATE ON public.interview_full_conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();