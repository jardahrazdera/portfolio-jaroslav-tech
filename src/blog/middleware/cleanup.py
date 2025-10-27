"""
Blog middleware for automatic periodic cleanup and monitoring.
"""
import threading
import time
import logging
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from ..signals import cleanup_orphaned_files, get_storage_stats

logger = logging.getLogger(__name__)


class PeriodicCleanupMiddleware(MiddlewareMixin):
    """
    Middleware that performs periodic cleanup based on request count.

    This provides an additional layer of cleanup that doesn't rely on cron jobs,
    ensuring orphaned files are cleaned up even if cron isn't configured.
    """

    # Configuration
    CLEANUP_INTERVAL = getattr(settings, 'BLOG_CLEANUP_INTERVAL', 1000)  # Every N requests
    CACHE_KEY = 'blog:cleanup:request_count'
    CACHE_LAST_CLEANUP = 'blog:cleanup:last_cleanup'
    CLEANUP_TIMEOUT = 30  # Maximum cleanup time in seconds

    def process_request(self, request):
        """
        Process incoming request and trigger cleanup if needed.

        This runs on every request but cleanup only happens periodically
        to avoid performance impact.
        """
        # Skip cleanup for certain paths to avoid unnecessary overhead
        if self._should_skip_cleanup(request):
            return None

        try:
            # Increment request counter
            current_count = cache.get(self.CACHE_KEY, 0) + 1
            cache.set(self.CACHE_KEY, current_count, timeout=86400)  # 24 hours

            # Check if it's time for cleanup
            if current_count % self.CLEANUP_INTERVAL == 0:
                self._trigger_background_cleanup(request)

        except Exception as e:
            # Never let cleanup middleware crash the request
            logger.warning(f"Cleanup middleware error: {str(e)}")

        return None

    def _should_skip_cleanup(self, request):
        """
        Determine if cleanup should be skipped for this request.

        Skip for:
        - Static files
        - Admin requests (to avoid interference)
        - AJAX requests
        - Health checks
        """
        path = request.path.lower()

        # Skip static files
        if path.startswith('/static/') or path.startswith('/media/'):
            return True

        # Skip admin pages (cleanup could interfere with file uploads)
        if path.startswith('/admin/'):
            return True

        # Skip AJAX requests to avoid delays
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True

        # Skip common health check endpoints
        health_checks = ['/health/', '/ping/', '/status/', '/favicon.ico']
        if any(path.startswith(check) for check in health_checks):
            return True

        return False

    def _trigger_background_cleanup(self, request):
        """
        Trigger cleanup in a background thread to avoid blocking the request.
        """
        # Check if cleanup is already running
        last_cleanup = cache.get(self.CACHE_LAST_CLEANUP, 0)
        now = time.time()

        # Avoid running cleanup too frequently (minimum 5 minutes between cleanups)
        if now - last_cleanup < 300:
            logger.debug("Skipping cleanup - too recent")
            return

        # Mark cleanup as starting
        cache.set(self.CACHE_LAST_CLEANUP, now, timeout=86400)

        # Start background cleanup thread
        cleanup_thread = threading.Thread(
            target=self._perform_cleanup,
            args=(request.path,),
            daemon=True,
            name='blog-cleanup-thread'
        )
        cleanup_thread.start()

        logger.info(f"Background cleanup triggered by request to {request.path}")

    def _perform_cleanup(self, trigger_path):
        """
        Perform the actual cleanup in a background thread.

        This method runs independently of the request-response cycle.
        """
        start_time = time.time()

        try:
            logger.info("Starting background cleanup...")

            # Set a timeout to prevent runaway cleanup
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Cleanup timeout")

            # Set timeout (only on Unix systems)
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.CLEANUP_TIMEOUT)

            try:
                # Perform the cleanup
                cleaned_count = cleanup_orphaned_files()

                # Get quick storage stats for monitoring
                stats = get_storage_stats()
                total_size_mb = stats['total_size'] / (1024 * 1024)

                duration = time.time() - start_time

                logger.info(
                    f"Background cleanup completed: {cleaned_count} files removed, "
                    f"{total_size_mb:.1f}MB total storage, {duration:.2f}s duration"
                )

                # Update cleanup metrics in cache for monitoring
                cleanup_stats = {
                    'last_cleanup': start_time,
                    'last_duration': duration,
                    'last_files_cleaned': cleaned_count,
                    'last_trigger_path': trigger_path,
                    'total_storage_mb': total_size_mb,
                }
                cache.set('blog:cleanup:last_stats', cleanup_stats, timeout=86400)

                # Alert if unusually high number of orphaned files
                if cleaned_count > 50:
                    logger.warning(
                        f"High number of orphaned files cleaned: {cleaned_count}. "
                        "This might indicate an issue with file handling."
                    )

            finally:
                # Clear timeout
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)

        except TimeoutError:
            logger.error(f"Background cleanup timed out after {self.CLEANUP_TIMEOUT} seconds")
        except Exception as e:
            logger.error(f"Background cleanup failed: {str(e)}", exc_info=True)
        finally:
            # Always update the last cleanup time
            cache.set(self.CACHE_LAST_CLEANUP, start_time, timeout=86400)


