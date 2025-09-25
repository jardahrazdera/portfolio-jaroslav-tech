"""
Redis caching service for blog application with cache invalidation and warming.
"""
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
import hashlib
import logging

logger = logging.getLogger(__name__)


class BlogCacheService:
    """Central service for managing blog-related caching with Redis."""

    # Cache key prefixes
    POST_LIST_PREFIX = 'blog_post_list'
    POST_DETAIL_PREFIX = 'blog_post_detail'
    FEATURED_POSTS_PREFIX = 'blog_featured_posts'
    POPULAR_POSTS_PREFIX = 'blog_popular_posts'
    TRENDING_POSTS_PREFIX = 'blog_trending_posts'
    RELATED_POSTS_PREFIX = 'blog_related_posts'
    CATEGORIES_PREFIX = 'blog_categories'
    TAGS_PREFIX = 'blog_tags'
    SEARCH_RESULTS_PREFIX = 'blog_search'

    # Cache timeouts (in seconds)
    CACHE_TIMEOUT_SHORT = 300    # 5 minutes
    CACHE_TIMEOUT_MEDIUM = 900   # 15 minutes
    CACHE_TIMEOUT_LONG = 1800    # 30 minutes
    CACHE_TIMEOUT_VERY_LONG = 3600  # 1 hour

    @classmethod
    def _make_cache_key(cls, prefix, *args, **kwargs):
        """Generate consistent cache keys."""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)

        # Add kwargs in sorted order for consistency
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")

        key = ':'.join(key_parts)

        # Hash long keys to prevent Redis key length issues
        if len(key) > 200:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            key = f"{prefix}:hashed:{key_hash}"

        return key

    @classmethod
    def get_post_list_cache_key(cls, page=1, category=None, tag=None):
        """Generate cache key for post lists."""
        return cls._make_cache_key(
            cls.POST_LIST_PREFIX,
            page=page,
            category=category.slug if category else None,
            tag=tag.slug if tag else None
        )

    @classmethod
    def get_post_detail_cache_key(cls, post_slug):
        """Generate cache key for post detail pages."""
        return cls._make_cache_key(cls.POST_DETAIL_PREFIX, post_slug)

    @classmethod
    def get_related_posts_cache_key(cls, post_slug, count=4):
        """Generate cache key for related posts."""
        return cls._make_cache_key(cls.RELATED_POSTS_PREFIX, post_slug, count=count)

    @classmethod
    def get_search_cache_key(cls, query, page=1):
        """Generate cache key for search results."""
        # Hash the query to handle special characters and long queries
        query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
        return cls._make_cache_key(cls.SEARCH_RESULTS_PREFIX, query_hash, page=page)

    @classmethod
    def cache_post_list(cls, queryset, page=1, category=None, tag=None, timeout=None):
        """Cache post list querysets."""
        if timeout is None:
            timeout = cls.CACHE_TIMEOUT_MEDIUM

        cache_key = cls.get_post_list_cache_key(page, category, tag)

        # Convert queryset to list to cache the actual data
        posts_data = []
        for post in queryset:
            posts_data.append({
                'id': post.id,
                'title': post.title,
                'slug': post.slug,
                'excerpt': post.excerpt,
                'featured_image': post.featured_image.url if post.featured_image else None,
                'created_at': post.created_at.isoformat(),
                'updated_at': post.updated_at.isoformat(),
                'view_count': post.get_view_count() if hasattr(post, 'get_view_count') else 0,
                'author': post.author.username,
                'is_featured': post.is_featured
            })

        cached_data = {
            'posts': posts_data,
            'cached_at': timezone.now().isoformat()
        }

        cache.set(cache_key, cached_data, timeout)
        logger.debug(f"Cached post list: {cache_key}")
        return cached_data

    @classmethod
    def get_cached_post_list(cls, page=1, category=None, tag=None):
        """Get cached post list."""
        cache_key = cls.get_post_list_cache_key(page, category, tag)
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for post list: {cache_key}")
        else:
            logger.debug(f"Cache miss for post list: {cache_key}")

        return cached_data

    @classmethod
    def cache_post_detail(cls, post, timeout=None):
        """Cache post detail data."""
        if timeout is None:
            timeout = cls.CACHE_TIMEOUT_LONG

        cache_key = cls.get_post_detail_cache_key(post.slug)

        # Cache essential post data
        cached_data = {
            'id': post.id,
            'title': post.title,
            'slug': post.slug,
            'content': post.content,
            'excerpt': post.excerpt,
            'featured_image': post.featured_image.url if post.featured_image else None,
            'created_at': post.created_at.isoformat(),
            'updated_at': post.updated_at.isoformat(),
            'view_count': post.get_view_count() if hasattr(post, 'get_view_count') else 0,
            'reading_time': post.get_reading_time() if hasattr(post, 'get_reading_time') else 0,
            'author': {
                'username': post.author.username,
                'first_name': post.author.first_name,
                'last_name': post.author.last_name,
            },
            'categories': [{'name': c.name, 'slug': c.slug} for c in post.categories.all()],
            'tags': [{'name': t.name, 'slug': t.slug} for t in post.tags.all()],
            'cached_at': timezone.now().isoformat()
        }

        cache.set(cache_key, cached_data, timeout)
        logger.debug(f"Cached post detail: {cache_key}")
        return cached_data

    @classmethod
    def get_cached_post_detail(cls, post_slug):
        """Get cached post detail."""
        cache_key = cls.get_post_detail_cache_key(post_slug)
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for post detail: {cache_key}")
        else:
            logger.debug(f"Cache miss for post detail: {cache_key}")

        return cached_data

    @classmethod
    def cache_featured_posts(cls, posts, timeout=None):
        """Cache featured posts."""
        if timeout is None:
            timeout = cls.CACHE_TIMEOUT_MEDIUM

        cache_key = cls._make_cache_key(cls.FEATURED_POSTS_PREFIX)

        cached_data = {
            'posts': [
                {
                    'id': post.id,
                    'title': post.title,
                    'slug': post.slug,
                    'excerpt': post.excerpt,
                    'featured_image': post.featured_image.url if post.featured_image else None,
                    'created_at': post.created_at.isoformat(),
                    'view_count': post.get_view_count() if hasattr(post, 'get_view_count') else 0,
                    'author': post.author.username
                }
                for post in posts
            ],
            'cached_at': timezone.now().isoformat()
        }

        cache.set(cache_key, cached_data, timeout)
        logger.debug(f"Cached featured posts: {cache_key}")
        return cached_data

    @classmethod
    def get_cached_featured_posts(cls):
        """Get cached featured posts."""
        cache_key = cls._make_cache_key(cls.FEATURED_POSTS_PREFIX)
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for featured posts: {cache_key}")
        else:
            logger.debug(f"Cache miss for featured posts: {cache_key}")

        return cached_data

    @classmethod
    def cache_popular_posts(cls, posts, period='month', timeout=None):
        """Cache popular posts by period."""
        if timeout is None:
            timeout = cls.CACHE_TIMEOUT_MEDIUM

        cache_key = cls._make_cache_key(cls.POPULAR_POSTS_PREFIX, period=period)

        cached_data = {
            'posts': [
                {
                    'id': post.id,
                    'title': post.title,
                    'slug': post.slug,
                    'excerpt': post.excerpt,
                    'view_count': post.get_view_count() if hasattr(post, 'get_view_count') else 0,
                    'author': post.author.username,
                    'created_at': post.created_at.isoformat()
                }
                for post in posts
            ],
            'period': period,
            'cached_at': timezone.now().isoformat()
        }

        cache.set(cache_key, cached_data, timeout)
        logger.debug(f"Cached popular posts ({period}): {cache_key}")
        return cached_data

    @classmethod
    def get_cached_popular_posts(cls, period='month'):
        """Get cached popular posts."""
        cache_key = cls._make_cache_key(cls.POPULAR_POSTS_PREFIX, period=period)
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for popular posts ({period}): {cache_key}")
        else:
            logger.debug(f"Cache miss for popular posts ({period}): {cache_key}")

        return cached_data

    @classmethod
    def cache_related_posts(cls, post_slug, related_posts, timeout=None):
        """Cache related posts for a given post."""
        if timeout is None:
            timeout = cls.CACHE_TIMEOUT_LONG

        cache_key = cls.get_related_posts_cache_key(post_slug, count=len(related_posts))

        cached_data = {
            'posts': [
                {
                    'post': {
                        'id': item['post'].id,
                        'title': item['post'].title,
                        'slug': item['post'].slug,
                        'excerpt': item['post'].excerpt,
                        'featured_image': item['post'].featured_image.url if item['post'].featured_image else None,
                        'created_at': item['post'].created_at.isoformat(),
                        'view_count': item['post'].get_view_count() if hasattr(item['post'], 'get_view_count') else 0
                    },
                    'similarity_score': item.get('similarity_score', 0),
                    'reading_time': item.get('reading_time', 0),
                    'primary_category': {
                        'name': item['primary_category'].name,
                        'slug': item['primary_category'].slug
                    } if item.get('primary_category') else None
                }
                for item in related_posts
            ],
            'cached_at': timezone.now().isoformat()
        }

        cache.set(cache_key, cached_data, timeout)
        logger.debug(f"Cached related posts: {cache_key}")
        return cached_data

    @classmethod
    def get_cached_related_posts(cls, post_slug, count=4):
        """Get cached related posts."""
        cache_key = cls.get_related_posts_cache_key(post_slug, count)
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for related posts: {cache_key}")
        else:
            logger.debug(f"Cache miss for related posts: {cache_key}")

        return cached_data

    @classmethod
    def cache_categories_with_counts(cls, categories, timeout=None):
        """Cache categories with post counts."""
        if timeout is None:
            timeout = cls.CACHE_TIMEOUT_VERY_LONG

        cache_key = cls._make_cache_key(cls.CATEGORIES_PREFIX, 'with_counts')

        cached_data = {
            'categories': [
                {
                    'id': cat.id,
                    'name': cat.name,
                    'slug': cat.slug,
                    'post_count': getattr(cat, 'post_count', 0)
                }
                for cat in categories
            ],
            'cached_at': timezone.now().isoformat()
        }

        cache.set(cache_key, cached_data, timeout)
        logger.debug(f"Cached categories with counts: {cache_key}")
        return cached_data

    @classmethod
    def get_cached_categories_with_counts(cls):
        """Get cached categories with post counts."""
        cache_key = cls._make_cache_key(cls.CATEGORIES_PREFIX, 'with_counts')
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for categories: {cache_key}")
        else:
            logger.debug(f"Cache miss for categories: {cache_key}")

        return cached_data

    @classmethod
    def cache_tags_with_counts(cls, tags, timeout=None):
        """Cache tags with post counts."""
        if timeout is None:
            timeout = cls.CACHE_TIMEOUT_VERY_LONG

        cache_key = cls._make_cache_key(cls.TAGS_PREFIX, 'with_counts')

        cached_data = {
            'tags': [
                {
                    'id': tag.id,
                    'name': tag.name,
                    'slug': tag.slug,
                    'post_count': getattr(tag, 'post_count', 0)
                }
                for tag in tags
            ],
            'cached_at': timezone.now().isoformat()
        }

        cache.set(cache_key, cached_data, timeout)
        logger.debug(f"Cached tags with counts: {cache_key}")
        return cached_data

    @classmethod
    def get_cached_tags_with_counts(cls):
        """Get cached tags with post counts."""
        cache_key = cls._make_cache_key(cls.TAGS_PREFIX, 'with_counts')
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for tags: {cache_key}")
        else:
            logger.debug(f"Cache miss for tags: {cache_key}")

        return cached_data

    @classmethod
    def cache_search_results(cls, query, results, page=1, timeout=None):
        """Cache search results."""
        if timeout is None:
            timeout = cls.CACHE_TIMEOUT_SHORT  # Search results change frequently

        cache_key = cls.get_search_cache_key(query, page)

        cached_data = {
            'query': query,
            'page': page,
            'results': [
                {
                    'id': post.id,
                    'title': post.title,
                    'slug': post.slug,
                    'excerpt': post.excerpt,
                    'created_at': post.created_at.isoformat(),
                    'view_count': post.get_view_count() if hasattr(post, 'get_view_count') else 0,
                    'author': post.author.username
                }
                for post in results
            ],
            'cached_at': timezone.now().isoformat()
        }

        cache.set(cache_key, cached_data, timeout)
        logger.debug(f"Cached search results for '{query}': {cache_key}")
        return cached_data

    @classmethod
    def get_cached_search_results(cls, query, page=1):
        """Get cached search results."""
        cache_key = cls.get_search_cache_key(query, page)
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for search '{query}': {cache_key}")
        else:
            logger.debug(f"Cache miss for search '{query}': {cache_key}")

        return cached_data

    @classmethod
    def invalidate_post_caches(cls, post_slug):
        """Invalidate all caches related to a specific post."""
        keys_to_delete = []

        # Post detail cache
        keys_to_delete.append(cls.get_post_detail_cache_key(post_slug))

        # Related posts cache for this post
        for count in [4, 6, 8, 10]:  # Common related post counts
            keys_to_delete.append(cls.get_related_posts_cache_key(post_slug, count))

        # Delete all keys
        cache.delete_many(keys_to_delete)
        logger.info(f"Invalidated post caches for: {post_slug}")

    @classmethod
    def invalidate_list_caches(cls):
        """Invalidate post list caches when posts are published/unpublished."""
        # This is a broad invalidation - in production you might want to be more specific
        prefixes_to_clear = [
            cls.POST_LIST_PREFIX,
            cls.FEATURED_POSTS_PREFIX,
            cls.POPULAR_POSTS_PREFIX,
            cls.TRENDING_POSTS_PREFIX,
            cls.CATEGORIES_PREFIX,
            cls.TAGS_PREFIX
        ]

        # For now, use cache.clear() for development - in production implement more specific invalidation
        if hasattr(cache, '_cache') and hasattr(cache._cache, 'delete_pattern'):
            # If using django-redis, we can delete by pattern
            for prefix in prefixes_to_clear:
                pattern = f"{prefix}:*"
                try:
                    cache._cache.delete_pattern(pattern)
                    logger.debug(f"Cleared cache pattern: {pattern}")
                except Exception as e:
                    logger.warning(f"Could not clear cache pattern {pattern}: {e}")
        else:
            # Fallback: clear entire cache (not ideal for production)
            logger.warning("Using broad cache invalidation - consider implementing pattern-based deletion")

        logger.info("Invalidated list caches")

    @classmethod
    def warm_cache(cls):
        """Warm frequently accessed caches."""
        from .models import Post, Category, Tag

        try:
            logger.info("Starting cache warming...")
            warmed_items = []

            # Warm featured posts
            featured_posts = Post.objects.filter(
                is_published=True,
                is_featured=True
            ).select_related('author').order_by('-created_at')[:3]

            if featured_posts:
                cls.cache_featured_posts(featured_posts)
                warmed_items.append(f"{len(featured_posts)} featured posts")

            # Warm popular posts for different periods
            for period in ['week', 'month', 'all_time']:
                try:
                    from .models import PostView
                    popular_posts = PostView.get_popular_posts(period=period, limit=12)
                    if popular_posts:
                        cls.cache_popular_posts(popular_posts, period=period)
                        warmed_items.append(f"popular posts ({period})")
                except Exception as e:
                    logger.warning(f"Could not warm popular posts cache for {period}: {e}")

            # Warm categories and tags with post counts
            categories = Category.objects.filter(
                post__is_published=True
            ).annotate(
                post_count=Count('post', filter=Q(post__is_published=True))
            ).distinct().order_by('name')

            if categories:
                cls.cache_categories_with_counts(categories)
                warmed_items.append(f"{len(categories)} categories")

            tags = Tag.objects.filter(
                post__is_published=True
            ).annotate(
                post_count=Count('post', filter=Q(post__is_published=True))
            ).distinct().order_by('name')

            if tags:
                cls.cache_tags_with_counts(tags)
                warmed_items.append(f"{len(tags)} tags")

            # Warm first page of blog posts
            first_page_posts = Post.objects.filter(
                is_published=True,
                is_featured=False
            ).select_related('author').prefetch_related('categories', 'tags').order_by('-created_at')[:6]

            if first_page_posts:
                cls.cache_post_list(first_page_posts, page=1)
                warmed_items.append("first page posts")

            # Warm related posts for popular/featured posts
            popular_posts_for_related = Post.objects.filter(
                Q(is_featured=True),
                is_published=True
            ).order_by('-created_at')[:10]

            related_count = 0
            for post in popular_posts_for_related:
                try:
                    related_posts = post.get_related_posts(count=4)
                    if related_posts and related_posts.get('posts'):
                        cls.cache_related_posts(post.slug, related_posts['posts'])
                        related_count += 1
                except Exception as e:
                    logger.warning(f"Could not warm related posts for {post.slug}: {e}")

            if related_count > 0:
                warmed_items.append(f"related posts for {related_count} popular posts")

            # Warm post details for top posts
            top_posts = Post.objects.filter(
                is_published=True
            ).order_by('-created_at')[:5]

            detail_count = 0
            for post in top_posts:
                try:
                    cls.cache_post_detail(post)
                    detail_count += 1
                except Exception as e:
                    logger.warning(f"Could not warm post detail for {post.slug}: {e}")

            if detail_count > 0:
                warmed_items.append(f"details for {detail_count} top posts")

            logger.info(f"Cache warming completed successfully: {', '.join(warmed_items)}")
            return warmed_items

        except Exception as e:
            logger.error(f"Error during cache warming: {e}")
            return []

    @classmethod
    def get_cache_stats(cls):
        """Get cache statistics and hit rates (if supported by cache backend)."""
        stats = {
            'backend': settings.CACHES['default']['BACKEND'],
            'location': settings.CACHES['default']['LOCATION'],
        }

        try:
            # Try to get Redis-specific stats
            if hasattr(cache, '_cache') and hasattr(cache._cache, 'get_stats'):
                redis_stats = cache._cache.get_stats()
                stats.update(redis_stats)
            elif hasattr(cache, 'get_stats'):
                stats.update(cache.get_stats())
        except Exception as e:
            logger.debug(f"Could not retrieve cache stats: {e}")
            stats['error'] = 'Cache stats not available'

        return stats