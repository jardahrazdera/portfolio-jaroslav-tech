from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile, Technology, Project, ProjectImage, WorkSession


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "has_bio", "has_github"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "user__email", "bio"]
    readonly_fields = ["created_at", "updated_at"]
    
    def has_bio(self, obj):
        return bool(obj.bio)
    has_bio.boolean = True
    
    def has_github(self, obj):
        return bool(obj.github_url)
    has_github.boolean = True


@admin.register(Technology)  
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "project_count", "created_at"]
    list_filter = ["category", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]
    
    def project_count(self, obj):
        return obj.projects.count()


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 0


class WorkSessionInline(admin.TabularInline):
    model = WorkSession
    extra = 0
    readonly_fields = ["duration_hours"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "status", "priority", "is_featured", "is_public", "created_at"]
    list_filter = ["status", "priority", "is_featured", "is_public", "created_at", "technologies"]
    search_fields = ["title", "description", "owner__username"]
    filter_horizontal = ["technologies"]
    inlines = [ProjectImageInline, WorkSessionInline]


@admin.register(ProjectImage)
class ProjectImageAdmin(admin.ModelAdmin):
    list_display = ["project", "title", "order", "is_featured", "created_at"]
    list_filter = ["is_featured", "created_at", "project"]


@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    list_display = ["project", "user", "title", "duration_hours", "is_active", "start_time"]
    list_filter = ["is_active", "productivity_rating", "start_time", "project", "user"]
    readonly_fields = ["duration_hours"]
    ordering = ["-start_time"]
