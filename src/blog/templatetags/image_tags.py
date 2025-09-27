"""
Advanced template tags for optimized image rendering with WebP support,
lazy loading, preload hints, and CDN optimization.
"""
from django import template
from django.utils.safestring import mark_safe
from django.templatetags.static import static
from django.core.files.storage import default_storage
from ..image_utils import generate_srcset, get_image_url
from ..image_utils_enhanced import (
    generate_srcset as generate_srcset_enhanced,
    get_image_url as get_image_url_enhanced,
    generate_picture_element,
    ImageCDNOptimizer,
    AltTextManager
)
from ..syntax_highlighter import process_code_blocks

register = template.Library()


@register.simple_tag
def responsive_image(post, size='medium', css_class='', alt_text='', lazy=True):
    """
    Generate responsive image HTML with WebP support and lazy loading.

    Usage:
        {% responsive_image post size='large' css_class='hero-image' alt_text='Blog post featured image' %}

    Args:
        post: Post object with featured image
        size: Default size to use ('small', 'medium', 'large', 'xl')
        css_class: CSS classes to apply to the image
        alt_text: Alt text for accessibility
        lazy: Whether to enable lazy loading
    """
    if not post.featured_image:
        return ''

    base_name = post.get_image_base_name()
    if not base_name:
        # Fallback to original image
        return f'<img src="{post.featured_image.url}" alt="{alt_text or post.title}" class="{css_class}">'

    # Get WebP and JPEG URLs
    webp_url = get_image_url(base_name, size, 'webp')
    jpeg_url = get_image_url(base_name, size, 'jpg')

    # Fallback to original if processed images don't exist
    if not webp_url and not jpeg_url:
        return f'<img src="{post.featured_image.url}" alt="{alt_text or post.title}" class="{css_class}">'

    # Generate srcsets for responsive images
    webp_srcset = generate_srcset(base_name, 'webp')
    jpeg_srcset = generate_srcset(base_name, 'jpg')

    # Default image URL (prefer JPEG for compatibility)
    default_url = jpeg_url or webp_url or post.featured_image.url

    # Build HTML with picture element for WebP support
    html_parts = ['<picture>']

    # WebP source with srcset
    if webp_url and webp_srcset:
        html_parts.append(f'  <source srcset="{webp_srcset}" type="image/webp">')
    elif webp_url:
        html_parts.append(f'  <source srcset="{webp_url}" type="image/webp">')

    # JPEG source with srcset
    if jpeg_url and jpeg_srcset:
        html_parts.append(f'  <source srcset="{jpeg_srcset}" type="image/jpeg">')

    # Fallback img element
    img_attrs = [
        f'src="{default_url}"',
        f'alt="{alt_text or post.title}"',
    ]

    if css_class:
        img_attrs.append(f'class="{css_class}"')

    if lazy:
        img_attrs.append('loading="lazy"')

    # Add sizes attribute for responsive images
    if jpeg_srcset or webp_srcset:
        img_attrs.append('sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"')

    html_parts.append(f'  <img {" ".join(img_attrs)}>')
    html_parts.append('</picture>')

    return mark_safe('\n'.join(html_parts))


@register.simple_tag
def image_url(post, size='medium', format_type='jpg'):
    """
    Get URL for a specific image size and format.

    Usage:
        {% image_url post size='large' format_type='webp' %}

    Args:
        post: Post object with featured image
        size: Image size ('thumbnail', 'small', 'medium', 'large', 'xl')
        format_type: Image format ('jpg' or 'webp')
    """
    if not post.featured_image:
        return ''

    base_name = post.get_image_base_name()
    if not base_name:
        return post.featured_image.url

    url = get_image_url(base_name, size, format_type)
    return url or post.featured_image.url


@register.simple_tag
def image_srcset(post, format_type='jpg'):
    """
    Generate srcset string for responsive images.

    Usage:
        <img srcset="{% image_srcset post format_type='webp' %}" src="...">

    Args:
        post: Post object with featured image
        format_type: Image format ('jpg' or 'webp')
    """
    if not post.featured_image:
        return ''

    base_name = post.get_image_base_name()
    if not base_name:
        return ''

    return generate_srcset(base_name, format_type)


