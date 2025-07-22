# src/core/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.9
    changefreq = 'weekly'
    i18n = True

    def items(self):
        return ['core:index']

    def location(self, item):
        return reverse(item)