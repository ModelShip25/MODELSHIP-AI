-- ModelShip Database Schema
-- This is the main schema file that sets up all tables and relationships

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- For password hashing
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- For query performance monitoring

-- Set up custom types
DO $$ BEGIN
    -- Enum for job status
    CREATE TYPE job_status AS ENUM (
        'pending',
        'processing',
        'completed',
        'failed'
    );
    
    -- Enum for export formats
    CREATE TYPE export_format AS ENUM (
        'yolo',
        'coco',
        'csv'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create schema for RLS policies
CREATE SCHEMA IF NOT EXISTS auth;

-- Import table definitions
\ir tables/users.sql
\ir tables/images.sql
\ir tables/annotations.sql

-- Create exports table
CREATE TABLE IF NOT EXISTS public.exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL,
    format export_format NOT NULL,
    filename TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    storage_path TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    CONSTRAINT exports_job_format_unique UNIQUE (job_id, format)
);

-- Create jobs table for batch processing
CREATE TABLE IF NOT EXISTS public.jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    status job_status NOT NULL DEFAULT 'pending',
    total_images INTEGER NOT NULL DEFAULT 0,
    processed_images INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    
    CONSTRAINT jobs_processed_total_check CHECK (processed_images <= total_images)
);

-- Create job_images junction table
CREATE TABLE IF NOT EXISTS public.job_images (
    job_id UUID REFERENCES public.jobs(id) ON DELETE CASCADE,
    image_id UUID REFERENCES public.images(id) ON DELETE CASCADE,
    status job_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    
    PRIMARY KEY (job_id, image_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_annotations_image_id ON public.annotations(image_id);
CREATE INDEX IF NOT EXISTS idx_annotations_job_id ON public.annotations(job_id);
CREATE INDEX IF NOT EXISTS idx_exports_job_id ON public.exports(job_id);
CREATE INDEX IF NOT EXISTS idx_images_user_id ON public.images(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON public.jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON public.jobs(status);
CREATE INDEX IF NOT EXISTS idx_job_images_status ON public.job_images(status);

-- Add updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON public.jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies

-- Jobs policies
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own jobs"
    ON public.jobs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own jobs"
    ON public.jobs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own jobs"
    ON public.jobs FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own jobs"
    ON public.jobs FOR DELETE
    USING (auth.uid() = user_id);

-- Job Images policies
ALTER TABLE public.job_images ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their job images"
    ON public.job_images FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.jobs
            WHERE jobs.id = job_images.job_id
            AND jobs.user_id = auth.uid()
        )
    );

-- Exports policies
ALTER TABLE public.exports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own exports"
    ON public.exports FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own exports"
    ON public.exports FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own exports"
    ON public.exports FOR DELETE
    USING (auth.uid() = user_id);

-- Comments
COMMENT ON TABLE public.jobs IS 'Batch processing jobs for image labeling';
COMMENT ON TABLE public.job_images IS 'Images associated with batch processing jobs';
COMMENT ON TABLE public.exports IS 'Exported datasets in various formats';
COMMENT ON COLUMN public.jobs.status IS 'Current status of the job';
COMMENT ON COLUMN public.jobs.total_images IS 'Total number of images to process';
COMMENT ON COLUMN public.jobs.processed_images IS 'Number of images processed so far';
COMMENT ON COLUMN public.exports.format IS 'Format of the exported dataset'; 