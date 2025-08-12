from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator, URLValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import re


class UserProfile(models.Model):
    """
    Extends Django's User model with additional profile information.
    One-to-One relationship with User.
    Enhanced with custom validation and business logic methods.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        help_text=_("Associated Django user account")
    )
    bio = models.TextField(
        blank=True,
        max_length=1000,
        verbose_name=_("Biography"),
        help_text=_("Short biography or professional summary (max 1000 characters)")
    )
    github_url = models.URLField(
        blank=True,
        verbose_name=_("GitHub URL"),
        help_text=_("Link to GitHub profile")
    )
    linkedin_url = models.URLField(
        blank=True,
        verbose_name=_("LinkedIn URL"),
        help_text=_("Link to LinkedIn profile")
    )
    portfolio_url = models.URLField(
        blank=True,
        verbose_name=_("Portfolio URL"),
        help_text=_("Link to personal portfolio website")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at")
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        display_name = self.user.get_full_name() or self.user.username
        return f"{display_name}'s Profile"

    def clean(self):
        """Custom validation for UserProfile model"""
        errors = {}
        
        # Validate bio content
        if self.bio:
            if len(self.bio.strip()) < 10:
                errors['bio'] = _("Biography must be at least 10 characters long.")
            
            # Check for suspicious content
            suspicious_patterns = ['test', 'lorem ipsum', 'asdf', 'qwerty']
            if any(pattern in self.bio.lower() for pattern in suspicious_patterns):
                errors['bio'] = _("Please write a genuine biography about yourself.")
        
        # Validate GitHub URL format
        if self.github_url:
            if not re.match(r'^https?://github\.com/[\w\-\.]+/?$', self.github_url):
                errors['github_url'] = _("Please enter a valid GitHub profile URL.")
        
        # Validate LinkedIn URL format
        if self.linkedin_url:
            linkedin_pattern = r'^https?://(?:www\.)?linkedin\.com/in/[\w\-\.]+/?$'
            if not re.match(linkedin_pattern, self.linkedin_url):
                errors['linkedin_url'] = _("Please enter a valid LinkedIn profile URL.")
        
        # Validate portfolio URL
        if self.portfolio_url:
            if 'localhost' in self.portfolio_url.lower() or '127.0.0.1' in self.portfolio_url:
                errors['portfolio_url'] = _("Portfolio URL cannot be a local development server.")
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to perform additional validation and cleanup"""
        self.full_clean()  # This calls clean() method
        
        # Normalize URLs by ensuring they don't end with unnecessary slashes
        if self.github_url and self.github_url.endswith('/'):
            self.github_url = self.github_url.rstrip('/')
        if self.linkedin_url and self.linkedin_url.endswith('/'):
            self.linkedin_url = self.linkedin_url.rstrip('/')
        if self.portfolio_url and self.portfolio_url.endswith('/'):
            self.portfolio_url = self.portfolio_url.rstrip('/')
            
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('projects:profile_detail', kwargs={'pk': self.pk})
    
    # Business logic methods
    @property
    def is_complete(self):
        """Check if profile has all essential information filled"""
        return bool(self.bio and (self.github_url or self.linkedin_url or self.portfolio_url))
    
    @property
    def completion_percentage(self):
        """Calculate profile completion percentage"""
        fields = ['bio', 'github_url', 'linkedin_url', 'portfolio_url']
        filled_fields = sum(1 for field in fields if getattr(self, field))
        return int((filled_fields / len(fields)) * 100)
    
    @property
    def social_links(self):
        """Return a list of available social links"""
        links = []
        if self.github_url:
            links.append(('GitHub', self.github_url))
        if self.linkedin_url:
            links.append(('LinkedIn', self.linkedin_url))
        if self.portfolio_url:
            links.append(('Portfolio', self.portfolio_url))
        return links
    
    @property
    def display_name(self):
        """Get the best display name for the user"""
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username
    
    def get_projects_count(self):
        """Get total number of projects for this user"""
        return self.user.projects.count()
    
    def get_public_projects_count(self):
        """Get number of public projects for this user"""
        return self.user.projects.filter(is_public=True).count()
    
    def get_total_work_hours(self):
        """Calculate total hours worked across all projects"""
        from django.db.models import Sum
        result = self.user.work_sessions.aggregate(total=Sum('duration_hours'))
        return result['total'] or Decimal('0.00')
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create profile for a user (utility method)"""
        profile, created = cls.objects.get_or_create(user=user)
        return profile, created


class Technology(models.Model):
    """
    Represents technologies/tools used in projects (tech stack tags).
    Many-to-Many relationship with Project.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Technology Name"),
        help_text=_("Name of the technology (e.g., Django, React, PostgreSQL)")
    )
    category = models.CharField(
        max_length=50,
        choices=[
            ('frontend', _('Frontend')),
            ('backend', _('Backend')),
            ('database', _('Database')),
            ('devops', _('DevOps')),
            ('mobile', _('Mobile')),
            ('other', _('Other')),
        ],
        default='other',
        verbose_name=_("Category"),
        help_text=_("Category of technology")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Brief description of the technology")
    )
    icon_url = models.URLField(
        blank=True,
        verbose_name=_("Icon URL"),
        help_text=_("URL to technology icon/logo")
    )
    official_url = models.URLField(
        blank=True,
        verbose_name=_("Official URL"),
        help_text=_("Link to official technology website")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )

    class Meta:
        verbose_name = _("Technology")
        verbose_name_plural = _("Technologies")
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects:technology_detail', kwargs={'pk': self.pk})


