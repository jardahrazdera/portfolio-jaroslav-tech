from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from django.db import models
from .models import Post, Category, Tag


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


# Function-based view aliases for URL patterns
post_list = BlogListView.as_view()
post_detail = BlogDetailView.as_view()
category_list = CategoryListView.as_view()
tag_list = TagListView.as_view()
