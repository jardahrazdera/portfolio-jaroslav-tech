"""
Django signals for automatic cache invalidation and file cleanup when blog content changes.
"""
import os
from django.db.models.signals import post_save, post_delete, m2m_changed, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from django.core.files.storage import default_storage
from .models import Post, Category, Tag, BlogFile
from .cache_service import BlogCacheService
from .image_utils import ImageProcessor
from .image_utils_enhanced import ImageProcessor as EnhancedImageProcessor
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Post)
def invalidate_post_caches_on_save(sender, instance, created, **kwargs):
    """
    Invalidate caches when a post is saved.

    This handles:
    - New post creation
    - Post updates (title, content, publication status, etc.)
    - Featured status changes
    """
    logger.info(f"Post {'created' if created else 'updated'}: {instance.title}")

    # Always invalidate post-specific caches
    BlogCacheService.invalidate_post_caches(instance.slug)

    # If post was published/unpublished or featured status changed, invalidate lists
    if created or instance.is_published or getattr(instance, '_was_published', False):
        BlogCacheService.invalidate_list_caches()
        logger.debug(f"Invalidated list caches due to post publication status change")

    # If this is a featured post, invalidate featured posts cache specifically
    if instance.is_featured:
        featured_cache_key = BlogCacheService._make_cache_key(
            BlogCacheService.FEATURED_POSTS_PREFIX
        )
        cache.delete(featured_cache_key)
        logger.debug(f"Invalidated featured posts cache")


@receiver(post_delete, sender=Post)
def invalidate_post_caches_on_delete(sender, instance, **kwargs):
    """
    Invalidate caches and clean up files when a post is deleted.
    """
    logger.info(f"Post deleted: {instance.title}")

    # Invalidate post-specific caches
    BlogCacheService.invalidate_post_caches(instance.slug)

    # Invalidate list caches since post counts will change
    BlogCacheService.invalidate_list_caches()

    # Clean up files associated with this post
    cleanup_post_files_on_delete(sender, instance, **kwargs)


@receiver(m2m_changed, sender=Post.categories.through)
def invalidate_category_caches_on_change(sender, instance, action, pk_set, **kwargs):
    """
    Invalidate caches when post-category relationships change.
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        logger.info(f"Post categories changed for: {instance.title}")

        # Invalidate post-specific caches
        BlogCacheService.invalidate_post_caches(instance.slug)

        # Invalidate category caches
        categories_cache_key = BlogCacheService._make_cache_key(
            BlogCacheService.CATEGORIES_PREFIX, 'with_counts'
        )
        cache.delete(categories_cache_key)

        # Invalidate list caches
        BlogCacheService.invalidate_list_caches()

        logger.debug(f"Invalidated category-related caches")


@receiver(m2m_changed, sender=Post.tags.through)
def invalidate_tag_caches_on_change(sender, instance, action, pk_set, **kwargs):
    """
    Invalidate caches when post-tag relationships change.
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        logger.info(f"Post tags changed for: {instance.title}")

        # Invalidate post-specific caches
        BlogCacheService.invalidate_post_caches(instance.slug)

        # Invalidate tag caches
        tags_cache_key = BlogCacheService._make_cache_key(
            BlogCacheService.TAGS_PREFIX, 'with_counts'
        )
        cache.delete(tags_cache_key)

        # Invalidate list caches
        BlogCacheService.invalidate_list_caches()

        logger.debug(f"Invalidated tag-related caches")


@receiver(post_save, sender=Category)
def invalidate_category_caches_on_category_save(sender, instance, created, **kwargs):
    """
    Invalidate caches when a category is created or updated.
    """
    logger.info(f"Category {'created' if created else 'updated'}: {instance.name}")

    # Invalidate category caches
    categories_cache_key = BlogCacheService._make_cache_key(
        BlogCacheService.CATEGORIES_PREFIX, 'with_counts'
    )
    cache.delete(categories_cache_key)

    # If category slug changed, invalidate related list caches
    if not created:
        BlogCacheService.invalidate_list_caches()

    logger.debug(f"Invalidated category caches")


@receiver(post_delete, sender=Category)
def invalidate_category_caches_on_category_delete(sender, instance, **kwargs):
    """
    Invalidate caches when a category is deleted.
    """
    logger.info(f"Category deleted: {instance.name}")

    # Invalidate all related caches
    categories_cache_key = BlogCacheService._make_cache_key(
        BlogCacheService.CATEGORIES_PREFIX, 'with_counts'
    )
    cache.delete(categories_cache_key)

    BlogCacheService.invalidate_list_caches()


@receiver(post_save, sender=Tag)
def invalidate_tag_caches_on_tag_save(sender, instance, created, **kwargs):
    """
    Invalidate caches when a tag is created or updated.
    """
    logger.info(f"Tag {'created' if created else 'updated'}: {instance.name}")

    # Invalidate tag caches
    tags_cache_key = BlogCacheService._make_cache_key(
        BlogCacheService.TAGS_PREFIX, 'with_counts'
    )
    cache.delete(tags_cache_key)

    # If tag slug changed, invalidate related list caches
    if not created:
        BlogCacheService.invalidate_list_caches()

    logger.debug(f"Invalidated tag caches")


