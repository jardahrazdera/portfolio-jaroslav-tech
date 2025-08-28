/**
 * Dynamic Styles Handler for DevTracker
 * Replaces inline styles with data attributes and JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle progress bars
    const progressBars = document.querySelectorAll('[data-progress]');
    progressBars.forEach(bar => {
        const percentage = bar.dataset.progress;
        bar.style.width = percentage + '%';
    });

    // Handle tag colors
    const tags = document.querySelectorAll('[data-tag-color]');
    tags.forEach(tag => {
        const color = tag.dataset.tagColor;
        tag.style.backgroundColor = color + '20';
        tag.style.color = color;
    });
});