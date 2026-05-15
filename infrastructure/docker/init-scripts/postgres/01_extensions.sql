-- ============================================================================
-- PostgreSQL Init Script — Extensions & RLS Setup
-- ============================================================================
-- Executed on first container startup to enable required extensions.
-- ============================================================================

-- Enable pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enable pg_trgm for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable btree_gin for composite GIN indexes
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Set default timezone
SET timezone = 'UTC';

-- Create the app.current_tenant setting for RLS
-- This is set per-session by the application before any query
ALTER DATABASE seo_platform SET app.current_tenant = '00000000-0000-0000-0000-000000000000';
