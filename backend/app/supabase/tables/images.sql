-- Images table definition
CREATE TABLE IF NOT EXISTS public.images (
    -- Core fields
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    width INTEGER,
    height INTEGER,
    file_hash TEXT NOT NULL,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Preview image (optional)
    preview_path TEXT,
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'uploaded',
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    
    -- Constraints
    CONSTRAINT images_file_hash_unique UNIQUE (file_hash),
    CONSTRAINT images_storage_path_unique UNIQUE (storage_path),
    CONSTRAINT images_preview_path_unique UNIQUE (preview_path),
    CONSTRAINT images_size_positive CHECK (size_bytes > 0),
    CONSTRAINT images_dimensions_positive CHECK (
        (width IS NULL AND height IS NULL) OR 
        (width > 0 AND height > 0)
    ),
    CONSTRAINT images_status_valid CHECK (
        status IN ('uploaded', 'processing', 'labeled', 'failed')
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_images_created_at ON public.images(created_at);
CREATE INDEX IF NOT EXISTS idx_images_status ON public.images(status);
CREATE INDEX IF NOT EXISTS idx_images_file_hash ON public.images(file_hash);

-- Updated at trigger
CREATE TRIGGER update_images_updated_at
    BEFORE UPDATE ON public.images
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE public.images ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own images"
    ON public.images FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own images"
    ON public.images FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own images"
    ON public.images FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own images"
    ON public.images FOR DELETE
    USING (auth.uid() = user_id);

-- Comments
COMMENT ON TABLE public.images IS 'Uploaded images for labeling';
COMMENT ON COLUMN public.images.id IS 'Unique identifier for the image';
COMMENT ON COLUMN public.images.filename IS 'Original filename of the uploaded image';
COMMENT ON COLUMN public.images.storage_path IS 'Path where the image is stored in Supabase Storage';
COMMENT ON COLUMN public.images.content_type IS 'MIME type of the image';
COMMENT ON COLUMN public.images.size_bytes IS 'Size of the image in bytes';
COMMENT ON COLUMN public.images.width IS 'Width of the image in pixels';
COMMENT ON COLUMN public.images.height IS 'Height of the image in pixels';
COMMENT ON COLUMN public.images.file_hash IS 'Hash of the file content for deduplication';
COMMENT ON COLUMN public.images.preview_path IS 'Path to the preview image with bounding boxes';
COMMENT ON COLUMN public.images.status IS 'Current status of the image processing';
COMMENT ON COLUMN public.images.processed_at IS 'When the image was last processed';
COMMENT ON COLUMN public.images.error_message IS 'Error message if processing failed'; 