class Project(models.Model):
    """
    Represents a development project in the portfolio.
    One-to-Many relationship with ProjectImage and WorkSession.
    Many-to-Many relationship with Technology.
    """
    STATUS_CHOICES = [
        ('planning', _('Planning')),
        ('development', _('Development')),
        ('testing', _('Testing')),
        ('completed', _('Completed')),
        ('archived', _('Archived')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
    ]
    
    title = models.CharField(
        max_length=200,
        verbose_name=_("Project Title"),
        help_text=_("Title of the project")
    )
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Detailed description of the project")
    )
    short_description = models.CharField(
        max_length=300,
        verbose_name=_("Short Description"),
        help_text=_("Brief summary for project listings")
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name=_("Project Owner"),
        help_text=_("User who owns this project")
    )
    technologies = models.ManyToManyField(
        Technology,
        blank=True,
        related_name='projects',
        verbose_name=_("Technologies"),
        help_text=_("Technologies used in this project")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planning',
        verbose_name=_("Status"),
        help_text=_("Current status of the project")
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_("Priority"),
        help_text=_("Project priority level")
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Start Date"),
        help_text=_("When the project started")
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("End Date"),
        help_text=_("When the project was completed")
    )
    github_url = models.URLField(
        blank=True,
        verbose_name=_("GitHub URL"),
        help_text=_("Link to project repository")
    )
    live_url = models.URLField(
        blank=True,
        verbose_name=_("Live Demo URL"),
        help_text=_("Link to live project demo")
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name=_("Featured Project"),
        help_text=_("Display this project prominently on portfolio")
    )
    is_public = models.BooleanField(
        default=True,
        verbose_name=_("Public Project"),
        help_text=_("Show this project in public portfolio")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at")
    )

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('projects:project_detail', kwargs={'pk': self.pk})

    @property
    def total_hours_worked(self):
        """Calculate total hours worked on this project."""
        return sum(session.duration_hours for session in self.work_sessions.all())

    @property
    def is_completed(self):
        """Check if project is completed."""
        return self.status == 'completed'

    @property
    def is_active(self):
        """Check if project is actively being worked on"""
        return self.status in ['planning', 'development', 'testing']
    
    @property
    def is_overdue(self):
        """Check if project is overdue (past end date but not completed)"""
        if not self.end_date:
            return False
        return self.end_date < timezone.now().date() and not self.is_completed
    
    @property
    def duration_days(self):
        """Calculate project duration in days"""
        if not self.start_date:
            return None
        
        end_date = self.end_date or timezone.now().date()
        return (end_date - self.start_date).days
    
    @property
    def progress_percentage(self):
        """Calculate project completion percentage based on status"""
        status_progress = {
            'planning': 10,
            'development': 50,
            'testing': 85,
            'completed': 100,
            'archived': 100,
        }
        return status_progress.get(self.status, 0)
    
    def can_be_edited_by(self, user):
        """Check if user can edit this project"""
        return self.owner == user or user.is_superuser
    
    def get_active_session(self):
        """Get currently active work session if any"""
        return self.work_sessions.filter(is_active=True).first()
    
    def mark_completed(self):
        """Mark project as completed"""
        self.status = 'completed'
        if not self.end_date:
            self.end_date = timezone.now().date()
        self.save(update_fields=['status', 'end_date'])
    
    @classmethod
    def get_user_stats(cls, user):
        """Get comprehensive statistics for a user's projects"""
        projects = cls.objects.filter(owner=user)
        
        stats = {
            'total': projects.count(),
            'by_status': {},
            'featured': projects.filter(is_featured=True).count(),
            'public': projects.filter(is_public=True).count(),
        }
        
        # Count by status
        for status_key, status_name in cls.STATUS_CHOICES:
            stats['by_status'][status_name] = projects.filter(status=status_key).count()
        
        return stats

    def clean(self):
        """Custom validation for Project model"""
        errors = {}
        
        # Validate title
        if self.title:
            self.title = self.title.strip()
            if len(self.title) < 3:
                errors['title'] = _('Project title must be at least 3 characters long.')
        
        # Validate descriptions
        if self.short_description and len(self.short_description.strip()) < 10:
            errors['short_description'] = _('Short description must be at least 10 characters long.')
            
        if self.description and len(self.description.strip()) < 20:
            errors['description'] = _('Description must be at least 20 characters long.')
        
        # Validate dates
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                errors['end_date'] = _('End date cannot be before start date.')
        
        if errors:
            raise ValidationError(errors)


