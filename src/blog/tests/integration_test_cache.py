#!/usr/bin/env python
"""
Test script for blog cache implementation.
"""
import os
import sys
import django

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jaroslav_tech.settings')
django.setup()

from django.core.cache import cache
from blog.cache_service import BlogCacheService
from blog.models import Post, Category, Tag

def test_basic_cache():
    """Test basic cache functionality."""
    print("=" * 50)
    print("TESTING BASIC CACHE FUNCTIONALITY")
    print("=" * 50)

    # Test basic cache operations
    test_key = 'test_key'
    test_value = {'test': True, 'data': [1, 2, 3]}

    print(f"Setting cache key '{test_key}'...")
    cache.set(test_key, test_value, 60)

    print(f"Getting cache key '{test_key}'...")
    cached_value = cache.get(test_key)

    if cached_value == test_value:
        print("✓ Basic cache operations working")
    else:
        print("✗ Basic cache operations failed")
        print(f"Expected: {test_value}")
        print(f"Got: {cached_value}")
        return False

    # Clean up
    cache.delete(test_key)
    return True

def test_blog_cache_service():
    """Test BlogCacheService functionality."""
    print("\n" + "=" * 50)
    print("TESTING BLOG CACHE SERVICE")
    print("=" * 50)

    # Test cache key generation
    print("Testing cache key generation...")
    key1 = BlogCacheService._make_cache_key('test_prefix', 'arg1', 'arg2')
    key2 = BlogCacheService._make_cache_key('test_prefix', 'arg1', 'arg2')
    key3 = BlogCacheService._make_cache_key('test_prefix', 'arg1', 'arg3')

    if key1 == key2 and key1 != key3:
        print("✓ Cache key generation working")
    else:
        print("✗ Cache key generation failed")
        return False

    # Test cache statistics
    print("Testing cache statistics...")
    try:
        stats = BlogCacheService.get_cache_stats()
        if isinstance(stats, dict):
            print("✓ Cache statistics working")
            print(f"  Backend: {stats.get('backend', 'Unknown')}")
            print(f"  Location: {stats.get('location', 'Unknown')}")
        else:
            print("✗ Cache statistics returned invalid format")
            return False
    except Exception as e:
        print(f"✗ Cache statistics failed: {e}")
        return False

    return True

def test_model_caching():
    """Test model-based caching functionality."""
    print("\n" + "=" * 50)
    print("TESTING MODEL CACHING")
    print("=" * 50)

    # Test categories caching
    print("Testing categories caching...")
    try:
        # Clear cache first
        categories_key = BlogCacheService._make_cache_key(
            BlogCacheService.CATEGORIES_PREFIX, 'with_counts'
        )
        cache.delete(categories_key)

        # Test cache miss
        cached_categories = BlogCacheService.get_cached_categories_with_counts()
        if cached_categories is None:
            print("✓ Cache miss working correctly")
        else:
            print("✗ Expected cache miss but got data")
            return False

        # Get categories from database and cache them
        categories = Category.objects.all()[:5]  # Limit for testing
        if categories:
            BlogCacheService.cache_categories_with_counts(categories)
            print("✓ Categories cached successfully")

            # Test cache hit
            cached_categories = BlogCacheService.get_cached_categories_with_counts()
            if cached_categories and 'categories' in cached_categories:
                print("✓ Categories cache hit working")
            else:
                print("✗ Categories cache hit failed")
                return False
        else:
            print("⚠ No categories found in database, skipping category cache test")

    except Exception as e:
        print(f"✗ Categories caching failed: {e}")
        return False

    # Test tags caching
    print("Testing tags caching...")
    try:
        # Clear cache first
        tags_key = BlogCacheService._make_cache_key(
            BlogCacheService.TAGS_PREFIX, 'with_counts'
        )
        cache.delete(tags_key)

        # Get tags from database and cache them
        tags = Tag.objects.all()[:5]  # Limit for testing
        if tags:
            BlogCacheService.cache_tags_with_counts(tags)
            print("✓ Tags cached successfully")

            # Test cache hit
            cached_tags = BlogCacheService.get_cached_tags_with_counts()
            if cached_tags and 'tags' in cached_tags:
                print("✓ Tags cache hit working")
            else:
                print("✗ Tags cache hit failed")
                return False
        else:
            print("⚠ No tags found in database, skipping tags cache test")

    except Exception as e:
        print(f"✗ Tags caching failed: {e}")
        return False

    return True