@register.filter
def has_processed_images(post):
    """
    Check if a post has processed images available.

    Usage:
        {% if post|has_processed_images %}
            <!-- Use responsive images -->
        {% else %}
            <!-- Use original image -->
        {% endif %}
    """
    if not post.featured_image:
        return False

    base_name = post.get_image_base_name()
    if not base_name:
        return False

    # Check if at least one processed image exists (enhanced check)
    return bool(
        get_image_url_enhanced(base_name, 'md', 'jpg') or
        get_image_url_enhanced(base_name, 'md', 'webp') or
        get_image_url(base_name, 'medium', 'jpg') or
        get_image_url(base_name, 'medium', 'webp')
    )


@register.inclusion_tag('blog/partials/lazy_image.html')
def lazy_image(post, size='medium', css_class='', alt_text=''):
    """
    Render lazy-loaded image with loading placeholder.

    Usage:
        {% lazy_image post size='large' css_class='hero-image' alt_text='Featured image' %}
    """
    return {
        'post': post,
        'size': size,
        'css_class': css_class,
        'alt_text': alt_text or post.title,
        'has_image': bool(post.featured_image),
    }


@register.simple_tag
def image_dimensions(post, size='medium'):
    """
    Get image dimensions for a specific size.

    Usage:
        {% image_dimensions post size='large' as dimensions %}
        Width: {{ dimensions.width }}, Height: {{ dimensions.height }}
    """
    from ..image_utils import ImageProcessor

    if size not in ImageProcessor.SIZES:
        return {'width': 0, 'height': 0}

    width, height = ImageProcessor.SIZES[size]
    return {'width': width, 'height': height}


@register.filter
def highlight_syntax(content):
    """
    Process blog content to add syntax highlighting to code blocks.

    Usage:
        {{ post.content|highlight_syntax|safe }}
    """
    if not content:
        return ''

    return process_code_blocks(content)


# Advanced image optimization tags

@register.simple_tag
def optimized_image(base_name, alt_text="", css_class="", sizes="100vw", loading="lazy", is_critical=False):
    """
    Render an optimized responsive image with WebP support and lazy loading.

    Usage:
        {% optimized_image "my_image_abc123" "Alt text" "img-class" "(max-width: 768px) 100vw, 50vw" %}
    """
    if not base_name:
        return ""

    # Generate WebP and JPEG srcsets using enhanced processor
    webp_srcset = generate_srcset_enhanced(base_name, 'webp')
    jpg_srcset = generate_srcset_enhanced(base_name, 'jpg')

    # Get fallback URL
    fallback_url = get_image_url_enhanced(base_name, 'md', 'jpg')

    if not fallback_url:
        return f'<img src="" alt="{alt_text}" class="{css_class}" loading="{loading}" />'

    # Build picture element HTML
    picture_classes = f"responsive-image {css_class}".strip()
    critical_attr = 'data-critical="true"' if is_critical else ''
    loading_attr = f'loading="{loading}"' if not is_critical else 'loading="eager"'

    html_parts = [f'<picture class="{picture_classes}" {critical_attr}>']

    # WebP source
    if webp_srcset:
        html_parts.append(f'  <source srcset="{webp_srcset}" sizes="{sizes}" type="image/webp" />')

    # JPEG source
    if jpg_srcset:
        html_parts.append(f'  <source srcset="{jpg_srcset}" sizes="{sizes}" type="image/jpeg" />')

    # Fallback img
    html_parts.append(
        f'  <img src="{fallback_url}" alt="{alt_text}" '
        f'class="responsive-img" {loading_attr} />'
    )

    html_parts.append('</picture>')

    return mark_safe('\n'.join(html_parts))


