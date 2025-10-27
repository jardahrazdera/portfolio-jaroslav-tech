"""
Django management command to clear blog caches selectively or completely.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from blog.cache_service import BlogCacheService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clear blog caches selectively or completely'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Clear all caches (default: clear only blog caches)',
        )
        parser.add_argument(
            '--posts',
            action='store_true',
            help='Clear only post-related caches',
        )
        parser.add_argument(
            '--lists',
            action='store_true',
            help='Clear only list caches (featured, popular, etc.)',
        )
        parser.add_argument(
            '--search',
            action='store_true',
            help='Clear only search result caches',
        )
        parser.add_argument(
            '--post-slug',
            type=str,
            help='Clear caches for a specific post slug',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show cache statistics after clearing',
        )

    def handle(self, *args, **options):
        try:
            cleared_items = []

            # Clear all caches
            if options['all']:
                cache.clear()
                cleared_items.append('all caches')
                self.stdout.write(
                    self.style.WARNING('Cleared all caches')
                )

            # Clear specific post caches
            elif options['post_slug']:
                slug = options['post_slug']
                BlogCacheService.invalidate_post_caches(slug)
                cleared_items.append(f'post caches for "{slug}"')
                self.stdout.write(
                    self.style.SUCCESS(f'Cleared post caches for: {slug}')
                )

            # Clear list caches
            elif options['lists']:
                BlogCacheService.invalidate_list_caches()
                cleared_items.append('list caches')
                self.stdout.write(
                    self.style.SUCCESS('Cleared blog list caches')
                )

            # Clear search caches
            elif options['search']:
                # Clear search caches by pattern
                if hasattr(cache, '_cache') and hasattr(cache._cache, 'delete_pattern'):
                    pattern = f"{BlogCacheService.SEARCH_RESULTS_PREFIX}:*"
                    try:
                        cache._cache.delete_pattern(pattern)
                        cleared_items.append('search result caches')
                        self.stdout.write(
                            self.style.SUCCESS('Cleared search result caches')
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Could not clear search caches: {e}')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING('Pattern-based cache clearing not supported')
                    )

            # Clear post-related caches
            elif options['posts']:
                # This would require knowing all post slugs, so we'll clear broadly
                BlogCacheService.invalidate_list_caches()
                cleared_items.append('post-related caches')
                self.stdout.write(
                    self.style.SUCCESS('Cleared post-related caches')
                )

            # Default: clear common blog caches
            else:
                BlogCacheService.invalidate_list_caches()
                cleared_items.append('default blog caches')
                self.stdout.write(
                    self.style.SUCCESS('Cleared default blog caches')
                )

            # Show statistics if requested
            if options['stats']:
                self.stdout.write('\n' + '='*50)
                self.stdout.write('CACHE STATISTICS')
                self.stdout.write('='*50)
                
                stats = BlogCacheService.get_cache_stats()
                for key, value in stats.items():
                    self.stdout.write(f'{key}: {value}')

            if cleared_items:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Cache clearing completed: {", ".join(cleared_items)}'
                    )
                )

        except Exception as e:
            logger.error(f'Error clearing cache: {e}')
            raise CommandError(f'Cache clearing failed: {e}')