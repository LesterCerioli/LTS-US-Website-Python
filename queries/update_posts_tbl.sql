-- Add base64_image column to posts table
ALTER TABLE public.posts 
ADD COLUMN IF NOT EXISTS base64_image TEXT,
ADD COLUMN IF NOT EXISTS image_mime_type VARCHAR(50);

-- Update existing posts to maintain compatibility
UPDATE public.posts 
SET base64_image = '' 
WHERE base64_image IS NULL;