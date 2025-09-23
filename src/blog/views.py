from django.views.generic import ListView, DetailView, TemplateView
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
from django.utils.encoding import smart_str
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import models
from django.db.models import Q, Count
import os
import mimetypes
import json
from .models import Post, Category, Tag, BlogFile


class BlogListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    ordering = ['-created_at']
    paginate_by = 6

    def get_queryset(self):
        # Exclude featured posts from the main pagination to avoid duplicates
        return Post.objects.filter(
            is_published=True,
            is_featured=False
        ).select_related('author').prefetch_related('categories', 'tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add featured posts (limit to 3 maximum)
        context['featured_posts'] = Post.objects.filter(
            is_published=True,
            is_featured=True
        ).select_related('author').prefetch_related('categories', 'tags').order_by('-created_at')[:3]

        # Add categories and tags that have published posts with post counts
        from django.db.models import Count
        context['categories'] = Category.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=models.Q(post__is_published=True))
        ).distinct().order_by('name')
        context['tags'] = Tag.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=models.Q(post__is_published=True))
        ).distinct().order_by('name')
        return context


class BlogDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    queryset = Post.objects.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sharing_data'] = self.object.get_sharing_data(self.request)
        return context


class CategoryListView(ListView):
    model = Post
    template_name = 'blog/category_list.html'
    context_object_name = 'posts'
    ordering = ['-created_at']
    paginate_by = 6

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return Post.objects.filter(
            is_published=True,
            categories=self.category
        ).select_related('author').prefetch_related('categories', 'tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['filter_type'] = 'category'
        # Add all categories and tags for sidebar navigation with post counts
        from django.db.models import Count
        context['categories'] = Category.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=models.Q(post__is_published=True))
        ).distinct().order_by('name')
        context['tags'] = Tag.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=models.Q(post__is_published=True))
        ).distinct().order_by('name')
        return context


class TagListView(ListView):
    model = Post
    template_name = 'blog/tag_list.html'
    context_object_name = 'posts'
    ordering = ['-created_at']
    paginate_by = 6

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs['slug'])
        return Post.objects.filter(
            is_published=True,
            tags=self.tag
        ).select_related('author').prefetch_related('categories', 'tags')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        context['filter_type'] = 'tag'
        # Add all categories and tags for sidebar navigation with post counts
        from django.db.models import Count
        context['categories'] = Category.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=models.Q(post__is_published=True))
        ).distinct().order_by('name')
        context['tags'] = Tag.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=models.Q(post__is_published=True))
        ).distinct().order_by('name')
        return context


class SearchView(ListView):
    model = Post
    template_name = 'blog/search_results.html'
    context_object_name = 'posts'
    ordering = ['-created_at']
    paginate_by = 6

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return Post.objects.none()

        # Search in title, content, and excerpt
        return Post.objects.filter(
            Q(is_published=True) & (
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(excerpt__icontains=query)
            )
        ).select_related('author').prefetch_related('categories', 'tags').distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        context['query'] = query
        context['search_performed'] = bool(query)

        # Add categories and tags for sidebar navigation with post counts
        context['categories'] = Category.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=models.Q(post__is_published=True))
        ).distinct().order_by('name')
        context['tags'] = Tag.objects.filter(
            post__is_published=True
        ).annotate(
            post_count=Count('post', filter=models.Q(post__is_published=True))
        ).distinct().order_by('name')

        return context


def download_file(request, file_id):
    """
    Secure file download view with access control and download tracking.

    Args:
        request: HTTP request object
        file_id: Primary key of the BlogFile to download

    Returns:
        FileResponse: The requested file for download

    Raises:
        Http404: If file doesn't exist or isn't public
    """
    # Get the file object or raise 404
    blog_file = get_object_or_404(BlogFile, pk=file_id)

    # Security checks
    if not blog_file.is_public:
        raise Http404("File not found or not available for download")

    if not blog_file.post.is_published:
        raise Http404("File not found or not available for download")

    # Check if file actually exists on disk
    if not blog_file.file or not os.path.exists(blog_file.file.path):
        raise Http404("File not found on server")

    # Increment download counter
    blog_file.increment_download_count()

    # Prepare file response
    file_path = blog_file.file.path
    file_name = os.path.basename(blog_file.file.name)

    # Guess content type
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'application/octet-stream'

    # Create file response
    response = FileResponse(
        open(file_path, 'rb'),
        content_type=content_type,
        as_attachment=True,
        filename=smart_str(file_name)
    )

    # Add security headers
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Frame-Options'] = 'DENY'

    return response


class EmbedDemoView(TemplateView):
    """Demo page for embedded content functionality."""
    template_name = 'blog/embed_demo.html'


class EmbedGuideView(TemplateView):
    """Guide page for using embedded content in blog posts."""
    template_name = 'blog/embed_guide.html'


class SavedPostsView(TemplateView):
    """Client-side bookmark management page for saved posts."""
    template_name = 'blog/saved_posts.html'


@csrf_exempt
@require_POST
def track_share(request):
    """
    Track social media sharing analytics.
    Accepts POST requests with post_id and platform.
    """
    try:
        data = json.loads(request.body)
        post_id = data.get('post_id')
        platform = data.get('platform')

        # Validate input
        if not post_id or not platform:
            return JsonResponse({'error': 'Missing post_id or platform'}, status=400)

        # Validate platform
        valid_platforms = ['twitter', 'linkedin', 'facebook', 'reddit']
        if platform not in valid_platforms:
            return JsonResponse({'error': 'Invalid platform'}, status=400)

        # Get the post
        try:
            post = Post.objects.get(id=post_id, is_published=True)
        except Post.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)

        # Increment share count
        post.increment_share_count(platform)

        # Return updated counts
        share_counts = post.get_share_counts()

        return JsonResponse({
            'success': True,
            'platform': platform,
            'count': share_counts[platform],
            'total': share_counts['total']
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


# Function-based view aliases for URL patterns
post_list = BlogListView.as_view()
post_detail = BlogDetailView.as_view()
category_list = CategoryListView.as_view()
tag_list = TagListView.as_view()
search = SearchView.as_view()
embed_demo = EmbedDemoView.as_view()
embed_guide = EmbedGuideView.as_view()
saved_posts = SavedPostsView.as_view()