@receiver(post_delete, sender=Tag)
def invalidate_tag_caches_on_tag_delete(sender, instance, **kwargs):
    """
    Invalidate caches when a tag is deleted.
    """
    logger.info(f"Tag deleted: {instance.name}")

    # Invalidate all related caches
    tags_cache_key = BlogCacheService._make_cache_key(
        BlogCacheService.TAGS_PREFIX, 'with_counts'
    )
    cache.delete(tags_cache_key)

    BlogCacheService.invalidate_list_caches()


def track_field_changes(sender, instance, **kwargs):
    """
    Track field changes for better cache invalidation decisions.
    This is a helper to track what fields actually changed.
    """
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._was_published = old_instance.is_published
            instance._was_featured = old_instance.is_featured
            instance._old_slug = old_instance.slug
        except sender.DoesNotExist:
            instance._was_published = False
            instance._was_featured = False
            instance._old_slug = None


# File cleanup signal handlers

def cleanup_old_featured_image(sender, instance, **kwargs):
    """
    Clean up old featured image files when a post's featured image is changed.
    This runs before the new image is saved.
    """
    if not instance.pk:
        return  # New instance, no cleanup needed

    try:
        old_post = Post.objects.get(pk=instance.pk)
        old_image = old_post.featured_image
        new_image = instance.featured_image

        # Check if the featured image has changed
        if old_image and old_image != new_image:
            logger.info(f"Featured image changed for post {instance.pk}: {old_image.name} -> {new_image.name if new_image else 'None'}")

            # Clean up old processed images
            old_base_name = old_post.get_image_base_name()
            if old_base_name:
                logger.info(f"Cleaning up processed images for base name: {old_base_name}")
                ImageProcessor.cleanup_processed_images(old_base_name)
                EnhancedImageProcessor.cleanup_processed_images(old_base_name)

            # Delete the original file
            if old_image and default_storage.exists(old_image.name):
                try:
                    default_storage.delete(old_image.name)
                    logger.info(f"Deleted original image file: {old_image.name}")
                except Exception as e:
                    logger.error(f"Failed to delete original image {old_image.name}: {e}")

    except Post.DoesNotExist:
        pass  # Post doesn't exist yet
    except Exception as e:
        logger.error(f"Error in cleanup_old_featured_image for post {instance.pk}: {e}")


def cleanup_post_files_on_delete(sender, instance, **kwargs):
    """
    Clean up all files associated with a post when it's deleted.
    This includes featured images, processed images, and file attachments.
    """
    logger.info(f"Cleaning up files for deleted post: {instance.title} (ID: {instance.pk})")

    # Clean up featured image and its processed variants
    if instance.featured_image:
        # Clean up processed images
        base_name = instance.get_image_base_name()
        if base_name:
            logger.info(f"Cleaning up processed images for base name: {base_name}")
            ImageProcessor.cleanup_processed_images(base_name)
            EnhancedImageProcessor.cleanup_processed_images(base_name)

        # Delete the original featured image
        if default_storage.exists(instance.featured_image.name):
            try:
                default_storage.delete(instance.featured_image.name)
                logger.info(f"Deleted featured image: {instance.featured_image.name}")
            except Exception as e:
                logger.error(f"Failed to delete featured image {instance.featured_image.name}: {e}")

    # Note: BlogFile attachments have their own cleanup in their delete method
    logger.info(f"File cleanup completed for post: {instance.title}")


@receiver(post_delete, sender=BlogFile)
def cleanup_blog_file_on_delete(sender, instance, **kwargs):
    """
    Clean up file when BlogFile instance is deleted.
    This is a safety net in addition to BlogFile.delete() method.
    """
    if instance.file and default_storage.exists(instance.file.name):
        try:
            default_storage.delete(instance.file.name)
            logger.info(f"Deleted blog file: {instance.file.name}")
        except Exception as e:
            logger.error(f"Failed to delete blog file {instance.file.name}: {e}")


# Connect the field change tracking to pre_save signal

@receiver(pre_save, sender=Post)
def track_post_changes(sender, instance, **kwargs):
    """Track Post field changes before saving and handle image cleanup."""
    track_field_changes(sender, instance, **kwargs)
    # Also handle featured image cleanup when changed
    cleanup_old_featured_image(sender, instance, **kwargs)


# Utility functions for file management

