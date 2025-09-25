"""
Privacy-friendly analytics middleware for blog posts.
Tracks page views without storing personal data or IP addresses.
"""

import logging
from django.utils.deprecation import MiddlewareMixin
from .models import Post, PostView

logger = logging.getLogger(__name__)


class PostViewTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track blog post views in a privacy-friendly way.

    Features:
    - No IP address storage
    - No personal data collection
    - Session-based duplicate prevention
    - Bot detection via user agent patterns
    - Respects Do Not Track headers
    """

    # Common bot user agent patterns (basic bot detection)
    BOT_PATTERNS = [
        'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
        'googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider',
        'yandexbot', 'facebookexternalhit', 'twitterbot', 'linkedinbot',
        'whatsapp', 'telegrambot', 'applebot', 'amazonbot',
        'lighthouse', 'pagespeed', 'gtmetrix', 'pingdom'
    ]

    def process_response(self, request, response):
        """
        Track post views on successful page loads.
        Only tracks blog post detail pages with 200 status.
        """

        # Only track successful responses
        if response.status_code != 200:
            return response

        # Check if this is a blog post detail view
        if not self._is_blog_post_view(request):
            return response

        # Respect Do Not Track header
        if self._should_respect_dnt(request):
            return response

        # Check for bot traffic (basic detection)
        if self._is_likely_bot(request):
            return response

        try:
            # Extract post slug from URL
            post_slug = self._extract_post_slug(request.path)
            if not post_slug:
                return response

            # Get the post
            try:
                post = Post.objects.get(slug=post_slug, is_published=True)
            except Post.DoesNotExist:
                return response

            # Track the view (with duplicate prevention)
            view = PostView.add_view(post, request)

            if view:
                logger.debug(f"Tracked view for post: {post.title}")
            else:
                logger.debug(f"Duplicate view not tracked for post: {post.title}")

        except Exception as e:
            # Don't break the response if tracking fails
            logger.error(f"Error tracking post view: {e}")

        return response

    def _is_blog_post_view(self, request):
        """Check if the request is for a blog post detail page."""
        path = request.path

        # Check if path matches blog post pattern: /blog/post/slug/
        # Adjust this pattern based on your URL structure
        if '/blog/post/' in path and path.count('/') >= 4:
            return True

        return False

    def _extract_post_slug(self, path):
        """Extract post slug from URL path."""
        try:
            # Expected format: /en/blog/post/slug/
            parts = [p for p in path.split('/') if p]

            # Find the position of 'post' in the path
            if 'post' in parts:
                post_index = parts.index('post')
                if len(parts) > post_index + 1:
                    return parts[post_index + 1]

        except (IndexError, ValueError):
            pass

        return None

    def _should_respect_dnt(self, request):
        """
        Check if we should respect Do Not Track header.
        Returns True if DNT is set and we should not track.
        """
        dnt_header = request.META.get('HTTP_DNT')
        return dnt_header == '1'

    def _is_likely_bot(self, request):
        """
        Basic bot detection using user agent patterns.
        More sophisticated bot detection could be added here.
        """
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

        # Check against known bot patterns
        for pattern in self.BOT_PATTERNS:
            if pattern in user_agent:
                return True

        # Additional heuristics for bot detection
        if not user_agent:
            return True  # No user agent is suspicious

        # Very short user agents are often bots
        if len(user_agent) < 20:
            return True

        # Check for missing common browser headers
        if not request.META.get('HTTP_ACCEPT'):
            return True

        return False


class ReadingAnalyticsMiddleware(MiddlewareMixin):
    """
    Middleware to inject reading analytics JavaScript into blog post pages.
    Adds reading completion tracking and engagement measurement.
    """

    def process_response(self, request, response):
        """Inject analytics script into blog post pages."""

        # Only process HTML responses
        if not response.get('Content-Type', '').startswith('text/html'):
            return response

        # Only inject on blog post pages
        if not self._is_blog_post_view(request):
            return response

        # Check if response has content to modify
        if not hasattr(response, 'content'):
            return response

        try:
            # Inject reading analytics script before closing body tag
            content = response.content.decode('utf-8')

            # Create the analytics script
            analytics_script = self._get_analytics_script(request)

            # Insert before closing body tag
            if '</body>' in content:
                content = content.replace('</body>', f'{analytics_script}\n</body>')
                response.content = content.encode('utf-8')
                response['Content-Length'] = str(len(response.content))

        except Exception as e:
            # Don't break the response if injection fails
            logger.error(f"Error injecting reading analytics: {e}")

        return response

    def _is_blog_post_view(self, request):
        """Check if the request is for a blog post detail page."""
        return '/blog/post/' in request.path and request.path.count('/') >= 4

    def _get_analytics_script(self, request):
        """Generate the reading analytics JavaScript."""
        post_slug = self._extract_post_slug(request.path)

        return f"""
<script>
// Reading Analytics - Privacy-friendly engagement tracking
(function() {{
    if (!document.body || typeof fetch === 'undefined') return;

    const postSlug = '{post_slug}';
    const startTime = Date.now();
    let scrolledToBottom = false;
    let maxScrollPercent = 0;
    let readingActive = true;

    // Track scroll progress
    function trackScroll() {{
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrollPercent = scrollTop / docHeight * 100;

        maxScrollPercent = Math.max(maxScrollPercent, scrollPercent);

        // Consider "completed reading" if user scrolled to 80% or more
        if (scrollPercent >= 80) {{
            scrolledToBottom = true;
        }}
    }}

    // Track when user becomes inactive
    let inactiveTimeout;
    function resetInactiveTimer() {{
        readingActive = true;
        clearTimeout(inactiveTimeout);
        inactiveTimeout = setTimeout(() => {{
            readingActive = false;
        }}, 30000); // 30 seconds of inactivity
    }}

    // Send analytics data
    function sendAnalytics() {{
        const readingTime = Math.round((Date.now() - startTime) / 1000);

        // Only send if user spent at least 10 seconds reading
        if (readingTime < 10) return;

        const data = {{
            post_slug: postSlug,
            reading_time_seconds: readingTime,
            completed_reading: scrolledToBottom,
            max_scroll_percent: Math.round(maxScrollPercent)
        }};

        // Send data to backend (fire and forget)
        fetch('/en/blog/api/track-reading/', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            }},
            body: JSON.stringify(data)
        }}).catch(() => {{}}); // Silently fail
    }}

    // Event listeners
    window.addEventListener('scroll', trackScroll, {{ passive: true }});
    window.addEventListener('mousemove', resetInactiveTimer, {{ passive: true }});
    window.addEventListener('keypress', resetInactiveTimer, {{ passive: true }});

    // Send analytics on page unload
    window.addEventListener('beforeunload', sendAnalytics);

    // Fallback: send analytics after 5 minutes
    setTimeout(() => {{
        if (readingActive) {{
            sendAnalytics();
        }}
    }}, 300000); // 5 minutes

    // Initial setup
    resetInactiveTimer();
}})();
</script>"""

    def _extract_post_slug(self, path):
        """Extract post slug from URL path."""
        try:
            parts = [p for p in path.split('/') if p]
            if 'post' in parts:
                post_index = parts.index('post')
                if len(parts) > post_index + 1:
                    return parts[post_index + 1]
        except (IndexError, ValueError):
            pass
        return 'unknown'