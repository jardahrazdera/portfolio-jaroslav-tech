from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator


class UserProfile(models.Model):
    """
    Extends Django's User model with additional profile information.
    One-to-One relationship with User.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        help_text=_("Associated Django user account")
    )
    bio = models.TextField(
        blank=True,
        verbose_name=_("Biography"),
        help_text=_("Short biography or professional summary")
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
        return f"{self.user.username}'s Profile"

    def get_absolute_url(self):
        return reverse('projects:profile_detail', kwargs={'pk': self.pk})


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
        choices=[
            ('planning', _('Planning')),
            ('development', _('Development')),
            ('testing', _('Testing')),
            ('completed', _('Completed')),
            ('archived', _('Archived')),
        ],
        default='planning',
        verbose_name=_("Status"),
        help_text=_("Current status of the project")
    )
    priority = models.CharField(
        max_length=10,
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
        ],
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
