from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
import re
from .models import Project, Technology, WorkSession, ProjectImage, UserProfile


class ProjectForm(forms.ModelForm):
    """
    Comprehensive form for creating and editing projects with advanced validation.
    """
    technologies = forms.ModelMultipleChoiceField(
        queryset=Technology.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text=_("Select technologies used in this project")
    )
    
    class Meta:
        model = Project
        fields = [
            "title", "short_description", "description",
            "technologies", "status", "priority",
            "start_date", "end_date",
            "github_url", "live_url",
            "is_featured", "is_public"
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "Enter project title",
                "maxlength": "200"
            }),
            "short_description": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "Brief description for listings",
                "maxlength": "300"
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "rows": 5,
                "placeholder": "Detailed project description"
            }),
            "status": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "priority": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "start_date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "end_date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "github_url": forms.URLInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "https://github.com/username/repo"
            }),
            "live_url": forms.URLInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "https://your-project.com"
            }),
        }
        error_messages = {
            "title": {
                "required": _("Project title is required."),
                "max_length": _("Title cannot exceed 200 characters.")
            },
            "short_description": {
                "max_length": _("Short description cannot exceed 300 characters.")
            }
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Organize technologies by category for better UX
        if self.fields["technologies"].queryset:
            self.fields["technologies"].queryset = Technology.objects.all().order_by("category", "name")

    def clean_title(self):
        """Validate project title"""
        title = self.cleaned_data.get("title")
        if not title:
            raise ValidationError(_("Project title is required."))
        
        # Check for profanity or inappropriate content
        inappropriate_words = ["spam", "test123", "asdf"]
        if any(word in title.lower() for word in inappropriate_words):
            raise ValidationError(_("Please choose a more descriptive project title."))
        
        # Check for duplicate titles for the same user
        if self.user:
            existing = Project.objects.filter(
                title__iexact=title, 
                owner=self.user
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(_("You already have a project with this title."))
        
        return title

    def clean_short_description(self):
        """Validate short description"""
        short_desc = self.cleaned_data.get("short_description")
        if short_desc and len(short_desc.strip()) < 10:
            raise ValidationError(_("Short description should be at least 10 characters long."))
        return short_desc

    def clean_description(self):
        """Validate full description"""
        description = self.cleaned_data.get("description")
        if description and len(description.strip()) < 20:
            raise ValidationError(_("Description should be at least 20 characters long to be meaningful."))
        return description

    def clean_github_url(self):
        """Validate GitHub URL"""
        github_url = self.cleaned_data.get("github_url")
        if github_url:
            if not re.match(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+/?", github_url):
                raise ValidationError(_("Please enter a valid GitHub repository URL."))
        return github_url

    def clean_live_url(self):
        """Validate live URL"""
        live_url = self.cleaned_data.get("live_url")
        if live_url:
            # Basic URL validation beyond Django default
            forbidden_domains = ["localhost", "127.0.0.1", "0.0.0.0"]
            for domain in forbidden_domains:
                if domain in live_url.lower():
                    raise ValidationError(_("Live URL cannot be localhost or development server."))
        return live_url

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        status = cleaned_data.get("status")

        # Date validation
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError(_("Start date cannot be after end date."))
            
            if end_date > timezone.now().date():
                if status == "completed":
                    raise ValidationError(_("Cannot mark project as completed with future end date."))

        # Status-specific validation
        if status == "completed" and not end_date:
            cleaned_data["end_date"] = timezone.now().date()

        # Technology validation
        technologies = cleaned_data.get("technologies")
        if technologies and technologies.count() > 15:
            raise ValidationError(_("Please select no more than 15 technologies."))

        return cleaned_data


class WorkSessionForm(forms.ModelForm):
    """
    Enhanced form for creating and editing work sessions with comprehensive validation.
    """
    class Meta:
        model = WorkSession
        fields = [
            "project", "title", "description",
            "start_time", "end_time", "productivity_rating", "notes"
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "What did you work on?",
                "maxlength": "200"
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "rows": 3,
                "placeholder": "Detailed description of work done"
            }),
            "start_time": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "end_time": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "productivity_rating": forms.Select(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
            }),
            "notes": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "rows": 2,
                "placeholder": "Additional notes or observations"
            }),
        }
        error_messages = {
            "title": {
                "required": _("Session title is required."),
                "max_length": _("Title cannot exceed 200 characters.")
            },
            "project": {
                "required": _("Please select a project for this session.")
            },
            "start_time": {
                "required": _("Start time is required.")
            }
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Limit projects to user"s own projects
        if self.user:
            self.fields["project"].queryset = Project.objects.filter(owner=self.user)

    def clean_title(self):
        """Validate session title"""
        title = self.cleaned_data.get("title")
        if title and len(title.strip()) < 3:
            raise ValidationError(_("Session title should be at least 3 characters long."))
        return title

    def clean_start_time(self):
        """Validate start time"""
        start_time = self.cleaned_data.get("start_time")
        if start_time:
            # Cannot be more than 1 year in the past
            one_year_ago = timezone.now() - timedelta(days=365)
            if start_time < one_year_ago:
                raise ValidationError(_("Start time cannot be more than 1 year in the past."))
            
            # Cannot be in the future (more than 1 hour)
            one_hour_future = timezone.now() + timedelta(hours=1)
            if start_time > one_hour_future:
                raise ValidationError(_("Start time cannot be more than 1 hour in the future."))
                
        return start_time

    def clean_end_time(self):
        """Validate end time"""
        end_time = self.cleaned_data.get("end_time")
        if end_time:
            # Cannot be in the future (more than 5 minutes)
            five_min_future = timezone.now() + timedelta(minutes=5)
            if end_time > five_min_future:
                raise ValidationError(_("End time cannot be in the future."))
        return end_time

    def clean_productivity_rating(self):
        """Validate productivity rating"""
        rating = self.cleaned_data.get("productivity_rating")
        if rating is not None and (rating < 1 or rating > 5):
            raise ValidationError(_("Productivity rating must be between 1 and 5."))
        return rating

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        project = cleaned_data.get("project")

        # Time validation
        if start_time and end_time:
            if start_time >= end_time:
                raise ValidationError(_("End time must be after start time."))
            
            duration = end_time - start_time
            if duration > timedelta(hours=16):
                raise ValidationError(_("Session duration cannot exceed 16 hours."))
            
            if duration < timedelta(minutes=1):
                raise ValidationError(_("Session duration must be at least 1 minute."))

        # Check for overlapping sessions
        if self.user and start_time and end_time:
            overlapping = WorkSession.objects.filter(
                user=self.user,
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            if self.instance and self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise ValidationError(_("This session overlaps with an existing session."))

        return cleaned_data


class ProjectImageForm(forms.ModelForm):
    """
    Enhanced form for uploading project images with validation.
    """
    class Meta:
        model = ProjectImage
        fields = ["title", "description", "image", "order", "is_featured"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "Image title or caption",
                "maxlength": "200"
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "rows": 2,
                "placeholder": "Describe what this image shows"
            }),
            "order": forms.NumberInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "min": 0,
                "max": 999
            }),
            "image": forms.FileInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "accept": "image/*"
            }),
        }
        error_messages = {
            "title": {
                "required": _("Image title is required."),
                "max_length": _("Title cannot exceed 200 characters.")
            },
            "image": {
                "required": _("Please select an image file.")
            }
        }

    def clean_image(self):
        """Validate uploaded image"""
        image = self.cleaned_data.get("image")
        if image:
            # Check file size (max 10MB)
            if image.size > 10 * 1024 * 1024:
                raise ValidationError(_("Image file size cannot exceed 10MB."))
            
            # Check file type
            allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if hasattr(image, "content_type"):
                if image.content_type not in allowed_types:
                    raise ValidationError(_("Only JPEG, PNG, GIF, and WebP images are allowed."))
            
            # Check image dimensions (optional)
            try:
                from PIL import Image as PILImage
                img = PILImage.open(image)
                width, height = img.size
                if width < 100 or height < 100:
                    raise ValidationError(_("Image dimensions must be at least 100x100 pixels."))
                if width > 4000 or height > 4000:
                    raise ValidationError(_("Image dimensions cannot exceed 4000x4000 pixels."))
            except Exception:
                # If PIL fails, just continue - basic validation passed
                pass
                
        return image

    def clean_order(self):
        """Validate display order"""
        order = self.cleaned_data.get("order")
        if order is not None and order < 0:
            raise ValidationError(_("Display order must be 0 or greater."))
        return order

    def clean_title(self):
        """Validate image title"""
        title = self.cleaned_data.get("title")
        if title and len(title.strip()) < 2:
            raise ValidationError(_("Image title should be at least 2 characters long."))
        return title


