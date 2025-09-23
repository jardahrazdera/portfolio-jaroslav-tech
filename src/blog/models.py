import os
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from ckeditor.fields import RichTextField
from .image_utils import ImageProcessor
from .file_utils import FileValidator, generate_file_path, get_file_type, format_file_size


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


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = RichTextField()
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

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


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
