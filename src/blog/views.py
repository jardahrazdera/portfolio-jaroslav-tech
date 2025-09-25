from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
from django.utils.encoding import smart_str
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import models
from django.db.models import Q, Count
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.core.exceptions import ValidationError
import os
import mimetypes
import json
import uuid
from .models import Post, Category, Tag, BlogFile, Newsletter
from .forms import NewsletterSubscriptionForm, NewsletterUnsubscribeForm
from .email_service import NewsletterEmailService


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


class NewsletterSubscribeView(FormView):
    """Newsletter subscription view with GDPR compliance."""
    template_name = 'blog/newsletter/subscribe.html'
    form_class = NewsletterSubscriptionForm
    success_url = reverse_lazy('blog:newsletter_success')

    def form_valid(self, form):
        """Process valid subscription form."""
        try:
            newsletter = form.save(request=self.request)

            # Store email in session for success page
            self.request.session['newsletter_email'] = newsletter.email

            # Send confirmation email
            email_sent = NewsletterEmailService.send_confirmation_email(newsletter, self.request)

            if email_sent:
                messages.success(
                    self.request,
                    f"Thank you! A confirmation email has been sent to {newsletter.email}. "
                    f"Please check your inbox and click the confirmation link to complete your subscription."
                )
            else:
                messages.warning(
                    self.request,
                    f"Your subscription has been registered, but we couldn't send the confirmation email. "
                    f"Please contact us if you don't receive the confirmation email within a few minutes."
                )

            return super().form_valid(form)

        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        except Exception as e:
            messages.error(
                self.request,
                "Sorry, there was an error processing your subscription. Please try again later."
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add extra context for the template."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Subscribe to Newsletter"
        return context


class NewsletterSuccessView(TemplateView):
    """Success page after newsletter subscription."""
    template_name = 'blog/newsletter/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email'] = self.request.session.get('newsletter_email', '')
        context['page_title'] = "Subscription Successful"
        return context


def confirm_newsletter_subscription(request, token):
    """Confirm newsletter subscription via token."""
    try:
        # Convert string token to UUID
        token_uuid = uuid.UUID(str(token))
        newsletter = get_object_or_404(Newsletter, confirmation_token=token_uuid)

        if newsletter.is_confirmed:
            messages.info(
                request,
                f"Your email {newsletter.email} is already confirmed and subscribed to our newsletter."
            )
        else:
            newsletter.confirm_subscription()

            # Send welcome email
            NewsletterEmailService.send_welcome_email(newsletter, request)

            messages.success(
                request,
                f"Great! Your email {newsletter.email} has been confirmed. "
                f"You're now subscribed to our newsletter."
            )

        return render(request, 'blog/newsletter/confirmed.html', {
            'newsletter': newsletter,
            'page_title': 'Subscription Confirmed'
        })

    except (ValueError, ValidationError):
        messages.error(request, "Invalid confirmation link. Please try subscribing again.")
        return redirect('blog:newsletter_subscribe')


def unsubscribe_newsletter(request, token):
    """Unsubscribe from newsletter via token."""
    try:
        # Convert string token to UUID
        token_uuid = uuid.UUID(str(token))
        newsletter = get_object_or_404(Newsletter, unsubscribe_token=token_uuid)

        if request.method == 'POST':
            form = NewsletterUnsubscribeForm(request.POST)
            if form.is_valid():
                newsletter.unsubscribe()

                # Log feedback if provided (for future improvement)
                reason = form.cleaned_data.get('reason')
                feedback = form.cleaned_data.get('feedback')

                # TODO: Log unsubscribe feedback for analytics

                messages.success(
                    request,
                    f"You have been successfully unsubscribed from our newsletter. "
                    f"We're sorry to see you go!"
                )

                return render(request, 'blog/newsletter/unsubscribed.html', {
                    'newsletter': newsletter,
                    'page_title': 'Unsubscribed Successfully'
                })
        else:
            form = NewsletterUnsubscribeForm()

        return render(request, 'blog/newsletter/unsubscribe.html', {
            'form': form,
            'newsletter': newsletter,
            'page_title': 'Unsubscribe from Newsletter'
        })

    except (ValueError, ValidationError):
        messages.error(request, "Invalid unsubscribe link. Please contact us for assistance.")
        return redirect('blog:post_list')


