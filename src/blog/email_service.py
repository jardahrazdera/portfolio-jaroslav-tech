from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


class NewsletterEmailService:
    """Service class for handling newsletter-related emails."""

    @staticmethod
    def send_confirmation_email(newsletter, request=None):
        """
        Send double opt-in confirmation email to subscriber.

        Args:
            newsletter: Newsletter instance
            request: HTTP request object for building absolute URLs

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get confirmation URL
            confirmation_url = newsletter.get_confirmation_url(request)

            # Prepare context for email template
            context = {
                'newsletter': newsletter,
                'confirmation_url': confirmation_url,
                'site_name': getattr(settings, 'SITE_NAME', 'Jaroslav.tech'),
                'site_url': getattr(settings, 'SITE_URL', 'https://jaroslav.tech'),
            }

            # Render email templates
            html_message = render_to_string('blog/emails/confirmation.html', context)
            plain_message = render_to_string('blog/emails/confirmation.txt', context)

            # Send email
            success = send_mail(
                subject=f'Confirm your newsletter subscription - {context["site_name"]}',
                message=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@jaroslav.tech'),
                recipient_list=[newsletter.email],
                html_message=html_message,
                fail_silently=False
            )

            if success:
                logger.info(f"Confirmation email sent successfully to {newsletter.email}")
                return True
            else:
                logger.error(f"Failed to send confirmation email to {newsletter.email}")
                return False

        except Exception as e:
            logger.error(f"Error sending confirmation email to {newsletter.email}: {str(e)}")
            return False

    @staticmethod
    def send_welcome_email(newsletter, request=None):
        """
        Send welcome email after successful confirmation.

        Args:
            newsletter: Newsletter instance
            request: HTTP request object for building absolute URLs

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get unsubscribe URL
            unsubscribe_url = newsletter.get_unsubscribe_url(request)

            # Prepare context for email template
            context = {
                'newsletter': newsletter,
                'unsubscribe_url': unsubscribe_url,
                'site_name': getattr(settings, 'SITE_NAME', 'Jaroslav.tech'),
                'site_url': getattr(settings, 'SITE_URL', 'https://jaroslav.tech'),
                'blog_url': f"{context.get('site_url', 'https://jaroslav.tech')}/en/blog/",
            }

            # Render email templates
            html_message = render_to_string('blog/emails/welcome.html', context)
            plain_message = render_to_string('blog/emails/welcome.txt', context)

            # Send email
            success = send_mail(
                subject=f'Welcome to {context["site_name"]} Newsletter!',
                message=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@jaroslav.tech'),
                recipient_list=[newsletter.email],
                html_message=html_message,
                fail_silently=False
            )

            if success:
                logger.info(f"Welcome email sent successfully to {newsletter.email}")
                return True
            else:
                logger.error(f"Failed to send welcome email to {newsletter.email}")
                return False

        except Exception as e:
            logger.error(f"Error sending welcome email to {newsletter.email}: {str(e)}")
            return False

    @staticmethod
    def send_unsubscribe_confirmation(newsletter, feedback=None, request=None):
        """
        Send unsubscribe confirmation email.

        Args:
            newsletter: Newsletter instance
            feedback: Optional feedback from user
            request: HTTP request object for building absolute URLs

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Prepare context for email template
            context = {
                'newsletter': newsletter,
                'feedback': feedback,
                'site_name': getattr(settings, 'SITE_NAME', 'Jaroslav.tech'),
                'site_url': getattr(settings, 'SITE_URL', 'https://jaroslav.tech'),
                'resubscribe_url': f"{context.get('site_url', 'https://jaroslav.tech')}/en/blog/newsletter/subscribe/",
            }

            # Render email templates
            html_message = render_to_string('blog/emails/unsubscribe_confirmation.html', context)
            plain_message = render_to_string('blog/emails/unsubscribe_confirmation.txt', context)

            # Send email
            success = send_mail(
                subject=f'Unsubscribed from {context["site_name"]} Newsletter',
                message=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@jaroslav.tech'),
                recipient_list=[newsletter.email],
                html_message=html_message,
                fail_silently=False
            )

            if success:
                logger.info(f"Unsubscribe confirmation email sent successfully to {newsletter.email}")
                return True
            else:
                logger.error(f"Failed to send unsubscribe confirmation email to {newsletter.email}")
                return False

        except Exception as e:
            logger.error(f"Error sending unsubscribe confirmation email to {newsletter.email}: {str(e)}")
            return False

    @staticmethod
    def test_email_configuration():
        """
        Test email configuration by sending a test email.

        Returns:
            dict: Result of the test including success status and message
        """
        try:
            test_email = getattr(settings, 'ADMIN_EMAIL', 'admin@jaroslav.tech')

            success = send_mail(
                subject='Newsletter Email Configuration Test',
                message='This is a test email to verify newsletter email configuration.',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@jaroslav.tech'),
                recipient_list=[test_email],
                fail_silently=False
            )

            if success:
                return {
                    'success': True,
                    'message': f'Test email sent successfully to {test_email}'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to send test email'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Email configuration test failed: {str(e)}'
            }