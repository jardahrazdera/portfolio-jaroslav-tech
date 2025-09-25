"""
Test module for blog cache implementation.
"""
from django.test import TestCase, TransactionTestCase
from django.core.cache import cache
from django.contrib.auth.models import User
from blog.cache_service import BlogCacheService
from blog.models import Post, Category, Tag


class BlogCacheServiceTestCase(TestCase):
    """Test cases for BlogCacheService functionality."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

        # Create test tag
        self.tag = Tag.objects.create(
            name='Test Tag',
            slug='test-tag',
            color='#FF0000'
        )

        # Create test post
        self.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            content='This is a test post content.',
            excerpt='Test excerpt',
            author=self.user,
            is_published=True,
            is_featured=True
        )
        self.post.categories.add(self.category)
        self.post.tags.add(self.tag)

    def tearDown(self):
        """Clean up after each test."""
        cache.clear()

    def test_cache_key_generation(self):
        """Test cache key generation."""
        key1 = BlogCacheService._make_cache_key('test_prefix', 'arg1', 'arg2')
        key2 = BlogCacheService._make_cache_key('test_prefix', 'arg1', 'arg2')
        key3 = BlogCacheService._make_cache_key('test_prefix', 'arg1', 'arg3')

        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)
        self.assertIn('test_prefix', key1)

    def test_cache_stats(self):
        """Test cache statistics functionality."""
        stats = BlogCacheService.get_cache_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('backend', stats)
        self.assertIn('location', stats)

    def test_post_detail_caching(self):
        """Test post detail caching and retrieval."""
        # Clear any existing cache
        cache_key = BlogCacheService.get_post_detail_cache_key(self.post.slug)
        cache.delete(cache_key)

        # Test cache miss
        cached_detail = BlogCacheService.get_cached_post_detail(self.post.slug)
        self.assertIsNone(cached_detail)

        # Cache the post
        BlogCacheService.cache_post_detail(self.post)

        # Test cache hit
        cached_detail = BlogCacheService.get_cached_post_detail(self.post.slug)
        self.assertIsNotNone(cached_detail)
        self.assertEqual(cached_detail['slug'], self.post.slug)
        self.assertEqual(cached_detail['title'], self.post.title)

    def test_post_cache_invalidation(self):
        """Test post cache invalidation."""
        # Cache the post first
        BlogCacheService.cache_post_detail(self.post)

        # Verify it's cached
        cached_detail = BlogCacheService.get_cached_post_detail(self.post.slug)
        self.assertIsNotNone(cached_detail)

        # Invalidate cache
        BlogCacheService.invalidate_post_caches(self.post.slug)

        # Verify cache is cleared
        cached_detail = BlogCacheService.get_cached_post_detail(self.post.slug)
        self.assertIsNone(cached_detail)

    def test_categories_caching(self):
        """Test categories caching functionality."""
        # Clear cache first
        categories_key = BlogCacheService._make_cache_key(
            BlogCacheService.CATEGORIES_PREFIX, 'with_counts'
        )
        cache.delete(categories_key)

        # Test cache miss
        cached_categories = BlogCacheService.get_cached_categories_with_counts()
        self.assertIsNone(cached_categories)

        # Cache categories
        categories = Category.objects.all()
        BlogCacheService.cache_categories_with_counts(categories)

        # Test cache hit
        cached_categories = BlogCacheService.get_cached_categories_with_counts()
        self.assertIsNotNone(cached_categories)
        self.assertIn('categories', cached_categories)

    def test_tags_caching(self):
        """Test tags caching functionality."""
        # Clear cache first
        tags_key = BlogCacheService._make_cache_key(
            BlogCacheService.TAGS_PREFIX, 'with_counts'
        )
        cache.delete(tags_key)

        # Test cache miss
        cached_tags = BlogCacheService.get_cached_tags_with_counts()
        self.assertIsNone(cached_tags)

        # Cache tags
        tags = Tag.objects.all()
        BlogCacheService.cache_tags_with_counts(tags)

        # Test cache hit
        cached_tags = BlogCacheService.get_cached_tags_with_counts()
        self.assertIsNotNone(cached_tags)
        self.assertIn('tags', cached_tags)

    def test_featured_posts_caching(self):
        """Test featured posts caching."""
        # Clear cache
        featured_key = BlogCacheService._make_cache_key(
            BlogCacheService.FEATURED_POSTS_PREFIX
        )
        cache.delete(featured_key)

        # Test cache miss
        cached_featured = BlogCacheService.get_cached_featured_posts()
        self.assertIsNone(cached_featured)

        # Cache featured posts
        featured_posts = Post.objects.filter(is_featured=True, is_published=True)[:3]
        BlogCacheService.cache_featured_posts(featured_posts)

        # Test cache hit
        cached_featured = BlogCacheService.get_cached_featured_posts()
        self.assertIsNotNone(cached_featured)
        self.assertIn('posts', cached_featured)

    def test_cache_warming(self):
        """Test cache warming functionality."""
        # Clear all caches
        cache.clear()

        # Run cache warming
        warmed_items = BlogCacheService.warm_cache()

        # Verify warming completed
        self.assertIsInstance(warmed_items, list)

        # Check that some key caches are warmed
        featured_key = BlogCacheService._make_cache_key(
            BlogCacheService.FEATURED_POSTS_PREFIX
        )
        cached_featured = cache.get(featured_key)

        # Should have cached something (even if empty results)
        if self.post.is_featured:
            self.assertIsNotNone(cached_featured)


class BlogCacheIntegrationTestCase(TransactionTestCase):
    """Integration tests for cache with database operations."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )

    def tearDown(self):
        """Clean up after each test."""
        cache.clear()

    def test_cache_performance(self):
        """Test basic cache performance characteristics."""
        import time

        # Create test data
        posts = []
        for i in range(5):
            post = Post.objects.create(
                title=f'Performance Test Post {i}',
                slug=f'performance-test-post-{i}',
                content=f'Content for post {i}',
                author=self.user,
                is_published=True
            )
            posts.append(post)

        # Time cache operations
        start_time = time.time()

        # Cache all posts
        for post in posts:
            BlogCacheService.cache_post_detail(post)

        cache_time = time.time() - start_time

        start_time = time.time()

        # Retrieve all cached posts
        for post in posts:
            cached_detail = BlogCacheService.get_cached_post_detail(post.slug)
            self.assertIsNotNone(cached_detail)

        retrieval_time = time.time() - start_time

        # Basic performance assertions
        self.assertLess(cache_time, 1.0)  # Caching should be fast
        self.assertLess(retrieval_time, 0.5)  # Retrieval should be very fast