@csrf_exempt
@require_POST
def newsletter_subscribe_ajax(request):
    """AJAX endpoint for newsletter subscription from form components."""
    try:
        form = NewsletterSubscriptionForm(request.POST)

        if form.is_valid():
            newsletter = form.save(request=request)

            # Send confirmation email
            email_sent = NewsletterEmailService.send_confirmation_email(newsletter, request)

            if email_sent:
                return JsonResponse({
                    'success': True,
                    'message': f'Thank you! A confirmation email has been sent to {newsletter.email}. '
                              f'Please check your inbox to complete your subscription.',
                    'email': newsletter.email
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': f'Your subscription has been registered, but we couldn\'t send the confirmation email. '
                              f'Please contact us if you don\'t receive it within a few minutes.',
                    'email': newsletter.email
                })
        else:
            # Return form errors
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = [str(error) for error in field_errors]

            return JsonResponse({
                'success': False,
                'errors': errors,
                'message': 'Please correct the errors below.'
            }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Sorry, there was an error processing your subscription. Please try again later.'
        }, status=500)


# Function-based view aliases for URL patterns
post_list = BlogListView.as_view()
post_detail = BlogDetailView.as_view()
category_list = CategoryListView.as_view()
tag_list = TagListView.as_view()
search = SearchView.as_view()
embed_demo = EmbedDemoView.as_view()
embed_guide = EmbedGuideView.as_view()
saved_posts = SavedPostsView.as_view()
newsletter_subscribe = NewsletterSubscribeView.as_view()
newsletter_success = NewsletterSuccessView.as_view()


def newsletter_unsubscribe_general(request):
    """General unsubscribe page for people without a token."""
    context = {
        'page_title': 'Unsubscribe from Newsletter'
    }
    return render(request, 'blog/newsletter/unsubscribe_general.html', context)


@require_POST
def track_related_click(request):
    """Track related post clicks for analytics."""
    import json
    import logging
    from django.http import JsonResponse
    from django.views.decorators.http import require_POST
    from django.views.decorators.csrf import csrf_protect

    logger = logging.getLogger(__name__)

    try:
        data = json.loads(request.body)
        source_post_slug = data.get('source_post')
        target_post_slug = data.get('target_post')
        context = data.get('context', 'unknown')
        layout_type = data.get('layout_type', 'default')

        # Log the click for analytics
        logger.info(f"Related post click: {source_post_slug} -> {target_post_slug} (context: {context}, layout: {layout_type})")

        # In a production environment, you might want to:
        # 1. Store clicks in a database table for analytics
        # 2. Send to Google Analytics or other analytics services
        # 3. Use for improving the recommendation algorithm

        # Basic response for now
        return JsonResponse({
            'success': True,
            'message': 'Click tracked successfully'
        })

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Invalid related post click tracking data: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Invalid data format'
        }, status=400)

    except Exception as e:
        logger.error(f"Error tracking related post click: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


def related_posts_ajax(request, slug):
    """AJAX endpoint for loading more related posts."""
    import json
    from django.http import JsonResponse
    from django.core.serializers.json import DjangoJSONEncoder

    try:
        # Get the source post
        post = get_object_or_404(Post, slug=slug, is_published=True)

        # Get pagination parameters
        offset = int(request.GET.get('offset', 0))
        count = min(int(request.GET.get('count', 4)), 10)  # Max 10 posts per request
        layout_type = request.GET.get('layout', 'default')

        # Get related posts using the advanced algorithm
        all_related = post.get_related_posts(count=offset + count, layout_type=layout_type)

        # Slice to get only the new posts
        new_posts = all_related['posts'][offset:offset + count]

        # Serialize the posts for JSON response
        posts_data = []
        for item in new_posts:
            post_data = {
                'title': item['post'].title,
                'slug': item['post'].slug,
                'url': item['post'].get_absolute_url(),
                'excerpt': item['post'].get_meta_description()[:100],
                'reading_time': item['reading_time'],
                'engagement_hints': item['engagement_hints'],
                'primary_category': {
                    'name': item['primary_category'].name,
                    'slug': item['primary_category'].slug
                } if item['primary_category'] else None,
                'featured_image_url': item['post'].featured_image.url if item['post'].featured_image else None,
                'similarity_score': item['similarity_score']
            }
            posts_data.append(post_data)

        return JsonResponse({
            'success': True,
            'posts': posts_data,
            'has_more': len(all_related['posts']) > offset + count,
            'total_available': len(all_related['posts'])
        })

    except Post.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Post not found'
        }, status=404)

    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid parameters: {e}'
        }, status=400)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading related posts AJAX for {slug}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)
