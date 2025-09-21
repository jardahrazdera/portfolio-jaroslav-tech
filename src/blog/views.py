from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404, FileResponse
from django.utils.encoding import smart_str
from django.db import models
from django.db.models import Q, Count
import os
import mimetypes
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


# Function-based view aliases for URL patterns
post_list = BlogListView.as_view()
post_detail = BlogDetailView.as_view()
category_list = CategoryListView.as_view()
tag_list = TagListView.as_view()
search = SearchView.as_view()
