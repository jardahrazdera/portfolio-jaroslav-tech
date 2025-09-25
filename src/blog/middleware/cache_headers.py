"""
Middleware for setting cache headers on blog responses.
"""
from django.utils.cache import patch_response_headers
from django.conf import settings
from django.urls import resolve
from django.utils import timezone
import mimetypes


class BlogCacheHeadersMiddleware:
    """
    Middleware to set appropriate cache headers for blog content and static files.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only process successful responses
        if response.status_code != 200:
            return response
        
        # Get URL pattern information
        try:
            resolved = resolve(request.path_info)
            app_name = resolved.app_name
            view_name = resolved.view_name
        except:
            app_name = None
            view_name = None
        
        # Set cache headers for blog content
        if app_name == 'blog':
            self._set_blog_cache_headers(request, response, view_name)
        
        # Set cache headers for media files
        elif request.path.startswith(settings.MEDIA_URL):
            self._set_media_cache_headers(request, response)
        
        # Set cache headers for static files (if served by Django in development)
        elif request.path.startswith(settings.STATIC_URL):
            self._set_static_cache_headers(request, response)
        
        return response

    def _set_blog_cache_headers(self, request, response, view_name):
        """Set cache headers for blog views."""
        
        # Different cache settings based on view type
        cache_settings = {
            'blog:post_list': {
                'max_age': 300,  # 5 minutes
                'public': True,
                'vary': ['Accept-Encoding', 'Accept-Language']
            },
            'blog:post_detail': {
                'max_age': 1800,  # 30 minutes
                'public': True,
                'vary': ['Accept-Encoding', 'Accept-Language']
            },
            'blog:category_list': {
                'max_age': 600,  # 10 minutes
                'public': True,
                'vary': ['Accept-Encoding', 'Accept-Language']
            },
            'blog:tag_list': {
                'max_age': 600,  # 10 minutes
                'public': True,
                'vary': ['Accept-Encoding', 'Accept-Language']
            },
            'blog:search': {
                'max_age': 300,  # 5 minutes (search results change frequently)
                'public': True,
                'vary': ['Accept-Encoding', 'Accept-Language']
            },
            'blog:trending_posts': {
                'max_age': 900,  # 15 minutes
                'public': True,
                'vary': ['Accept-Encoding', 'Accept-Language']
            },
            'blog:popular_posts': {
                'max_age': 1200,  # 20 minutes
                'public': True,
                'vary': ['Accept-Encoding', 'Accept-Language']
            },
        }
        
        # Get settings for this view
        settings_key = f'blog:{view_name}' if view_name else None
        cache_config = cache_settings.get(settings_key, {
            'max_age': 300,  # Default 5 minutes
            'public': True,
            'vary': ['Accept-Encoding']
        })
        
        # Apply cache headers
        if cache_config.get('public', True):
            response['Cache-Control'] = f'public, max-age={cache_config["max_age"]}'
        else:
            response['Cache-Control'] = f'private, max-age={cache_config["max_age"]}'
        
        # Set Vary headers
        if 'vary' in cache_config:
            response['Vary'] = ', '.join(cache_config['vary'])
        
        # Set ETag for better caching
        if hasattr(response, 'content') and response.content:
            import hashlib
            etag = hashlib.md5(response.content).hexdigest()[:16]
            response['ETag'] = f'"{etag}"'
        
        # Set Last-Modified for blog posts
        if view_name == 'post_detail' and hasattr(request, 'resolver_match'):
            # Try to get post from view context
            try:
                # This is a simplified approach - in production you might want to
                # extract this from the view or add it to the request
                slug = request.resolver_match.kwargs.get('slug')
                if slug:
                    from blog.models import Post
                    try:
                        post = Post.objects.get(slug=slug, is_published=True)
                        response['Last-Modified'] = post.updated_at.strftime(
                            '%a, %d %b %Y %H:%M:%S GMT'
                        )
                    except Post.DoesNotExist:
                        pass
            except:
                pass

    def _set_media_cache_headers(self, request, response):
        """Set cache headers for media files."""
        
        # Get file extension to determine cache duration
        path = request.path_info
        content_type, _ = mimetypes.guess_type(path)
        
        # Different cache durations based on file type
        if content_type and content_type.startswith('image/'):
            # Images can be cached for a long time
            max_age = 86400 * 30  # 30 days
        elif content_type and content_type.startswith('video/'):
            # Videos can be cached for a long time
            max_age = 86400 * 30  # 30 days
        elif content_type and content_type.startswith('audio/'):
            # Audio files can be cached for a long time
            max_age = 86400 * 30  # 30 days
        elif path.endswith('.pdf'):
            # PDFs can be cached for a moderate time
            max_age = 86400 * 7   # 7 days
        else:
            # Default for other files
            max_age = 86400       # 1 day
        
        response['Cache-Control'] = f'public, max-age={max_age}'
        response['Vary'] = 'Accept-Encoding'
        
        # Add immutable directive for versioned files
        if 'v=' in request.GET or '_' in path:
            response['Cache-Control'] += ', immutable'

    def _set_static_cache_headers(self, request, response):
        """Set cache headers for static files (development only)."""
        
        # In production, static files should be served by nginx/apache
        # This is only for development
        if not settings.DEBUG:
            return
        
        path = request.path_info
        
        # Long cache for assets with hash in filename
        if any(pattern in path for pattern in ['.min.', '-', '.hash.']):
            max_age = 86400 * 365  # 1 year
            response['Cache-Control'] = f'public, max-age={max_age}, immutable'
        else:
            # Shorter cache for other static files
            max_age = 86400  # 1 day
            response['Cache-Control'] = f'public, max-age={max_age}'
        
        response['Vary'] = 'Accept-Encoding'
        
        # Add CORS headers for fonts
        if any(ext in path for ext in ['.woff', '.woff2', '.ttf', '.otf']):
            response['Access-Control-Allow-Origin'] = '*'