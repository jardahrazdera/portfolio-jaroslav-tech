from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Tag(models.Model):
    """Categorization tag."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    color = models.CharField(max_length=7, default='#CBA6F7')  # Mauve from Catppuccin

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"


class Technology(models.Model):
    """Technology/tool used in projects."""
    name = models.CharField(max_length=50, unique=True)
    icon_class = models.CharField(max_length=50, blank=True)  # For future icon support

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Technology"
        verbose_name_plural = "Technologies"


class Project(models.Model):
    """Main project entity."""
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('on-hold', 'On Hold'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    github_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Relations
    tags = models.ManyToManyField('Tag', blank=True)
    technologies = models.ManyToManyField('Technology', blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_progress_percentage(self):
        """Calculate project completion percentage based on completed tasks."""
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        completed_tasks = self.tasks.filter(is_completed=True).count()
        return round((completed_tasks / total_tasks) * 100)

    def get_total_hours(self):
        """Calculate total hours logged for this project."""
        return sum(log.hours for log in self.time_logs.all())

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ['-created_at']


class Task(models.Model):
    """Individual task within a project."""
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.is_completed and self.completed_at:
            self.completed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project.name} - {self.title}"

    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ['-priority', 'created_at']


class TimeLog(models.Model):
    """Time tracking entry."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='time_logs')
    date = models.DateField()
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.name} - {self.hours}h on {self.date}"

    class Meta:
        verbose_name = "Time Log"
        verbose_name_plural = "Time Logs"
        ordering = ['-date', '-created_at']


class ProjectStatus(models.Model):
    """Project milestone/status update."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='status_updates')
    status = models.CharField(max_length=200)
    date = models.DateField()
    note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.project.name} - {self.status}"

    class Meta:
        verbose_name = "Project Status"
        verbose_name_plural = "Project Statuses"
        ordering = ['-date']
