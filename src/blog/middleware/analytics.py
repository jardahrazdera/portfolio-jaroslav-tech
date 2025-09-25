"""
Analytics middleware for reading tracking and engagement measurement.
"""
from django.utils.deprecation import MiddlewareMixin


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

        # Only inject for successful responses
        if response.status_code != 200:
            return response

        # Get response content
        content = response.content.decode('utf-8', errors='ignore')

        # Check if </body> tag exists (should be there for valid HTML)
        if '</body>' not in content:
            return response

        # Create the analytics script
        analytics_script = self._create_analytics_script(request)

        # Inject script before closing body tag
        content = content.replace('</body>', f'{analytics_script}\n</body>')

        # Update response
        response.content = content.encode('utf-8')
        response['Content-Length'] = len(response.content)

        return response

    def _is_blog_post_view(self, request):
        """Check if this is a blog post detail view."""
        try:
            # Check URL pattern
            if '/blog/' in request.path and request.path.count('/') >= 3:
                # Pattern like /blog/post-slug/ or /blog/category/post-slug/
                return True
            return False
        except:
            return False

    def _create_analytics_script(self, request):
        """Create the analytics tracking script."""
        script = """
        <script>
        (function() {
            // Reading analytics for blog posts
            let startTime = Date.now();
            let maxScrollPercent = 0;
            let readingCompleted = false;

            // Get post slug from URL
            const pathParts = window.location.pathname.split('/').filter(p => p);
            const postSlug = pathParts[pathParts.length - 1];

            if (!postSlug) return;

            // Track scroll progress
            function updateScrollProgress() {
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
                const scrollPercent = Math.round((scrollTop / docHeight) * 100);

                maxScrollPercent = Math.max(maxScrollPercent, scrollPercent);

                // Consider reading completed if user scrolled past 80%
                if (scrollPercent > 80) {
                    readingCompleted = true;
                }
            }

            // Send reading data to server
            function sendReadingData() {
                const readingTime = Math.round((Date.now() - startTime) / 1000);

                // Only send if user spent at least 10 seconds reading
                if (readingTime < 10) return;

                fetch('/blog/track-reading/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        post_slug: postSlug,
                        reading_time_seconds: readingTime,
                        max_scroll_percent: maxScrollPercent,
                        completed_reading: readingCompleted
                    })
                }).catch(err => console.debug('Reading tracking failed:', err));
            }

            // Throttled scroll handler
            let scrollTimeout;
            window.addEventListener('scroll', function() {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(updateScrollProgress, 100);
            });

            // Send data on page unload
            window.addEventListener('beforeunload', sendReadingData);

            // Also send data periodically for long reading sessions
            setInterval(sendReadingData, 60000); // Every minute
        })();
        </script>
        """
        return script