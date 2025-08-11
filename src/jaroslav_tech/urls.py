from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap
from core.views import RobotstxtView

sitemaps = {
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", RobotstxtView.as_view()),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("core.urls", namespace="core")),
    path("", include("projects.urls", namespace="projects")),
)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