class ProjectImage(models.Model):
    """
    Represents images/screenshots for projects (gallery).
    Many-to-One relationship with Project.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_("Project"),
        help_text=_("Project this image belongs to")
    )
    image = models.ImageField(
        upload_to='projects/images/',
        verbose_name=_("Image"),
        help_text=_("Project screenshot or image")
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Image Title"),
        help_text=_("Title or caption for the image")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description of what the image shows")
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Order for displaying images (lower numbers first)")
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name=_("Featured Image"),
        help_text=_("Use as main project image")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )

    class Meta:
        verbose_name = _("Project Image")
        verbose_name_plural = _("Project Images")
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"{self.project.title} - Image {self.order}"

    def get_absolute_url(self):
        return reverse('projects:image_detail', kwargs={'pk': self.pk})


class WorkSession(models.Model):
    """
    Represents a work session/time tracking entry for projects.
    Many-to-One relationship with Project and User.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='work_sessions',
        verbose_name=_("Project"),
        help_text=_("Project this session belongs to")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='work_sessions',
        verbose_name=_("User"),
        help_text=_("User who worked in this session")
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_("Session Title"),
        help_text=_("Brief title describing what was worked on")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description of work done in this session")
    )
    start_time = models.DateTimeField(
        verbose_name=_("Start Time"),
        help_text=_("When the work session started")
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("End Time"),
        help_text=_("When the work session ended")
    )
    duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name=_("Duration (Hours)"),
        help_text=_("Duration of work session in hours")
    )
    productivity_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Productivity Rating"),
        help_text=_("Rate productivity from 1 (low) to 5 (high)")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Additional notes or observations")
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name=_("Active Session"),
        help_text=_("Is this session currently active?")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at")
    )

    class Meta:
        verbose_name = _("Work Session")
        verbose_name_plural = _("Work Sessions")
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.project.title} - {self.title} ({self.duration_hours}h)"

    def get_absolute_url(self):
        return reverse('projects:session_detail', kwargs={'pk': self.pk})

    @property
    def is_completed(self):
        """Check if session is completed (has end time)."""
        return self.end_time is not None

    def save(self, *args, **kwargs):
        """
        Override save to calculate duration if both start and end times are set.
        """
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            self.duration_hours = duration.total_seconds() / 3600
            self.is_active = False
        super().save(*args, **kwargs)

    # Enhanced validation and business logic methods
    @property
    def duration_formatted(self):
        """Get formatted duration string"""
        if not self.duration_hours:
            return "0h 0m"
        
        hours = int(self.duration_hours)
        minutes = int((self.duration_hours - hours) * 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    @property
    def is_today(self):
        """Check if session started today"""
        if not self.start_time:
            return False
        return self.start_time.date() == timezone.now().date()
    
    @property
    def is_this_week(self):
        """Check if session started this week"""
        if not self.start_time:
            return False
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        return self.start_time.date() >= week_start
    
    @property
    def productivity_stars(self):
        """Get productivity rating as star symbols"""
        if not self.productivity_rating:
            return ""
        
        filled_stars = "★" * self.productivity_rating
        empty_stars = "☆" * (5 - self.productivity_rating)
        return filled_stars + empty_stars
    
    def can_be_edited_by(self, user):
        """Check if user can edit this work session"""
        return self.user == user or user.is_superuser
    
    def can_be_stopped_by(self, user):
        """Check if user can stop this active session"""
        return self.is_active and self.user == user
    
    def stop_session(self):
        """Stop this active session"""
        if not self.is_active:
            raise ValueError("Session is not active")
        
        self.end_time = timezone.now()
        self.is_active = False
        self.save()
        return self.duration_hours
    
    def get_break_duration(self, next_session=None):
        """Calculate break duration between this and next session"""
        if not self.end_time or not next_session or not next_session.start_time:
            return None
        
        if next_session.start_time <= self.end_time:
            return timedelta(0)  # Overlapping sessions
        
        break_duration = next_session.start_time - self.end_time
        return break_duration
    
    @classmethod
    def get_user_stats(cls, user, days=30):
        """Get comprehensive statistics for user's work sessions"""
        cutoff_date = timezone.now() - timedelta(days=days)
        sessions = cls.objects.filter(
            user=user,
            start_time__gte=cutoff_date
        )
        
        from django.db.models import Sum, Avg, Count
        
        stats = sessions.aggregate(
            total_sessions=Count('id'),
            total_hours=Sum('duration_hours'),
            avg_session_length=Avg('duration_hours'),
            avg_productivity=Avg('productivity_rating'),
        )
        
        # Convert None values to appropriate defaults
        for key, value in stats.items():
            if value is None:
                stats[key] = 0 if key != 'avg_productivity' else None
        
        # Add additional computed stats
        if stats['total_sessions'] > 0:
            # Calculate productivity distribution
            productivity_dist = {}
            for i in range(1, 6):
                count = sessions.filter(productivity_rating=i).count()
                productivity_dist[i] = count
            stats['productivity_distribution'] = productivity_dist
            
            # Calculate daily averages
            unique_days = sessions.values('start_time__date').distinct().count()
            if unique_days > 0:
                stats['avg_hours_per_day'] = stats['total_hours'] / unique_days
                stats['avg_sessions_per_day'] = stats['total_sessions'] / unique_days
            else:
                stats['avg_hours_per_day'] = 0
                stats['avg_sessions_per_day'] = 0
        
        return stats
    
    @classmethod
    def get_active_sessions(cls, user=None):
        """Get all currently active sessions, optionally filtered by user"""
        queryset = cls.objects.filter(is_active=True).select_related('project', 'user')
        if user:
            queryset = queryset.filter(user=user)
        return queryset
    
    @classmethod
    def get_recent_sessions(cls, user, limit=10):
        """Get recent completed sessions for a user"""
        return cls.objects.filter(
            user=user,
            is_active=False
        ).select_related('project').order_by('-start_time')[:limit]
