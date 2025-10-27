"""
Syntax highlighting utilities for blog content.
Uses Pygments for code highlighting with Catppuccin themes.
"""
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer, ClassNotFound
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound as PygmentsClassNotFound
import re
from django.utils.safestring import mark_safe


class CatppuccinFormatter(HtmlFormatter):
    """Custom Pygments formatter with Catppuccin color scheme."""

    def __init__(self, **options):
        # Set default options for Catppuccin theme
        options.setdefault('style', 'monokai')  # Base style, we'll override colors
        options.setdefault('cssclass', 'highlight')
        options.setdefault('linenos', False)
        options.setdefault('linenostart', 1)
        options.setdefault('hl_lines', [])
        super().__init__(**options)


def highlight_code(code, language=None, line_numbers=False):
    """
    Highlight code using Pygments with Catppuccin theme.

    Args:
        code: Code string to highlight
        language: Programming language name (python, javascript, etc.)
        line_numbers: Whether to include line numbers

    Returns:
        str: HTML string with syntax highlighting
    """
    if not code.strip():
        return ''

    try:
        if language:
            # Try to get lexer by specified language
            lexer = get_lexer_by_name(language, stripall=True)
        else:
            # Try to guess the language
            lexer = guess_lexer(code)
    except (ClassNotFound, PygmentsClassNotFound):
        # Fallback to plain text
        lexer = get_lexer_by_name('text', stripall=True)

    # Create formatter with options
    formatter = CatppuccinFormatter(
        linenos=line_numbers,
        cssclass='code-block',
        wrapcode=True
    )

    # Generate highlighted HTML
    highlighted = highlight(code, lexer, formatter)

    # Wrap in container with language info and copy button
    language_name = getattr(lexer, 'name', 'Code')
    container_html = f'''
    <div class="code-container" data-language="{language or 'text'}">
        <div class="code-header">
            <span class="language-label">{language_name}</span>
            <button class="copy-button" type="button" aria-label="Copy code to clipboard">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="m5 15-5-5v-6a2 2 0 0 1 2-2h6l5 5"></path>
                </svg>
                Copy
            </button>
        </div>
        {highlighted}
    </div>
    '''

    return mark_safe(container_html)


def process_code_blocks(content):
    """
    Process HTML content to find and highlight code blocks.

    Looks for:
    - <pre><code class="language-python">...</code></pre>
    - <code class="language-python">...</code> (inline)

    Args:
        content: HTML content string

    Returns:
        str: Processed HTML with syntax highlighting
    """
    if not content:
        return content

    # Pattern for code blocks with language specification
    code_block_pattern = r'<pre><code(?:\s+class="language-([^"]*)")?>(.*?)</code></pre>'
    inline_code_pattern = r'<code(?:\s+class="language-([^"]*)")?>(.*?)</code>'

    def replace_code_block(match):
        language = match.group(1)
        code = match.group(2)

        # Decode HTML entities
        import html
        code = html.unescape(code)

        # Remove extra whitespace but preserve structure
        code = code.strip()

        return highlight_code(code, language, line_numbers=True)

    def replace_inline_code(match):
        language = match.group(1)
        code = match.group(2)

        # For inline code, don't add line numbers or container
        if language and len(code.strip()) > 50:  # Multi-line inline code
            return highlight_code(code, language, line_numbers=False)
        else:
            # Keep simple inline code as-is but with basic styling
            return f'<code class="inline-code">{code}</code>'

    # Process code blocks first
    content = re.sub(code_block_pattern, replace_code_block, content, flags=re.DOTALL)

    # Process remaining inline code (not already processed)
    content = re.sub(inline_code_pattern, replace_inline_code, content, flags=re.DOTALL)

    return mark_safe(content)


# Language aliases for common names
LANGUAGE_ALIASES = {
    'js': 'javascript',
    'ts': 'typescript',
    'py': 'python',
    'rb': 'ruby',
    'sh': 'bash',
    'shell': 'bash',
    'yml': 'yaml',
    'jsx': 'javascript',
    'tsx': 'typescript',
    'vue': 'html',
    'svelte': 'html',
}


def normalize_language(language):
    """Normalize language name to standard Pygments lexer name."""
    if not language:
        return None

    language = language.lower().strip()
    return LANGUAGE_ALIASES.get(language, language)


def get_supported_languages():
    """Get list of commonly supported programming languages."""
    return [
        'python', 'javascript', 'typescript', 'html', 'css', 'scss', 'sass',
        'json', 'xml', 'yaml', 'markdown', 'bash', 'shell', 'sql',
        'java', 'c', 'cpp', 'csharp', 'php', 'ruby', 'go', 'rust',
        'swift', 'kotlin', 'dart', 'r', 'matlab', 'latex', 'dockerfile',
        'nginx', 'apache', 'ini', 'toml', 'makefile', 'cmake'
    ]