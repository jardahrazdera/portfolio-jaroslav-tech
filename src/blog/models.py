import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import EmailValidator
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field
from .image_utils import ImageProcessor
from .file_utils import FileValidator, generate_file_path, get_file_type, format_file_size


class PostManager(models.Manager):
    """Custom manager for Post model with optimized query methods."""

    def published(self):
        """Get published posts with related data pre-loaded."""
        return self.filter(is_published=True).select_related('author').prefetch_related('categories', 'tags')

    def featured(self):
        """Get featured published posts with related data."""
        return self.published().filter(is_featured=True)

    def by_category(self, category_slug):
        """Get published posts in a specific category."""
        return self.published().filter(categories__slug=category_slug).distinct()

    def by_tag(self, tag_slug):
        """Get published posts with a specific tag."""
        return self.published().filter(tags__slug=tag_slug).distinct()

    def by_author(self, author_id):
        """Get published posts by a specific author."""
        return self.published().filter(author_id=author_id)

    def search(self, query):
        """Search published posts by title, content, or excerpt with PostgreSQL full-text search."""
        if not query:
            return self.none()

        from django.db.models import Q
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
        import re

        # Clean the query
        query = re.sub(r'[^\w\s-]', '', query.strip())
        if not query:
            return self.none()

        try:
            # Use PostgreSQL full-text search if available
            search_vector = SearchVector('title', weight='A') + SearchVector('content', weight='B') + SearchVector('excerpt', weight='C')
            search_query = SearchQuery(query)

            return self.published().annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).filter(search=search_query).order_by('-rank', '-created_at')

        except Exception:
            # Fallback to icontains search for non-PostgreSQL databases
            return self.published().filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(excerpt__icontains=query)
            ).distinct()

    def recent(self, count=10):
        """Get recent published posts."""
        return self.published().order_by('-created_at')[:count]

    def popular_by_views(self, days=30, count=10):
        """Get popular posts by view count in the last N days."""
        from django.utils import timezone
        from django.db.models import Count, Q

        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.published().filter(
            views__viewed_at__gte=cutoff_date
        ).annotate(
            view_count=Count('views', filter=Q(views__viewed_at__gte=cutoff_date))
        ).order_by('-view_count')[:count]

    def with_attachments(self):
        """Get posts that have file attachments."""
        return self.published().filter(attachments__isnull=False).prefetch_related('attachments').distinct()


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=['slug']),  # Category slug lookups
            models.Index(fields=['name']),  # Category name ordering/search
        ]


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    color = models.CharField(max_length=7, default='#CBA6F7')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['slug']),  # Tag slug lookups
            models.Index(fields=['name']),  # Tag name ordering/search
        ]


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = CKEditor5Field('Text', config_name='extends')
    excerpt = models.TextField(blank=True)
    featured_image = models.ImageField(upload_to='blog/images/', blank=True, null=True, help_text='Featured image for the blog post')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text='Featured posts appear prominently on the blog homepage')

    # SEO Meta Fields
    meta_description = models.TextField(
        max_length=155,
        blank=True,
        help_text='SEO meta description (max 155 characters, will fall back to excerpt if empty)'
    )
    meta_keywords = models.CharField(
        max_length=255,
        blank=True,
        help_text='SEO keywords, comma-separated (will auto-generate from tags if empty)'
    )

    # External Discussion Link
    discussion_url = models.URLField(
        blank=True,
        max_length=500,
        help_text='Link to external discussion (Twitter thread, LinkedIn post, Reddit discussion, etc.)'
    )

    # Sharing Analytics (Basic)
    share_count_twitter = models.PositiveIntegerField(default=0, help_text='Number of Twitter shares')
    share_count_linkedin = models.PositiveIntegerField(default=0, help_text='Number of LinkedIn shares')
    share_count_facebook = models.PositiveIntegerField(default=0, help_text='Number of Facebook shares')
    share_count_reddit = models.PositiveIntegerField(default=0, help_text='Number of Reddit shares')
    total_shares = models.PositiveIntegerField(default=0, help_text='Total number of shares across all platforms')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Custom manager with optimized query methods
    objects = PostManager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        # Check if this is a new image or the image has changed
        process_image = False
        old_image_name = None

        if self.pk:
            try:
                old_post = Post.objects.get(pk=self.pk)
                if old_post.featured_image != self.featured_image:
                    process_image = True
                    if old_post.featured_image:
                        old_image_name = os.path.splitext(os.path.basename(old_post.featured_image.name))[0]
            except Post.DoesNotExist:
                process_image = True
        else:
            process_image = True

        super().save(*args, **kwargs)

        # Process the image after saving to ensure we have a pk
        if process_image and self.featured_image:
            # Clean up old processed images if they exist
            if old_image_name:
                ImageProcessor.cleanup_processed_images(old_image_name)

            # Process new image
            base_name = f"post_{self.pk}_{os.path.splitext(os.path.basename(self.featured_image.name))[0]}"
            ImageProcessor.process_image(self.featured_image, base_name)

    def delete(self, *args, **kwargs):
        # Clean up processed images when post is deleted
        if self.featured_image:
            base_name = f"post_{self.pk}_{os.path.splitext(os.path.basename(self.featured_image.name))[0]}"
            ImageProcessor.cleanup_processed_images(base_name)
        super().delete(*args, **kwargs)

    def get_image_base_name(self):
        """Get the base name used for processed images."""
        if self.featured_image:
            return f"post_{self.pk}_{os.path.splitext(os.path.basename(self.featured_image.name))[0]}"
        return None

    def get_absolute_url(self):
        """Get the absolute URL for this post."""
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    def get_meta_description(self):
        """Get SEO meta description, falling back to excerpt if empty."""
        if self.meta_description:
            return self.meta_description[:155]
        elif self.excerpt:
            return self.excerpt[:155]
        else:
            # Strip HTML tags from content and truncate
            import re
            content_text = re.sub(r'<[^>]+>', '', self.content)
            return content_text[:155].strip()

    def get_meta_keywords(self):
        """Get SEO keywords, auto-generating from tags if empty."""
        if self.meta_keywords:
            return self.meta_keywords
        else:
            return ', '.join([tag.name for tag in self.tags.all()])

    def get_reading_time(self):
        """Calculate estimated reading time in minutes."""
        import re
        # Strip HTML tags and count words
        content_text = re.sub(r'<[^>]+>', '', self.content)
        word_count = len(content_text.split())
        # Average reading speed: 200 words per minute
        reading_time = max(1, round(word_count / 200))
        return reading_time

    def get_discussion_platform(self):
        """Detect the discussion platform from the URL."""
        if not self.discussion_url:
            return None

        url = self.discussion_url.lower()

        if 'twitter.com' in url or 'x.com' in url:
            return {
                'name': 'Twitter',
                'icon': 'fab fa-twitter',
                'color': '#1DA1F2',
                'label': 'Join the discussion on Twitter'
            }
        elif 'linkedin.com' in url:
            return {
                'name': 'LinkedIn',
                'icon': 'fab fa-linkedin',
                'color': '#0077B5',
                'label': 'Join the discussion on LinkedIn'
            }
        elif 'reddit.com' in url:
            return {
                'name': 'Reddit',
                'icon': 'fab fa-reddit',
                'color': '#FF4500',
                'label': 'Join the discussion on Reddit'
            }
        elif 'news.ycombinator.com' in url:
            return {
                'name': 'Hacker News',
                'icon': 'fab fa-hacker-news',
                'color': '#FF6600',
                'label': 'Join the discussion on Hacker News'
            }
        elif 'github.com' in url:
            return {
                'name': 'GitHub',
                'icon': 'fab fa-github',
                'color': '#333',
                'label': 'Join the discussion on GitHub'
            }
        elif 'dev.to' in url:
            return {
                'name': 'DEV',
                'icon': 'fab fa-dev',
                'color': '#0A0A0A',
                'label': 'Join the discussion on DEV'
            }
        elif 'hashnode.com' in url:
            return {
                'name': 'Hashnode',
                'icon': 'fas fa-hashtag',
                'color': '#2962FF',
                'label': 'Join the discussion on Hashnode'
            }
        else:
            return {
                'name': 'External Discussion',
                'icon': 'fas fa-external-link-alt',
                'color': 'var(--mauve)',
                'label': 'Join the external discussion'
            }

    def get_sharing_data(self, request=None):
        """Generate platform-specific sharing data with discussion prompts."""
        import urllib.parse

        if request:
            post_url = request.build_absolute_uri(self.get_absolute_url())
        else:
            post_url = f"https://jaroslav.tech{self.get_absolute_url()}"

        # Create engaging discussion prompts based on post content
        base_prompt = f"Just read this insightful post: \"{self.title}\""

        # Generate category-based prompts
        categories = list(self.categories.all())
        if categories:
            category_names = [cat.name.lower() for cat in categories]
            if any(cat in ['tutorial', 'guide', 'how-to'] for cat in category_names):
                discussion_prompt = "Have you tried this approach? What's been your experience?"
            elif any(cat in ['opinion', 'thoughts', 'analysis'] for cat in category_names):
                discussion_prompt = "What's your take on this? Do you agree or see it differently?"
            elif any(cat in ['news', 'updates', 'announcement'] for cat in category_names):
                discussion_prompt = "Thoughts on this development? How might it impact the industry?"
            elif any(cat in ['review', 'comparison'] for cat in category_names):
                discussion_prompt = "What has your experience been? Any other alternatives you'd recommend?"
            else:
                discussion_prompt = "What are your thoughts? Have you encountered similar challenges or insights?"
        else:
            discussion_prompt = "What are your thoughts? I'd love to hear your perspective on this!"

        # Get relevant hashtags from tags
        tags = list(self.tags.all())
        hashtags = []
        if tags:
            # Limit to 3-4 most relevant tags for each platform
            for tag in tags[:4]:
                hashtag = tag.name.replace(' ', '').replace('-', '').replace('_', '')
                if hashtag.isalnum():
                    hashtags.append(f"#{hashtag}")

        return {
            'twitter': {
                'name': 'Twitter/X',
                'icon': 'fab fa-x-twitter',
                'color': '#000000',
                'url': self._generate_twitter_share_url(post_url, base_prompt, discussion_prompt, hashtags),
                'text': f"{base_prompt} {discussion_prompt}",
                'prompt': "Share your thoughts on Twitter and start a conversation!"
            },
            'linkedin': {
                'name': 'LinkedIn',
                'icon': 'fab fa-linkedin',
                'color': '#0077B5',
                'url': self._generate_linkedin_share_url(post_url, base_prompt, discussion_prompt),
                'text': f"{base_prompt} {discussion_prompt} #TechInsights #WebDevelopment",
                'prompt': "Share with your professional network on LinkedIn!"
            },
            'facebook': {
                'name': 'Facebook',
                'icon': 'fab fa-facebook',
                'color': '#1877F2',
                'url': self._generate_facebook_share_url(post_url),
                'text': f"{base_prompt} {discussion_prompt}",
                'prompt': "Share with friends and start a discussion!"
            },
            'reddit': {
                'name': 'Reddit',
                'icon': 'fab fa-reddit',
                'color': '#FF4500',
                'url': self._generate_reddit_share_url(post_url, self.title),
                'text': f"Found this interesting article: \"{self.title}\" - {discussion_prompt}",
                'prompt': "Share in relevant subreddits and get community feedback!"
            }
        }

    def _generate_twitter_share_url(self, post_url, base_prompt, discussion_prompt, hashtags):
        """Generate Twitter/X share URL with optimized text."""
        import urllib.parse

        # Twitter has 280 char limit, so we need to be strategic
        hashtag_text = ' '.join(hashtags[:3]) if hashtags else ''  # Max 3 hashtags

        # Calculate available space for content
        url_length = 23  # Twitter's t.co URL length
        hashtag_length = len(hashtag_text)
        available_space = 280 - url_length - hashtag_length - 4  # 4 for spaces

        # Trim content to fit
        full_text = f"{base_prompt} {discussion_prompt}"
        if len(full_text) > available_space:
            # Prioritize the discussion prompt
            if len(discussion_prompt) + 10 < available_space:  # 10 for "Just read: "
                content = f"Just read: \"{self.title[:available_space-len(discussion_prompt)-15]}...\" {discussion_prompt}"
            else:
                content = full_text[:available_space-3] + "..."
        else:
            content = full_text

        tweet_text = f"{content} {hashtag_text}".strip()

        return f"https://twitter.com/intent/tweet?text={urllib.parse.quote(tweet_text)}&url={urllib.parse.quote(post_url)}"

    def _generate_linkedin_share_url(self, post_url, base_prompt, discussion_prompt):
        """Generate LinkedIn share URL."""
        import urllib.parse

        summary = f"{base_prompt} {discussion_prompt} What's your experience with this? #TechInsights #WebDevelopment"

        return f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(post_url)}"

    def _generate_facebook_share_url(self, post_url):
        """Generate Facebook share URL."""
        import urllib.parse

        return f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(post_url)}"

    def _generate_reddit_share_url(self, post_url, title):
        """Generate Reddit share URL."""
        import urllib.parse

        return f"https://www.reddit.com/submit?url={urllib.parse.quote(post_url)}&title={urllib.parse.quote(title)}"

    def increment_share_count(self, platform):
        """Increment share count for a specific platform."""
        platform_map = {
            'twitter': 'share_count_twitter',
            'linkedin': 'share_count_linkedin',
            'facebook': 'share_count_facebook',
            'reddit': 'share_count_reddit'
        }

        if platform in platform_map:
            field_name = platform_map[platform]
            current_count = getattr(self, field_name)
            setattr(self, field_name, current_count + 1)

            # Update total shares
            self.total_shares = (
                self.share_count_twitter +
                self.share_count_linkedin +
                self.share_count_facebook +
                self.share_count_reddit
            )

            self.save(update_fields=[field_name, 'total_shares'])

    def get_share_counts(self):
        """Get sharing statistics for this post."""
        return {
            'twitter': self.share_count_twitter,
            'linkedin': self.share_count_linkedin,
            'facebook': self.share_count_facebook,
            'reddit': self.share_count_reddit,
            'total': self.total_shares
        }

    def get_related_posts(self, count=6, layout_type='default'):
        """Get related posts using advanced similarity algorithm."""
        from .related_posts_service import RelatedPostsService
        service = RelatedPostsService(self)
        return service.get_related_posts(count=count, layout_type=layout_type)

    def get_related_by_category(self, count=4):
        """Get related posts from the same categories (fallback method)."""
        from .related_posts_service import RelatedPostsService
        service = RelatedPostsService(self)
        return service.get_related_by_category(count=count)

    def get_more_from_author(self, count=3):
        """Get more posts from the same author."""
        from .related_posts_service import RelatedPostsService
        service = RelatedPostsService(self)
        return service.get_more_from_author(count=count)

    def get_reading_recommendations(self, context='bottom'):
        """
        Get reading recommendations based on context.

        Args:
            context (str): 'sidebar', 'bottom', 'cards', 'minimal'

        Returns:
            dict: Context-appropriate recommendations with metadata
        """
        from .related_posts_service import RelatedPostsService
        service = RelatedPostsService(self)

        if context == 'sidebar':
            # Compact sidebar display
            related = service.get_related_posts(count=4, layout_type='sidebar')
            return {
                'primary': related,
                'fallback_category': service.get_related_by_category(count=2),
                'layout_hints': {
                    'compact': True,
                    'show_images': False,
                    'show_excerpt': False,
                    'show_reading_time': True
                }
            }
        elif context == 'bottom':
            # Full-width bottom section
            related = service.get_related_posts(count=6, layout_type='grid')
            return {
                'primary': related,
                'more_from_author': service.get_more_from_author(count=3),
                'from_category': service.get_related_by_category(count=3),
                'layout_hints': {
                    'compact': False,
                    'show_images': True,
                    'show_excerpt': True,
                    'show_reading_time': True,
                    'grid_columns': 3
                }
            }
        elif context == 'cards':
            # Card-based display
            related = service.get_related_posts(count=4, layout_type='cards')
            return {
                'primary': related,
                'layout_hints': {
                    'card_style': True,
                    'show_images': True,
                    'show_excerpt': True,
                    'show_engagement_hints': True
                }
            }
        else:  # minimal
            related = service.get_related_posts(count=3, layout_type='minimal')
            return {
                'primary': related,
                'layout_hints': {
                    'minimal': True,
                    'show_title_only': True
                }
            }

    def get_sidebar_recommendations(self):
        """Get recommendations specifically for sidebar display."""
        return self.get_reading_recommendations(context='sidebar')

    def get_view_count(self, period=None):
        """
        Get view count for this post.

        Args:
            period (str): 'week', 'month', or None for all-time

        Returns:
            int: Number of views
        """
        from django.utils import timezone
        from django.db.models import Count

        views = self.views.all()

        if period == 'week':
            cutoff = timezone.now() - timezone.timedelta(days=7)
            views = views.filter(viewed_at__gte=cutoff)
        elif period == 'month':
            cutoff = timezone.now() - timezone.timedelta(days=30)
            views = views.filter(viewed_at__gte=cutoff)

        return views.count()

    def get_reading_completion_rate(self):
        """
        Get reading completion rate as percentage.

        Returns:
            float: Percentage of viewers who completed reading
        """
        total_views = self.views.count()
        if total_views == 0:
            return 0.0

        completed_views = self.views.filter(completed_reading=True).count()
        return (completed_views / total_views) * 100

    def get_average_reading_time(self):
        """
        Get average reading time in seconds.

        Returns:
            float: Average reading time or None if no data
        """
        from django.db.models import Avg

        result = self.views.filter(
            reading_time_seconds__isnull=False
        ).aggregate(avg_time=Avg('reading_time_seconds'))

        return result['avg_time']

    def is_trending(self, days=7, min_views=5):
        """
        Check if this post is currently trending.

        Args:
            days (int): Period to check for trending
            min_views (int): Minimum views to consider trending

        Returns:
            bool: True if post is trending
        """
        recent_views = self.get_view_count(period='week' if days == 7 else None)
        return recent_views >= min_views

    def get_view_stats(self):
        """
        Get comprehensive view statistics for this post.

        Returns:
            dict: Statistics including view counts, completion rate, etc.
        """
        return {
            'total_views': self.get_view_count(),
            'weekly_views': self.get_view_count(period='week'),
            'monthly_views': self.get_view_count(period='month'),
            'completion_rate': self.get_reading_completion_rate(),
            'average_reading_time': self.get_average_reading_time(),
            'is_trending': self.is_trending(),
        }

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),  # Slug lookups (already unique, but explicit index)
            models.Index(fields=['is_published', '-created_at']),  # Published posts ordered by date
            models.Index(fields=['is_featured', 'is_published']),  # Featured published posts
            models.Index(fields=['author', 'is_published']),  # Posts by author
            models.Index(fields=['-created_at']),  # Date ordering
            models.Index(fields=['is_published', 'title']),  # Search by title
        ]


