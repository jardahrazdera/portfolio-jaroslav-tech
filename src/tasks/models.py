from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import uuid


class TaskManager(models.Manager):
    """Custom manager for Task model with useful querysets."""
    
    def get_active_tasks(self):
        """Get all non-completed tasks."""
        return self.filter(status__in=['todo', 'in_progress'])
    
    def get_overdue_tasks(self):
        """Get tasks that are past their due date and not completed."""
        return self.filter(
            due_date__lt=timezone.now().date(),
            status__in=['todo', 'in_progress']
        )
    
    def get_high_priority_tasks(self):
        """Get high priority tasks."""
        return self.filter(priority='high')
    
    def get_user_tasks(self, user):
        """Get tasks assigned to a specific user."""
        return self.filter(assignee=user)
    
    def get_project_tasks(self, project):
        """Get all tasks for a specific project."""
        return self.filter(project=project)


class Task(models.Model):
    """
    Comprehensive Task model with subtasks, dependencies, status tracking, and assignee functionality.
    """
    
    STATUS_CHOICES = [
        ('todo', _('To Do')),
        ('in_progress', _('In Progress')),
        ('review', _('In Review')),
        ('testing', _('Testing')),
        ('done', _('Done')),
        ('blocked', _('Blocked')),
        ('cancelled', _('Cancelled')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    TYPE_CHOICES = [
        ('feature', _('Feature')),
        ('bug', _('Bug Fix')),
        ('improvement', _('Improvement')),
        ('documentation', _('Documentation')),
        ('testing', _('Testing')),
        ('research', _('Research')),
        ('maintenance', _('Maintenance')),
    ]
    
    # Basic task information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(
        max_length=200,
        verbose_name=_("Task Title"),
        help_text=_("Brief, descriptive title for the task")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Detailed description of what needs to be done")
    )
    
    # Project relationship
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_("Project"),
        help_text=_("Project this task belongs to")
    )
    
    # Task hierarchy for subtasks
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtasks',
        verbose_name=_("Parent Task"),
        help_text=_("Parent task if this is a subtask")
    )
    
    # Task dependencies
    dependencies = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='dependent_tasks',
        verbose_name=_("Dependencies"),
        help_text=_("Tasks that must be completed before this task can start")
    )
    
    # Assignment and ownership
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name=_("Assignee"),
        help_text=_("User responsible for completing this task")
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tasks',
        verbose_name=_("Creator"),
        help_text=_("User who created this task")
    )
    
    # Task properties
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo',
        verbose_name=_("Status"),
        help_text=_("Current status of the task")
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_("Priority"),
        help_text=_("Task priority level")
    )
    task_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='feature',
        verbose_name=_("Type"),
        help_text=_("Type/category of the task")
    )
    
    # Time tracking
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1)],
        verbose_name=_("Estimated Hours"),
        help_text=_("Estimated time to complete this task")
    )
    actual_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name=_("Actual Hours"),
        help_text=_("Actual time spent on this task")
    )
    
    # Dates
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Due Date"),
        help_text=_("When this task should be completed")
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Start Date"),
        help_text=_("When work on this task should begin")
    )
    completed_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed Date"),
        help_text=_("When this task was completed")
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Progress %"),
        help_text=_("Task completion percentage (0-100)")
    )
    
    # Additional metadata
    tags = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("Tags"),
        help_text=_("Comma-separated tags for categorization")
    )
    external_url = models.URLField(
        blank=True,
        verbose_name=_("External URL"),
        help_text=_("Link to external resource related to this task")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Additional notes or comments about this task")
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )
    
    objects = TaskManager()
    
    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['priority', 'status']),
        ]
    
    def __str__(self):
        return f"{self.project.title} - {self.title}"
    
    def get_absolute_url(self):
        return reverse('tasks:task_detail', kwargs={'pk': self.pk})
    
    # Properties for enhanced functionality
    @property
    def is_overdue(self):
        """Check if task is overdue."""
        if not self.due_date or self.status == 'done':
            return False
        return self.due_date < timezone.now().date()
    
    @property
    def is_subtask(self):
        """Check if this is a subtask."""
        return self.parent_task is not None
    
    @property
    def has_subtasks(self):
        """Check if this task has subtasks."""
        return self.subtasks.exists()
    
    @property
    def can_start(self):
        """Check if task can be started (all dependencies completed)."""
        if not self.dependencies.exists():
            return True
        
        return not self.dependencies.filter(status__in=['todo', 'in_progress', 'review', 'testing', 'blocked']).exists()
    
    @property
    def status_color(self):
        """Get color class for status display."""
        colors = {
            'todo': 'bg-gray-100 text-gray-800',
            'in_progress': 'bg-blue-100 text-blue-800',
            'review': 'bg-yellow-100 text-yellow-800',
            'testing': 'bg-purple-100 text-purple-800',
            'done': 'bg-green-100 text-green-800',
            'blocked': 'bg-red-100 text-red-800',
            'cancelled': 'bg-gray-100 text-gray-600',
        }
        return colors.get(self.status, 'bg-gray-100 text-gray-800')
    
    @property
    def priority_color(self):
        """Get color class for priority display."""
        colors = {
            'low': 'text-green-600',
            'medium': 'text-yellow-600',
            'high': 'text-orange-600',
            'urgent': 'text-red-600',
        }
        return colors.get(self.priority, 'text-gray-600')
    
    def clean(self):
        """Custom validation for Task model."""
        errors = {}
        
        # Validate title
        if self.title and len(self.title.strip()) < 3:
            errors['title'] = _('Task title must be at least 3 characters long.')
        
        # Validate dates
        if self.start_date and self.due_date:
            if self.start_date > self.due_date:
                errors['due_date'] = _('Due date cannot be before start date.')
        
        # Validate parent task doesn't create circular dependency
        if self.parent_task and self.parent_task == self:
            errors['parent_task'] = _('A task cannot be its own parent.')
        
        if errors:
            raise ValidationError(errors)
    
    def mark_completed(self):
        """Mark task as completed."""
        self.status = 'done'
        self.completed_date = timezone.now()
        self.progress_percentage = 100
        self.save(update_fields=['status', 'completed_date', 'progress_percentage', 'updated_at'])
    
    def can_be_edited_by(self, user):
        """Check if user can edit this task."""
        return (
            user == self.creator or 
            user == self.assignee or 
            user == self.project.owner or 
            user.is_superuser
        )
    
    @classmethod
    def get_project_stats(cls, project):
        """Get comprehensive task statistics for a project."""
        project_tasks = cls.objects.filter(project=project)
        
        stats = {
            'total_tasks': project_tasks.count(),
            'completed': project_tasks.filter(status='done').count(),
            'in_progress': project_tasks.filter(status='in_progress').count(),
            'blocked': project_tasks.filter(status='blocked').count(),
            'overdue': project_tasks.filter(
                due_date__lt=timezone.now().date(),
                status__in=['todo', 'in_progress']
            ).count(),
        }
        
        # Calculate completion percentage
        if stats['total_tasks'] > 0:
            stats['completion_percentage'] = int((stats['completed'] / stats['total_tasks']) * 100)
        else:
            stats['completion_percentage'] = 0
        
        return stats


class TaskComment(models.Model):
    """
    Comments on tasks for collaboration and discussion.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_("Task")
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_comments',
        verbose_name=_("Author")
    )
    content = models.TextField(
        verbose_name=_("Comment"),
        help_text=_("Comment content")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    
    class Meta:
        verbose_name = _("Task Comment")
        verbose_name_plural = _("Task Comments")
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment on {self.task.title} by {self.author.username}"
