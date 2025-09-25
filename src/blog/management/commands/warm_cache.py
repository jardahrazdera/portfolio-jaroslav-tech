"""
Django management command to warm blog caches with frequently accessed content.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from blog.cache_service import BlogCacheService
import logging
import time

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Warm blog caches with frequently accessed content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-first',
            action='store_true',
            help='Clear all caches before warming',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show cache statistics after warming',
        )

    def handle(self, *args, **options):
        start_time = time.time()
        
        if options['verbose']:
            self.stdout.write('Starting cache warming process...')

        try:
            # Clear caches first if requested
            if options['clear_first']:
                if options['verbose']:
                    self.stdout.write('Clearing existing caches...')
                cache.clear()
                self.stdout.write(
                    self.style.WARNING('Cleared all existing caches')
                )

            # Warm the cache
            if options['verbose']:
                self.stdout.write('Warming blog caches...')
            
            BlogCacheService.warm_cache()

            # Calculate execution time
            execution_time = time.time() - start_time

            # Show statistics if requested
            if options['stats']:
                self.stdout.write('\n' + '='*50)
                self.stdout.write('CACHE STATISTICS')
                self.stdout.write('='*50)
                
                stats = BlogCacheService.get_cache_stats()
                for key, value in stats.items():
                    self.stdout.write(f'{key}: {value}')

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully warmed blog caches in {execution_time:.2f} seconds'
                )
            )

        except Exception as e:
            logger.error(f'Error warming cache: {e}')
            raise CommandError(f'Cache warming failed: {e}')