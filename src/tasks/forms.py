from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import models
from datetime import datetime, timedelta

from projects.models import Project
from .models import Task, TaskComment


class TaskForm(forms.ModelForm):
    """
    Comprehensive form for creating and editing tasks with advanced validation.
    """
    dependencies = forms.ModelMultipleChoiceField(
        queryset=Task.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text=_("Select tasks that must be completed before this task can start")
    )
    
    assignee = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label=_("Unassigned"),
        help_text=_("User responsible for completing this task")
    )
    
    class Meta:
        model = Task
        fields = [
            "title", "description", "project", "parent_task", "dependencies",
            "assignee", "status", "priority", "task_type",
            "estimated_hours", "due_date", "start_date", "progress_percentage",
            "tags", "external_url", "notes"
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "Enter task title",
                "maxlength": "200"
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "rows": 4,
                "placeholder": "Detailed task description"
            }),
            "project": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "parent_task": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "status": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "priority": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "task_type": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "estimated_hours": forms.NumberInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "step": "0.25",
                "min": "0.1"
            }),
            "due_date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "start_date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "progress_percentage": forms.NumberInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "min": "0",
                "max": "100",
                "step": "5"
            }),
            "tags": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "tag1, tag2, tag3"
            }),
            "external_url": forms.URLInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "https://example.com/related-resource"
            }),
            "notes": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "rows": 3,
                "placeholder": "Additional notes or comments"
            }),
        }
        error_messages = {
            "title": {
                "required": _("Task title is required."),
                "max_length": _("Title cannot exceed 200 characters.")
            },
            "project": {
                "required": _("Please select a project for this task.")
            }
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        
        # Limit projects to user's projects
        if self.user:
            self.fields["project"].queryset = Project.objects.filter(owner=self.user)
            self.fields["assignee"].queryset = User.objects.filter(
                models.Q(id=self.user.id) | 
                models.Q(projects__owner=self.user)
            ).distinct()
        
        # Set project if provided
        if self.project:
            self.fields["project"].initial = self.project
            self.fields["project"].widget.attrs["readonly"] = True
        
        # Configure parent task and dependencies based on project
        if self.instance and self.instance.project_id:
            project_tasks = Task.objects.filter(project=self.instance.project).exclude(id=self.instance.id)
            self.fields["parent_task"].queryset = project_tasks.filter(parent_task__isnull=True)
            self.fields["dependencies"].queryset = project_tasks
        elif self.project:
            project_tasks = Task.objects.filter(project=self.project)
            self.fields["parent_task"].queryset = project_tasks.filter(parent_task__isnull=True)
            self.fields["dependencies"].queryset = project_tasks

    def clean_title(self):
        """Validate task title."""
        title = self.cleaned_data.get("title")
        if not title:
            raise ValidationError(_("Task title is required."))
        
        title = title.strip()
        if len(title) < 3:
            raise ValidationError(_("Task title must be at least 3 characters long."))
        
        return title

    def clean_description(self):
        """Validate task description."""
        description = self.cleaned_data.get("description")
        if description and len(description.strip()) < 5:
            raise ValidationError(_("Task description should be at least 5 characters long."))
        return description

    def clean_estimated_hours(self):
        """Validate estimated hours."""
        hours = self.cleaned_data.get("estimated_hours")
        if hours is not None:
            if hours <= 0:
                raise ValidationError(_("Estimated hours must be greater than 0."))
            if hours > 999:
                raise ValidationError(_("Estimated hours cannot exceed 999."))
        return hours

    def clean_progress_percentage(self):
        """Validate progress percentage."""
        progress = self.cleaned_data.get("progress_percentage")
        if progress is not None:
            if progress < 0 or progress > 100:
                raise ValidationError(_("Progress must be between 0 and 100 percent."))
        return progress

    def clean_tags(self):
        """Validate and normalize tags."""
        tags = self.cleaned_data.get("tags", "")
        if tags:
            # Split by comma and normalize
            tag_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
            # Remove duplicates while preserving order
            unique_tags = []
            seen = set()
            for tag in tag_list:
                if tag not in seen:
                    unique_tags.append(tag)
                    seen.add(tag)
            
            # Validate individual tags
            for tag in unique_tags:
                if len(tag) > 50:
                    raise ValidationError(_("Individual tags cannot exceed 50 characters."))
                if not tag.replace("-", "").replace("_", "").replace(" ", "").isalnum():
                    raise ValidationError(_("Tags can only contain letters, numbers, hyphens, underscores, and spaces."))
            
            if len(unique_tags) > 20:
                raise ValidationError(_("Cannot have more than 20 tags."))
            
            return ", ".join(unique_tags)
        return tags

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        due_date = cleaned_data.get("due_date")
        parent_task = cleaned_data.get("parent_task")
        dependencies = cleaned_data.get("dependencies")
        project = cleaned_data.get("project")

        # Date validation
        if start_date and due_date:
            if start_date > due_date:
                raise ValidationError(_("Start date cannot be after due date."))

        # Parent task validation
        if parent_task:
            if parent_task == self.instance:
                raise ValidationError(_("A task cannot be its own parent."))
            
            # Check if parent is in same project
            if parent_task.project != project:
                raise ValidationError(_("Parent task must be in the same project."))

        # Dependencies validation
        if dependencies:
            for dep in dependencies:
                if dep == self.instance:
                    raise ValidationError(_("A task cannot depend on itself."))
                
                # Check if dependency is in same project
                if dep.project != project:
                    raise ValidationError(_("All dependencies must be in the same project."))

        # Status-specific validation
        status = cleaned_data.get("status")
        progress = cleaned_data.get("progress_percentage", 0)

        if status == "done" and progress < 100:
            cleaned_data["progress_percentage"] = 100
        elif status == "todo" and progress > 0:
            # Don't automatically reset progress for todo status
            pass

        return cleaned_data


class TaskFilterForm(forms.Form):
    """
    Form for filtering tasks with various criteria.
    """
    status = forms.ChoiceField(
        choices=[(""  , _("All Status"))] + Task.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    priority = forms.ChoiceField(
        choices=[(""  , _("All Priorities"))] + Task.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    task_type = forms.ChoiceField(
        choices=[(""  , _("All Types"))] + Task.TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    assignee = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label=_("All Assignees"),
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    due_date_filter = forms.ChoiceField(
        choices=[
            ("", _("Any Due Date")),
            ("overdue", _("Overdue")),
            ("today", _("Due Today")),
            ("week", _("Due This Week")),
            ("month", _("Due This Month")),
            ("no_date", _("No Due Date")),
        ],
        required=False,
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
            "placeholder": _("Search tasks...")
        })
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)
        
        # Filter assignees based on project or user context
        if project:
            # Get users involved in the project
            self.fields["assignee"].queryset = User.objects.filter(
                models.Q(id=project.owner.id) | 
                models.Q(assigned_tasks__project=project)
            ).distinct()
        elif user:
            # Get users from projects owned by the user
            self.fields["assignee"].queryset = User.objects.filter(
                models.Q(id=user.id) | 
                models.Q(assigned_tasks__project__owner=user)
            ).distinct()

    def clean_search(self):
        """Validate search query."""
        search = self.cleaned_data.get("search")
        if search:
            search = search.strip()
            if len(search) < 2:
                raise ValidationError(_("Search query must be at least 2 characters long."))
            if len(search) > 100:
                raise ValidationError(_("Search query cannot exceed 100 characters."))
        return search


class TaskCommentForm(forms.ModelForm):
    """
    Form for adding comments to tasks.
    """
    class Meta:
        model = TaskComment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "rows": 3,
                "placeholder": "Add a comment..."
            })
        }
        error_messages = {
            "content": {
                "required": _("Comment content is required.")
            }
        }

    def clean_content(self):
        """Validate comment content."""
        content = self.cleaned_data.get("content")
        if content:
            content = content.strip()
            if len(content) < 3:
                raise ValidationError(_("Comment must be at least 3 characters long."))
            if len(content) > 2000:
                raise ValidationError(_("Comment cannot exceed 2000 characters."))
        return content
