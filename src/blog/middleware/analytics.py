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

        # Check if analytics script is already injected to prevent duplicates
        if 'reading-analytics.js' in content:
            return response

        # Create the analytics script
        analytics_script = self._create_analytics_script()

        # Inject script before closing body tag
        content = content.replace('</body>', f'{analytics_script}\n</body>')

        # Update response
        response.content = content.encode('utf-8')
        response['Content-Length'] = len(response.content)

        return response

    def _is_blog_post_view(self, request):
        """Check if this is a blog post detail view."""
        try:
            # Check URL pattern for blog post detail pages
            if '/blog/post/' in request.path:
                return True
            return False
        except Exception:
            return False

    def _create_analytics_script(self):
        """Create the analytics tracking script reference."""
        from django.templatetags.static import static

        # Generate the static file URL
        script_url = static('blog/js/reading-analytics.js')

        script = f'<script src="{script_url}" defer></script>'
        return script