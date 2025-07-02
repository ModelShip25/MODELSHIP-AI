-- Annotations table definition
CREATE TABLE IF NOT EXISTS public.annotations (
    -- Core fields
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id UUID NOT NULL REFERENCES public.images(id) ON DELETE CASCADE,
    job_id UUID REFERENCES public.jobs(id) ON DELETE SET NULL,
    
    -- Classification
    class_name TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    confidence REAL NOT NULL,
    
    -- Bounding box (normalized 0-1 coordinates)
    bbox JSONB NOT NULL,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Source tracking
    source TEXT NOT NULL DEFAULT 'auto',  -- 'auto', 'manual', 'imported'
    verified BOOLEAN NOT NULL DEFAULT false,
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Constraints
    CONSTRAINT annotations_confidence_range CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT annotations_source_valid CHECK (source IN ('auto', 'manual', 'imported')),
    CONSTRAINT annotations_bbox_format CHECK (
        bbox ? 'x_min' AND
        bbox ? 'y_min' AND
        bbox ? 'x_max' AND
        bbox ? 'y_max' AND
        (bbox->>'x_min')::float >= 0 AND
        (bbox->>'y_min')::float >= 0 AND
        (bbox->>'x_max')::float <= 1 AND
        (bbox->>'y_max')::float <= 1 AND
        (bbox->>'x_max')::float > (bbox->>'x_min')::float AND
        (bbox->>'y_max')::float > (bbox->>'y_min')::float
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_annotations_image_id ON public.annotations(image_id);
CREATE INDEX IF NOT EXISTS idx_annotations_job_id ON public.annotations(job_id);
CREATE INDEX IF NOT EXISTS idx_annotations_class_name ON public.annotations(class_name);
CREATE INDEX IF NOT EXISTS idx_annotations_class_id ON public.annotations(class_id);
CREATE INDEX IF NOT EXISTS idx_annotations_verified ON public.annotations(verified);
CREATE INDEX IF NOT EXISTS idx_annotations_source ON public.annotations(source);

-- Updated at trigger
CREATE TRIGGER update_annotations_updated_at
    BEFORE UPDATE ON public.annotations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verification timestamp trigger
CREATE OR REPLACE FUNCTION update_verified_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.verified = true AND OLD.verified = false THEN
        NEW.verified_at = NOW();
        NEW.verified_by = auth.uid();
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_annotations_verified_at
    BEFORE UPDATE ON public.annotations
    FOR EACH ROW
    WHEN (NEW.verified = true AND OLD.verified = false)
    EXECUTE FUNCTION update_verified_timestamp();

-- Enable RLS
ALTER TABLE public.annotations ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view annotations on their images"
    ON public.annotations FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.images
            WHERE images.id = annotations.image_id
            AND images.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert annotations on their images"
    ON public.annotations FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.images
            WHERE images.id = annotations.image_id
            AND images.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update annotations on their images"
    ON public.annotations FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.images
            WHERE images.id = annotations.image_id
            AND images.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete annotations on their images"
    ON public.annotations FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.images
            WHERE images.id = annotations.image_id
            AND images.user_id = auth.uid()
        )
    );

-- Comments
COMMENT ON TABLE public.annotations IS 'Bounding box annotations for images';
COMMENT ON COLUMN public.annotations.id IS 'Unique identifier for the annotation';
COMMENT ON COLUMN public.annotations.image_id IS 'Reference to the annotated image';
COMMENT ON COLUMN public.annotations.job_id IS 'Reference to the batch job that created this annotation';
COMMENT ON COLUMN public.annotations.class_name IS 'Name of the detected object class';
COMMENT ON COLUMN public.annotations.class_id IS 'Numeric ID of the detected object class';
COMMENT ON COLUMN public.annotations.confidence IS 'Confidence score of the detection (0-1)';
COMMENT ON COLUMN public.annotations.bbox IS 'Bounding box coordinates in normalized format';
COMMENT ON COLUMN public.annotations.source IS 'Source of the annotation (auto/manual/imported)';
COMMENT ON COLUMN public.annotations.verified IS 'Whether the annotation has been verified by a user';
COMMENT ON COLUMN public.annotations.verified_at IS 'When the annotation was verified';
COMMENT ON COLUMN public.annotations.verified_by IS 'Who verified the annotation'; 