@register.simple_tag
def lazy_image_enhanced(base_name, alt_text="", css_class="", sizes="100vw"):
    """
    Render a lazy-loaded image with intersection observer support.

    Usage:
        {% lazy_image_enhanced "my_image_abc123" "Alt text" "img-class" %}
    """
    if not base_name:
        return ""

    # Get image URLs
    webp_url = get_image_url_enhanced(base_name, 'md', 'webp')
    jpg_url = get_image_url_enhanced(base_name, 'md', 'jpg')
    thumbnail_url = get_image_url_enhanced(base_name, 'thumbnail', 'jpg')

    if not jpg_url:
        return f'<img src="" alt="{alt_text}" class="{css_class}" />'

    # Generate srcsets
    webp_srcset = generate_srcset_enhanced(base_name, 'webp')
    jpg_srcset = generate_srcset_enhanced(base_name, 'jpg')

    picture_classes = f"lazy-image {css_class}".strip()

    # SVG placeholder for better performance
    svg_placeholder = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PC9zdmc+'
    placeholder_src = thumbnail_url or svg_placeholder

    html_parts = [f'<picture class="{picture_classes}" data-loaded="false">']

    # WebP source with data attributes for lazy loading
    if webp_srcset:
        html_parts.append(
            f'  <source data-srcset="{webp_srcset}" sizes="{sizes}" type="image/webp" />'
        )

    # JPEG source with data attributes
    if jpg_srcset:
        html_parts.append(
            f'  <source data-srcset="{jpg_srcset}" sizes="{sizes}" type="image/jpeg" />'
        )

    # Image with placeholder
    html_parts.append(
        f'  <img src="{placeholder_src}" data-src="{jpg_url}" '
        f'data-webp-src="{webp_url or ""}" alt="{alt_text}" '
        f'class="lazy-img" loading="lazy" />'
    )

    html_parts.append('</picture>')

    return mark_safe('\n'.join(html_parts))


@register.simple_tag
def hero_image(base_name, alt_text="", css_class="hero-image", sizes="100vw"):
    """
    Render a hero image with preload hints and immediate loading.

    Usage:
        {% hero_image "hero_image_abc123" "Hero alt text" %}
    """
    if not base_name:
        return ""

    # Use hero-specific sizes if available
    webp_srcset = generate_srcset_enhanced(base_name, 'webp', 'hero')
    jpg_srcset = generate_srcset_enhanced(base_name, 'jpg', 'hero')

    # Fallback to standard sizes if hero sizes don't exist
    if not webp_srcset and not jpg_srcset:
        webp_srcset = generate_srcset_enhanced(base_name, 'webp')
        jpg_srcset = generate_srcset_enhanced(base_name, 'jpg')

    # Get largest available image for immediate display
    fallback_url = (
        get_image_url_enhanced(base_name, 'hero_xl', 'jpg') or
        get_image_url_enhanced(base_name, 'hero_lg', 'jpg') or
        get_image_url_enhanced(base_name, 'xl', 'jpg') or
        get_image_url_enhanced(base_name, 'lg', 'jpg')
    )

    if not fallback_url:
        return f'<img src="" alt="{alt_text}" class="{css_class}" />'

    picture_classes = f"hero-image {css_class}".strip()

    html_parts = [f'<picture class="{picture_classes}" data-critical="true">']

    # WebP source
    if webp_srcset:
        html_parts.append(f'  <source srcset="{webp_srcset}" sizes="{sizes}" type="image/webp" />')

    # JPEG source
    if jpg_srcset:
        html_parts.append(f'  <source srcset="{jpg_srcset}" sizes="{sizes}" type="image/jpeg" />')

    # Hero img with immediate loading
    html_parts.append(
        f'  <img src="{fallback_url}" alt="{alt_text}" '
        f'class="hero-img" loading="eager" fetchpriority="high" />'
    )

    html_parts.append('</picture>')

    return mark_safe('\n'.join(html_parts))


@register.simple_tag
def image_preload_hints(base_name, priority="high"):
    """
    Generate preload hints for critical images.

    Usage:
        {% image_preload_hints "hero_image_abc123" "high" %}
    """
    if not base_name:
        return ""

    # Get best available formats for preloading
    webp_url = get_image_url_enhanced(base_name, 'lg', 'webp')
    jpg_url = get_image_url_enhanced(base_name, 'lg', 'jpg')

    hints = []

    # Preload WebP if available
    if webp_url:
        hints.append(
            f'<link rel="preload" as="image" href="{webp_url}" '
            f'type="image/webp" fetchpriority="{priority}" />'
        )

    # Preload JPEG as fallback if no WebP
    elif jpg_url:
        hints.append(
            f'<link rel="preload" as="image" href="{jpg_url}" '
            f'type="image/jpeg" fetchpriority="{priority}" />'
        )

    return mark_safe('\n'.join(hints))


