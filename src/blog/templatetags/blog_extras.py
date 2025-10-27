from django import template
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.timesince import timesince
from django.utils import timezone
import re
import math

register = template.Library()


@register.filter
def reading_time(content):
    """
    Calculate estimated reading time for content.
    Based on average reading speed of 200-250 words per minute.
    """
    if not content:
        return "1 min read"

    # Strip HTML tags and get plain text
    plain_text = strip_tags(content)

    # Count words (split by whitespace)
    word_count = len(plain_text.split())

    # Calculate reading time (assuming 225 words per minute average)
    reading_time_minutes = math.ceil(word_count / 225)

    # Return formatted string
    if reading_time_minutes < 1:
        return "< 1 min read"
    elif reading_time_minutes == 1:
        return "1 min read"
    else:
        return f"{reading_time_minutes} min read"


@register.filter
def time_ago(date):
    """
    Return a user-friendly time ago string.
    """
    if not date:
        return ""

    # Handle string dates (from cache serialization)
    if isinstance(date, str):
        from django.utils.dateparse import parse_datetime
        try:
            date = parse_datetime(date)
            if not date:
                return ""
        except (ValueError, TypeError):
            return ""

    now = timezone.now()
    diff = now - date

    # If less than 24 hours, show time ago
    if diff.days == 0:
        return f"{timesince(date, now).split(',')[0]} ago"

    # If less than 7 days, show days ago
    elif diff.days < 7:
        if diff.days == 1:
            return "1 day ago"
        else:
            return f"{diff.days} days ago"

    # If less than 30 days, show weeks ago
    elif diff.days < 30:
        weeks = diff.days // 7
        if weeks == 1:
            return "1 week ago"
        else:
            return f"{weeks} weeks ago"

    # Otherwise show the formatted date
    else:
        return date.strftime("%B %d, %Y")


@register.filter
def word_count(content):
    """
    Return word count for content.
    """
    if not content:
        return 0

    plain_text = strip_tags(content)
    return len(plain_text.split())


@register.simple_tag
def post_meta_separator():
    """
    Return a consistent separator for meta information.
    """
    return "•"


@register.filter
def highlight_search(text, search_term):
    """
    Highlight search terms in text with HTML markup.
    Case-insensitive search with word boundary consideration.
    """
    if not search_term or not text:
        return text

    # Escape the text first to prevent XSS
    escaped_text = escape(str(text))
    escaped_search = escape(str(search_term))

    # Create a regex pattern for case-insensitive search
    # Use word boundaries for better matching
    pattern = re.compile(re.escape(escaped_search), re.IGNORECASE)

    # Replace matches with highlighted version
    highlighted = pattern.sub(
        lambda m: f'<mark class="search-highlight">{m.group()}</mark>',
        escaped_text
    )

    return mark_safe(highlighted)


@register.filter
def lookup(dictionary, key):
    """
    Template filter to lookup dictionary values by key.
    Usage: {{ dict|lookup:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0


@register.inclusion_tag('blog/components/popular_posts.html', takes_context=True)
def popular_posts_widget(context, period='week', limit=5, show_view_all=True, show_period_selector=False):
    """
    Template tag to display popular posts widget.

    Usage:
    {% popular_posts_widget period='week' limit=5 show_view_all=True %}
    """
    from ..models import PostView

    popular_posts = PostView.get_popular_posts(period=period, limit=limit)

    return {
        'popular_posts': popular_posts,
        'period': period,
        'show_view_all': show_view_all,
        'show_period_selector': show_period_selector,
        'debug': context.get('debug', False),
        'request': context['request']
    }


@register.simple_tag
def get_trending_posts(limit=10):
    """
    Template tag to get trending posts.

    Usage:
    {% get_trending_posts limit=5 as trending %}
    """
    from ..models import PostView
    return PostView.get_trending_posts(limit=limit)


@register.filter
def format_view_count(count):
    """
    Format view count for display (e.g., 1.2K, 3.4M).

    Usage: {{ post.get_view_count|format_view_count }}
    """
    if not count:
        return '0'

    if count < 1000:
        return str(count)
    elif count < 1000000:
        return f"{count/1000:.1f}K"
    else:
        return f"{count/1000000:.1f}M"


@register.filter
def completion_rate_class(rate):
    """
    Get CSS class for completion rate.

    Usage: {{ post.get_reading_completion_rate|completion_rate_class }}
    """
    if not rate:
        return 'completion-rate--unknown'
    elif rate >= 80:
        return 'completion-rate--excellent'
    elif rate >= 60:
        return 'completion-rate--good'
    elif rate >= 40:
        return 'completion-rate--average'
    else:
        return 'completion-rate--low'