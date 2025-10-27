"""
Image processing utilities for blog images.
Handles resizing, optimization, and WebP conversion.
"""
import os
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from io import BytesIO


class ImageProcessor:
    """Handle image processing operations for blog images."""

    # Define standard sizes for responsive images
    SIZES = {
        'thumbnail': (150, 150),
        'small': (400, 300),
        'medium': (800, 600),
        'large': (1200, 900),
        'xl': (1920, 1440),
    }

    # Image quality settings
    JPEG_QUALITY = 85
    WEBP_QUALITY = 80

    @classmethod
    def process_image(cls, image_file, base_name=None):
        """
        Process an uploaded image to create multiple sizes and formats.

        Args:
            image_file: Django UploadedFile or file-like object
            base_name: Base name for the processed files

        Returns:
            dict: Dictionary containing paths to all processed images
        """
        if not base_name:
            base_name = os.path.splitext(image_file.name)[0]

        # Open and process the image
        try:
            with Image.open(image_file) as img:
                # Convert to RGB if necessary (handles RGBA, P mode images)
                if img.mode in ('RGBA', 'P'):
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                # Apply EXIF orientation
                img = ImageOps.exif_transpose(img)

                # Store original dimensions
                original_width, original_height = img.size

                processed_images = {}

                # Create different sizes
                for size_name, max_dimensions in cls.SIZES.items():
                    # Skip if original is smaller than target size
                    if (original_width <= max_dimensions[0] and
                        original_height <= max_dimensions[1] and
                        size_name != 'thumbnail'):
                        continue

                    # Create resized version
                    resized_img = cls._resize_image(img, max_dimensions, size_name == 'thumbnail')

                    # Save as JPEG
                    jpeg_path = cls._save_image(resized_img, base_name, size_name, 'jpg')
                    if jpeg_path:
                        processed_images[f'{size_name}_jpg'] = jpeg_path

                    # Save as WebP
                    webp_path = cls._save_image(resized_img, base_name, size_name, 'webp')
                    if webp_path:
                        processed_images[f'{size_name}_webp'] = webp_path

                return processed_images

        except Exception as e:
            # Log error in production
            print(f"Error processing image {image_file.name}: {e}")
            return {}

    @classmethod
    def _resize_image(cls, img, max_dimensions, crop_to_fit=False):
        """
        Resize image while maintaining aspect ratio.

        Args:
            img: PIL Image object
            max_dimensions: (width, height) tuple
            crop_to_fit: If True, crop to exact dimensions (for thumbnails)

        Returns:
            PIL Image: Resized image
        """
        if crop_to_fit:
            # For thumbnails, crop to exact dimensions
            return ImageOps.fit(img, max_dimensions, Image.Resampling.LANCZOS)
        else:
            # For other sizes, maintain aspect ratio
            img.thumbnail(max_dimensions, Image.Resampling.LANCZOS)
            return img

    @classmethod
    def _save_image(cls, img, base_name, size_name, format_name):
        """
        Save processed image to storage.

        Args:
            img: PIL Image object
            base_name: Base filename
            size_name: Size variant name
            format_name: 'jpg' or 'webp'

        Returns:
            str: Path to saved image or None if failed
        """
        try:
            # Create filename
            filename = f"blog/images/processed/{base_name}_{size_name}.{format_name}"

            # Prepare image data
            img_io = BytesIO()

            if format_name.lower() == 'webp':
                img.save(img_io, format='WebP', quality=cls.WEBP_QUALITY, optimize=True)
            else:
                img.save(img_io, format='JPEG', quality=cls.JPEG_QUALITY, optimize=True)

            img_io.seek(0)

            # Save to storage
            content_file = ContentFile(img_io.getvalue())
            saved_path = default_storage.save(filename, content_file)

            return saved_path

        except Exception as e:
            print(f"Error saving image {base_name}_{size_name}.{format_name}: {e}")
            return None

    @classmethod
    def cleanup_processed_images(cls, base_name):
        """
        Clean up all processed images for a given base name.

        Args:
            base_name: Base filename to clean up
        """
        try:
            for size_name in cls.SIZES.keys():
                for format_name in ['jpg', 'webp']:
                    filename = f"blog/images/processed/{base_name}_{size_name}.{format_name}"
                    if default_storage.exists(filename):
                        default_storage.delete(filename)
        except Exception as e:
            print(f"Error cleaning up images for {base_name}: {e}")


def generate_srcset(base_name, format_name='jpg'):
    """
    Generate srcset string for responsive images.

    Args:
        base_name: Base filename
        format_name: 'jpg' or 'webp'

    Returns:
        str: srcset string for responsive images
    """
    srcset_parts = []

    for size_name, (width, height) in ImageProcessor.SIZES.items():
        if size_name == 'thumbnail':
            continue

        filename = f"blog/images/processed/{base_name}_{size_name}.{format_name}"
        if default_storage.exists(filename):
            url = default_storage.url(filename)
            srcset_parts.append(f"{url} {width}w")

    return ', '.join(srcset_parts)


def get_image_url(base_name, size='medium', format_name='jpg'):
    """
    Get URL for specific image size and format.

    Args:
        base_name: Base filename
        size: Size variant name
        format_name: 'jpg' or 'webp'

    Returns:
        str: Image URL or None if not found
    """
    filename = f"blog/images/processed/{base_name}_{size}.{format_name}"
    if default_storage.exists(filename):
        return default_storage.url(filename)
    return None