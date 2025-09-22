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
    list_display = ('title', 'author', 'featured_image_thumbnail', 'attachment_count', 'is_published', 'is_featured', 'seo_status', 'created_at')
    list_filter = ('is_published', 'is_featured', 'categories', 'created_at')
    search_fields = ('title', 'content', 'meta_description', 'meta_keywords')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('categories', 'tags')
    list_editable = ('is_published', 'is_featured')
    inlines = [BlogFileInline]

    class Media:
        css = {
            'all': ('blog/admin/ckeditor_fix.css',)
        }

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'author', 'excerpt', 'content'),
            'description': 'Basic post information and content'
        }),
        ('Media & Attachments', {
            'fields': ('featured_image',),
            'description': 'Featured image and file attachments (use inline section below for file attachments)'
        }),
        ('SEO Settings', {
            'fields': ('seo_status_display', 'meta_description', 'meta_keywords'),
            'description': 'Search engine optimization settings. Meta description will fall back to excerpt if empty. Keywords will auto-generate from tags if empty.',
            'classes': ('collapse',)
        }),
        ('Categorization', {
            'fields': ('categories', 'tags'),
            'description': 'Organize your post with categories and tags'
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_featured'),
            'description': 'Publication status and featured post settings'
        }),
    )

    readonly_fields = ('seo_status_display',)

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

    def seo_status(self, obj):
        """Display SEO optimization status."""
        score = 0
        issues = []

        # Check meta description
        if obj.meta_description:
            if 50 <= len(obj.meta_description) <= 155:
                score += 25
            else:
                issues.append("Meta description length")
        elif obj.excerpt:
            if 50 <= len(obj.excerpt) <= 155:
                score += 15
            else:
                issues.append("Excerpt length for meta")
        else:
            issues.append("Missing meta description")

        # Check meta keywords or tags
        if obj.meta_keywords or obj.tags.exists():
            score += 25
        else:
            issues.append("No keywords/tags")

        # Check featured image for social sharing
        if obj.featured_image:
            score += 25
        else:
            issues.append("No featured image")

        # Check content length
        content_length = len(obj.content.strip())
        if content_length > 300:
            score += 25
        else:
            issues.append("Content too short")

        # Determine color and status with black text for all
        if score >= 75:
            bg_color = "#28a745"  # Green
            text_color = "black"
            status = "Excellent"
        elif score >= 50:
            bg_color = "#ffc107"  # Yellow
            text_color = "black"
            status = "Good"
        elif score >= 25:
            bg_color = "#fd7e14"  # Orange
            text_color = "black"
            status = "Needs work"
        else:
            bg_color = "#dc3545"  # Red
            text_color = "black"
            status = "Poor"

        return format_html(
            '<span style="background: {}; color: {}; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 500;" title="{}">{} ({}%)</span>',
            bg_color,
            text_color,
            f"Issues: {', '.join(issues)}" if issues else "All good!",
            status,
            score
        )
    seo_status.short_description = 'SEO Status'

    def seo_status_display(self, obj):
        """Display SEO status in the change form with additional details."""
        if not obj.pk:  # New object
            return format_html(
                '<div style="padding: 10px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;">'
                '<strong>SEO Status:</strong> Save the post first to see SEO analysis'
                '</div>'
            )

        # Use the same logic as seo_status but with more detailed output
        score = 0
        issues = []
        recommendations = []

        # Check meta description
        if obj.meta_description:
            if 50 <= len(obj.meta_description) <= 155:
                score += 25
                recommendations.append("✓ Meta description length is optimal")
            else:
                issues.append(f"Meta description is {len(obj.meta_description)} chars (should be 50-155)")
        elif obj.excerpt:
            if 50 <= len(obj.excerpt) <= 155:
                score += 15
                recommendations.append("✓ Using excerpt as meta description (consider adding dedicated meta description)")
            else:
                issues.append(f"Excerpt length is {len(obj.excerpt)} chars (should be 50-155 for meta description)")
        else:
            issues.append("Missing meta description and excerpt")

        # Check meta keywords or tags
        if obj.meta_keywords:
            score += 25
            recommendations.append("✓ Custom meta keywords set")
        elif obj.tags.exists():
            score += 15
            recommendations.append("✓ Using tags as keywords (consider adding custom meta keywords)")
        else:
            issues.append("No meta keywords or tags")

        # Check featured image
        if obj.featured_image:
            score += 25
            recommendations.append("✓ Featured image set for social sharing")
        else:
            issues.append("No featured image for social media sharing")

        # Check content length
        content_length = len(obj.content.strip())
        if content_length > 300:
            score += 25
            recommendations.append(f"✓ Content length is good ({content_length} characters)")
        else:
            issues.append(f"Content is too short ({content_length} chars, should be >300)")

        # Determine status
        if score >= 75:
            status = "Excellent"
            status_color = "#28a745"
        elif score >= 50:
            status = "Good"
            status_color = "#ffc107"
        elif score >= 25:
            status = "Needs work"
            status_color = "#fd7e14"
        else:
            status = "Poor"
            status_color = "#dc3545"

        # Build detailed display with better contrast
        html = f'''
        <div style="padding: 15px; background: white; border: 2px solid #dee2e6; border-radius: 6px; margin-bottom: 10px; color: #212529;">
            <div style="margin-bottom: 12px;">
                <strong style="color: #212529; font-size: 14px;">SEO Status: </strong>
                <span style="background: {status_color}; color: black; padding: 4px 10px; border-radius: 4px; font-weight: 600; font-size: 13px;">
                    {status} ({score}%)
                </span>
            </div>
        '''

        if recommendations:
            html += '<div style="margin-bottom: 10px;"><strong style="color: #155724; font-size: 14px;">✓ What\'s working:</strong></div>'
            for rec in recommendations:
                html += f'<div style="color: #155724; margin-left: 15px; margin-bottom: 4px; font-weight: 500;">• {rec}</div>'

        if issues:
            html += '<div style="margin-top: 10px; margin-bottom: 10px;"><strong style="color: #721c24; font-size: 14px;">⚠ Issues to fix:</strong></div>'
            for issue in issues:
                html += f'<div style="color: #721c24; margin-left: 15px; margin-bottom: 4px; font-weight: 500;">• {issue}</div>'

        html += '</div>'
        return format_html(html)

    seo_status_display.short_description = 'SEO Analysis'


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
