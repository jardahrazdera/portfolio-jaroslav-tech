from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse
from django.contrib import messages
from ckeditor.widgets import CKEditorWidget
from .models import Category, Tag, Post, BlogFile, Newsletter, PostView
from .email_service import NewsletterEmailService


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
    list_display = ('title', 'author', 'featured_image_thumbnail', 'attachment_count', 'view_stats_display', 'is_published', 'is_featured', 'seo_status', 'created_at')
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
        ('External Discussion', {
            'fields': ('discussion_url', 'discussion_platform_display'),
            'description': 'Link to external discussion platforms (Twitter, Reddit, LinkedIn, etc.)',
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('seo_status_display', 'discussion_platform_display')

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
