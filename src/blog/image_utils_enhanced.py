"""
Advanced image processing utilities for blog images.
Handles resizing, optimization, WebP conversion, progressive JPEG,
alt text generation, and CDN preparation.
"""
import os
import hashlib
import json
import glob
from PIL import Image, ImageOps, ExifTags
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils.text import slugify
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Advanced image processing operations for blog images."""

    # Define standard sizes for responsive images (CDN-optimized breakpoints)
    SIZES = {
        'thumbnail': (150, 150),
        'xs': (320, 240),      # Mobile portrait
        'sm': (480, 360),      # Mobile landscape
        'md': (768, 576),      # Tablet
        'lg': (1024, 768),     # Desktop
        'xl': (1280, 960),     # Large desktop
        'xxl': (1920, 1440),   # 4K/Retina
    }

    # Progressive sizing for hero/featured images
    HERO_SIZES = {
        'hero_sm': (800, 400),
        'hero_md': (1200, 600),
        'hero_lg': (1600, 800),
        'hero_xl': (2400, 1200),
    }

    # Image quality settings (optimized for web)
    JPEG_QUALITY = 85
    WEBP_QUALITY = 80
    PROGRESSIVE_JPEG_QUALITY = 80

    # Compression settings
    MAX_FILE_SIZE_KB = 500  # Target max file size for optimization
    AGGRESSIVE_COMPRESSION_THRESHOLD = 1000  # KB threshold for aggressive compression

    @classmethod
    def process_image(cls, image_file, base_name=None, is_hero=False, generate_alt=True):
        """
        Advanced image processing with WebP conversion, progressive JPEG,
        and intelligent optimization.

        Args:
            image_file: Django UploadedFile or file-like object
            base_name: Base name for the processed files
            is_hero: Whether this is a hero/featured image (uses different sizes)
            generate_alt: Whether to generate alt text automatically

        Returns:
            dict: Dictionary containing all processed images and metadata
        """
        if not base_name:
            base_name = cls._generate_base_name(image_file.name)

        try:
            with Image.open(image_file) as img:
                # Extract and preserve EXIF data
                exif_data = cls._extract_exif_data(img)

                # Convert to RGB if necessary (handles transparency gracefully)
                img = cls._prepare_image_for_web(img)

                # Apply EXIF orientation
                img = ImageOps.exif_transpose(img)

                # Store original dimensions and calculate aspect ratio
                original_width, original_height = img.size
                aspect_ratio = original_width / original_height

                # Determine if we need aggressive compression
                image_file.seek(0)
                original_size_kb = len(image_file.read()) / 1024
                aggressive_compression = original_size_kb > cls.AGGRESSIVE_COMPRESSION_THRESHOLD

                processed_images = {
                    'metadata': {
                        'original_width': original_width,
                        'original_height': original_height,
                        'aspect_ratio': aspect_ratio,
                        'original_size_kb': original_size_kb,
                        'exif_data': exif_data,
                        'processed_at': cls._get_timestamp(),
                    }
                }

                # Generate alt text if requested
                if generate_alt:
                    processed_images['generated_alt'] = cls._generate_alt_text(img, exif_data, base_name)

                # Choose size sets based on image type
                size_sets = [('standard', cls.SIZES)]
                if is_hero:
                    size_sets.append(('hero', cls.HERO_SIZES))

                # Process each size set
                for set_name, sizes in size_sets:
                    for size_name, max_dimensions in sizes.items():
                        # Skip if original is significantly smaller (except thumbnails)
                        if cls._should_skip_size(original_width, original_height, max_dimensions, size_name):
                            continue

                        # Create resized version with smart cropping
                        resized_img = cls._resize_image_smart(img, max_dimensions, size_name)

                        # Generate multiple formats
                        size_key = f"{set_name}_{size_name}" if set_name != 'standard' else size_name

                        # Progressive JPEG
                        jpeg_path = cls._save_progressive_jpeg(resized_img, base_name, size_key, aggressive_compression)
                        if jpeg_path:
                            processed_images[f'{size_key}_jpg'] = jpeg_path

                        # Optimized WebP
                        webp_path = cls._save_optimized_webp(resized_img, base_name, size_key, aggressive_compression)
                        if webp_path:
                            processed_images[f'{size_key}_webp'] = webp_path

                # Generate CDN-ready metadata
                processed_images['cdn_metadata'] = cls._generate_cdn_metadata(processed_images)

                return processed_images

        except Exception as e:
            logger.error(f"Error processing image {image_file.name}: {e}")
            return {}

    @classmethod
    def _resize_image_smart(cls, img, max_dimensions, size_name):
        """
        Smart image resizing with content-aware cropping.

        Args:
            img: PIL Image object
            max_dimensions: (width, height) tuple
            size_name: Name of the size variant

        Returns:
            PIL Image: Resized image
        """
        # Thumbnails and hero images use exact cropping
        if size_name in ['thumbnail'] or size_name.startswith('hero_'):
            return ImageOps.fit(img, max_dimensions, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        else:
            # Other sizes maintain aspect ratio
            img_copy = img.copy()
            img_copy.thumbnail(max_dimensions, Image.Resampling.LANCZOS)
            return img_copy

    @classmethod
    def _save_progressive_jpeg(cls, img, base_name, size_name, aggressive=False):
        """
        Save progressive JPEG with optimized compression.

        Args:
            img: PIL Image object
            base_name: Base filename
            size_name: Size variant name
            aggressive: Whether to use aggressive compression

        Returns:
            str: Path to saved image or None if failed
        """
        try:
            filename = f"blog/images/processed/{base_name}_{size_name}.jpg"
            img_io = BytesIO()

            # Determine quality based on size and aggressiveness
            quality = cls._calculate_jpeg_quality(img.size, aggressive)

            # Save as progressive JPEG
            img.save(img_io,
                    format='JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True,
                    subsampling=0)  # Better quality

            img_io.seek(0)

            # Check file size and adjust quality if needed
            if aggressive:
                img_io = cls._optimize_file_size(img, img_io, 'JPEG', cls.MAX_FILE_SIZE_KB)

            content_file = ContentFile(img_io.getvalue())
            saved_path = default_storage.save(filename, content_file)

            return saved_path

        except Exception as e:
            logger.error(f"Error saving progressive JPEG {base_name}_{size_name}: {e}")
            return None

    @classmethod
    def _save_optimized_webp(cls, img, base_name, size_name, aggressive=False):
        """
        Save optimized WebP with advanced compression.

        Args:
            img: PIL Image object
            base_name: Base filename
            size_name: Size variant name
            aggressive: Whether to use aggressive compression

        Returns:
            str: Path to saved image or None if failed
        """
        try:
            filename = f"blog/images/processed/{base_name}_{size_name}.webp"
            img_io = BytesIO()

            # Determine quality based on size and aggressiveness
            quality = cls._calculate_webp_quality(img.size, aggressive)

            # Save as optimized WebP
            img.save(img_io,
                    format='WebP',
                    quality=quality,
                    optimize=True,
                    method=6,  # Best compression
                    lossless=False)

            img_io.seek(0)

            # Check file size and adjust quality if needed
            if aggressive:
                img_io = cls._optimize_file_size(img, img_io, 'WebP', cls.MAX_FILE_SIZE_KB)

            content_file = ContentFile(img_io.getvalue())
            saved_path = default_storage.save(filename, content_file)

            return saved_path

        except Exception as e:
            logger.error(f"Error saving optimized WebP {base_name}_{size_name}: {e}")
            return None

    @classmethod
    def cleanup_processed_images(cls, base_name):
        """
        Clean up all processed images for a given base name.
        This uses pattern matching to catch all variants including those with random suffixes.

        Args:
            base_name: Base filename to clean up
        """
        try:
            # Use the actual file system path for cleanup
            processed_dir = os.path.join(settings.MEDIA_ROOT, 'blog', 'images', 'processed')

            # Find all files that start with the base name
            pattern = os.path.join(processed_dir, f"{base_name}_*")
            matching_files = glob.glob(pattern)

            deleted_count = 0
            for file_path in matching_files:
                try:
                    # Convert file system path to storage path
                    relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                    storage_path = relative_path.replace(os.sep, '/')

                    if default_storage.exists(storage_path):
                        default_storage.delete(storage_path)
                        deleted_count += 1
                        logger.debug(f"Deleted processed image: {storage_path}")
                    elif os.path.exists(file_path):
                        # Fallback: delete directly from filesystem if storage doesn't work
                        os.remove(file_path)
                        deleted_count += 1
                        logger.debug(f"Deleted processed image (direct): {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")

            logger.info(f"Cleaned up {deleted_count} processed images for base name: {base_name}")

        except Exception as e:
            logger.error(f"Error cleaning up images for {base_name}: {e}")

    # New utility methods for advanced processing

    @classmethod
    def _generate_base_name(cls, filename):
        """Generate a clean, SEO-friendly base name from filename."""
        name = os.path.splitext(filename)[0]
        # Remove special characters and make SEO-friendly
        clean_name = slugify(name).replace('-', '_')
        # Add timestamp hash to prevent conflicts
        timestamp = cls._get_timestamp()
        hash_suffix = hashlib.md5(f"{clean_name}_{timestamp}".encode()).hexdigest()[:8]
        return f"{clean_name}_{hash_suffix}"

    @classmethod
    def _prepare_image_for_web(cls, img):
        """Prepare image for web by handling transparency and color modes."""
        if img.mode in ('RGBA', 'P'):
            # Create optimized background for transparency
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            # Use alpha compositing for better quality
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            return background
        elif img.mode != 'RGB':
            return img.convert('RGB')
        return img

    @classmethod
    def _extract_exif_data(cls, img):
        """Extract relevant EXIF data for metadata and alt text generation."""
        exif_data = {}
        try:
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                for tag_id, value in exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag in ['Make', 'Model', 'DateTime', 'Software', 'Orientation']:
                        exif_data[tag] = str(value)
        except Exception:
            pass
        return exif_data

    @classmethod
    def _generate_alt_text(cls, img, exif_data, base_name):
        """Generate intelligent alt text based on image analysis."""
        # Basic alt text generation (can be enhanced with AI/ML later)
        alt_parts = []

        # Use cleaned base name as foundation
        clean_name = base_name.replace('_', ' ').title()
        alt_parts.append(clean_name)

        # Add image characteristics
        width, height = img.size
        if width > height * 1.5:
            alt_parts.append("landscape image")
        elif height > width * 1.5:
            alt_parts.append("portrait image")
        else:
            alt_parts.append("square image")

        # Add technical info if relevant
        if exif_data.get('Make') and exif_data.get('Model'):
            alt_parts.append(f"taken with {exif_data['Make']} {exif_data['Model']}")

        return ' - '.join(alt_parts)

    @classmethod
    def _should_skip_size(cls, orig_w, orig_h, max_dims, size_name):
        """Determine if we should skip generating a particular size."""
        # Always generate thumbnails
        if size_name in ['thumbnail'] or size_name.startswith('hero_'):
            return False

        # Skip if original is much smaller than target
        return (orig_w <= max_dims[0] * 0.8 and orig_h <= max_dims[1] * 0.8)

    @classmethod
    def _calculate_jpeg_quality(cls, size, aggressive=False):
        """Calculate optimal JPEG quality based on image size."""
        width, height = size
        pixels = width * height

        if aggressive:
            if pixels > 2000000:  # > 2MP
                return 75
            elif pixels > 500000:  # > 0.5MP
                return 80
            else:
                return 85
        else:
            return cls.PROGRESSIVE_JPEG_QUALITY

    @classmethod
    def _calculate_webp_quality(cls, size, aggressive=False):
        """Calculate optimal WebP quality based on image size."""
        width, height = size
        pixels = width * height

        if aggressive:
            if pixels > 2000000:  # > 2MP
                return 70
            elif pixels > 500000:  # > 0.5MP
                return 75
            else:
                return 80
        else:
            return cls.WEBP_QUALITY

    @classmethod
    def _optimize_file_size(cls, img, img_io, format_name, target_kb):
        """Optimize file size by adjusting quality iteratively."""
        current_size_kb = len(img_io.getvalue()) / 1024

        if current_size_kb <= target_kb:
            return img_io

        # Try reducing quality iteratively
        for quality in [75, 70, 65, 60, 55, 50]:
            new_io = BytesIO()
            if format_name == 'WebP':
                img.save(new_io, format='WebP', quality=quality, optimize=True, method=6)
            else:
                img.save(new_io, format='JPEG', quality=quality, optimize=True, progressive=True)

            new_size_kb = len(new_io.getvalue()) / 1024
            if new_size_kb <= target_kb:
                return new_io

        # Return best effort if we can't reach target
        return new_io if 'new_io' in locals() else img_io

    @classmethod
    def _generate_cdn_metadata(cls, processed_images):
        """Generate CDN-ready metadata for optimized delivery."""
        metadata = {
            'formats': [],
            'sizes': [],
            'breakpoints': {},
            'preload_hints': []
        }

        # Identify available formats
        for key in processed_images.keys():
            if key.endswith('_jpg') and 'jpg' not in metadata['formats']:
                metadata['formats'].append('jpg')
            elif key.endswith('_webp') and 'webp' not in metadata['formats']:
                metadata['formats'].append('webp')

        # Map sizes to responsive breakpoints
        for size_name, (width, height) in cls.SIZES.items():
            if any(key.startswith(f"{size_name}_") for key in processed_images.keys()):
                metadata['sizes'].append(size_name)
                metadata['breakpoints'][size_name] = {'width': width, 'height': height}

        # Generate preload hints for critical images
        if any(key.startswith('hero_') for key in processed_images.keys()):
            metadata['preload_hints'].extend(['hero_md_webp', 'hero_lg_webp'])
        elif any(key.startswith('lg_') for key in processed_images.keys()):
            metadata['preload_hints'].extend(['lg_webp', 'md_webp'])

        return metadata

    @classmethod
    def _get_timestamp(cls):
        """Get current timestamp for metadata."""
        from datetime import datetime
        return datetime.now().isoformat()


def generate_srcset(base_name, format_name='webp', image_type='standard'):
    """
    Generate srcset string for responsive images with format fallback.

    Args:
        base_name: Base filename
        format_name: 'webp' or 'jpg'
        image_type: 'standard', 'hero', or 'all'

    Returns:
        str: srcset string for responsive images
    """
    srcset_parts = []

    # Determine which sizes to include
    if image_type == 'hero':
        sizes_to_check = ImageProcessor.HERO_SIZES
        prefix = 'hero_'
    elif image_type == 'all':
        sizes_to_check = {**ImageProcessor.SIZES, **ImageProcessor.HERO_SIZES}
        prefix = ''
    else:
        sizes_to_check = ImageProcessor.SIZES
        prefix = ''

    for size_name, (width, height) in sizes_to_check.items():
        # Skip thumbnail for srcset
        if size_name == 'thumbnail':
            continue

        # Build filename with proper prefix
        if image_type == 'hero' or (image_type == 'all' and size_name in ImageProcessor.HERO_SIZES):
            filename = f"blog/images/processed/{base_name}_hero_{size_name}.{format_name}"
        else:
            filename = f"blog/images/processed/{base_name}_{size_name}.{format_name}"

        if default_storage.exists(filename):
            url = default_storage.url(filename)
            srcset_parts.append(f"{url} {width}w")

    return ', '.join(srcset_parts)


def get_image_url(base_name, size='md', format_name='webp', fallback=True):
    """
    Get URL for specific image size and format with intelligent fallback.

    Args:
        base_name: Base filename
        size: Size variant name
        format_name: 'webp' or 'jpg'
        fallback: Whether to fallback to other formats/sizes

    Returns:
        str: Image URL or None if not found
    """
    # Try the requested format and size
    filename = f"blog/images/processed/{base_name}_{size}.{format_name}"
    if default_storage.exists(filename):
        return default_storage.url(filename)

    if not fallback:
        return None

    # Fallback strategy
    fallback_formats = ['webp', 'jpg'] if format_name == 'webp' else ['jpg', 'webp']
    fallback_sizes = ['md', 'lg', 'sm', 'xl', 'xs'] if size not in ['md', 'lg', 'sm', 'xl', 'xs'] else [size]

    # Try different format with same size
    for fmt in fallback_formats:
        if fmt != format_name:
            filename = f"blog/images/processed/{base_name}_{size}.{fmt}"
            if default_storage.exists(filename):
                return default_storage.url(filename)

    # Try different sizes with preferred format
    for fallback_size in fallback_sizes:
        if fallback_size != size:
            filename = f"blog/images/processed/{base_name}_{fallback_size}.{format_name}"
            if default_storage.exists(filename):
                return default_storage.url(filename)

    return None


def get_image_metadata(base_name):
    """
    Get comprehensive metadata for an image.

    Args:
        base_name: Base filename

    Returns:
        dict: Image metadata including sizes, formats, and optimization data
    """
    metadata = {
        'available_sizes': [],
        'available_formats': [],
        'srcsets': {},
        'preload_candidates': [],
        'total_variants': 0
    }

    # Check all possible combinations
    all_sizes = {**ImageProcessor.SIZES, **ImageProcessor.HERO_SIZES}
    formats = ['jpg', 'webp']

    for size_name, (width, height) in all_sizes.items():
        size_data = {'name': size_name, 'width': width, 'height': height, 'formats': []}

        for fmt in formats:
            # Check standard sizes
            filename = f"blog/images/processed/{base_name}_{size_name}.{fmt}"
            if default_storage.exists(filename):
                size_data['formats'].append(fmt)
                if fmt not in metadata['available_formats']:
                    metadata['available_formats'].append(fmt)
                metadata['total_variants'] += 1

            # Check hero sizes
            hero_filename = f"blog/images/processed/{base_name}_hero_{size_name}.{fmt}"
            if default_storage.exists(hero_filename):
                hero_size_data = {
                    'name': f'hero_{size_name}',
                    'width': width,
                    'height': height,
                    'formats': [fmt] if fmt not in size_data.get('formats', []) else size_data['formats'] + [fmt]
                }
                metadata['total_variants'] += 1

        if size_data['formats']:
            metadata['available_sizes'].append(size_data)

    # Generate srcsets for available formats
    for fmt in metadata['available_formats']:
        metadata['srcsets'][fmt] = generate_srcset(base_name, fmt)
        if any('hero_' in size['name'] for size in metadata['available_sizes']):
            metadata['srcsets'][f'{fmt}_hero'] = generate_srcset(base_name, fmt, 'hero')

    # Identify preload candidates (largest available in each format)
    for fmt in metadata['available_formats']:
        largest_size = None
        largest_pixels = 0

        for size_data in metadata['available_sizes']:
            if fmt in size_data['formats']:
                pixels = size_data['width'] * size_data['height']
                if pixels > largest_pixels:
                    largest_pixels = pixels
                    largest_size = size_data['name']

        if largest_size:
            metadata['preload_candidates'].append(f"{largest_size}.{fmt}")

    return metadata


def generate_picture_element(base_name, alt_text="", css_class="", sizes="100vw", loading="lazy"):
    """
    Generate a complete HTML picture element with WebP and JPEG fallbacks.

    Args:
        base_name: Base filename
        alt_text: Alt text for the image
        css_class: CSS classes to apply
        sizes: Sizes attribute for responsive images
        loading: Loading strategy ('lazy', 'eager', or 'auto')

    Returns:
        str: Complete HTML picture element
    """
    webp_srcset = generate_srcset(base_name, 'webp')
    jpg_srcset = generate_srcset(base_name, 'jpg')
    fallback_url = get_image_url(base_name, 'md', 'jpg')

    if not fallback_url:
        return f'<img src="" alt="{alt_text}" class="{css_class}" loading="{loading}" />'

    picture_html = f'<picture>'

    if webp_srcset:
        picture_html += f'<source srcset="{webp_srcset}" sizes="{sizes}" type="image/webp" />'

    if jpg_srcset:
        picture_html += f'<source srcset="{jpg_srcset}" sizes="{sizes}" type="image/jpeg" />'

    picture_html += f'<img src="{fallback_url}" alt="{alt_text}" class="{css_class}" loading="{loading}" />'
    picture_html += '</picture>'

    return picture_html


class AltTextManager:
    """Manage and enhance alt text for images."""

    @staticmethod
    def generate_smart_alt(image_path, context=None, user_input=None):
        """
        Generate smart alt text based on context and user input.

        Args:
            image_path: Path to the image
            context: Context information (post title, category, etc.)
            user_input: User-provided description or keywords

        Returns:
            str: Generated alt text
        """
        alt_parts = []

        # Use user input as primary source
        if user_input and user_input.strip():
            alt_parts.append(user_input.strip())
        else:
            # Extract from filename
            filename = os.path.basename(image_path)
            clean_name = os.path.splitext(filename)[0]
            clean_name = clean_name.replace('_', ' ').replace('-', ' ').title()
            alt_parts.append(clean_name)

        # Add context if available
        if context:
            if 'post_title' in context:
                alt_parts.append(f"related to {context['post_title']}")
            elif 'category' in context:
                alt_parts.append(f"in {context['category']} category")

        return ' - '.join(alt_parts)

    @staticmethod
    def validate_alt_text(alt_text):
        """
        Validate and improve alt text for accessibility.

        Args:
            alt_text: Alt text to validate

        Returns:
            dict: Validation results and suggestions
        """
        results = {
            'is_valid': True,
            'warnings': [],
            'suggestions': [],
            'score': 100
        }

        if not alt_text or not alt_text.strip():
            results['is_valid'] = False
            results['warnings'].append('Alt text is empty')
            results['score'] = 0
            return results

        alt_text = alt_text.strip()

        # Check length
        if len(alt_text) < 5:
            results['warnings'].append('Alt text is too short (< 5 characters)')
            results['score'] -= 20
        elif len(alt_text) > 125:
            results['warnings'].append('Alt text is too long (> 125 characters)')
            results['score'] -= 10

        # Check for redundant phrases
        redundant_phrases = ['image of', 'picture of', 'photo of', 'graphic of']
        for phrase in redundant_phrases:
            if phrase.lower() in alt_text.lower():
                results['suggestions'].append(f'Remove redundant phrase: "{phrase}"')
                results['score'] -= 5

        # Check for file extensions
        file_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        for ext in file_extensions:
            if ext.lower() in alt_text.lower():
                results['suggestions'].append(f'Remove file extension: "{ext}"')
                results['score'] -= 5

        return results


class ImageCDNOptimizer:
    """Optimize images for CDN delivery and performance."""

    @staticmethod
    def generate_preload_hints(image_metadata, priority='high'):
        """
        Generate preload hints for critical images.

        Args:
            image_metadata: Image metadata dict
            priority: 'high', 'medium', or 'low'

        Returns:
            list: List of preload hint HTML strings
        """
        hints = []

        if 'preload_candidates' in image_metadata:
            for candidate in image_metadata['preload_candidates'][:2]:  # Limit to 2 preloads
                size, fmt = candidate.split('.')
                url = get_image_url(image_metadata.get('base_name'), size, fmt)
                if url:
                    hints.append(
                        f'<link rel="preload" as="image" href="{url}" '
                        f'type="image/{fmt}" fetchpriority="{priority}" />'
                    )

        return hints

    @staticmethod
    def generate_responsive_sizes(breakpoints=None):
        """
        Generate sizes attribute for responsive images.

        Args:
            breakpoints: Custom breakpoints dict

        Returns:
            str: Sizes attribute value
        """
        if not breakpoints:
            breakpoints = {
                '320px': '100vw',
                '768px': '50vw',
                '1024px': '33vw',
                '1200px': '25vw'
            }

        sizes_parts = []
        for breakpoint, size in breakpoints.items():
            sizes_parts.append(f'(max-width: {breakpoint}) {size}')

        sizes_parts.append('100vw')  # Default fallback

        return ', '.join(sizes_parts)

    @staticmethod
    def calculate_critical_images(post_content, limit=3):
        """
        Identify critical images that should be prioritized for loading.

        Args:
            post_content: Post content HTML
            limit: Maximum number of critical images

        Returns:
            list: List of critical image identifiers
        """
        # This would typically parse HTML and identify:
        # 1. Featured/hero images
        # 2. Above-the-fold images
        # 3. Images in the first few paragraphs

        critical_images = []

        # For now, return a simple heuristic
        # In production, this would use HTML parsing
        if 'featured_image' in str(post_content):
            critical_images.append('featured_image')

        return critical_images[:limit]