@register.simple_tag
def post_featured_image_optimized(post, css_class="featured-image", sizes="100vw", loading="eager"):
    """
    Render a post's featured image with full optimization.

    Usage:
        {% post_featured_image_optimized post "custom-class" %}
    """
    if not post.featured_image:
        return ""

    base_name = post.get_image_base_name()
    if not base_name:
        return f'<img src="{post.featured_image.url}" alt="{post.title}" class="{css_class}" />'

    # Generate smart alt text
    alt_text = post.get_meta_description()[:100] or f"Featured image for {post.title}"

    return optimized_image(base_name, alt_text, css_class, sizes, loading, is_critical=True)


@register.simple_tag
def responsive_sizes_attr(breakpoints=None):
    """
    Generate responsive sizes attribute for images.

    Usage:
        {% responsive_sizes_attr %}
        {% responsive_sizes_attr "mobile:100vw,tablet:50vw,desktop:33vw" %}
    """
    if breakpoints:
        # Parse custom breakpoints
        parts = breakpoints.split(',')
        size_map = {}
        for part in parts:
            if ':' in part:
                device, size = part.split(':')
                if device == 'mobile':
                    size_map['320px'] = size
                elif device == 'tablet':
                    size_map['768px'] = size
                elif device == 'desktop':
                    size_map['1024px'] = size
    else:
        size_map = None

    return ImageCDNOptimizer.generate_responsive_sizes(size_map)


@register.simple_tag
def smart_alt_text(image_path, context=None, user_input=None):
    """
    Generate smart alt text for images.

    Usage:
        {% smart_alt_text "path/to/image.jpg" %}
    """
    return AltTextManager.generate_smart_alt(image_path, context, user_input)


@register.filter
def has_optimized_images(base_name):
    """
    Check if optimized images exist for a base name.

    Usage:
        {% if post.get_image_base_name|has_optimized_images %}
    """
    if not base_name:
        return False

    # Check for at least one processed image
    for size in ['thumbnail', 'xs', 'sm', 'md', 'lg']:
        for fmt in ['webp', 'jpg']:
            filename = f"blog/images/processed/{base_name}_{size}.{fmt}"
            if default_storage.exists(filename):
                return True

    return False


@register.simple_tag
def image_meta_tags(post):
    """
    Generate Open Graph and Twitter meta tags for post images.

    Usage:
        {% image_meta_tags post %}
    """
    if not post.featured_image:
        return ""

    base_name = post.get_image_base_name()

    # Get the best image for social sharing (large, high quality)
    og_image_url = None
    if base_name:
        og_image_url = (
            get_image_url_enhanced(base_name, 'xl', 'jpg') or
            get_image_url_enhanced(base_name, 'lg', 'jpg') or
            get_image_url_enhanced(base_name, 'md', 'jpg')
        )

    if not og_image_url:
        og_image_url = post.featured_image.url

    # Make URL absolute
    if og_image_url.startswith('/'):
        og_image_url = f"https://jaroslav.tech{og_image_url}"

    alt_description = post.get_meta_description()[:100] or post.title

    meta_tags = [
        f'<meta property="og:image" content="{og_image_url}" />',
        f'<meta property="og:image:alt" content="{alt_description}" />',
        f'<meta name="twitter:image" content="{og_image_url}" />',
        f'<meta name="twitter:image:alt" content="{alt_description}" />',
    ]

    return mark_safe('\n'.join(meta_tags))


