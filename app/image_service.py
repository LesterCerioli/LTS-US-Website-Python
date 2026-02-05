
import base64
import imghdr
from typing import Tuple, Optional, Dict, Any, List, Union
from fastapi import HTTPException
import magic
from PIL import Image
import io
import re
import asyncio
import hashlib
from datetime import datetime
from uuid import UUID


class ImageService:
        
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB limit for Render free tier
    ALLOWED_MIME_TYPES = {'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'}
    
    def __init__(self, db_instance):
        
        self.db = db_instance
    
        
    async def validate_and_process_image(self, base64_data: str, mime_type: Optional[str] = None) -> Dict[str, Any]:
        
        try:
            
            if base64_data.startswith('data:'):
                match = re.match(r'data:(image/[a-zA-Z0-9+-]+);base64,(.*)', base64_data)
                if match:
                    mime_type = match.group(1)
                    base64_data = match.group(2)
                else:
                    raise ValueError("Invalid data URL format")
            
            
            loop = asyncio.get_event_loop()
            image_bytes = await loop.run_in_executor(
                None, 
                lambda: base64.b64decode(base64_data)
            )
            
            
            if len(image_bytes) > self.MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image size exceeds limit of {self.MAX_IMAGE_SIZE // (1024*1024)}MB"
                )
            
            
            if not mime_type:
                mime_type = magic.from_buffer(image_bytes, mime=True)
            
            
            if mime_type not in self.ALLOWED_MIME_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image type. Allowed: {', '.join(self.ALLOWED_MIME_TYPES)}"
                )
            
            
            def process_image(bytes_data):
                image = Image.open(io.BytesIO(bytes_data))
                image.verify()  # Verify it's a valid image
                
                
                image = Image.open(io.BytesIO(bytes_data))
                width, height = image.size
                
                
                if len(bytes_data) > 1 * 1024 * 1024:  # If > 1MB
                    if width > 1920:
                        new_height = int((1920 / width) * height)
                        image = image.resize((1920, new_height), Image.Resampling.LANCZOS)
                        
                        
                        buffer = io.BytesIO()
                        if mime_type in ['image/jpeg', 'image/jpg']:
                            image.save(buffer, format='JPEG', quality=85, optimize=True)
                        else:
                            image.save(buffer, format='PNG', optimize=True)
                        
                        return buffer.getvalue(), width, height, new_height
                
                return bytes_data, width, height, height
            
            image_bytes, width, height, new_height = await loop.run_in_executor(
                None, 
                lambda: process_image(image_bytes)
            )
            
            
            if len(image_bytes) != len(base64.b64decode(base64_data)):
                base64_data = await loop.run_in_executor(
                    None,
                    lambda: base64.b64encode(image_bytes).decode('utf-8')
                )
            
            
            image_hash = await loop.run_in_executor(
                None,
                lambda: hashlib.md5(image_bytes).hexdigest()
            )
            
            return {
                'base64_data': base64_data,
                'mime_type': mime_type,
                'size_bytes': len(image_bytes),
                'original_dimensions': (width, height),
                'processed_dimensions': (1920, new_height) if width > 1920 else (width, height),
                'image_hash': image_hash,
                'created_at': datetime.utcnow()
            }
            
        except base64.binascii.Error:
            raise HTTPException(status_code=400, detail="Invalid base64 encoding")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image processing error: {str(e)}")
    
        
    async def save_image_to_post(self, post_id: UUID, image_data: Dict[str, Any]) -> bool:
        
        query = """
            UPDATE public.posts 
            SET base64_image = %s,
                image_mime_type = %s,
                image_alt = COALESCE(%s, image_alt),
                image_hash = %s,
                image_size_bytes = %s,
                image_dimensions = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id;
        """
        
        params = (
            image_data['base64_data'],
            image_data['mime_type'],
            image_data.get('image_alt', ''),
            image_data['image_hash'],
            image_data['size_bytes'],
            f"{image_data['processed_dimensions'][0]}x{image_data['processed_dimensions'][1]}",
            post_id
        )
        
        try:
            result = await self.db.execute_query(query, params)
            return len(result) > 0
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error saving image: {str(e)}"
            )
    
    async def get_post_image(self, post_id: UUID, include_metadata: bool = False) -> Optional[Dict[str, Any]]:
        
        if include_metadata:
            query = """
                SELECT 
                    base64_image, 
                    image_mime_type, 
                    image_alt,
                    image_hash,
                    image_size_bytes,
                    image_dimensions,
                    updated_at as image_updated_at
                FROM public.posts 
                WHERE id = %s AND base64_image IS NOT NULL;
            """
        else:
            query = """
                SELECT base64_image, image_mime_type, image_alt
                FROM public.posts 
                WHERE id = %s AND base64_image IS NOT NULL;
            """
        
        try:
            result = await self.db.fetch_one(query, (post_id,))
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error fetching image: {str(e)}"
            )
    
    async def remove_post_image(self, post_id: UUID) -> bool:
        
        query = """
            UPDATE public.posts 
            SET base64_image = NULL,
                image_mime_type = NULL,
                image_alt = NULL,
                image_hash = NULL,
                image_size_bytes = NULL,
                image_dimensions = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND base64_image IS NOT NULL
            RETURNING id;
        """
        
        try:
            result = await self.db.execute_query(query, (post_id,))
            return len(result) > 0
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error removing image: {str(e)}"
            )
    
    async def find_duplicate_image(self, image_hash: str, exclude_post_id: UUID = None) -> List[Dict[str, Any]]:
        
        if exclude_post_id:
            query = """
                SELECT 
                    id,
                    title,
                    slug,
                    image_alt,
                    image_dimensions,
                    updated_at
                FROM public.posts 
                WHERE image_hash = %s 
                  AND id != %s 
                  AND base64_image IS NOT NULL
                ORDER BY updated_at DESC;
            """
            params = (image_hash, exclude_post_id)
        else:
            query = """
                SELECT 
                    id,
                    title,
                    slug,
                    image_alt,
                    image_dimensions,
                    updated_at
                FROM public.posts 
                WHERE image_hash = %s 
                  AND base64_image IS NOT NULL
                ORDER BY updated_at DESC;
            """
            params = (image_hash,)
        
        try:
            results = await self.db.execute_query(query, params)
            return results
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error finding duplicate images: {str(e)}"
            )
    
    async def get_posts_by_image_status(self, organization_id: UUID, has_image: bool = True) -> List[Dict[str, Any]]:
        
        if has_image:
            query = """
                SELECT 
                    p.id,
                    p.title,
                    p.slug,
                    p.status,
                    p.image_alt,
                    p.image_mime_type,
                    p.image_size_bytes,
                    p.image_dimensions,
                    p.updated_at,
                    u.username,
                    u.email as user_email
                FROM public.posts p
                LEFT JOIN public.users u ON p.user_id = u.id
                WHERE p.organization_id = %s 
                  AND p.base64_image IS NOT NULL
                  AND p.deleted_at IS NULL
                ORDER BY p.updated_at DESC;
            """
        else:
            query = """
                SELECT 
                    p.id,
                    p.title,
                    p.slug,
                    p.status,
                    p.updated_at,
                    u.username,
                    u.email as user_email
                FROM public.posts p
                LEFT JOIN public.users u ON p.user_id = u.id
                WHERE p.organization_id = %s 
                  AND p.base64_image IS NULL
                  AND p.deleted_at IS NULL
                ORDER BY p.updated_at DESC;
            """
        
        try:
            results = await self.db.execute_query(query, (organization_id,))
            return results
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error fetching posts by image status: {str(e)}"
            )
    
    async def bulk_update_image_metadata(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        
        success_count = 0
        failed_posts = []
        
        query = """
            UPDATE public.posts 
            SET image_alt = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND base64_image IS NOT NULL;
        """
        
        try:
            
            for update in updates:
                post_id = update.get('post_id')
                image_alt = update.get('image_alt', '')
                
                if not post_id:
                    failed_posts.append({'post_id': None, 'error': 'Missing post_id'})
                    continue
                
                try:
                    
                    success = await self.db.execute_update(query, (image_alt, post_id))
                    if success:
                        success_count += 1
                    else:
                        failed_posts.append({'post_id': post_id, 'error': 'Post not found or no image'})
                except Exception as e:
                    failed_posts.append({'post_id': post_id, 'error': str(e)})
            
            return {
                'success': True,
                'updated_count': success_count,
                'failed_count': len(failed_posts),
                'failed_posts': failed_posts,
                'total_processed': len(updates)
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error in bulk update: {str(e)}"
            )
    
    async def get_image_statistics(self, organization_id: UUID) -> Dict[str, Any]:
        
        try:
            # Total posts with images
            result1 = await self.db.fetch_one('''
                SELECT COUNT(*) as total_with_images
                FROM public.posts 
                WHERE organization_id = %s 
                  AND base64_image IS NOT NULL 
                  AND deleted_at IS NULL;
            ''', (organization_id,))
            total_with_images = result1['total_with_images'] if result1 else 0
            
            
            result2 = await self.db.fetch_one('''
                SELECT COUNT(*) as total_without_images
                FROM public.posts 
                WHERE organization_id = %s 
                  AND base64_image IS NULL 
                  AND deleted_at IS NULL;
            ''', (organization_id,))
            total_without_images = result2['total_without_images'] if result2 else 0
            
            
            result3 = await self.db.fetch_one('''
                SELECT COALESCE(SUM(image_size_bytes), 0) as total_storage_bytes
                FROM public.posts 
                WHERE organization_id = %s 
                  AND image_size_bytes IS NOT NULL;
            ''', (organization_id,))
            total_storage = result3['total_storage_bytes'] if result3 else 0
            
            
            result4 = await self.db.execute_query('''
                SELECT 
                    image_mime_type,
                    COUNT(*) as count,
                    SUM(image_size_bytes) as total_size
                FROM public.posts 
                WHERE organization_id = %s 
                  AND image_mime_type IS NOT NULL
                GROUP BY image_mime_type
                ORDER BY count DESC;
            ''', (organization_id,))
            image_types = result4
            
            
            result5 = await self.db.execute_query('''
                SELECT 
                    id,
                    title,
                    image_mime_type,
                    image_size_bytes,
                    image_dimensions,
                    updated_at
                FROM public.posts 
                WHERE organization_id = %s 
                  AND base64_image IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT 10;
            ''', (organization_id,))
            recent_images = result5
                        
            result6 = await self.db.fetch_one('''
                SELECT 
                    COALESCE(AVG(image_size_bytes), 0) as avg_size,
                    COALESCE(MIN(image_size_bytes), 0) as min_size,
                    COALESCE(MAX(image_size_bytes), 0) as max_size
                FROM public.posts 
                WHERE organization_id = %s 
                  AND image_size_bytes IS NOT NULL;
            ''', (organization_id,))
            size_stats = result6 or {}
            
            return {
                'total_posts_with_images': total_with_images,
                'total_posts_without_images': total_without_images,
                'total_storage_bytes': total_storage,
                'total_storage_mb': round(total_storage / (1024 * 1024), 2),
                'image_types_distribution': [
                    {
                        'mime_type': row['image_mime_type'],
                        'count': row['count'],
                        'total_size_bytes': row['total_size'],
                        'percentage': round(row['count'] * 100 / total_with_images, 2) if total_with_images > 0 else 0
                    }
                    for row in image_types
                ],
                'size_statistics': {
                    'avg_bytes': round(size_stats.get('avg_size', 0) or 0),
                    'min_bytes': size_stats.get('min_size', 0) or 0,
                    'max_bytes': size_stats.get('max_size', 0) or 0,
                    'avg_kb': round((size_stats.get('avg_size', 0) or 0) / 1024, 2),
                    'avg_mb': round((size_stats.get('avg_size', 0) or 0) / (1024 * 1024), 2)
                },
                'recent_images': [
                    {
                        'post_id': row['id'],
                        'title': row['title'],
                        'mime_type': row['image_mime_type'],
                        'size_bytes': row['image_size_bytes'],
                        'dimensions': row['image_dimensions'],
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    }
                    for row in recent_images
                ],
                'storage_percentage': round((total_storage / (self.MAX_IMAGE_SIZE * 100)) * 100, 2)
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error fetching statistics: {str(e)}"
            )
    
    async def cleanup_orphaned_images(self, organization_id: UUID, days_threshold: int = 30) -> Dict[str, Any]:
        
        query = """
            UPDATE public.posts 
            SET base64_image = NULL,
                image_mime_type = NULL,
                image_alt = NULL,
                image_hash = NULL,
                image_size_bytes = NULL,
                image_dimensions = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE organization_id = %s 
              AND deleted_at IS NOT NULL
              AND deleted_at < CURRENT_TIMESTAMP - INTERVAL %s
              AND base64_image IS NOT NULL
            RETURNING id, title, image_size_bytes;
        """
        
        try:
            
            interval = f"{days_threshold} days"
            results = await self.db.execute_query(query, (organization_id, interval))
            
            cleaned_posts = results
            total_space_freed = sum(row['image_size_bytes'] or 0 for row in cleaned_posts)
            
            return {
                'success': True,
                'cleaned_count': len(cleaned_posts),
                'total_space_freed_bytes': total_space_freed,
                'total_space_freed_mb': round(total_space_freed / (1024 * 1024), 2),
                'cleaned_posts': cleaned_posts
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error cleaning up images: {str(e)}"
            )
    
        
    @staticmethod
    def create_data_url(base64_data: str, mime_type: str) -> str:
        
        return f"data:{mime_type};base64,{base64_data}"
    
    @staticmethod
    def extract_from_data_url(data_url: str) -> Tuple[str, str]:
        
        if not data_url.startswith('data:'):
            return data_url, 'image/jpeg'
        
        match = re.match(r'data:(image/[a-zA-Z0-9+-]+);base64,(.*)', data_url)
        if match:
            return match.group(2), match.group(1)
        return data_url, 'image/jpeg'
    
    async def is_base64_image(self, data: str) -> bool:
        
        try:
            if data.startswith('data:'):
                data = data.split(',')[1]
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: base64.b64decode(data, validate=True)
            )
            return True
        except:
            return False
    
    async def optimize_image_size(self, base64_data: str, target_size_kb: int = 500) -> str:
        
        def optimize_image(bytes_data, quality=85):
            img = Image.open(io.BytesIO(bytes_data))
            buffer = io.BytesIO()
            
            if img.format == 'JPEG' or img.mode == 'RGB':
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                mime_type = 'image/jpeg'
            else:
                img.save(buffer, format='PNG', optimize=True)
                mime_type = 'image/png'
            
            return buffer.getvalue(), mime_type
        
        try:
            loop = asyncio.get_event_loop()
            original_bytes = await loop.run_in_executor(
                None,
                lambda: base64.b64decode(base64_data)
            )
            
            target_bytes = target_size_kb * 1024
            current_bytes = len(original_bytes)
            
            if current_bytes <= target_bytes:
                return base64_data
            
            
            quality = 85
            optimized_bytes = original_bytes
            optimized_base64 = base64_data
            
            while current_bytes > target_bytes and quality > 10:
                optimized_bytes, mime_type = await loop.run_in_executor(
                    None,
                    lambda: optimize_image(optimized_bytes, quality)
                )
                
                current_bytes = len(optimized_bytes)
                quality -= 5
            
            optimized_base64 = await loop.run_in_executor(
                None,
                lambda: base64.b64encode(optimized_bytes).decode('utf-8')
            )
            
            return optimized_base64
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Image optimization error: {str(e)}"
            )
    
    async def generate_image_thumbnail(self, base64_data: str, max_dimension: int = 300) -> str:
        
        def create_thumbnail(bytes_data, max_dim):
            img = Image.open(io.BytesIO(bytes_data))
            
            
            width, height = img.size
            if width > height:
                new_width = max_dim
                new_height = int((max_dim / width) * height)
            else:
                new_height = max_dim
                new_width = int((max_dim / height) * width)
            
            
            img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
            
            
            buffer = io.BytesIO()
            if img.mode == 'RGBA':
                img.save(buffer, format='PNG', optimize=True)
                mime_type = 'image/png'
            else:
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                mime_type = 'image/jpeg'
            
            return buffer.getvalue(), mime_type
        
        try:
            loop = asyncio.get_event_loop()
            image_bytes = await loop.run_in_executor(
                None,
                lambda: base64.b64decode(base64_data)
            )
            
            thumbnail_bytes, mime_type = await loop.run_in_executor(
                None,
                lambda: create_thumbnail(image_bytes, max_dimension)
            )
            
            thumbnail_base64 = await loop.run_in_executor(
                None,
                lambda: base64.b64encode(thumbnail_bytes).decode('utf-8')
            )
            
            return thumbnail_base64
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Thumbnail generation error: {str(e)}"
            )