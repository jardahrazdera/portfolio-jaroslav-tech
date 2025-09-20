"""
Template tags for responsive image handling in blog templates.
"""
from django import template
from django.utils.safestring import mark_safe
from django.templatetags.static import static
from ..image_utils import generate_srcset, get_image_url

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

    # Check if at least one processed image exists
    return bool(get_image_url(base_name, 'medium', 'jpg') or get_image_url(base_name, 'medium', 'webp'))


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