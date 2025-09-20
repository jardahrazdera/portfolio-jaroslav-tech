from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Tag, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'featured_image_thumbnail', 'is_published', 'is_featured', 'created_at')
    list_filter = ('is_published', 'is_featured', 'categories', 'created_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('categories', 'tags')
    list_editable = ('is_published', 'is_featured')
    fields = ('title', 'slug', 'featured_image', 'excerpt', 'content', 'author', 'categories', 'tags', 'is_published', 'is_featured')

    def featured_image_thumbnail(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.featured_image.url
            )
        return "No image"
    featured_image_thumbnail.short_description = 'Image'
