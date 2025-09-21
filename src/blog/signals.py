"""
Blog app signal handlers for file cleanup and other automated tasks.
"""
import os
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from .models import BlogFile, Post


@receiver(pre_delete, sender=BlogFile)
def delete_file_on_blogfile_delete(sender, instance, **kwargs):
    """
    Delete the physical file when a BlogFile instance is deleted.

    This signal handler ensures that when a BlogFile is deleted from the database,
    the corresponding file is also removed from the filesystem to prevent
    orphaned files from accumulating.
    """
    if instance.file:
        # Check if file exists before attempting to delete
        if os.path.isfile(instance.file.path):
            try:
                os.remove(instance.file.path)
            except OSError:
                # File might be in use or permission denied
                # Log the error but don't raise exception to prevent
                # database deletion from failing
                pass


@receiver(post_delete, sender=BlogFile)
def cleanup_empty_directories(sender, instance, **kwargs):
    """
    Clean up empty directories after file deletion.

    When files are deleted, this removes empty parent directories
    to keep the media folder organized.
    """
    if instance.file:
        try:
            # Get the directory containing the file
            file_dir = os.path.dirname(instance.file.path)

            # Only remove if directory is empty and it's within our blog files structure
            if 'blog/files' in file_dir and os.path.exists(file_dir):
                # Check if directory is empty
                if not os.listdir(file_dir):
                    os.rmdir(file_dir)

                    # Also check parent directory (post_X folder)
                    parent_dir = os.path.dirname(file_dir)
                    if 'blog/files' in parent_dir and os.path.exists(parent_dir):
                        if not os.listdir(parent_dir):
                            os.rmdir(parent_dir)
        except OSError:
            # Directory might not be empty or permission denied
            # Fail silently to avoid breaking the deletion process
            pass


@receiver(pre_delete, sender=Post)
def cleanup_post_files_on_delete(sender, instance, **kwargs):
    """
    Clean up all associated files when a Post is deleted.

    This ensures that when a blog post is deleted, all its file attachments
    are also removed from the filesystem.
    """
    # Get all file attachments for this post
    attachments = instance.attachments.all()

    for attachment in attachments:
        if attachment.file and os.path.isfile(attachment.file.path):
            try:
                os.remove(attachment.file.path)
            except OSError:
                # File might be in use or permission denied
                pass

    # Clean up the post's file directory
    if attachments.exists():
        try:
            # Construct the expected directory path
            post_dir = os.path.join(
                os.path.dirname(attachments.first().file.path),
                f'post_{instance.pk}'
            )

            if os.path.exists(post_dir):
                # Remove any remaining files in the directory
                for filename in os.listdir(post_dir):
                    file_path = os.path.join(post_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

                # Remove the directory if it's empty
                if not os.listdir(post_dir):
                    os.rmdir(post_dir)
        except OSError:
            pass