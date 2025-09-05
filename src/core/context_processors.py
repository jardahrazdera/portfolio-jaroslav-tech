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
