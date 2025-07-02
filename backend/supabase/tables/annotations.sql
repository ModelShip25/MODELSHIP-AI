-- Annotations table for storing object detection results
CREATE TABLE IF NOT EXISTS annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL CHECK (class_id >= 0),
    class_name TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    bbox_x REAL NOT NULL CHECK (bbox_x >= 0),
    bbox_y REAL NOT NULL CHECK (bbox_y >= 0),
    bbox_width REAL NOT NULL CHECK (bbox_width > 0),
    bbox_height REAL NOT NULL CHECK (bbox_height > 0),
    area REAL NOT NULL CHECK (area > 0),
    source TEXT DEFAULT 'yolox',
    verified BOOLEAN DEFAULT FALSE,
    user_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE annotations ENABLE ROW LEVEL SECURITY;

-- Create policies for RLS (inherit from images table)
CREATE POLICY "Users can view annotations for their images" ON annotations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM images 
            WHERE images.id = annotations.image_id 
            AND images.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert annotations for their images" ON annotations
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM images 
            WHERE images.id = annotations.image_id 
            AND images.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update annotations for their images" ON annotations
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM images 
            WHERE images.id = annotations.image_id 
            AND images.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete annotations for their images" ON annotations
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM images 
            WHERE images.id = annotations.image_id 
            AND images.user_id = auth.uid()
        )
    );

-- Create trigger for updated_at
CREATE TRIGGER update_annotations_updated_at 
    BEFORE UPDATE ON annotations 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column(); 