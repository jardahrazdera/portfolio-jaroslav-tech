from django.views.generic import ListView, DetailView
from .models import Post


class BlogListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    queryset = Post.objects.filter(is_published=True)
    ordering = ['-created_at']


class BlogDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    queryset = Post.objects.filter(is_published=True)


# Function-based view aliases for URL patterns
post_list = BlogListView.as_view()
post_detail = BlogDetailView.as_view()
