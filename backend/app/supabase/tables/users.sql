-- Users table definition
-- Note: This extends Supabase's built-in auth.users table with additional profile data

-- Create users table in public schema that references auth.users
CREATE TABLE IF NOT EXISTS public.users (
    -- Core fields (mapped from auth.users)
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    
    -- Profile & preferences
    avatar_url TEXT,
    company TEXT,
    job_title TEXT,
    
    -- Usage & limits
    credits_remaining INTEGER NOT NULL DEFAULT 100,
    subscription_tier TEXT NOT NULL DEFAULT 'free',
    subscription_status TEXT NOT NULL DEFAULT 'active',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT users_email_unique UNIQUE (email),
    CONSTRAINT users_subscription_tier_valid CHECK (
        subscription_tier IN ('free', 'pro', 'enterprise')
    ),
    CONSTRAINT users_subscription_status_valid CHECK (
        subscription_status IN ('active', 'cancelled', 'suspended')
    ),
    CONSTRAINT users_credits_non_negative CHECK (credits_remaining >= 0)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_subscription_tier ON public.users(subscription_tier);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON public.users(subscription_status);

-- Updated at trigger
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to handle new user creation
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert into public.users
    INSERT INTO public.users (id, email, full_name, created_at)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'full_name',
        NEW.created_at
    );
    RETURN NEW;
END;
$$ language 'plpgsql' SECURITY DEFINER;

-- Trigger to automatically create public.users record
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- Enable RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own profile"
    ON public.users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

-- Comments
COMMENT ON TABLE public.users IS 'Extended user profiles and preferences';
COMMENT ON COLUMN public.users.id IS 'References the auth.users table';
COMMENT ON COLUMN public.users.email IS 'User email address';
COMMENT ON COLUMN public.users.full_name IS 'User full name';
COMMENT ON COLUMN public.users.avatar_url IS 'URL to user avatar image';
COMMENT ON COLUMN public.users.company IS 'User company or organization';
COMMENT ON COLUMN public.users.job_title IS 'User job title or role';
COMMENT ON COLUMN public.users.credits_remaining IS 'Available credits for API usage';
COMMENT ON COLUMN public.users.subscription_tier IS 'Current subscription level';
COMMENT ON COLUMN public.users.subscription_status IS 'Status of current subscription';
COMMENT ON COLUMN public.users.last_login_at IS 'Timestamp of last login'; 