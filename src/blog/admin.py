from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from django.contrib import messages
from django_ckeditor_5.widgets import CKEditor5Widget
import time
from .models import Category, Tag, Post, BlogFile, Newsletter, PostView
from .email_service import NewsletterEmailService
from .signals import cleanup_orphaned_files, get_storage_stats, format_file_size
from .image_utils_enhanced import get_image_metadata


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
    list_display = ('title', 'author', 'featured_image_thumbnail', 'image_optimization_status', 'attachment_count', 'view_stats_display', 'is_published', 'is_featured', 'seo_status', 'created_at')
    list_filter = ('is_published', 'is_featured', 'categories', 'created_at')
    search_fields = ('title', 'content', 'meta_description', 'meta_keywords')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('categories', 'tags')
    list_editable = ('is_published', 'is_featured')
    inlines = [BlogFileInline]

    class Media:
        css = {
            'all': ('blog/admin/ckeditor.css',)
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
        ('External Discussion', {
            'fields': ('discussion_url', 'discussion_platform_display'),
            'description': 'Link to external discussion platforms (Twitter, Reddit, LinkedIn, etc.)',
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('seo_status_display', 'discussion_platform_display')

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'content':
            kwargs['widget'] = CKEditor5Widget(config_name='extends')
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

    def discussion_platform_display(self, obj):
        """Display detected discussion platform information."""
        if not obj.discussion_url:
            return format_html(
                '<div style="padding: 10px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; color: #6c757d;">'
                '<i class="fas fa-info-circle"></i> No external discussion link set'
                '</div>'
            )

        platform = obj.get_discussion_platform()
        if platform:
            return format_html(
                '<div style="padding: 12px; background: white; border: 2px solid #e9ecef; border-radius: 6px;">'
                '<div style="margin-bottom: 8px;">'
                '<strong style="color: #212529; font-size: 14px;">Discussion Platform:</strong>'
                '</div>'
                '<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">'
                '<i class="{}" style="color: {}; font-size: 18px;"></i>'
                '<span style="font-weight: 600; color: #495057;">{}</span>'
                '</div>'
                '<div style="color: #6c757d; font-size: 13px; margin-bottom: 8px;">'
                '{}'
                '</div>'
                '<a href="{}" target="_blank" rel="noopener noreferrer" '
                'style="display: inline-block; padding: 6px 12px; background: {}; color: white; '
                'text-decoration: none; border-radius: 4px; font-size: 12px; font-weight: 500;">'
                '<i class="fas fa-external-link-alt"></i> View Discussion'
                '</a>'
                '</div>',
                platform['icon'],
                platform['color'],
                platform['name'],
                platform['label'],
                obj.discussion_url,
                platform['color']
            )
        else:
            return format_html(
                '<div style="padding: 10px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px;">'
                '<i class="fas fa-question-circle" style="color: #856404;"></i> '
                '<span style="color: #856404;">Unknown platform</span>'
                '</div>'
            )

    discussion_platform_display.short_description = 'Discussion Platform'

    def view_stats_display(self, obj):
        """Display view statistics for the post."""
        if not obj.pk:
            return format_html(
                '<div style="text-align: center; color: #999;">—</div>'
            )

        total_views = obj.get_view_count()
        weekly_views = obj.get_view_count('week')
        completion_rate = obj.get_reading_completion_rate()
        is_trending = obj.is_trending()

        # Choose color based on performance
        if total_views >= 100 or is_trending:
            color = '#28a745'  # Green
        elif total_views >= 50:
            color = '#ffc107'  # Yellow
        elif total_views >= 10:
            color = '#fd7e14'  # Orange
        else:
            color = '#6c757d'  # Gray

        # Build display
        html = f'''
        <div style="text-align: center; min-width: 80px;">
            <div style="font-weight: 600; color: {color}; font-size: 14px;">
                {total_views} views
            </div>
        '''

        if weekly_views > 0:
            html += f'<div style="font-size: 11px; color: #666; margin-top: 2px;">{weekly_views} this week</div>'

        if completion_rate > 0:
            rate_color = '#28a745' if completion_rate >= 70 else '#ffc107' if completion_rate >= 50 else '#dc3545'
            html += f'<div style="font-size: 11px; color: {rate_color}; margin-top: 2px;">{completion_rate:.0f}% completion</div>'

        if is_trending:
            html += '<div style="font-size: 10px; color: #dc3545; margin-top: 2px; font-weight: 600;">🔥 TRENDING</div>'

        html += '</div>'

        return format_html(html)

    view_stats_display.short_description = 'Analytics'

    def image_optimization_status(self, obj):
        """Display image optimization status."""
        if not obj.featured_image:
            return format_html(
                '<div style="text-align: center; color: #999;">—</div>'
            )

        base_name = obj.get_image_base_name()
        if not base_name:
            return format_html(
                '<div style="text-align: center; color: #dc3545; font-size: 12px;">Not processed</div>'
            )

        try:
            metadata = get_image_metadata(base_name)
            variant_count = metadata.get('total_variants', 0)

            if variant_count > 0:
                formats = metadata.get('available_formats', [])
                webp_available = 'webp' in formats

                # Determine status
                if webp_available and variant_count >= 4:
                    color = '#28a745'  # Green
                    status = '✓ Optimized'
                elif variant_count >= 2:
                    color = '#ffc107'  # Yellow
                    status = '⚠ Partial'
                else:
                    color = '#fd7e14'  # Orange
                    status = '○ Basic'

                webp_indicator = mark_safe('<div style="font-size: 10px; color: #28a745;">WebP ✓</div>') if webp_available else ''
                return format_html(
                    '<div style="text-align: center;">'
                    '<div style="font-weight: 600; color: {}; font-size: 12px;">{}</div>'
                    '<div style="font-size: 10px; color: #666;">{} variants</div>'
                    '{}'
                    '</div>',
                    color, status, variant_count, webp_indicator
                )
            else:
                return format_html(
                    '<div style="text-align: center; color: #dc3545; font-size: 12px;">✗ Failed</div>'
                )
        except Exception:
            return format_html(
                '<div style="text-align: center; color: #dc3545; font-size: 12px;">Error</div>'
            )

    image_optimization_status.short_description = 'Image Opt.'

    # Admin actions
    actions = ['optimize_selected_images', 'cleanup_orphaned_files_action']

    def optimize_selected_images(self, request, queryset):
        """Admin action to optimize images for selected posts."""
        from .image_utils_enhanced import ImageProcessor as EnhancedImageProcessor

        optimized_count = 0
        failed_count = 0

        for post in queryset.filter(featured_image__isnull=False):
            try:
                base_name = post.get_image_base_name()
                if not base_name:
                    base_name = f'post_{post.pk}_{int(time.time())}'

                is_hero = post.is_featured
                processed_data = EnhancedImageProcessor.process_image(
                    post.featured_image,
                    base_name,
                    is_hero=is_hero,
                    generate_alt=True
                )

                if processed_data:
                    optimized_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                failed_count += 1

        if optimized_count > 0:
            self.message_user(
                request,
                f'Successfully optimized {optimized_count} images. {failed_count} failed.',
                messages.SUCCESS if failed_count == 0 else messages.WARNING
            )
        else:
            self.message_user(
                request,
                f'No images were optimized. {failed_count} failed.',
                messages.ERROR
            )

    optimize_selected_images.short_description = "Optimize featured images for selected posts"

    def cleanup_orphaned_files_action(self, request, queryset):
        """Admin action to clean up orphaned files."""
        try:
            orphaned_count = cleanup_orphaned_files()
            if orphaned_count > 0:
                self.message_user(
                    request,
                    f'Successfully cleaned up {orphaned_count} orphaned files.',
                    messages.SUCCESS
                )
            else:
                self.message_user(
                    request,
                    'No orphaned files found.',
                    messages.INFO
                )
        except Exception as e:
            self.message_user(
                request,
                f'Error during cleanup: {e}',
                messages.ERROR
            )

    cleanup_orphaned_files_action.short_description = "Clean up orphaned files (run only once)"

    def get_readonly_fields(self, request, obj=None):
        """Add image optimization info to readonly fields."""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.featured_image:
            readonly.extend(['image_optimization_info'])
        return readonly

    def image_optimization_info(self, obj):
        """Detailed image optimization information for the edit form."""
        if not obj.featured_image:
            return "No featured image"

        base_name = obj.get_image_base_name()
        if not base_name:
            return format_html(
                '<div style="padding: 10px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px;">'
                'Image not processed yet. Save the post to trigger optimization.'
                '</div>'
            )

        try:
            metadata = get_image_metadata(base_name)
            variant_count = metadata.get('total_variants', 0)

            if variant_count == 0:
                return format_html(
                    '<div style="padding: 10px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px;">'
                    'Image processing failed. Try re-saving the post or check the logs.'
                    '</div>'
                )

            storage_stats = get_storage_stats()

            html = f'''
            <div style="padding: 15px; background: white; border: 2px solid #dee2e6; border-radius: 6px;">
                <h4 style="margin-top: 0; color: #495057;">Image Optimization Status</h4>
                <div style="margin-bottom: 10px;">
                    <strong>Total Variants:</strong> {variant_count}
                </div>
                <div style="margin-bottom: 10px;">
                    <strong>Available Formats:</strong> {', '.join(metadata.get('available_formats', []))}
                </div>
                <div style="margin-bottom: 10px;">
                    <strong>Available Sizes:</strong> {len(metadata.get('available_sizes', []))}
                </div>
            '''

            if metadata.get('available_sizes'):
                html += '<div style="margin-bottom: 10px;"><strong>Size Variants:</strong><ul style="margin: 5px 0;">'
                for size_data in metadata['available_sizes']:
                    html += f'<li>{size_data["name"]} ({size_data["width"]}×{size_data["height"]}) - {", ".join(size_data["formats"])}</li>'
                html += '</ul></div>'

            # Show total storage info
            html += f'''
                <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #dee2e6;">
                    <strong>Storage Overview:</strong><br>
                    • Featured Images: {storage_stats["featured_images"]["count"]} files ({format_file_size(storage_stats["featured_images"]["size"])})<br>
                    • Processed Images: {storage_stats["processed_images"]["count"]} files ({format_file_size(storage_stats["processed_images"]["size"])})<br>
                    • Blog Files: {storage_stats["blog_files"]["count"]} files ({format_file_size(storage_stats["blog_files"]["size"])})
                </div>
            </div>
            '''

            return format_html(html)

        except Exception as e:
            return format_html(
                '<div style="padding: 10px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px;">'
                f'Error loading optimization info: {e}'
                '</div>'
            )

    image_optimization_info.short_description = 'Image Optimization Details'

    # === Cleanup Monitoring and Management Actions ===

    def cleanup_monitoring_display(self, obj):
        """Display cleanup monitoring information in admin."""
        try:
            from .middleware.cleanup import get_cleanup_stats, get_storage_history

            # Get latest cleanup stats
            cleanup_stats = get_cleanup_stats()
            storage_history = get_storage_history()

            if not cleanup_stats:
                return format_html(
                    '<div style="padding: 8px; background: #ffeaa7; border-left: 4px solid #fdcb6e;">'
                    '<strong>Cleanup Status:</strong> No cleanup performed yet<br>'
                    '<small>Automatic cleanup will trigger based on request count</small>'
                    '</div>'
                )

            last_cleanup = cleanup_stats.get('last_cleanup', 0)
            if last_cleanup:
                from datetime import datetime
                cleanup_time = datetime.fromtimestamp(last_cleanup)
                time_ago = datetime.now() - cleanup_time
                hours_ago = time_ago.total_seconds() / 3600

                if hours_ago < 1:
                    time_display = f"{int(time_ago.total_seconds() / 60)} minutes ago"
                elif hours_ago < 24:
                    time_display = f"{int(hours_ago)} hours ago"
                else:
                    time_display = f"{int(hours_ago / 24)} days ago"

                # Status color based on recency
                if hours_ago < 24:
                    status_color = "#00b894"  # Green - recent
                elif hours_ago < 168:  # 1 week
                    status_color = "#fdcb6e"  # Yellow - moderate
                else:
                    status_color = "#e17055"  # Red - old

                return format_html(
                    '<div style="padding: 8px; background: #f8f9fa; border-left: 4px solid {};">'
                    '<strong>Last Cleanup:</strong> {} ({})<br>'
                    '<strong>Files Cleaned:</strong> {}<br>'
                    '<strong>Duration:</strong> {:.2f}s<br>'
                    '<strong>Storage:</strong> {:.1f}MB<br>'
                    '<small>Trigger: {}</small>'
                    '</div>',
                    status_color,
                    cleanup_time.strftime('%Y-%m-%d %H:%M'),
                    time_display,
                    cleanup_stats.get('last_files_cleaned', 0),
                    cleanup_stats.get('last_duration', 0),
                    cleanup_stats.get('total_storage_mb', 0),
                    cleanup_stats.get('last_trigger_path', 'Unknown')
                )
            else:
                return format_html(
                    '<div style="padding: 8px; background: #ffeaa7; border-left: 4px solid #fdcb6e;">'
                    'No cleanup data available'
                    '</div>'
                )

        except Exception as e:
            return format_html(
                '<div style="padding: 8px; background: #fab1a0; border-left: 4px solid #e17055;">'
                f'Error loading cleanup info: {e}'
                '</div>'
            )

    cleanup_monitoring_display.short_description = 'Cleanup Status'

    # Admin Actions for Cleanup Management

    def trigger_manual_cleanup(self, request, queryset):
        """Admin action to manually trigger cleanup."""
        try:
            from .middleware.cleanup import force_cleanup
            from .signals import cleanup_orphaned_files

            # Run immediate cleanup (synchronous for admin feedback)
            cleaned_count = cleanup_orphaned_files()

            if cleaned_count > 0:
                self.message_user(
                    request,
                    f"Cleanup completed successfully! Removed {cleaned_count} orphaned files.",
                    level='SUCCESS'
                )
            else:
                self.message_user(
                    request,
                    "Cleanup completed - no orphaned files found.",
                    level='INFO'
                )

        except Exception as e:
            self.message_user(
                request,
                f"Cleanup failed: {str(e)}",
                level='ERROR'
            )

    trigger_manual_cleanup.short_description = "🧹 Clean up orphaned files"

    def display_storage_stats(self, request, queryset):
        """Admin action to display detailed storage statistics."""
        try:
            stats = get_storage_stats()
            total_size_mb = stats['total_size'] / (1024 * 1024)

            message = (
                f"📊 Storage Statistics:\n"
                f"• Total Storage: {format_file_size(stats['total_size'])}\n"
                f"• Featured Images: {stats['featured_images']['count']} files "
                f"({format_file_size(stats['featured_images']['size'])})\n"
                f"• Processed Images: {stats['processed_images']['count']} files "
                f"({format_file_size(stats['processed_images']['size'])})\n"
                f"• Blog Files: {stats['blog_files']['count']} files "
                f"({format_file_size(stats['blog_files']['size'])})"
            )

            level = 'INFO'
            if total_size_mb > 1000:  # Over 1GB
                level = 'WARNING'
                message += "\n⚠️ High storage usage detected!"

            self.message_user(request, message, level=level)

        except Exception as e:
            self.message_user(
                request,
                f"Failed to get storage stats: {str(e)}",
                level='ERROR'
            )

    display_storage_stats.short_description = "📊 Show storage statistics"

    def reset_cleanup_counters(self, request, queryset):
        """Admin action to reset cleanup counters."""
        try:
            from .middleware.cleanup import reset_cleanup_counters
            reset_cleanup_counters()

            self.message_user(
                request,
                "Cleanup counters have been reset. Next cleanup will trigger based on new request count.",
                level='SUCCESS'
            )

        except Exception as e:
            self.message_user(
                request,
                f"Failed to reset counters: {str(e)}",
                level='ERROR'
            )

    reset_cleanup_counters.short_description = "🔄 Reset cleanup counters"

    # Add cleanup actions to the list
    actions = ['bulk_publish', 'bulk_unpublish', 'bulk_optimize_images', 'bulk_cleanup_orphaned_files',
               'trigger_manual_cleanup', 'display_storage_stats', 'reset_cleanup_counters']


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


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscription_status_display', 'is_active', 'is_confirmed', 'days_since_subscription', 'source', 'subscribed_at')
    list_filter = ('is_active', 'is_confirmed', 'source', 'subscribed_at')
    search_fields = ('email',)
    readonly_fields = ('subscription_status_display', 'confirmation_token', 'unsubscribe_token', 'subscribed_at', 'confirmed_at', 'unsubscribed_at', 'days_since_subscription', 'subscription_urls')
    actions = ['send_confirmation_email', 'activate_subscriptions', 'deactivate_subscriptions', 'export_active_subscribers']

    fieldsets = (
        ('Subscription Information', {
            'fields': ('email', 'subscription_status_display', 'is_active', 'is_confirmed'),
            'description': 'Core subscription details and status'
        }),
        ('GDPR Compliance & Tokens', {
            'fields': ('confirmation_token', 'unsubscribe_token', 'subscription_urls'),
            'description': 'Security tokens and URLs for GDPR compliance',
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('subscribed_at', 'confirmed_at', 'unsubscribed_at', 'days_since_subscription'),
            'description': 'Subscription timeline and history',
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('source', 'ip_address', 'user_agent'),
            'description': 'Source tracking and compliance metadata',
            'classes': ('collapse',)
        }),
    )

    def subscription_status_display(self, obj):
        """Display subscription status with color coding."""
        status = obj.subscription_status

        if status == "Active":
            color = "#28a745"  # Green
            icon = "fas fa-check-circle"
        elif status == "Pending Confirmation":
            color = "#ffc107"  # Yellow
            icon = "fas fa-clock"
        else:  # Unsubscribed
            color = "#dc3545"  # Red
            icon = "fas fa-times-circle"

        return format_html(
            '<span style="color: {}; font-weight: 600;"><i class="{}"></i> {}</span>',
            color,
            icon,
            status
        )
    subscription_status_display.short_description = 'Status'

    def days_since_subscription(self, obj):
        """Display days since subscription with formatting."""
        days = obj.days_since_subscription
        if days == 0:
            return "Today"
        elif days == 1:
            return "1 day ago"
        else:
            return f"{days} days ago"
    days_since_subscription.short_description = 'Subscribed'

    def subscription_urls(self, obj):
        """Display confirmation and unsubscribe URLs."""
        if not obj.pk:
            return format_html(
                '<div style="padding: 10px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;">'
                'Save the subscription first to generate URLs'
                '</div>'
            )

        confirmation_url = obj.get_confirmation_url()
        unsubscribe_url = obj.get_unsubscribe_url()

        return format_html(
            '<div style="padding: 15px; background: white; border: 2px solid #dee2e6; border-radius: 6px;">'
            '<div style="margin-bottom: 10px;">'
            '<strong style="color: #212529;">Confirmation URL:</strong><br>'
            '<a href="{}" target="_blank" style="color: #007bff; word-break: break-all;">{}</a>'
            '</div>'
            '<div>'
            '<strong style="color: #212529;">Unsubscribe URL:</strong><br>'
            '<a href="{}" target="_blank" style="color: #dc3545; word-break: break-all;">{}</a>'
            '</div>'
            '</div>',
            confirmation_url,
            confirmation_url,
            unsubscribe_url,
            unsubscribe_url
        )
    subscription_urls.short_description = 'GDPR URLs'

    def send_confirmation_email(self, request, queryset):
        """Send confirmation emails to selected unconfirmed subscribers."""
        sent_count = 0
        failed_count = 0

        for newsletter in queryset.filter(is_confirmed=False):
            try:
                success = NewsletterEmailService.send_confirmation_email(newsletter, request)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                    self.message_user(
                        request,
                        f"Failed to send confirmation email to {newsletter.email}",
                        level=messages.WARNING
                    )
            except Exception as e:
                failed_count += 1
                self.message_user(
                    request,
                    f"Error sending email to {newsletter.email}: {e}",
                    level=messages.ERROR
                )

        if sent_count > 0:
            self.message_user(
                request,
                f"Successfully sent {sent_count} confirmation emails.",
                level=messages.SUCCESS
            )

        if failed_count > 0:
            self.message_user(
                request,
                f"Failed to send {failed_count} emails. Please check email configuration.",
                level=messages.ERROR
            )
    send_confirmation_email.short_description = "Send confirmation emails"

    def activate_subscriptions(self, request, queryset):
        """Activate selected confirmed subscriptions."""
        updated = queryset.filter(is_confirmed=True).update(is_active=True)
        self.message_user(
            request,
            f"Activated {updated} confirmed subscriptions.",
            level=messages.SUCCESS
        )
    activate_subscriptions.short_description = "Activate confirmed subscriptions"

    def deactivate_subscriptions(self, request, queryset):
        """Deactivate selected subscriptions."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"Deactivated {updated} subscriptions.",
            level=messages.SUCCESS
        )
    deactivate_subscriptions.short_description = "Deactivate subscriptions"

    def export_active_subscribers(self, request, queryset):
        """Export active subscribers as CSV."""
        import csv

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="newsletter_subscribers.csv"'

        writer = csv.writer(response)
        writer.writerow(['Email', 'Subscribed Date', 'Confirmed Date', 'Source', 'Days Active'])

        active_subscribers = queryset.filter(is_active=True, is_confirmed=True)
        for subscriber in active_subscribers:
            writer.writerow([
                subscriber.email,
                subscriber.subscribed_at.strftime('%Y-%m-%d %H:%M:%S'),
                subscriber.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if subscriber.confirmed_at else '',
                subscriber.source,
                subscriber.days_since_subscription
            ])

        self.message_user(
            request,
            f"Exported {active_subscribers.count()} active subscribers.",
            level=messages.SUCCESS
        )

        return response
    export_active_subscribers.short_description = "Export active subscribers (CSV)"

    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related()


@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    """Admin interface for post view analytics."""

    list_display = ('post', 'viewed_at', 'reading_time_display', 'completed_reading', 'referrer_display')
    list_filter = ('viewed_at', 'completed_reading', 'referrer_domain')
    search_fields = ('post__title', 'referrer_domain')
    readonly_fields = ('post', 'viewed_at', 'reading_time_seconds', 'completed_reading',
                      'user_agent_hash', 'referrer_domain', 'session_hash')
    date_hierarchy = 'viewed_at'
    list_per_page = 50

    # Disable add/edit permissions (views are auto-created)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete analytics

    def reading_time_display(self, obj):
        """Display reading time in a user-friendly format."""
        if obj.reading_time_seconds:
            minutes, seconds = divmod(obj.reading_time_seconds, 60)
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "—"
    reading_time_display.short_description = 'Reading Time'

    def referrer_display(self, obj):
        """Display referrer domain with icon."""
        if obj.referrer_domain:
            if 'google' in obj.referrer_domain.lower():
                icon = '🔍'
            elif 'twitter' in obj.referrer_domain.lower():
                icon = '🐦'
            elif 'facebook' in obj.referrer_domain.lower():
                icon = '📘'
            elif 'linkedin' in obj.referrer_domain.lower():
                icon = '💼'
            else:
                icon = '🌐'
            return f"{icon} {obj.referrer_domain}"
        return "Direct"
    referrer_display.short_description = 'Referrer'

    def get_queryset(self, request):
        """Optimize queryset for admin list view."""
        return super().get_queryset(request).select_related('post')
