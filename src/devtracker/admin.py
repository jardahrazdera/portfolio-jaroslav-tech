from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Project, Task, TimeLog, Tag, Technology, ProjectStatus


class TaskInline(admin.TabularInline):
    """Inline editing of tasks within project admin."""
    model = Task
    extra = 0
    fields = ('title', 'priority', 'is_completed', 'created_at')
    readonly_fields = ('created_at',)


class TimeLogInline(admin.TabularInline):
    """Inline editing of time logs within project admin."""
    model = TimeLog
    extra = 0
    fields = ('date', 'hours', 'description', 'created_at')
    readonly_fields = ('created_at',)


class ProjectStatusInline(admin.TabularInline):
    """Inline editing of status updates within project admin."""
    model = ProjectStatus
    extra = 0
    fields = ('status', 'date', 'note')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Project model."""
    list_display = ('name', 'owner', 'status', 'start_date', 'end_date', 'is_public', 'created_at')
    list_filter = ('status', 'is_public', 'created_at', 'start_date', 'end_date', 'owner')
    search_fields = ('name', 'description', 'owner__username')
    prepopulated_fields = {'slug': ('name',)}
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'owner')
        }),
        ('Project Details', {
            'fields': ('status', 'start_date', 'end_date', 'is_public')
        }),
        ('External Links', {
            'fields': ('github_url', 'live_url'),
            'classes': ('collapse',)
        }),
        ('Relations', {
            'fields': ('tags', 'technologies'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automatic timestamps'
        })
    )
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('tags', 'technologies')
    
    inlines = [TaskInline, TimeLogInline, ProjectStatusInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Task model."""
    list_display = ('title', 'project', 'priority', 'is_completed', 'created_at', 'completed_at')
    list_filter = ('priority', 'is_completed', 'created_at', 'project__status', 'project__owner')
    search_fields = ('title', 'description', 'project__name')
    date_hierarchy = 'created_at'
    ordering = ('-priority', '-created_at')
    
    fieldsets = (
        ('Task Information', {
            'fields': ('project', 'title', 'description')
        }),
        ('Task Details', {
            'fields': ('priority', 'is_completed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('created_at', 'completed_at')


@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    """Enhanced admin interface for TimeLog model."""
    list_display = ('project', 'date', 'hours', 'description', 'created_at')
    list_filter = ('date', 'created_at', 'project__status', 'project__owner')
    search_fields = ('description', 'project__name')
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')
    
    fieldsets = (
        ('Time Entry', {
            'fields': ('project', 'date', 'hours', 'description')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('created_at',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Tag model."""
    list_display = ('name', 'slug', 'color', 'project_count')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    
    def project_count(self, obj):
        """Display number of projects using this tag."""
        return obj.project_set.count()
    project_count.short_description = 'Projects'


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Technology model."""
    list_display = ('name', 'icon_class', 'project_count')
    search_fields = ('name',)
    ordering = ('name',)
    
    def project_count(self, obj):
        """Display number of projects using this technology."""
        return obj.project_set.count()
    project_count.short_description = 'Projects'


@admin.register(ProjectStatus)
class ProjectStatusAdmin(admin.ModelAdmin):
    """Enhanced admin interface for ProjectStatus model."""
    list_display = ('project', 'status', 'date', 'note_preview')
    list_filter = ('date', 'project__status', 'project__owner')
    search_fields = ('status', 'note', 'project__name')
    date_hierarchy = 'date'
    ordering = ('-date',)
    
    def note_preview(self, obj):
        """Display truncated note."""
        if obj.note:
            return obj.note[:50] + ('...' if len(obj.note) > 50 else '')
        return '-'
    note_preview.short_description = 'Note Preview'


# User approval management
class UserApprovalAdmin(BaseUserAdmin):
    """Enhanced User admin for managing registrations and approvals."""
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined', 'project_count')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    actions = ['approve_users', 'deactivate_users']
    
    def project_count(self, obj):
        """Display number of projects owned by user."""
        return obj.projects.count()
    project_count.short_description = 'Projects'
    
    def approve_users(self, request, queryset):
        """Approve selected users."""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} user(s) approved successfully.')
    approve_users.short_description = 'Approve selected users'
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} user(s) deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'


# Re-register User admin with our custom admin
admin.site.unregister(User)
admin.site.register(User, UserApprovalAdmin)