class UserProfileForm(forms.ModelForm):
    """
    Enhanced form for editing user profile with comprehensive validation.
    """
    class Meta:
        model = UserProfile
        fields = ["bio", "github_url", "linkedin_url", "portfolio_url"]
        widgets = {
            "bio": forms.Textarea(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "rows": 4,
                "placeholder": "Tell us about yourself",
                "maxlength": "1000"
            }),
            "github_url": forms.URLInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "https://github.com/username"
            }),
            "linkedin_url": forms.URLInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "https://linkedin.com/in/username"
            }),
            "portfolio_url": forms.URLInput(attrs={
                "class": "w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none",
                "placeholder": "https://your-portfolio.com"
            }),
        }
        error_messages = {
            "bio": {
                "max_length": _("Bio cannot exceed 1000 characters.")
            }
        }

    def clean_bio(self):
        """Validate biography"""
        bio = self.cleaned_data.get("bio")
        if bio:
            if len(bio.strip()) < 10:
                raise ValidationError(_("Bio should be at least 10 characters long."))
            
            # Check for inappropriate content
            inappropriate_words = ["spam", "fake", "test user"]
            if any(word in bio.lower() for word in inappropriate_words):
                raise ValidationError(_("Please write a genuine bio about yourself."))
        
        return bio

    def clean_github_url(self):
        """Validate GitHub URL"""
        github_url = self.cleaned_data.get("github_url")
        if github_url:
            if not re.match(r"https?://github\.com/[\w\-\.]+/?$", github_url):
                raise ValidationError(_("Please enter a valid GitHub profile URL."))
        return github_url

    def clean_linkedin_url(self):
        """Validate LinkedIn URL"""
        linkedin_url = self.cleaned_data.get("linkedin_url")
        if linkedin_url:
            if not re.match(r"https?://(?:www\.)?linkedin\.com/in/[\w\-\.]+/?$", linkedin_url):
                raise ValidationError(_("Please enter a valid LinkedIn profile URL."))
        return linkedin_url

    def clean_portfolio_url(self):
        """Validate portfolio URL"""
        portfolio_url = self.cleaned_data.get("portfolio_url")
        if portfolio_url:
            # Additional validation for portfolio URLs
            forbidden_domains = ["localhost", "127.0.0.1", "example.com"]
            for domain in forbidden_domains:
                if domain in portfolio_url.lower():
                    raise ValidationError(_("Please enter your actual portfolio URL."))
        return portfolio_url


