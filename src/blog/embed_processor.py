"""
Simple embed processor for blog content.
Converts simple shortcodes and URLs automatically to embedded content.
"""
import re
from django.utils.safestring import mark_safe
from django.utils.html import escape


class EmbedProcessor:
    """
    Process blog content to convert simple shortcodes and URLs to embeds.

    Supports:
    - Automatic URL detection
    - Simple shortcodes like [youtube:VIDEO_ID] or [embed:URL]
    - User-friendly syntax
    """

    def __init__(self):
        self.youtube_patterns = [
            r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)',
            r'\[youtube:([a-zA-Z0-9_-]+)\]',
            r'\[yt:([a-zA-Z0-9_-]+)\]'
        ]

        self.twitter_patterns = [
            r'https?://(?:twitter\.com|x\.com)/([\w]+)/status/(\d+)',
            r'\[twitter:(\d+)\]',
            r'\[tweet:(\d+)\]'
        ]

        self.codepen_patterns = [
            r'https?://codepen\.io/([\w-]+)/(?:pen|full)/([a-zA-Z0-9]+)',
            r'\[codepen:([\w-]+)/([a-zA-Z0-9]+)\]',
            r'\[pen:([\w-]+)/([a-zA-Z0-9]+)\]'
        ]

        self.gist_patterns = [
            r'https?://gist\.github\.com/(?:[\w-]+/)?([a-fA-F0-9]+)',
            r'\[gist:([a-fA-F0-9]+)\]'
        ]

    def process_content(self, content):
        """Process content and convert all embeds."""
        if not content:
            return content

        # Process in order: shortcodes first, then URLs
        content = self._process_youtube(content)
        content = self._process_twitter(content)
        content = self._process_codepen(content)
        content = self._process_gist(content)
        content = self._process_generic_embeds(content)

        return mark_safe(content)

    def _process_youtube(self, content):
        """Process YouTube embeds."""
        def replace_youtube(match):
            video_id = match.group(1)
            return self._generate_youtube_embed(video_id)

        for pattern in self.youtube_patterns:
            content = re.sub(pattern, replace_youtube, content, flags=re.IGNORECASE)

        return content

    def _process_twitter(self, content):
        """Process Twitter embeds."""
        def replace_twitter_url(match):
            username = match.group(1)
            post_id = match.group(2)
            url = f"https://twitter.com/{username}/status/{post_id}"
            return self._generate_twitter_embed(url, post_id)

        def replace_twitter_shortcode(match):
            post_id = match.group(1)
            url = f"https://twitter.com/i/status/{post_id}"
            return self._generate_twitter_embed(url, post_id)

        # Handle full URLs
        content = re.sub(self.twitter_patterns[0], replace_twitter_url, content, flags=re.IGNORECASE)

        # Handle shortcodes
        for pattern in self.twitter_patterns[1:]:
            content = re.sub(pattern, replace_twitter_shortcode, content)

        return content

    def _process_codepen(self, content):
        """Process CodePen embeds."""
        def replace_codepen_url(match):
            username = match.group(1)
            pen_id = match.group(2)
            return self._generate_codepen_embed(username, pen_id)

        def replace_codepen_shortcode(match):
            username = match.group(1)
            pen_id = match.group(2)
            return self._generate_codepen_embed(username, pen_id)

        # Handle full URLs
        content = re.sub(self.codepen_patterns[0], replace_codepen_url, content, flags=re.IGNORECASE)

        # Handle shortcodes
        for pattern in self.codepen_patterns[1:]:
            content = re.sub(pattern, replace_codepen_shortcode, content)

        return content

    def _process_gist(self, content):
        """Process GitHub Gist embeds."""
        def replace_gist(match):
            gist_id = match.group(1)
            return self._generate_gist_embed(gist_id)

        for pattern in self.gist_patterns:
            content = re.sub(pattern, replace_gist, content, flags=re.IGNORECASE)

        return content

    def _process_generic_embeds(self, content):
        """Process generic embed shortcodes."""
        def replace_embed(match):
            url = match.group(1)
            title = match.group(2) if len(match.groups()) > 1 and match.group(2) else "Embedded Content"
            return self._generate_generic_embed(url, title)

        # [embed:URL] or [embed:URL:Title]
        pattern = r'\[embed:([^\]:\s]+)(?::([^\]]+))?\]'
        content = re.sub(pattern, replace_embed, content)

        return content

    def _generate_youtube_embed(self, video_id, title="YouTube Video"):
        """Generate YouTube embed HTML."""
        embed_url = f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1&fs=1"

        return f"""
        <div class="embed-container youtube-embed">
            <div class="embed-wrapper">
                <iframe src="{embed_url}" title="{escape(title)}" frameborder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                        allowfullscreen loading="lazy" referrerpolicy="strict-origin-when-cross-origin">
                </iframe>
            </div>
            <div class="embed-caption">
                <i class="fab fa-youtube"></i>
                <span>{escape(title)}</span>
                <a href="https://www.youtube.com/watch?v={video_id}" target="_blank" rel="noopener noreferrer" class="embed-link">
                    Watch on YouTube
                </a>
            </div>
        </div>
        """

    def _generate_twitter_embed(self, url, post_id, theme="dark"):
        """Generate Twitter embed HTML."""
        return f"""
        <div class="embed-container twitter-embed" data-theme="{theme}">
            <div class="embed-wrapper">
                <blockquote class="twitter-tweet" data-theme="{theme}" data-conversation="none">
                    <a href="{escape(url)}">View Tweet</a>
                </blockquote>
            </div>
            <div class="embed-caption">
                <i class="fab fa-twitter"></i>
                <span>Twitter/X Post</span>
                <a href="{escape(url)}" target="_blank" rel="noopener noreferrer" class="embed-link">
                    View on Twitter
                </a>
            </div>
        </div>
        <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
        """

    def _generate_codepen_embed(self, username, pen_id, title="CodePen", height=400):
        """Generate CodePen embed HTML."""
        embed_url = f"https://codepen.io/{username}/embed/{pen_id}?default-tab=result&theme-id=dark"
        pen_url = f"https://codepen.io/{username}/pen/{pen_id}"

        return f"""
        <div class="embed-container codepen-embed">
            <div class="embed-wrapper" style="height: {height}px;">
                <iframe src="{embed_url}" title="{escape(title)}" frameborder="0"
                        loading="lazy" allowtransparency="true" allowfullscreen="true"
                        referrerpolicy="strict-origin-when-cross-origin">
                </iframe>
            </div>
            <div class="embed-caption">
                <i class="fab fa-codepen"></i>
                <span>{escape(title)}</span>
                <a href="{escape(pen_url)}" target="_blank" rel="noopener noreferrer" class="embed-link">
                    View on CodePen
                </a>
            </div>
        </div>
        """

    def _generate_gist_embed(self, gist_id, title="GitHub Gist"):
        """Generate GitHub Gist embed HTML."""
        script_url = f"https://gist.github.com/{gist_id}.js"
        gist_url = f"https://gist.github.com/{gist_id}"

        return f"""
        <div class="embed-container gist-embed">
            <div class="embed-wrapper">
                <script src="{script_url}"></script>
                <noscript>
                    <div class="embed-fallback">
                        <p>JavaScript is required to view this GitHub Gist.</p>
                        <a href="{escape(gist_url)}" target="_blank" rel="noopener noreferrer">
                            View Gist on GitHub
                        </a>
                    </div>
                </noscript>
            </div>
            <div class="embed-caption">
                <i class="fab fa-github"></i>
                <span>{escape(title)}</span>
                <a href="{escape(gist_url)}" target="_blank" rel="noopener noreferrer" class="embed-link">
                    View on GitHub
                </a>
            </div>
        </div>
        """

    def _generate_generic_embed(self, url, title="Embedded Content", height=400):
        """Generate generic embed HTML."""
        return f"""
        <div class="embed-container generic-embed">
            <div class="embed-wrapper" style="height: {height}px;">
                <iframe src="{escape(url)}" title="{escape(title)}" width="100%" height="{height}"
                        frameborder="0" loading="lazy" referrerpolicy="strict-origin-when-cross-origin"
                        sandbox="allow-scripts allow-same-origin allow-presentation">
                </iframe>
            </div>
            <div class="embed-caption">
                <i class="fas fa-external-link-alt"></i>
                <span>{escape(title)}</span>
            </div>
        </div>
        """

    def get_supported_formats(self):
        """Return information about supported embed formats."""
        return {
            'youtube': {
                'name': 'YouTube',
                'examples': [
                    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'https://youtu.be/dQw4w9WgXcQ',
                    '[youtube:dQw4w9WgXcQ]',
                    '[yt:dQw4w9WgXcQ]'
                ]
            },
            'twitter': {
                'name': 'Twitter/X',
                'examples': [
                    'https://twitter.com/username/status/1234567890',
                    'https://x.com/username/status/1234567890',
                    '[twitter:1234567890]',
                    '[tweet:1234567890]'
                ]
            },
            'codepen': {
                'name': 'CodePen',
                'examples': [
                    'https://codepen.io/username/pen/abc123',
                    '[codepen:username/abc123]',
                    '[pen:username/abc123]'
                ]
            },
            'gist': {
                'name': 'GitHub Gist',
                'examples': [
                    'https://gist.github.com/username/abc123def456',
                    '[gist:abc123def456]'
                ]
            },
            'generic': {
                'name': 'Generic Embed',
                'examples': [
                    '[embed:https://example.com/widget]',
                    '[embed:https://example.com/widget:Custom Title]'
                ]
            }
        }


# Global processor instance
embed_processor = EmbedProcessor()