class StorageMonitoringMiddleware(MiddlewareMixin):
    """
    Lightweight middleware for storage monitoring and alerting.

    This middleware tracks storage usage trends and can trigger alerts
    when storage usage grows unexpectedly.
    """

    MONITORING_INTERVAL = getattr(settings, 'BLOG_MONITORING_INTERVAL', 5000)  # Every N requests
    CACHE_KEY = 'blog:monitoring:request_count'
    STORAGE_HISTORY_KEY = 'blog:monitoring:storage_history'
    MAX_HISTORY_POINTS = 10  # Keep last 10 measurements

    def process_request(self, request):
        """Monitor storage usage periodically."""
        # Skip for same paths as cleanup middleware
        if self._should_skip_monitoring(request):
            return None

        try:
            # Increment monitoring counter
            current_count = cache.get(self.CACHE_KEY, 0) + 1
            cache.set(self.CACHE_KEY, current_count, timeout=86400)

            # Check if it's time for monitoring
            if current_count % self.MONITORING_INTERVAL == 0:
                self._monitor_storage()

        except Exception as e:
            logger.warning(f"Storage monitoring error: {str(e)}")

        return None

    def _should_skip_monitoring(self, request):
        """Same skip logic as cleanup middleware."""
        path = request.path.lower()
        return (
            path.startswith('/static/') or
            path.startswith('/media/') or
            path.startswith('/admin/') or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )

    def _monitor_storage(self):
        """Monitor storage usage and track trends."""
        try:
            # Get current storage stats
            stats = get_storage_stats()
            current_size_mb = stats['total_size'] / (1024 * 1024)
            current_time = time.time()

            # Get storage history
            history = cache.get(self.STORAGE_HISTORY_KEY, [])

            # Add current measurement
            history.append({
                'timestamp': current_time,
                'size_mb': current_size_mb,
                'file_count': (
                    stats['featured_images']['count'] +
                    stats['processed_images']['count'] +
                    stats['blog_files']['count']
                )
            })

            # Keep only recent history
            if len(history) > self.MAX_HISTORY_POINTS:
                history = history[-self.MAX_HISTORY_POINTS:]

            # Update cache
            cache.set(self.STORAGE_HISTORY_KEY, history, timeout=86400)

            # Analyze trends
            self._analyze_storage_trends(history)

            logger.debug(f"Storage monitoring: {current_size_mb:.1f}MB total")

        except Exception as e:
            logger.error(f"Storage monitoring failed: {str(e)}")

    def _analyze_storage_trends(self, history):
        """Analyze storage trends and trigger alerts if needed."""
        if len(history) < 3:
            return  # Need at least 3 points for trend analysis

        # Calculate growth rate
        recent = history[-3:]  # Last 3 measurements
        if len(recent) >= 2:
            size_growth = recent[-1]['size_mb'] - recent[0]['size_mb']
            time_diff = recent[-1]['timestamp'] - recent[0]['timestamp']

            if time_diff > 0:
                growth_rate_mb_per_hour = (size_growth / time_diff) * 3600

                # Alert on rapid growth (more than 100MB per hour)
                if growth_rate_mb_per_hour > 100:
                    logger.warning(
                        f"Rapid storage growth detected: {growth_rate_mb_per_hour:.1f}MB/hour. "
                        f"Current usage: {recent[-1]['size_mb']:.1f}MB"
                    )

                # Alert on very large storage usage (over 5GB)
                if recent[-1]['size_mb'] > 5000:
                    logger.warning(
                        f"High storage usage: {recent[-1]['size_mb']:.1f}MB. "
                        "Consider running manual cleanup or reviewing file retention policies."
                    )


# Utility functions for monitoring
def get_cleanup_stats():
    """Get the latest cleanup statistics from cache."""
    return cache.get('blog:cleanup:last_stats', {})


def get_storage_history():
    """Get storage usage history for monitoring dashboard."""
    return cache.get('blog:monitoring:storage_history', [])


def reset_cleanup_counters():
    """Reset cleanup counters (useful for testing or configuration changes)."""
    cache.delete(PeriodicCleanupMiddleware.CACHE_KEY)
    cache.delete(StorageMonitoringMiddleware.CACHE_KEY)
    cache.delete(PeriodicCleanupMiddleware.CACHE_LAST_CLEANUP)
    logger.info("Cleanup counters reset")


def force_cleanup():
    """Force an immediate cleanup (for testing or manual triggers)."""
    middleware = PeriodicCleanupMiddleware()

    # Create a mock request object
    class MockRequest:
        path = '/force-cleanup'
        headers = {}

    mock_request = MockRequest()
    middleware._trigger_background_cleanup(mock_request)
    logger.info("Forced cleanup triggered")