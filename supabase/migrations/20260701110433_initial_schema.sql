-- 20260701110433_initial_schema.sql
-- Enable pgvector extension for AI embeddings

CREATE EXTENSION IF NOT EXISTS vector;
-- Users table
-- Supabase Auth handles actual login
-- This table stores extra user info

CREATE TABLE users (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Receipts table
-- Stores raw receipt data before agent processing
CREATE TABLE receipts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  source TEXT CHECK (source IN ('image', 'gmail', 'pdf')),
  raw_text TEXT,
  image_url TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Expenses table
-- Stores structured data after agent processing
-- embedding column stores 768-dimensional vector for semantic search
CREATE TABLE expenses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  receipt_id UUID REFERENCES receipts(id),
  user_id UUID REFERENCES users(id),
  merchant TEXT,
  date DATE,
  total FLOAT,
  currency TEXT DEFAULT 'INR',
  category TEXT,
  payment_method TEXT,
  line_items JSONB,
  embedding vector(768),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Anomalies table
-- Stores flags from Anomaly Detector Agent
CREATE TABLE anomalies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  expense_id UUID REFERENCES expenses(id),
  type TEXT CHECK (type IN ('spike', 'duplicate', 'unusual_merchant')),
  description TEXT,
  flagged_at TIMESTAMP DEFAULT NOW(),
  resolved BOOLEAN DEFAULT FALSE
);

-- Insights table
-- Stores monthly summaries from Insight Agent
CREATE TABLE insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  month TEXT,
  predictions JSONB,
  inflation_flags JSONB,
  summary_text TEXT,
  generated_at TIMESTAMP DEFAULT NOW()
);