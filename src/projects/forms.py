from django import forms
from django.contrib.auth.models import User
from .models import Project, Technology, WorkSession, ProjectImage, UserProfile


class ProjectForm(forms.ModelForm):
    """
    Form for creating and editing projects.
    """
    technologies = forms.ModelMultipleChoiceField(
        queryset=Technology.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Project
        fields = [
            'title', 'short_description', 'description',
            'technologies', 'status', 'priority',
            'start_date', 'end_date',
            'github_url', 'live_url',
            'is_featured', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'placeholder': 'Enter project title'
            }),
            'short_description': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'placeholder': 'Brief description for listings'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'rows': 5,
                'placeholder': 'Detailed project description'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none'
            }),
            'github_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'placeholder': 'https://github.com/username/repo'
            }),
            'live_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'placeholder': 'https://your-project.com'
            }),
        }


class WorkSessionForm(forms.ModelForm):
    """
    Form for creating work sessions.
    """
    class Meta:
        model = WorkSession
        fields = [
            'project', 'title', 'description',
            'start_time', 'end_time', 'productivity_rating', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'placeholder': 'What did you work on?'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'rows': 3,
                'placeholder': 'Detailed description of work done'
            }),
            'start_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none'
            }),
            'productivity_rating': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'rows': 2,
                'placeholder': 'Additional notes or observations'
            }),
        }


class ProjectImageForm(forms.ModelForm):
    """
    Form for uploading project images.
    """
    class Meta:
        model = ProjectImage
        fields = ['title', 'description', 'image', 'order', 'is_featured']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'placeholder': 'Image title or caption'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'rows': 2,
                'placeholder': 'Describe what this image shows'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'min': 0
            }),
            'image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'accept': 'image/*'
            }),
        }


class UserProfileForm(forms.ModelForm):
    """
    Form for editing user profile.
    """
    class Meta:
        model = UserProfile
        fields = ['bio', 'github_url', 'linkedin_url', 'portfolio_url']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'rows': 4,
                'placeholder': 'Tell us about yourself'
            }),
            'github_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'placeholder': 'https://github.com/username'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'placeholder': 'https://linkedin.com/in/username'
            }),
            'portfolio_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
                'placeholder': 'https://your-portfolio.com'
            }),
        }


class TechnologyFilterForm(forms.Form):
    """
    Form for filtering projects by technology and status.
    """
    technology = forms.ModelChoiceField(
        queryset=Technology.objects.all(),
        required=False,
        empty_label="All Technologies",
        widget=forms.Select(attrs={
            'class': 'px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Project.status.field.choices,
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'px-4 py-2 border border-overlay rounded-lg bg-mantle text-text focus:border-mauve focus:ring-2 focus:ring-mauve/20 outline-none',
            'placeholder': 'Search projects...'
        })
    )
