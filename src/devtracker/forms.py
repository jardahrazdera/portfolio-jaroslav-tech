from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3
from .models import Project, TimeLog, Task, ProjectStatus


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


class TaskForm(forms.ModelForm):
    """Form for creating and editing tasks."""
    
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'is_completed']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Task title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Task details (optional)'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProjectStatusForm(forms.ModelForm):
    """Form for adding project status updates."""
    
    class Meta:
        model = ProjectStatus
        fields = ['status', 'date', 'note']
        widgets = {
            'status': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., MVP Released, Beta Testing'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes about this milestone'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set today as default date
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['date'].initial = timezone.now().date()


class RegistrationForm(UserCreationForm):
    """Custom user registration form with reCAPTCHA protection."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        })
    )
    captcha = ReCaptchaField(
        widget=ReCaptchaV3(
            attrs={'data-theme': 'dark'}  # Match our theme
        ),
        error_messages={
            'required': 'Please complete the reCAPTCHA verification.',
            'invalid': 'reCAPTCHA verification failed. Please try again.',
        }
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'captcha')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add classes to password fields
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def clean_captcha(self):
        """Custom validation for reCAPTCHA field with better error messages."""
        from django.conf import settings
        
        # Check if reCAPTCHA keys are configured
        if not getattr(settings, 'RECAPTCHA_PUBLIC_KEY', None) or not getattr(settings, 'RECAPTCHA_PRIVATE_KEY', None):
            raise forms.ValidationError(
                'reCAPTCHA is not properly configured on this server. '
                'Please contact the administrator.'
            )
        
        captcha = self.cleaned_data.get('captcha')
        if not captcha:
            raise forms.ValidationError('Please complete the reCAPTCHA verification.')
        
        return captcha
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user