"""
Django management command to show detailed cache statistics and performance metrics.
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from blog.cache_service import BlogCacheService
from django.conf import settings
import time


class Command(BaseCommand):
    help = 'Show detailed cache statistics and performance metrics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-performance',
            action='store_true',
            help='Run cache performance tests',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed cache information',
        )

    def handle(self, *args, **options):
        self.stdout.write('='*60)
        self.stdout.write(self.style.HTTP_INFO('BLOG CACHE STATISTICS'))
        self.stdout.write('='*60)

        # Basic cache configuration
        self.stdout.write('\n' + self.style.HTTP_INFO('Cache Configuration:'))
        cache_config = settings.CACHES['default']
        self.stdout.write(f"Backend: {cache_config.get('BACKEND', 'Unknown')}")
        self.stdout.write(f"Location: {cache_config.get('LOCATION', 'Unknown')}")
        
        # Cache statistics
        self.stdout.write('\n' + self.style.HTTP_INFO('Cache Statistics:'))
        stats = BlogCacheService.get_cache_stats()
        
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                self.stdout.write(f"{key}: {value:,}")
            else:
                self.stdout.write(f"{key}: {value}")

        # Test cache performance if requested
        if options['test_performance']:
            self.stdout.write('\n' + self.style.HTTP_INFO('Performance Tests:'))
            self._run_performance_tests()

        # Show detailed information if requested
        if options['detailed']:
            self.stdout.write('\n' + self.style.HTTP_INFO('Detailed Cache Information:'))
            self._show_detailed_info()

    def _run_performance_tests(self):
        """Run basic cache performance tests."""
        test_key = 'blog_cache_perf_test'
        test_data = {'test': True, 'data': list(range(100))}
        
        # Test write performance
        start_time = time.time()
        for i in range(100):
            cache.set(f'{test_key}_{i}', test_data, 60)
        write_time = time.time() - start_time
        
        self.stdout.write(f"Write Performance: {write_time:.3f}s for 100 operations ({100/write_time:.1f} ops/sec)")
        
        # Test read performance
        start_time = time.time()
        hits = 0
        for i in range(100):
            result = cache.get(f'{test_key}_{i}')
            if result:
                hits += 1
        read_time = time.time() - start_time
        
        self.stdout.write(f"Read Performance: {read_time:.3f}s for 100 operations ({100/read_time:.1f} ops/sec)")
        self.stdout.write(f"Cache Hit Rate: {hits}/100 ({hits}%)")
        
        # Clean up test keys
        for i in range(100):
            cache.delete(f'{test_key}_{i}')

    def _show_detailed_info(self):
        """Show detailed cache information."""
        
        # Test some common cache keys
        test_keys = [
            BlogCacheService._make_cache_key(BlogCacheService.FEATURED_POSTS_PREFIX),
            BlogCacheService._make_cache_key(BlogCacheService.CATEGORIES_PREFIX, 'with_counts'),
            BlogCacheService._make_cache_key(BlogCacheService.TAGS_PREFIX, 'with_counts'),
        ]
        
        self.stdout.write('\nCache Key Status:')
        for key in test_keys:
            cached_data = cache.get(key)
            if cached_data:
                cache_age = 'Unknown'
                if isinstance(cached_data, dict) and 'cached_at' in cached_data:
                    from django.utils import timezone
                    from datetime import datetime
                    try:
                        cached_at = datetime.fromisoformat(cached_data['cached_at'])
                        if cached_at.tzinfo is None:
                            cached_at = timezone.make_aware(cached_at)
                        age = timezone.now() - cached_at
                        cache_age = f"{age.total_seconds():.0f} seconds"
                    except (ValueError, TypeError):
                        pass
                
                data_size = len(str(cached_data))
                self.stdout.write(f"✓ {key[:50]}... (Size: {data_size} chars, Age: {cache_age})")
            else:
                self.stdout.write(f"✗ {key[:50]}... (Not cached)")

        # Cache timeout information
        self.stdout.write('\nCache Timeout Settings:')
        self.stdout.write(f"Short: {BlogCacheService.CACHE_TIMEOUT_SHORT}s ({BlogCacheService.CACHE_TIMEOUT_SHORT/60:.1f} min)")
        self.stdout.write(f"Medium: {BlogCacheService.CACHE_TIMEOUT_MEDIUM}s ({BlogCacheService.CACHE_TIMEOUT_MEDIUM/60:.1f} min)")
        self.stdout.write(f"Long: {BlogCacheService.CACHE_TIMEOUT_LONG}s ({BlogCacheService.CACHE_TIMEOUT_LONG/60:.1f} min)")
        self.stdout.write(f"Very Long: {BlogCacheService.CACHE_TIMEOUT_VERY_LONG}s ({BlogCacheService.CACHE_TIMEOUT_VERY_LONG/60:.1f} min)")