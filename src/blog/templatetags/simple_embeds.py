"""
Simple embed template filters for easy content processing.
Just use |process_embeds filter and everything works automatically!
"""
from django import template
from django.utils.safestring import mark_safe
from ..embed_processor import embed_processor

register = template.Library()


@register.filter
def process_embeds(content):
    """
    Automatically process all embeds in content.

    Usage in templates:
    {{ post.content|process_embeds }}

    Supports:
    - YouTube URLs and [youtube:VIDEO_ID] shortcodes
    - Twitter URLs and [twitter:POST_ID] shortcodes
    - CodePen URLs and [codepen:USER/PEN] shortcodes
    - GitHub Gist URLs and [gist:GIST_ID] shortcodes
    - Generic embeds with [embed:URL] shortcodes

    Examples of what users can type:
    - Just paste a YouTube URL: https://www.youtube.com/watch?v=abc123
    - Or use shortcode: [youtube:abc123]
    - Twitter: [twitter:1234567890] or paste URL
    - CodePen: [codepen:username/pen123] or paste URL
    - Gist: [gist:abc123def456] or paste URL
    - Any site: [embed:https://example.com/widget:Custom Title]
    """
    if not content:
        return content

    return embed_processor.process_content(content)


@register.filter
def has_embeds(content):
    """Check if content contains any embeddable URLs or shortcodes."""
    if not content:
        return False

    # Quick check for common patterns
    embed_indicators = [
        'youtube.com', 'youtu.be', '[youtube:', '[yt:',
        'twitter.com', 'x.com', '[twitter:', '[tweet:',
        'codepen.io', '[codepen:', '[pen:',
        'gist.github.com', '[gist:',
        '[embed:'
    ]

    content_lower = content.lower()
    return any(indicator in content_lower for indicator in embed_indicators)


@register.simple_tag
def embed_help():
    """Provide help information about supported embed formats."""
    return embed_processor.get_supported_formats()


@register.inclusion_tag('blog/components/embed_help.html')
def show_embed_help():
    """Display embed help as a component."""
    return {'formats': embed_processor.get_supported_formats()}


@register.simple_tag
def quick_embed(embed_type, identifier, title=""):
    """
    Quick embed tag for specific types.

    Usage:
    {% quick_embed "youtube" "dQw4w9WgXcQ" "Rick Roll" %}
    {% quick_embed "twitter" "1234567890" %}
    {% quick_embed "codepen" "username/pen123" "My Pen" %}
    {% quick_embed "gist" "abc123def456" "Code Example" %}
    """
    if embed_type == "youtube":
        return mark_safe(embed_processor._generate_youtube_embed(identifier, title or "YouTube Video"))
    elif embed_type == "twitter":
        url = f"https://twitter.com/i/status/{identifier}"
        return mark_safe(embed_processor._generate_twitter_embed(url, identifier))
    elif embed_type == "codepen":
        if '/' in identifier:
            username, pen_id = identifier.split('/', 1)
            return mark_safe(embed_processor._generate_codepen_embed(username, pen_id, title or "CodePen"))
    elif embed_type == "gist":
        return mark_safe(embed_processor._generate_gist_embed(identifier, title or "GitHub Gist"))

    return ""