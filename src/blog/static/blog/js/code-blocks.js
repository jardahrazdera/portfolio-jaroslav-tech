/**
 * Code block functionality for blog posts
 * Handles copy-to-clipboard functionality with accessibility support
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeCodeBlocks();
});

function initializeCodeBlocks() {
    const codeContainers = document.querySelectorAll('.code-container');

    codeContainers.forEach(container => {
        const copyButton = container.querySelector('.copy-button');
        const codeBlock = container.querySelector('.code-block pre, .code-block code, .code-block');

        if (copyButton && codeBlock) {
            copyButton.addEventListener('click', () => copyCodeToClipboard(copyButton, codeBlock));

            // Add keyboard support for copy button
            copyButton.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    copyCodeToClipboard(copyButton, codeBlock);
                }
            });
        }
    });
}

async function copyCodeToClipboard(button, codeElement) {
    try {
        // Get the text content, preserving line breaks
        const codeText = getCodeText(codeElement);

        // Use the modern Clipboard API if available
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(codeText);
        } else {
            // Fallback for older browsers
            fallbackCopyToClipboard(codeText);
        }

        // Update button state to show success
        showCopySuccess(button);

        // Announce to screen readers
        announceToScreenReader('Code copied to clipboard');

    } catch (error) {
        console.error('Failed to copy code:', error);

        // Show error state
        showCopyError(button);

        // Announce error to screen readers
        announceToScreenReader('Failed to copy code to clipboard');
    }
}

function getCodeText(codeElement) {
    // Create a clone to avoid modifying the original
    const clone = codeElement.cloneNode(true);

    // Remove any line number elements if present
    const lineNumbers = clone.querySelectorAll('.linenos, .linenodiv');
    lineNumbers.forEach(el => el.remove());

    // Get the text content, which preserves line breaks
    let text = clone.textContent || clone.innerText;

    // Clean up any extra whitespace at the beginning/end
    text = text.trim();

    return text;
}

function fallbackCopyToClipboard(text) {
    // Create a temporary textarea element
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-999999px';
    textarea.style.top = '-999999px';
    document.body.appendChild(textarea);

    // Select and copy the text
    textarea.focus();
    textarea.select();

    try {
        document.execCommand('copy');
    } finally {
        document.body.removeChild(textarea);
    }
}

function showCopySuccess(button) {
    const originalText = button.innerHTML;
    const originalClass = button.className;

    // Update button appearance
    button.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20,6 9,17 4,12"></polyline>
        </svg>
        Copied!
    `;
    button.classList.add('copied');

    // Reset after 2 seconds
    setTimeout(() => {
        button.innerHTML = originalText;
        button.className = originalClass;
    }, 2000);
}

function showCopyError(button) {
    const originalText = button.innerHTML;

    // Update button to show error
    button.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        Error
    `;

    // Reset after 2 seconds
    setTimeout(() => {
        button.innerHTML = originalText;
    }, 2000);
}

function announceToScreenReader(message) {
    // Create a live region for screen reader announcements
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.style.position = 'absolute';
    announcement.style.left = '-10000px';
    announcement.style.width = '1px';
    announcement.style.height = '1px';
    announcement.style.overflow = 'hidden';

    document.body.appendChild(announcement);

    // Set the message
    announcement.textContent = message;

    // Remove after announcement
    setTimeout(() => {
        document.body.removeChild(announcement);
    }, 1000);
}

// Export for potential use in other scripts
window.codeBlocks = {
    initialize: initializeCodeBlocks,
    copyCode: copyCodeToClipboard
};