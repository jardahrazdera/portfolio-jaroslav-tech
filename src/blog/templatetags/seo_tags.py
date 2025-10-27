from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json

register = template.Library()


@register.simple_tag(takes_context=True)
def seo_meta_tags(context, post=None):
    """Generate comprehensive SEO meta tags for blog posts."""
    request = context.get('request')
    if not request:
        return ''

    # Default values
    site_name = getattr(settings, 'SITE_NAME', 'Jaroslav Tech Blog')
    default_description = getattr(settings, 'SITE_DESCRIPTION', 'Personal tech blog with insights on development, design, and technology.')

    if post:
        title = f"{post.title} | {site_name}"
        description = post.get_meta_description()
        keywords = post.get_meta_keywords()
        url = request.build_absolute_uri(post.get_absolute_url())
        image_url = ''
        if post.featured_image:
            image_url = request.build_absolute_uri(post.featured_image.url)
    else:
        title = site_name
        description = default_description
        keywords = 'technology, programming, web development, software engineering'
        url = request.build_absolute_uri()
        image_url = ''

    # Build meta tags
    meta_tags = []

    # Basic SEO meta tags
    meta_tags.append(f'<title>{title}</title>')
    meta_tags.append(f'<meta name="description" content="{description}">')
    if keywords:
        meta_tags.append(f'<meta name="keywords" content="{keywords}">')

    # Canonical URL
    meta_tags.append(f'<link rel="canonical" href="{url}">')

    # Open Graph tags
    meta_tags.extend([
        f'<meta property="og:title" content="{post.title if post else title}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:site_name" content="{site_name}">',
        '<meta property="og:type" content="article">' if post else '<meta property="og:type" content="website">',
    ])

    if image_url:
        meta_tags.append(f'<meta property="og:image" content="{image_url}">')
        meta_tags.append('<meta property="og:image:type" content="image/jpeg">')

    # Twitter Card tags
    meta_tags.extend([
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{post.title if post else title}">',
        f'<meta name="twitter:description" content="{description}">',
    ])

    if image_url:
        meta_tags.append(f'<meta name="twitter:image" content="{image_url}">')

    # Article-specific meta tags
    if post:
        meta_tags.extend([
            f'<meta property="article:published_time" content="{post.created_at.isoformat()}">',
            f'<meta property="article:modified_time" content="{post.updated_at.isoformat()}">',
            f'<meta property="article:author" content="{post.author.get_full_name() or post.author.username}">',
        ])

        # Add category and tag meta
        for category in post.categories.all():
            meta_tags.append(f'<meta property="article:section" content="{category.name}">')

        for tag in post.tags.all():
            meta_tags.append(f'<meta property="article:tag" content="{tag.name}">')

    return mark_safe('\n    '.join(meta_tags))


@register.simple_tag(takes_context=True)
def structured_data_json_ld(context, post=None):
    """Generate JSON-LD structured data for blog posts."""
    request = context.get('request')
    if not request:
        return ''

    site_name = getattr(settings, 'SITE_NAME', 'Jaroslav Tech Blog')

    if post:
        # Article structured data
        structured_data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": post.title,
            "description": post.get_meta_description(),
            "datePublished": post.created_at.isoformat(),
            "dateModified": post.updated_at.isoformat(),
            "author": {
                "@type": "Person",
                "name": post.author.get_full_name() or post.author.username
            },
            "publisher": {
                "@type": "Organization",
                "name": site_name,
                "url": request.build_absolute_uri('/')
            },
            "url": request.build_absolute_uri(post.get_absolute_url()),
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": request.build_absolute_uri(post.get_absolute_url())
            }
        }

        # Add image if available
        if post.featured_image:
            structured_data["image"] = {
                "@type": "ImageObject",
                "url": request.build_absolute_uri(post.featured_image.url)
            }

        # Add categories and keywords
        if post.categories.exists():
            structured_data["articleSection"] = [cat.name for cat in post.categories.all()]

        if post.tags.exists():
            structured_data["keywords"] = [tag.name for tag in post.tags.all()]

        # Add reading time
        structured_data["timeRequired"] = f"PT{post.get_reading_time()}M"

    else:
        # Website structured data
        structured_data = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": site_name,
            "url": request.build_absolute_uri('/'),
            "description": getattr(settings, 'SITE_DESCRIPTION', 'Personal tech blog with insights on development, design, and technology.'),
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": request.build_absolute_uri(reverse('blog:search')) + "?q={search_term_string}"
                },
                "query-input": "required name=search_term_string"
            }
        }

    json_output = json.dumps(structured_data, indent=2)
    return mark_safe(f'<script type="application/ld+json">\n{json_output}\n</script>')


@register.simple_tag
def page_title(post=None, page_title=None):
    """Generate dynamic page titles."""
    site_name = getattr(settings, 'SITE_NAME', 'Jaroslav Tech Blog')

    if post:
        return f"{post.title} | {site_name}"
    elif page_title:
        return f"{page_title} | {site_name}"
    else:
        return site_name


@register.simple_tag(takes_context=True)
def canonical_url(context, post=None):
    """Generate canonical URL for the current page."""
    request = context.get('request')
    if not request:
        return ''

    if post:
        url = request.build_absolute_uri(post.get_absolute_url())
    else:
        url = request.build_absolute_uri(request.path)

    return format_html('<link rel="canonical" href="{}">', url)


@register.simple_tag
def reading_time(post):
    """Generate reading time meta information."""
    if not post:
        return ''

    time = post.get_reading_time()
    return f"{time} min read"


@register.simple_tag(takes_context=True)
def breadcrumb_json_ld(context, post=None):
    """Generate JSON-LD breadcrumb structured data."""
    request = context.get('request')
    if not request:
        return ''

    breadcrumbs = [
        {
            "@type": "ListItem",
            "position": 1,
            "name": "Home",
            "item": request.build_absolute_uri('/')
        },
        {
            "@type": "ListItem",
            "position": 2,
            "name": "Blog",
            "item": request.build_absolute_uri(reverse('blog:post_list'))
        }
    ]

    if post:
        breadcrumbs.append({
            "@type": "ListItem",
            "position": 3,
            "name": post.title,
            "item": request.build_absolute_uri(post.get_absolute_url())
        })

    structured_data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": breadcrumbs
    }

    json_output = json.dumps(structured_data, indent=2)
    return mark_safe(f'<script type="application/ld+json">\n{json_output}\n</script>')