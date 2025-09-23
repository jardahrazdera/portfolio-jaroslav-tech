from django import forms
from django.core.exceptions import ValidationError
from .models import Newsletter


class NewsletterSubscriptionForm(forms.ModelForm):
    """Form for newsletter subscription with GDPR compliance."""

    # Add honeypot field for spam protection
    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label="Do not fill this field"
    )

    # Add consent checkbox for GDPR compliance
    consent = forms.BooleanField(
        required=True,
        label="I agree to receive newsletter emails and understand I can unsubscribe at any time.",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Newsletter
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address',
                'autocomplete': 'email',
                'required': True
            })
        }

    def clean_honeypot(self):
        """Check honeypot field for spam protection."""
        honeypot = self.cleaned_data.get('honeypot')
        if honeypot:
            raise ValidationError("Spam detected. Please try again.")
        return honeypot

    def clean_email(self):
        """Validate email and check for existing subscriptions."""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()

            # Check if email already exists
            existing = Newsletter.objects.filter(email=email).first()
            if existing:
                if existing.is_active:
                    raise ValidationError(
                        "This email is already subscribed to our newsletter."
                    )
                elif existing.is_confirmed and not existing.is_active:
                    # User previously unsubscribed but confirmed
                    raise ValidationError(
                        "This email was previously subscribed. "
                        "Please contact us if you want to resubscribe."
                    )
                else:
                    # User exists but never confirmed - we can resend confirmation
                    self.existing_subscription = existing

        return email

    def save(self, commit=True, request=None):
        """Save the subscription with metadata."""
        # Check if we have an existing unconfirmed subscription
        if hasattr(self, 'existing_subscription'):
            newsletter = self.existing_subscription
            # Regenerate tokens for security
            newsletter.regenerate_tokens()
        else:
            newsletter = super().save(commit=False)

        # Add metadata if request is provided
        if request:
            # Get IP address (considering proxy headers)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                newsletter.ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                newsletter.ip_address = request.META.get('REMOTE_ADDR')

            # Get user agent
            newsletter.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        # Set source based on referrer or default
        if request and request.META.get('HTTP_REFERER'):
            if 'blog' in request.META.get('HTTP_REFERER', ''):
                newsletter.source = 'blog'
            elif 'post' in request.META.get('HTTP_REFERER', ''):
                newsletter.source = 'post'
            else:
                newsletter.source = 'website'
        else:
            newsletter.source = 'direct'

        if commit:
            newsletter.save()

        return newsletter


class NewsletterUnsubscribeForm(forms.Form):
    """Simple form for newsletter unsubscription confirmation."""

    confirm = forms.BooleanField(
        required=True,
        label="Yes, I want to unsubscribe from the newsletter",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    reason = forms.ChoiceField(
        required=False,
        label="Optional: Why are you unsubscribing?",
        choices=[
            ('', 'Select a reason (optional)'),
            ('too_frequent', 'Emails are too frequent'),
            ('not_relevant', 'Content is not relevant to me'),
            ('never_signed_up', 'I never signed up for this'),
            ('temporary', 'Taking a temporary break'),
            ('other', 'Other reason'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    feedback = forms.CharField(
        required=False,
        label="Additional feedback (optional)",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Help us improve by sharing your feedback...'
        })
    )


class NewsletterContactForm(forms.Form):
    """Contact form for newsletter-related inquiries."""

    name = forms.CharField(
        max_length=100,
        label="Your Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )

    email = forms.EmailField(
        label="Your Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )

    subject = forms.ChoiceField(
        label="Subject",
        choices=[
            ('subscription', 'Subscription Issue'),
            ('unsubscribe', 'Unsubscribe Problem'),
            ('content', 'Content Feedback'),
            ('technical', 'Technical Issue'),
            ('other', 'Other Inquiry'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Describe your inquiry or issue...'
        })
    )

    # Honeypot for spam protection
    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label="Do not fill this field"
    )

    def clean_honeypot(self):
        """Check honeypot field for spam protection."""
        honeypot = self.cleaned_data.get('honeypot')
        if honeypot:
            raise ValidationError("Spam detected. Please try again.")
        return honeypot