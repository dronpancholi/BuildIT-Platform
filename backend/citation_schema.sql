-- ==============================================
-- PHASE 1A: Citation Automation Schema
-- BuildIT SEO Platform
-- ==============================================

-- Enums
DO $$ BEGIN
    CREATE TYPE citation_project_status AS ENUM ('active', 'paused', 'completed', 'archived');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE citation_status AS ENUM ('pending', 'not_started', 'in_progress', 'already_exists', 'new_backlink', 'pending_review', 'failed', 'rejected');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE citation_category AS ENUM ('general', 'local', 'business', 'social', 'review', 'directory', 'niche', 'government', 'education');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

-- Master Citation Sites Table
CREATE TABLE citation_sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    submission_url VARCHAR(500),
    registration_url VARCHAR(500),
    category citation_category NOT NULL DEFAULT 'general',
    niche VARCHAR(255),
    geo_target VARCHAR(100),
    has_logo_upload BOOLEAN DEFAULT false,
    has_description BOOLEAN DEFAULT true,
    has_hours BOOLEAN DEFAULT false,
    has_social_links BOOLEAN DEFAULT false,
    has_images BOOLEAN DEFAULT false,
    has_video BOOLEAN DEFAULT false,
    requires_email_verification BOOLEAN DEFAULT true,
    difficulty_score INTEGER DEFAULT 50,
    monthly_visitors INTEGER DEFAULT 0,
    domain_authority INTEGER DEFAULT 30,
    is_free BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Citation Projects Table
CREATE TABLE citation_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    business_name VARCHAR(255) NOT NULL,
    website_url VARCHAR(500),
    category VARCHAR(255),
    keywords TEXT[],
    phone VARCHAR(50),
    email VARCHAR(255),
    description TEXT,
    short_bio TEXT,
    long_bio TEXT,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Australia',
    postal_code VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    hours_mon VARCHAR(50),
    hours_tue VARCHAR(50),
    hours_wed VARCHAR(50),
    hours_thu VARCHAR(50),
    hours_fri VARCHAR(50),
    hours_sat VARCHAR(50),
    hours_sun VARCHAR(50),
    logo_url VARCHAR(500),
    images JSONB DEFAULT '[]'::jsonb,
    facebook_url VARCHAR(500),
    twitter_url VARCHAR(500),
    linkedin_url VARCHAR(500),
    instagram_url VARCHAR(500),
    youtube_url VARCHAR(500),
    pinterest_url VARCHAR(500),
    submission_email VARCHAR(255),
    submission_password VARCHAR(255),
    status citation_project_status DEFAULT 'active',
    total_sites INTEGER DEFAULT 0,
    pending_count INTEGER DEFAULT 0,
    in_progress_count INTEGER DEFAULT 0,
    already_exists_count INTEGER DEFAULT 0,
    new_backlink_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Citation Submissions Table
CREATE TABLE citation_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES citation_projects(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES citation_sites(id) ON DELETE CASCADE,
    status citation_status DEFAULT 'not_started',
    status_notes TEXT,
    account_created BOOLEAN DEFAULT false,
    email_verified BOOLEAN DEFAULT false,
    listing_claimed BOOLEAN DEFAULT false,
    listing_url VARCHAR(500),
    form_data JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMP WITH TIME ZONE,
    submitted_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    assigned_to UUID,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(project_id, site_id)
);

-- Indexes
CREATE INDEX ix_citation_sites_tenant ON citation_sites(tenant_id);
CREATE INDEX ix_citation_sites_category ON citation_sites(category);
CREATE INDEX ix_citation_sites_niche ON citation_sites(niche);
CREATE INDEX ix_citation_sites_difficulty ON citation_sites(difficulty_score);
CREATE INDEX ix_citation_projects_tenant ON citation_projects(tenant_id);
CREATE INDEX ix_citation_projects_client ON citation_projects(client_id);
CREATE INDEX ix_citation_projects_status ON citation_projects(status);
CREATE INDEX ix_citation_submissions_tenant ON citation_submissions(tenant_id);
CREATE INDEX ix_citation_submissions_project ON citation_submissions(project_id);
CREATE INDEX ix_citation_submissions_status ON citation_submissions(status);

SELECT 'Schema created successfully' as result;