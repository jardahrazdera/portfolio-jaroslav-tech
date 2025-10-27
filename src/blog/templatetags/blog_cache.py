"""
Template tags for blog caching operations.
"""
from django import template
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from blog.cache_service import BlogCacheService
from django.utils.safestring import mark_safe
import hashlib
import logging

logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag
def cache_fragment(fragment_name, *args, timeout=None):
    """
    Cache a template fragment with automatic invalidation.
    
    Usage:
    {% load blog_cache %}
    {% cache_fragment "expensive_operation" post.id as cached_content %}
    {% if not cached_content %}
        <!-- Expensive operation here -->
        {% cache_fragment_store "expensive_operation" post.id rendered_content %}
    {% else %}
        {{ cached_content|safe }}
    {% endif %}
    """
    if timeout is None:
        timeout = BlogCacheService.CACHE_TIMEOUT_MEDIUM
    
    # Create cache key
    key_parts = [fragment_name] + [str(arg) for arg in args]
    cache_key = BlogCacheService._make_cache_key('template_fragment', *key_parts)
    
    # Get cached content
    cached_content = cache.get(cache_key)
    return cached_content


@register.simple_tag
def cache_fragment_store(fragment_name, *args, content, timeout=None):
    """
    Store content in template fragment cache.
    
    Usage:
    {% cache_fragment_store "expensive_operation" post.id rendered_content %}
    """
    if timeout is None:
        timeout = BlogCacheService.CACHE_TIMEOUT_MEDIUM
    
    # Create cache key
    key_parts = [fragment_name] + [str(arg) for arg in args[:-1]]  # Exclude content from args
    cache_key = BlogCacheService._make_cache_key('template_fragment', *key_parts)
    
    # Store content
    cache.set(cache_key, content, timeout)
    logger.debug(f"Cached template fragment: {cache_key}")
    
    return content


@register.inclusion_tag('blog/fragments/cached_post_card.html')
def cached_post_card(post, cache_timeout=None):
    """
    Render a post card with caching.
    
    Usage:
    {% load blog_cache %}
    {% cached_post_card post %}
    """
    if cache_timeout is None:
        cache_timeout = BlogCacheService.CACHE_TIMEOUT_LONG
    
    cache_key = BlogCacheService._make_cache_key('post_card', post.slug)
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        # Prepare post data for template
        cached_data = {
            'post': post,
            'categories': post.categories.all(),
            'reading_time': post.reading_time,
            'view_count': post.view_count,
        }
        cache.set(cache_key, cached_data, cache_timeout)
        logger.debug(f"Cached post card: {post.slug}")
    
    return cached_data


@register.inclusion_tag('blog/fragments/cached_category_list.html')
def cached_category_list(cache_timeout=None):
    """
    Render category list with caching.
    
    Usage:
    {% load blog_cache %}
    {% cached_category_list %}
    """
    if cache_timeout is None:
        cache_timeout = BlogCacheService.CACHE_TIMEOUT_VERY_LONG
    
    cached_data = BlogCacheService.get_cached_categories_with_counts()
    
    if not cached_data:
        # Fallback to database
        from blog.models import Category
        from django.db.models import Count, Q
        
        categories = Category.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=Q(post__is_published=True))
        ).distinct().order_by('name')
        
        BlogCacheService.cache_categories_with_counts(categories)
        cached_data = {'categories': categories}
    
    return cached_data


@register.inclusion_tag('blog/fragments/cached_tag_cloud.html')
def cached_tag_cloud(limit=20, cache_timeout=None):
    """
    Render tag cloud with caching.
    
    Usage:
    {% load blog_cache %}
    {% cached_tag_cloud limit=30 %}
    """
    if cache_timeout is None:
        cache_timeout = BlogCacheService.CACHE_TIMEOUT_VERY_LONG
    
    cache_key = BlogCacheService._make_cache_key('tag_cloud', limit=limit)
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        from blog.models import Tag
        from django.db.models import Count, Q
        
        tags = Tag.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=Q(post__is_published=True))
        ).distinct().order_by('-post_count', 'name')[:limit]
        
        cached_data = {'tags': tags, 'limit': limit}
        cache.set(cache_key, cached_data, cache_timeout)
        logger.debug(f"Cached tag cloud: {limit} tags")
    
    return cached_data


@register.simple_tag
def cached_popular_posts(period='month', limit=5):
    """
    Get popular posts with caching.
    
    Usage:
    {% load blog_cache %}
    {% cached_popular_posts period='week' limit=10 as popular_posts %}
    """
    cached_data = BlogCacheService.get_cached_popular_posts(period)
    
    if cached_data:
        # Return limited results from cache
        posts = cached_data['posts'][:limit]
        return posts
    
    # Fallback to database
    try:
        from blog.models import PostView
        popular_posts = PostView.get_popular_posts(period=period, limit=limit)
        
        # Cache the results
        BlogCacheService.cache_popular_posts(popular_posts, period)
        return popular_posts
    except Exception as e:
        logger.warning(f"Could not get popular posts: {e}")
        return []


@register.simple_tag
def cached_related_posts(post, limit=4):
    """
    Get related posts with caching.
    
    Usage:
    {% load blog_cache %}
    {% cached_related_posts post limit=6 as related_posts %}
    """
    cached_data = BlogCacheService.get_cached_related_posts(post.slug, limit)
    
    if cached_data:
        return cached_data['posts'][:limit]
    
    # Fallback to database
    try:
        related_data = post.get_related_posts(count=limit)
        related_posts = related_data['posts']
        
        # Cache the results
        BlogCacheService.cache_related_posts(post.slug, related_posts)
        return related_posts[:limit]
    except Exception as e:
        logger.warning(f"Could not get related posts for {post.slug}: {e}")
        return []


@register.filter
def cache_bust(url, post=None):
    """
    Add cache busting parameter to URLs based on content modification time.
    
    Usage:
    {{ post.featured_image.url|cache_bust:post }}
    """
    if not url:
        return url
    
    # Use post's updated_at timestamp as cache buster
    if post and hasattr(post, 'updated_at'):
        timestamp = int(post.updated_at.timestamp())
    else:
        # Fallback to current time (less efficient but works)
        import time
        timestamp = int(time.time())
    
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}v={timestamp}"


@register.simple_tag
def cache_key_debug(prefix, *args):
    """
    Debug template tag to show what cache key would be generated.
    Only works in DEBUG mode.
    
    Usage:
    {% load blog_cache %}
    {% cache_key_debug "post_detail" post.slug %}
    """
    from django.conf import settings
    
    if not settings.DEBUG:
        return ''
    
    cache_key = BlogCacheService._make_cache_key(prefix, *args)
    return mark_safe(f'<!-- Cache key: {cache_key} -->')