class BlogFile(models.Model):
    """File attachments for blog posts."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(
        upload_to=generate_file_path,
        validators=[FileValidator()],
        help_text='Upload a document, archive, or code file to attach to this blog post'
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text='Display title for the file (defaults to filename)'
    )
    description = models.TextField(
        blank=True,
        help_text='Optional description of the file contents'
    )
    is_public = models.BooleanField(
        default=True,
        help_text='Whether this file is publicly downloadable'
    )
    download_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of times this file has been downloaded'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Set title to filename if not provided
        if not self.title and self.file:
            self.title = os.path.splitext(os.path.basename(self.file.name))[0]
        super().save(*args, **kwargs)

    def get_file_info(self):
        """Get file type information including icon and description."""
        if self.file:
            return get_file_type(self.file.name)
        return None

    def get_file_size_display(self):
        """Get human-readable file size."""
        if self.file:
            return format_file_size(self.file.size)
        return "Unknown"

    def increment_download_count(self):
        """Increment download counter."""
        self.download_count += 1
        self.save(update_fields=['download_count'])

    def delete(self, *args, **kwargs):
        """Override delete to clean up file before deleting the model instance."""
        # Store file path before deletion
        file_path = self.file.path if self.file else None

        # Delete the model instance first
        super().delete(*args, **kwargs)

        # Then clean up the physical file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)

                # Clean up empty directories
                file_dir = os.path.dirname(file_path)
                if 'blog/files' in file_dir and os.path.exists(file_dir):
                    if not os.listdir(file_dir):
                        os.rmdir(file_dir)

                        # Also check parent directory
                        parent_dir = os.path.dirname(file_dir)
                        if 'blog/files' in parent_dir and os.path.exists(parent_dir):
                            if not os.listdir(parent_dir):
                                os.rmdir(parent_dir)
            except OSError:
                # File might be in use or permission denied
                pass

    def __str__(self):
        return f"{self.title or self.file.name} - {self.post.title}"

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Blog File"
        verbose_name_plural = "Blog Files"


class PostView(models.Model):
    """
    Privacy-friendly post view tracking model.
    Tracks page views without storing any personal data or IP addresses.
    """

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='views',
        help_text='Post being viewed'
    )

    # Privacy-friendly tracking - no IP addresses or personal data
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the view occurred',
        db_index=True  # Index for fast time-based queries
    )

    # Optional reading engagement data
    reading_time_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='How long user spent reading (seconds) - tracked via JavaScript'
    )

    completed_reading = models.BooleanField(
        default=False,
        help_text='Whether user scrolled to end of article'
    )

    # Technical metadata (no personal data)
    user_agent_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text='Hashed user agent for bot detection (no personal data stored)',
        db_index=True
    )

    referrer_domain = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Domain of referring site (no full URLs stored)'
    )

    # Session-based duplicate prevention (no personal tracking)
    session_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text='Anonymized session identifier for duplicate view prevention',
        db_index=True
    )

    class Meta:
        verbose_name = "Post View"
        verbose_name_plural = "Post Views"
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['post', '-viewed_at']),  # Fast post-specific queries
            models.Index(fields=['-viewed_at']),          # Trending queries
            models.Index(fields=['post', 'session_hash']), # Duplicate prevention
        ]

    def __str__(self):
        return f"View of '{self.post.title}' at {self.viewed_at.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def get_trending_posts(cls, days=7, limit=10):
        """
        Get trending posts based on recent views.

        Args:
            days (int): Number of days to look back
            limit (int): Maximum number of posts to return

        Returns:
            QuerySet: Posts ordered by view count in specified period
        """
        from django.utils import timezone
        from django.db.models import Count

        cutoff_date = timezone.now() - timezone.timedelta(days=days)

        return Post.objects.filter(
            is_published=True,
            views__viewed_at__gte=cutoff_date
        ).annotate(
            recent_views=Count('views', filter=models.Q(views__viewed_at__gte=cutoff_date))
        ).filter(
            recent_views__gt=0
        ).order_by('-recent_views')[:limit]

    @classmethod
    def get_popular_posts(cls, period='week', limit=10):
        """
        Get popular posts for different time periods.

        Args:
            period (str): 'week', 'month', or 'all_time'
            limit (int): Maximum number of posts to return

        Returns:
            QuerySet: Posts with view counts
        """
        from django.utils import timezone
        from django.db.models import Count

        now = timezone.now()

        if period == 'week':
            cutoff = now - timezone.timedelta(days=7)
        elif period == 'month':
            cutoff = now - timezone.timedelta(days=30)
        else:  # all_time
            cutoff = None

        queryset = Post.objects.filter(is_published=True)

        if cutoff:
            queryset = queryset.annotate(
                period_views=Count('views', filter=models.Q(views__viewed_at__gte=cutoff))
            ).filter(period_views__gt=0).order_by('-period_views')
        else:
            queryset = queryset.annotate(
                total_views=Count('views')
            ).filter(total_views__gt=0).order_by('-total_views')

        return queryset[:limit]

    @classmethod
    def add_view(cls, post, request=None, reading_data=None):
        """
        Add a privacy-friendly page view.

        Args:
            post: Post instance being viewed
            request: HTTP request (optional, for metadata)
            reading_data: Dict with reading engagement data (optional)

        Returns:
            PostView: Created view instance or None if duplicate
        """
        import hashlib
        from urllib.parse import urlparse

        # Create session hash for duplicate prevention (no personal data)
        session_key = request.session.session_key if request and hasattr(request, 'session') else None
        session_hash = None

        if session_key:
            # Hash the session key so we don't store personal data
            session_hash = hashlib.sha256(session_key.encode()).hexdigest()

            # Check for duplicate views in the last hour
            from django.utils import timezone
            recent_cutoff = timezone.now() - timezone.timedelta(hours=1)

            if cls.objects.filter(
                post=post,
                session_hash=session_hash,
                viewed_at__gte=recent_cutoff
            ).exists():
                return None  # Duplicate view, don't count

        # Process user agent (hash only, no personal data)
        user_agent_hash = None
        if request and request.META.get('HTTP_USER_AGENT'):
            user_agent = request.META['HTTP_USER_AGENT']
            user_agent_hash = hashlib.md5(user_agent.encode()).hexdigest()

        # Process referrer (domain only, no personal data)
        referrer_domain = None
        if request and request.META.get('HTTP_REFERER'):
            try:
                parsed = urlparse(request.META['HTTP_REFERER'])
                referrer_domain = parsed.netloc[:100]  # Limit length
            except:
                pass

        # Create view record
        view_data = {
            'post': post,
            'session_hash': session_hash,
            'user_agent_hash': user_agent_hash,
            'referrer_domain': referrer_domain,
        }

        # Add reading engagement data if provided
        if reading_data:
            if 'reading_time_seconds' in reading_data:
                view_data['reading_time_seconds'] = reading_data['reading_time_seconds']
            if 'completed_reading' in reading_data:
                view_data['completed_reading'] = reading_data['completed_reading']

        return cls.objects.create(**view_data)


class Newsletter(models.Model):
    """Newsletter subscription model with GDPR compliance and double opt-in."""

    # Core fields
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text='Subscriber email address'
    )

    # Subscription status
    is_active = models.BooleanField(
        default=False,
        help_text='Whether the subscription is active (confirmed)'
    )
    is_confirmed = models.BooleanField(
        default=False,
        help_text='Whether the email has been confirmed via double opt-in'
    )

    # GDPR compliance
    confirmation_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text='Unique token for email confirmation'
    )
    unsubscribe_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text='Unique token for unsubscribing'
    )

    # Timestamps
    subscribed_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the subscription was first created'
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the email was confirmed'
    )
    unsubscribed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the subscription was cancelled'
    )

    # Metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address when subscribed (for compliance tracking)'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='User agent when subscribed (for compliance tracking)'
    )

    # Source tracking
    source = models.CharField(
        max_length=100,
        default='website',
        help_text='Where the subscription came from (website, sidebar, post, etc.)'
    )

    def confirm_subscription(self):
        """Confirm the subscription via double opt-in."""
        if not self.is_confirmed:
            self.is_confirmed = True
            self.is_active = True
            self.confirmed_at = timezone.now()
            self.save(update_fields=['is_confirmed', 'is_active', 'confirmed_at'])

    def unsubscribe(self):
        """Unsubscribe the user."""
        if self.is_active:
            self.is_active = False
            self.unsubscribed_at = timezone.now()
            self.save(update_fields=['is_active', 'unsubscribed_at'])

    def resubscribe(self):
        """Reactivate subscription (if already confirmed)."""
        if self.is_confirmed:
            self.is_active = True
            self.unsubscribed_at = None
            self.save(update_fields=['is_active', 'unsubscribed_at'])

    def regenerate_tokens(self):
        """Regenerate confirmation and unsubscribe tokens."""
        self.confirmation_token = uuid.uuid4()
        self.unsubscribe_token = uuid.uuid4()
        self.save(update_fields=['confirmation_token', 'unsubscribe_token'])

    @property
    def subscription_status(self):
        """Get human-readable subscription status."""
        if not self.is_confirmed:
            return "Pending Confirmation"
        elif self.is_active:
            return "Active"
        else:
            return "Unsubscribed"

    @property
    def days_since_subscription(self):
        """Get number of days since first subscription."""
        return (timezone.now() - self.subscribed_at).days

    def get_confirmation_url(self, request=None):
        """Generate confirmation URL for double opt-in."""
        from django.urls import reverse

        confirmation_path = reverse('blog:confirm_subscription', kwargs={'token': self.confirmation_token})

        if request:
            return request.build_absolute_uri(confirmation_path)
        else:
            return f"https://jaroslav.tech{confirmation_path}"

    def get_unsubscribe_url(self, request=None):
        """Generate unsubscribe URL."""
        from django.urls import reverse

        unsubscribe_path = reverse('blog:unsubscribe', kwargs={'token': self.unsubscribe_token})

        if request:
            return request.build_absolute_uri(unsubscribe_path)
        else:
            return f"https://jaroslav.tech{unsubscribe_path}"

    def clean(self):
        """Validate the model."""
        from django.core.exceptions import ValidationError

        # Normalize email
        if self.email:
            self.email = self.email.lower().strip()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} - {self.subscription_status}"

    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = "Newsletter Subscription"
        verbose_name_plural = "Newsletter Subscriptions"
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active', 'is_confirmed']),
            models.Index(fields=['confirmation_token']),
            models.Index(fields=['unsubscribe_token']),
        ]