@register.simple_tag
def critical_image_css():
    """
    Generate critical CSS for above-the-fold images.

    Usage:
        {% critical_image_css %}
    """
    css = """
    <style>
    /* Image loading states */
    .responsive-image, .lazy-image, .hero-image {
        background: linear-gradient(90deg, #f0f0f0 25%, transparent 25%, transparent 50%, #f0f0f0 50%, #f0f0f0 75%, transparent 75%, transparent);
        background-size: 20px 20px;
        animation: loading-shimmer 1.5s infinite;
    }

    .responsive-img, .hero-img, .lazy-img {
        transition: opacity 0.3s ease-in-out, filter 0.3s ease-in-out;
        opacity: 0;
        filter: blur(5px);
    }

    .responsive-img.loaded, .hero-img.loaded, .lazy-img.loaded {
        opacity: 1;
        filter: blur(0);
    }

    .responsive-img.loading, .hero-img.loading, .lazy-img.loading {
        opacity: 0.7;
        filter: blur(2px);
    }

    .responsive-img.error, .hero-img.error, .lazy-img.error {
        opacity: 0.5;
        filter: grayscale(100%);
    }

    /* Responsive image containers */
    .responsive-image, .lazy-image, .hero-image {
        display: block;
        width: 100%;
        height: auto;
    }

    .responsive-image img, .lazy-image img, .hero-image img {
        width: 100%;
        height: auto;
        display: block;
    }

    @keyframes loading-shimmer {
        0% { background-position: -468px 0; }
        100% { background-position: 468px 0; }
    }

    /* Remove shimmer once loaded */
    .responsive-image[data-loaded="true"],
    .lazy-image[data-loaded="true"],
    .hero-image {
        background: none;
        animation: none;
    }
    </style>
    """

    return mark_safe(css)


@register.inclusion_tag('blog/partials/optimized_image.html', takes_context=True)
def include_optimized_image(context, base_name, alt_text="", css_class="", sizes="100vw", loading="lazy", is_hero=False, original_url=None):
    """
    Include an optimized image using a template partial.

    Usage:
        {% include_optimized_image "my_image_abc123" "Alt text" "img-class" %}
    """
    webp_srcset = generate_srcset_enhanced(base_name, 'webp', 'hero' if is_hero else 'standard')
    jpg_srcset = generate_srcset_enhanced(base_name, 'jpg', 'hero' if is_hero else 'standard')
    fallback_url = get_image_url_enhanced(base_name, 'md', 'jpg')

    return {
        'base_name': base_name,
        'alt_text': alt_text,
        'css_class': css_class,
        'sizes': sizes,
        'loading': loading,
        'is_hero': is_hero,
        'webp_srcset': webp_srcset,
        'jpg_srcset': jpg_srcset,
        'fallback_url': fallback_url,
        'original_url': original_url,
        'is_critical': is_hero or loading == 'eager',
        'request': context.get('request')
    }


@register.inclusion_tag('blog/partials/optimized_image.html', takes_context=True)
def post_optimized_image(context, post, css_class="", sizes="100vw", loading="lazy", is_hero=False):
    """
    Include an optimized image for a post with automatic fallback to original image.

    Usage:
        {% post_optimized_image post "featured-image" "(max-width: 768px) 100vw, 50vw" %}
    """
    if not post.featured_image:
        return {
            'fallback_url': None,
            'original_url': None,
            'base_name': None,
            'alt_text': post.title,
            'css_class': css_class,
            'sizes': sizes,
            'loading': loading,
            'is_hero': is_hero,
            'webp_srcset': None,
            'jpg_srcset': None,
            'is_critical': is_hero or loading == 'eager',
            'request': context.get('request')
        }

    base_name = post.get_image_base_name()
    if not base_name:
        # No processed images, use original only
        return {
            'fallback_url': post.featured_image.url,
            'original_url': post.featured_image.url,
            'base_name': None,
            'alt_text': post.title,
            'css_class': css_class,
            'sizes': sizes,
            'loading': loading,
            'is_hero': is_hero,
            'webp_srcset': None,
            'jpg_srcset': None,
            'is_critical': is_hero or loading == 'eager',
            'request': context.get('request')
        }

    # Get processed images
    webp_srcset = generate_srcset_enhanced(base_name, 'webp', 'hero' if is_hero else 'standard')
    jpg_srcset = generate_srcset_enhanced(base_name, 'jpg', 'hero' if is_hero else 'standard')
    fallback_url = get_image_url_enhanced(base_name, 'md', 'jpg')

    return {
        'base_name': base_name,
        'alt_text': post.title,
        'css_class': css_class,
        'sizes': sizes,
        'loading': loading,
        'is_hero': is_hero,
        'webp_srcset': webp_srcset,
        'jpg_srcset': jpg_srcset,
        'fallback_url': fallback_url,
        'original_url': post.featured_image.url,  # Always provide original as final fallback
        'is_critical': is_hero or loading == 'eager',
        'request': context.get('request')
    }