def cleanup_orphaned_files():
    """
    Utility function to clean up orphaned files.
    This can be called manually or from management commands.
    """
    orphaned_count = 0

    # Clean up orphaned featured images
    try:
        # Get all featured image paths from existing posts
        existing_posts = Post.objects.filter(featured_image__isnull=False)
        used_images = set()

        for post in existing_posts:
            if post.featured_image:
                used_images.add(post.featured_image.name)

        # List all files in the blog images directory
        try:
            if default_storage.exists('blog/images/'):
                dirs, files = default_storage.listdir('blog/images/')

                for filename in files:
                    file_path = f'blog/images/{filename}'
                    if file_path not in used_images:
                        # This is an orphaned file
                        try:
                            default_storage.delete(file_path)
                            logger.info(f"Deleted orphaned image: {file_path}")
                            orphaned_count += 1
                        except Exception as e:
                            logger.error(f"Failed to delete orphaned image {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error listing blog images directory: {e}")

    except Exception as e:
        logger.error(f"Error in orphaned featured images cleanup: {e}")

    # Clean up orphaned processed images
    try:
        # Get all valid base names from existing posts
        valid_base_names = set()
        for post in Post.objects.filter(featured_image__isnull=False):
            base_name = post.get_image_base_name()
            if base_name:
                valid_base_names.add(base_name)

        # List all files in the processed images directory
        try:
            if default_storage.exists('blog/images/processed/'):
                dirs, files = default_storage.listdir('blog/images/processed/')

                for filename in files:
                    # Extract base name from processed filename
                    # Format: base_name_size.format
                    name_parts = filename.rsplit('_', 1)
                    if len(name_parts) == 2:
                        potential_base = name_parts[0]
                        if potential_base not in valid_base_names:
                            # This is an orphaned processed file
                            file_path = f'blog/images/processed/{filename}'
                            try:
                                default_storage.delete(file_path)
                                logger.info(f"Deleted orphaned processed image: {file_path}")
                                orphaned_count += 1
                            except Exception as e:
                                logger.error(f"Failed to delete orphaned processed image {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error listing processed images directory: {e}")

    except Exception as e:
        logger.error(f"Error in orphaned processed images cleanup: {e}")

    # Clean up orphaned blog files
    try:
        # Get all file paths from existing BlogFile instances
        existing_files = BlogFile.objects.all()
        used_files = set()

        for blog_file in existing_files:
            if blog_file.file:
                used_files.add(blog_file.file.name)

        # List all files in the blog files directory
        try:
            # Check if directory exists first
            if default_storage.exists('blog/files/'):
                dirs, files = default_storage.listdir('blog/files/')

                # Also check subdirectories
                all_files = []
                for filename in files:
                    all_files.append(f'blog/files/{filename}')

                for dirname in dirs:
                    try:
                        subdirs, subfiles = default_storage.listdir(f'blog/files/{dirname}/')
                        for subfile in subfiles:
                            all_files.append(f'blog/files/{dirname}/{subfile}')
                    except Exception:
                        pass

                for file_path in all_files:
                    if file_path not in used_files:
                        # This is an orphaned file
                        try:
                            default_storage.delete(file_path)
                            logger.info(f"Deleted orphaned blog file: {file_path}")
                            orphaned_count += 1
                        except Exception as e:
                            logger.error(f"Failed to delete orphaned blog file {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error listing blog files directory: {e}")

    except Exception as e:
        logger.error(f"Error in orphaned blog files cleanup: {e}")

    logger.info(f"Orphaned files cleanup completed. Removed {orphaned_count} files.")
    return orphaned_count


def get_storage_stats():
    """
    Get statistics about file storage usage.
    """
    stats = {
        'featured_images': {'count': 0, 'size': 0},
        'processed_images': {'count': 0, 'size': 0},
        'blog_files': {'count': 0, 'size': 0},
        'total_size': 0
    }

    # Count featured images
    try:
        if default_storage.exists('blog/images/'):
            dirs, files = default_storage.listdir('blog/images/')
            stats['featured_images']['count'] = len(files)

            for filename in files:
                try:
                    file_path = f'blog/images/{filename}'
                    if hasattr(default_storage, 'size'):
                        file_size = default_storage.size(file_path)
                        stats['featured_images']['size'] += file_size
                except Exception:
                    pass
    except Exception:
        pass

    # Count processed images
    try:
        if default_storage.exists('blog/images/processed/'):
            dirs, files = default_storage.listdir('blog/images/processed/')
            stats['processed_images']['count'] = len(files)

            for filename in files:
                try:
                    file_path = f'blog/images/processed/{filename}'
                    if hasattr(default_storage, 'size'):
                        file_size = default_storage.size(file_path)
                        stats['processed_images']['size'] += file_size
                except Exception:
                    pass
    except Exception:
        pass

    # Count blog files
    try:
        if default_storage.exists('blog/files/'):
            dirs, files = default_storage.listdir('blog/files/')
            all_files = list(files)

            # Also count files in subdirectories
            for dirname in dirs:
                try:
                    subdirs, subfiles = default_storage.listdir(f'blog/files/{dirname}/')
                    all_files.extend(subfiles)
                except Exception:
                    pass

            stats['blog_files']['count'] = len(all_files)

            for filename in files:
                try:
                    file_path = f'blog/files/{filename}'
                    if hasattr(default_storage, 'size'):
                        file_size = default_storage.size(file_path)
                        stats['blog_files']['size'] += file_size
                except Exception:
                    pass
    except Exception:
        pass

    # Calculate total size
    stats['total_size'] = (
        stats['featured_images']['size'] +
        stats['processed_images']['size'] +
        stats['blog_files']['size']
    )

    return stats


def format_file_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"