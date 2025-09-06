# File: src/core/context_processors.py
# This file will contain custom context processors for the project.

from django.conf import settings
from .models import SiteSettings

def site_settings(request):
    """
    Makes the site settings and debug status available to all templates.
    """
    return {
        'site_settings': SiteSettings.load(),
        'debug': settings.DEBUG
    }

def seo_defaults(request):
    """
    Provides default SEO metadata to all templates.
    """
    return {
        'seo': {
            'title': 'Jarek - Fullstack Developer & DevOps Enthusiast',
            'description': 'Personal portfolio of a passionate Fullstack Developer and DevOps enthusiast from the Czech Republic.',
            'image': 'https://jaroslav.tech/static/core/assets/thumbnail.jpg',
            'url': request.build_absolute_uri(),
        }
    }
