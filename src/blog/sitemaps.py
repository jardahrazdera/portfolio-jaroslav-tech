from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Post, Category, Tag


class BlogPostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = 'https'
    i18n = True

    def items(self):
        return Post.objects.filter(is_published=True).order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class BlogCategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = 'https'
    i18n = True

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse('blog:category_detail', kwargs={'slug': obj.slug})


class BlogTagSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5
    protocol = 'https'
    i18n = True

    def items(self):
        return Tag.objects.all()

    def location(self, obj):
        return reverse('blog:tag_detail', kwargs={'slug': obj.slug})


class BlogStaticSitemap(Sitemap):
    priority = 0.7
    changefreq = 'weekly'
    protocol = 'https'
    i18n = True

    def items(self):
        return ['blog:post_list', 'blog:category_list', 'blog:tag_list']

    def location(self, item):
        return reverse(item)