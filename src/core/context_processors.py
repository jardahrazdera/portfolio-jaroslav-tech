# File: src/core/context_processors.py
# This file will contain custom context processors for the project.

from .models import SiteSettings

def site_settings(request):
    """
    Makes the site settings available to all templates.
    """
    return {
        'site_settings': SiteSettings.load()
    }
