"""
File attachment utilities for blog posts.
Handles file validation, security, and display.
"""
import os
import mimetypes
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify
from django.conf import settings


# Allowed file types with their MIME types and extensions
ALLOWED_FILE_TYPES = {
    # Documents
    'pdf': {
        'mime_types': ['application/pdf'],
        'extensions': ['.pdf'],
        'icon': 'file-pdf',
        'description': 'PDF Document'
    },
    'doc': {
        'mime_types': [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ],
        'extensions': ['.doc', '.docx'],
        'icon': 'file-text',
        'description': 'Word Document'
    },
    'xls': {
        'mime_types': [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ],
        'extensions': ['.xls', '.xlsx'],
        'icon': 'file-spreadsheet',
        'description': 'Excel Spreadsheet'
    },
    'ppt': {
        'mime_types': [
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ],
        'extensions': ['.ppt', '.pptx'],
        'icon': 'file-presentation',
        'description': 'PowerPoint Presentation'
    },
    'txt': {
        'mime_types': ['text/plain'],
        'extensions': ['.txt'],
        'icon': 'file-text',
        'description': 'Text File'
    },
    'rtf': {
        'mime_types': ['application/rtf'],
        'extensions': ['.rtf'],
        'icon': 'file-text',
        'description': 'Rich Text Format'
    },
    # Archives
    'zip': {
        'mime_types': ['application/zip'],
        'extensions': ['.zip'],
        'icon': 'file-archive',
        'description': 'ZIP Archive'
    },
    'rar': {
        'mime_types': ['application/vnd.rar'],
        'extensions': ['.rar'],
        'icon': 'file-archive',
        'description': 'RAR Archive'
    },
    'tar': {
        'mime_types': ['application/x-tar'],
        'extensions': ['.tar', '.tar.gz', '.tgz'],
        'icon': 'file-archive',
        'description': 'TAR Archive'
    },
    # Code files
    'code': {
        'mime_types': [
            'text/plain',
            'application/javascript',
            'text/html',
            'text/css',
            'application/json'
        ],
        'extensions': ['.py', '.js', '.html', '.css', '.json', '.xml', '.sql', '.md'],
        'icon': 'file-code',
        'description': 'Code File'
    }
}

# File size limits (in bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES_PER_POST = 10


@deconstructible
class FileValidator:
    """Validator for uploaded blog files."""

    def __init__(self, max_size=MAX_FILE_SIZE):
        self.max_size = max_size

    def __call__(self, file):
        # Check file size
        if file.size > self.max_size:
            raise ValidationError(
                f'File size must be under {self.max_size // (1024*1024)}MB. '
                f'Current file size: {file.size // (1024*1024)}MB.'
            )

        # Check file extension
        file_ext = os.path.splitext(file.name)[1].lower()
        allowed_extensions = []
        for file_type in ALLOWED_FILE_TYPES.values():
            allowed_extensions.extend(file_type['extensions'])

        if file_ext not in allowed_extensions:
            raise ValidationError(
                f'File type "{file_ext}" is not allowed. '
                f'Allowed types: {", ".join(allowed_extensions)}'
            )

        # Check MIME type
        mime_type, _ = mimetypes.guess_type(file.name)
        allowed_mimes = []
        for file_type in ALLOWED_FILE_TYPES.values():
            allowed_mimes.extend(file_type['mime_types'])

        if mime_type and mime_type not in allowed_mimes:
            raise ValidationError(
                f'MIME type "{mime_type}" is not allowed.'
            )


def get_file_type(filename):
    """
    Get file type information based on filename.

    Args:
        filename: Name of the file

    Returns:
        dict: File type information with icon, description, etc.
    """
    file_ext = os.path.splitext(filename)[1].lower()

    for file_type, info in ALLOWED_FILE_TYPES.items():
        if file_ext in info['extensions']:
            return {
                'type': file_type,
                'icon': info['icon'],
                'description': info['description'],
                'extension': file_ext
            }

    # Default for unknown types
    return {
        'type': 'unknown',
        'icon': 'file',
        'description': 'File',
        'extension': file_ext
    }


def generate_file_path(instance, filename):
    """
    Generate upload path for blog files.

    Args:
        instance: BlogFile model instance
        filename: Original filename

    Returns:
        str: Upload path
    """
    # Get file extension
    file_ext = os.path.splitext(filename)[1].lower()

    # Create safe filename
    base_name = os.path.splitext(filename)[0]
    safe_name = slugify(base_name)
    safe_filename = f"{safe_name}{file_ext}"

    # Create path: blog/files/post_id/filename
    return f'blog/files/post_{instance.post.pk}/{safe_filename}'


def format_file_size(size_bytes):
    """
    Format file size in human readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))

    if i >= len(size_names):
        i = len(size_names) - 1

    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return f"{s} {size_names[i]}"


def is_safe_filename(filename):
    """
    Check if filename is safe for storage.

    Args:
        filename: Filename to check

    Returns:
        bool: True if safe, False otherwise
    """
    # Check for dangerous characters
    dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']

    for char in dangerous_chars:
        if char in filename:
            return False

    # Check length
    if len(filename) > 255:
        return False

    # Check for empty name
    if not filename.strip():
        return False

    return True


def get_file_icon_class(filename):
    """
    Get CSS icon class for file type.

    Args:
        filename: Name of the file

    Returns:
        str: CSS class for icon
    """
    file_info = get_file_type(filename)
    icon_map = {
        'file-pdf': 'fa-file-pdf',
        'file-text': 'fa-file-alt',
        'file-spreadsheet': 'fa-file-excel',
        'file-presentation': 'fa-file-powerpoint',
        'file-archive': 'fa-file-archive',
        'file-code': 'fa-file-code',
        'file': 'fa-file'
    }

    return icon_map.get(file_info['icon'], 'fa-file')