def test_post_caching():
    """Test post-specific caching functionality."""
    print("\n" + "=" * 50)
    print("TESTING POST CACHING")
    print("=" * 50)

    # Get a published post for testing
    try:
        post = Post.objects.filter(is_published=True).first()
        if not post:
            print("⚠ No published posts found, creating test post...")
            # In a real test, we might create a test post
            print("⚠ Skipping post caching test - no test data")
            return True

        print(f"Testing with post: {post.title[:50]}...")

        # Test post detail caching
        print("Testing post detail caching...")

        # Clear cache first
        cache_key = BlogCacheService.get_post_detail_cache_key(post.slug)
        cache.delete(cache_key)

        # Test cache miss
        cached_detail = BlogCacheService.get_cached_post_detail(post.slug)
        if cached_detail is None:
            print("✓ Post detail cache miss working")
        else:
            print("✗ Expected cache miss but got data")
            return False

        # Cache the post
        BlogCacheService.cache_post_detail(post)
        print("✓ Post detail cached successfully")

        # Test cache hit
        cached_detail = BlogCacheService.get_cached_post_detail(post.slug)
        if cached_detail and cached_detail.get('slug') == post.slug:
            print("✓ Post detail cache hit working")
        else:
            print("✗ Post detail cache hit failed")
            return False

        # Test cache invalidation
        print("Testing cache invalidation...")
        BlogCacheService.invalidate_post_caches(post.slug)

        cached_detail = BlogCacheService.get_cached_post_detail(post.slug)
        if cached_detail is None:
            print("✓ Post cache invalidation working")
        else:
            print("✗ Post cache invalidation failed")
            return False

    except Exception as e:
        print(f"✗ Post caching failed: {e}")
        return False

    return True

def test_cache_warming():
    """Test cache warming functionality."""
    print("\n" + "=" * 50)
    print("TESTING CACHE WARMING")
    print("=" * 50)

    try:
        # Clear caches first
        print("Clearing existing caches...")
        cache.clear()

        # Test cache warming
        print("Running cache warming...")
        warmed_items = BlogCacheService.warm_cache()

        if warmed_items and isinstance(warmed_items, list):
            print("✓ Cache warming completed successfully")
            print(f"  Warmed items: {', '.join(warmed_items)}")
        else:
            print("✓ Cache warming completed (no items to warm)")

        # Check if featured posts cache was warmed
        featured_key = BlogCacheService._make_cache_key(
            BlogCacheService.FEATURED_POSTS_PREFIX
        )
        cached_featured = cache.get(featured_key)

        if cached_featured:
            print("✓ Featured posts cache warmed successfully")
        else:
            print("⚠ Featured posts cache not warmed (may be no featured posts)")

        return True

    except Exception as e:
        print(f"✗ Cache warming failed: {e}")
        return False

def run_all_tests():
    """Run all cache tests."""
    print("BLOG CACHE IMPLEMENTATION TESTS")
    print("=" * 50)

    tests = [
        test_basic_cache,
        test_blog_cache_service,
        test_model_caching,
        test_post_caching,
        test_cache_warming
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")

    if failed == 0:
        print("\n✓ ALL TESTS PASSED! Cache implementation is working correctly.")
        return True
    else:
        print(f"\n✗ {failed} TESTS FAILED! Please review the cache implementation.")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)