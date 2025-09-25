"""
Django signals for automatic cache invalidation when blog content changes.
"""
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Post, Category, Tag
from .cache_service import BlogCacheService
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
    Invalidate caches when a post is deleted.
    """
    logger.info(f"Post deleted: {instance.title}")

    # Invalidate post-specific caches
    BlogCacheService.invalidate_post_caches(instance.slug)

    # Invalidate list caches since post counts will change
    BlogCacheService.invalidate_list_caches()


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


# Connect the field change tracking to pre_save signal
from django.db.models.signals import pre_save

@receiver(pre_save, sender=Post)
def track_post_changes(sender, instance, **kwargs):
    """Track Post field changes before saving."""
    track_field_changes(sender, instance, **kwargs)