class TechnologyFilterForm(forms.Form):
    """
    Enhanced form for filtering projects with additional options.
    """
    technology = forms.ModelChoiceField(
        queryset=Technology.objects.all(),
        required=False,
        empty_label=_("All Technologies"),
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    status = forms.ChoiceField(
        choices=[("", _("All Status"))] + [
            ('planning', _('Planning')),
            ('development', _('Development')),
            ('testing', _('Testing')),
            ('completed', _('Completed')),
            ('archived', _('Archived')),
        ],
        required=False,
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    priority = forms.ChoiceField(
        choices=[("", _("All Priorities"))] + [
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
        ],
        required=False,
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    date_range = forms.ChoiceField(
        choices=[
            ("", _("Any Time")),
            ("week", _("Last Week")),
            ("month", _("Last Month")),
            ("quarter", _("Last 3 Months")),
            ("year", _("Last Year"))
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
            "placeholder": _("Search projects...")
        })
    )

    def clean_search(self):
        """Validate search query"""
        search = self.cleaned_data.get("search")
        if search:
            # Minimum search length
            if len(search.strip()) < 2:
                raise ValidationError(_("Search query must be at least 2 characters long."))
            
            # Maximum search length
            if len(search) > 100:
                raise ValidationError(_("Search query cannot exceed 100 characters."))
        
        return search


class BulkProjectActionForm(forms.Form):
    """
    Form for bulk actions on multiple projects.
    """
    ACTION_CHOICES = [
        ("", _("Select Action")),
        ("set_status", _("Change Status")),
        ("set_priority", _("Change Priority")),
        ("set_visibility", _("Change Visibility")),
        ("delete", _("Delete Selected"))
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.none(),
        widget=forms.CheckboxSelectMultiple
    )
    
    # Optional fields for specific actions
    new_status = forms.ChoiceField(
        choices=[
            ('planning', _('Planning')),
            ('development', _('Development')),
            ('testing', _('Testing')),
            ('completed', _('Completed')),
            ('archived', _('Archived')),
        ],
        required=False,
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    new_priority = forms.ChoiceField(
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
        ],
        required=False,
        widget=forms.Select(attrs={
            "class": "px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none"
        })
    )
    
    new_visibility = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "h-4 w-4 text-mauve focus:ring-mauve/20 border-overlay rounded"
        }),
        label=_("Make Public")
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["projects"].queryset = Project.objects.filter(owner=user)

    def clean(self):
        """Validate bulk action requirements"""
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        projects = cleaned_data.get("projects")

        if not action:
            raise ValidationError(_("Please select an action."))

        if not projects:
            raise ValidationError(_("Please select at least one project."))

        if projects and len(projects) > 50:
            raise ValidationError(_("Cannot perform bulk actions on more than 50 projects at once."))

        # Validate action-specific requirements
        if action == "set_status" and not cleaned_data.get("new_status"):
            raise ValidationError(_("Please select a new status."))
        elif action == "set_priority" and not cleaned_data.get("new_priority"):
            raise ValidationError(_("Please select a new priority."))

        return cleaned_data
