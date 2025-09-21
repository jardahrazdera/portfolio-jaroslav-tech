import os
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
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
