"""
Cache monitoring and performance analysis for the blog system.
"""
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_safe
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from .cache_service import BlogCacheService
import time
import json
import logging

logger = logging.getLogger(__name__)


@staff_member_required
@never_cache
@require_safe
def cache_monitor_view(request):
    """
    Admin view for monitoring cache performance and statistics.
    """
    # Get cache statistics
    cache_stats = BlogCacheService.get_cache_stats()

    # Test cache performance
    performance_stats = _run_cache_performance_test()

    # Check cache key status
    key_status = _check_cache_key_status()

    # Get cache configuration
    cache_config = settings.CACHES.get('default', {})

    # Calculate cache health score
    health_score = _calculate_cache_health_score(performance_stats, key_status)

    data = {
        'timestamp': timezone.now().isoformat(),
        'cache_backend': cache_config.get('BACKEND', 'Unknown'),
        'cache_location': cache_config.get('LOCATION', 'Unknown'),
        'health_score': health_score,
        'statistics': cache_stats,
        'performance': performance_stats,
        'key_status': key_status,
        'configuration': {
            'timeouts': {
                'short': BlogCacheService.CACHE_TIMEOUT_SHORT,
                'medium': BlogCacheService.CACHE_TIMEOUT_MEDIUM,
                'long': BlogCacheService.CACHE_TIMEOUT_LONG,
                'very_long': BlogCacheService.CACHE_TIMEOUT_VERY_LONG
            }
        }
    }

    return JsonResponse(data, json_dumps_params={'indent': 2})


def _run_cache_performance_test(iterations=50):
    """Run a quick cache performance test."""
    test_key_prefix = 'blog_perf_test'
    test_data = {'test': True, 'timestamp': time.time(), 'data': list(range(100))}

    # Test write performance
    start_time = time.time()
    for i in range(iterations):
        cache.set(f'{test_key_prefix}_{i}', test_data, 60)
    write_time = time.time() - start_time

    # Test read performance
    start_time = time.time()
    hits = 0
    for i in range(iterations):
        result = cache.get(f'{test_key_prefix}_{i}')
        if result:
            hits += 1
    read_time = time.time() - start_time

    # Test delete performance
    start_time = time.time()
    for i in range(iterations):
        cache.delete(f'{test_key_prefix}_{i}')
    delete_time = time.time() - start_time

    return {
        'write_ops_per_sec': round(iterations / write_time, 1) if write_time > 0 else 0,
        'read_ops_per_sec': round(iterations / read_time, 1) if read_time > 0 else 0,
        'delete_ops_per_sec': round(iterations / delete_time, 1) if delete_time > 0 else 0,
        'hit_rate_percent': round((hits / iterations) * 100, 1),
        'total_test_time': round(write_time + read_time + delete_time, 3)
    }


def _check_cache_key_status():
    """Check the status of important cache keys."""
    important_keys = [
        ('featured_posts', BlogCacheService._make_cache_key(BlogCacheService.FEATURED_POSTS_PREFIX)),
        ('categories', BlogCacheService._make_cache_key(BlogCacheService.CATEGORIES_PREFIX, 'with_counts')),
        ('tags', BlogCacheService._make_cache_key(BlogCacheService.TAGS_PREFIX, 'with_counts')),
        ('popular_week', BlogCacheService._make_cache_key(BlogCacheService.POPULAR_POSTS_PREFIX, period='week')),
        ('popular_month', BlogCacheService._make_cache_key(BlogCacheService.POPULAR_POSTS_PREFIX, period='month')),
    ]

    key_status = {}

    for key_name, cache_key in important_keys:
        cached_data = cache.get(cache_key)

        if cached_data:
            # Try to determine cache age
            cache_age = None
            data_size = len(str(cached_data))

            if isinstance(cached_data, dict) and 'cached_at' in cached_data:
                try:
                    from django.utils.dateparse import parse_datetime
                    cached_at = parse_datetime(cached_data['cached_at'])
                    if cached_at:
                        age = timezone.now() - cached_at
                        cache_age = round(age.total_seconds())
                except (ValueError, TypeError):
                    pass

            key_status[key_name] = {
                'status': 'cached',
                'size_bytes': data_size,
                'age_seconds': cache_age,
                'has_data': bool(cached_data.get('posts') or cached_data.get('categories') or cached_data.get('tags'))
            }
        else:
            key_status[key_name] = {
                'status': 'not_cached',
                'size_bytes': 0,
                'age_seconds': None,
                'has_data': False
            }

    return key_status


def _calculate_cache_health_score(performance_stats, key_status):
    """Calculate an overall cache health score (0-100)."""
    score = 0
    max_score = 100

    # Performance score (40 points max)
    read_ops = performance_stats.get('read_ops_per_sec', 0)
    write_ops = performance_stats.get('write_ops_per_sec', 0)
    hit_rate = performance_stats.get('hit_rate_percent', 0)

    # Read performance (15 points)
    if read_ops >= 1000:
        score += 15
    elif read_ops >= 500:
        score += 12
    elif read_ops >= 100:
        score += 8
    elif read_ops >= 50:
        score += 4

    # Write performance (15 points)
    if write_ops >= 500:
        score += 15
    elif write_ops >= 250:
        score += 12
    elif write_ops >= 100:
        score += 8
    elif write_ops >= 50:
        score += 4

    # Hit rate (10 points)
    score += min(hit_rate / 10, 10)  # Up to 10 points for 100% hit rate

    # Cache coverage score (35 points max)
    cached_keys = sum(1 for status in key_status.values() if status['status'] == 'cached')
    total_keys = len(key_status)

    if total_keys > 0:
        coverage_percent = (cached_keys / total_keys) * 100
        score += (coverage_percent / 100) * 35

    # Freshness score (15 points max)
    fresh_keys = 0
    stale_threshold = 3600  # 1 hour

    for status in key_status.values():
        if status['status'] == 'cached':
            age = status.get('age_seconds')
            if age is None or age < stale_threshold:
                fresh_keys += 1

    if total_keys > 0:
        freshness_percent = (fresh_keys / total_keys) * 100
        score += (freshness_percent / 100) * 15

    # Data quality score (10 points max)
    keys_with_data = sum(1 for status in key_status.values() if status.get('has_data', False))
    if total_keys > 0:
        quality_percent = (keys_with_data / total_keys) * 100
        score += (quality_percent / 100) * 10

    return min(round(score, 1), max_score)


@staff_member_required
@never_cache
def warm_cache_view(request):
    """
    Admin endpoint to manually warm the cache.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        start_time = time.time()
        warmed_items = BlogCacheService.warm_cache()
        execution_time = time.time() - start_time

        return JsonResponse({
            'success': True,
            'warmed_items': warmed_items,
            'execution_time_seconds': round(execution_time, 2),
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@staff_member_required
@never_cache
def clear_cache_view(request):
    """
    Admin endpoint to manually clear caches.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        clear_type = request.POST.get('type', 'lists')  # lists, all, post
        post_slug = request.POST.get('post_slug')

        if clear_type == 'all':
            cache.clear()
            message = "Cleared all caches"
        elif clear_type == 'post' and post_slug:
            BlogCacheService.invalidate_post_caches(post_slug)
            message = f"Cleared caches for post: {post_slug}"
        else:
            BlogCacheService.invalidate_list_caches()
            message = "Cleared list caches"

        return JsonResponse({
            'success': True,
            'message': message,
            'type': clear_type,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Cache clearing failed: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)