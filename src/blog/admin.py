from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse
from ckeditor.widgets import CKEditorWidget
from .models import Category, Tag, Post, BlogFile


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color')
    prepopulated_fields = {'slug': ('name',)}


class BlogFileInline(admin.TabularInline):
    """Inline admin for blog file attachments."""
    model = BlogFile
    extra = 0
    fields = ('file', 'title', 'description', 'is_public')
    readonly_fields = ('uploaded_at', 'download_count')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'featured_image_thumbnail', 'attachment_count', 'is_published', 'is_featured', 'created_at')
    list_filter = ('is_published', 'is_featured', 'categories', 'created_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('categories', 'tags')
    list_editable = ('is_published', 'is_featured')
    fields = ('title', 'slug', 'featured_image', 'excerpt', 'content', 'author', 'categories', 'tags', 'is_published', 'is_featured')
    inlines = [BlogFileInline]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'content':
            kwargs['widget'] = CKEditorWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def featured_image_thumbnail(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.featured_image.url
            )
        return "No image"
    featured_image_thumbnail.short_description = 'Image'

    def attachment_count(self, obj):
        """Display number of file attachments."""
        count = obj.attachments.count()
        if count > 0:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
                count
            )
        return "0"
    attachment_count.short_description = 'Files'


@admin.register(BlogFile)
class BlogFileAdmin(admin.ModelAdmin):
    list_display = ('title', 'post', 'file_type_display', 'file_size_display', 'download_count', 'is_public', 'uploaded_at')
    list_filter = ('is_public', 'uploaded_at', 'post__categories')
    search_fields = ('title', 'description', 'post__title')
    readonly_fields = ('uploaded_at', 'updated_at', 'download_count', 'file_info_display')
    fields = ('post', 'file', 'title', 'description', 'is_public', 'file_info_display', 'download_count', 'uploaded_at', 'updated_at')

    def file_type_display(self, obj):
        """Display file type with icon."""
        file_info = obj.get_file_info()
        if file_info:
            return format_html(
                '<i class="fas {}"></i> {}',
                file_info.get('icon', 'fa-file'),
                file_info.get('description', 'File')
            )
        return "Unknown"
    file_type_display.short_description = 'Type'

    def file_size_display(self, obj):
        """Display formatted file size."""
        return obj.get_file_size_display()
    file_size_display.short_description = 'Size'

    def file_info_display(self, obj):
        """Display detailed file information."""
        if obj.file:
            file_info = obj.get_file_info()
            return format_html(
                '<div style="padding: 10px; background: #f0f0f0; border-radius: 4px;">'
                '<strong>File:</strong> {}<br>'
                '<strong>Type:</strong> {}<br>'
                '<strong>Size:</strong> {}<br>'
                '<strong>Extension:</strong> {}'
                '</div>',
                obj.file.name,
                file_info.get('description', 'Unknown') if file_info else 'Unknown',
                obj.get_file_size_display(),
                file_info.get('extension', 'Unknown') if file_info else 'Unknown'
            )
        return "No file"
    file_info_display.short_description = 'File Information'
