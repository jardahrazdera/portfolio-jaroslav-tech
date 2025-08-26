from django import forms
from .models import Project, TimeLog


class ProjectForm(forms.ModelForm):
    """Form for creating and editing projects."""
    
    class Meta:
        model = Project
        fields = ['name', 'description', 'status', 'start_date', 'end_date', 'is_public', 'github_url', 'live_url', 'tags', 'technologies']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'github_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://github.com/username/repo'}),
            'live_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://yoursite.com'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'technologies': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }


class TimeLogForm(forms.ModelForm):
    """Form for logging time to projects."""
    
    class Meta:
        model = TimeLog
        fields = ['date', 'hours', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25', 'min': '0.25', 'max': '24'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief description of work performed'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set today as default date
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['date'].initial = timezone.now().date()