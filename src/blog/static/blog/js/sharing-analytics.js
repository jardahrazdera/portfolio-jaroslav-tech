/**
 * Social Sharing Analytics Tracking
 * Tracks sharing button clicks and updates analytics via AJAX
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeSharingAnalytics();
});

function initializeSharingAnalytics() {
    const sharingButtons = document.querySelectorAll('.sharing-button[data-platform]');

    sharingButtons.forEach(button => {
        button.addEventListener('click', function() {
            const platform = this.dataset.platform;
            const postId = this.dataset.postId;

            // Track the share asynchronously (don't block the navigation)
            if (platform && postId) {
                trackShare(platform, postId);
            }

            // Let the user navigate to the sharing platform
            // (the click will still open the sharing URL)
        });
    });
}

async function trackShare(platform, postId) {
    try {
        const response = await fetch('/blog/api/track-share/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                platform: platform,
                post_id: parseInt(postId)
            })
        });

        if (response.ok) {
            const data = await response.json();

            // Update the UI with new share counts
            updateShareCounts(platform, data.count, data.total);

            // Optional: Show a brief success indicator
            showShareSuccess(platform);
        } else {
            console.warn('Failed to track share:', response.status);
        }
    } catch (error) {
        console.warn('Error tracking share:', error);
        // Fail silently - don't interrupt the user's sharing experience
    }
}

function updateShareCounts(platform, count, total) {
    // Update platform-specific share count
    const platformStats = document.querySelector(`[data-platform="${platform}"] .sharing-stats`);
    if (platformStats) {
        if (count > 0) {
            platformStats.innerHTML = `
                <span class="share-count">${count}</span>
                <span class="share-label">share${count !== 1 ? 's' : ''}</span>
            `;
        }
    }

    // Update total share count
    const totalElement = document.querySelector('.sharing-total');
    if (totalElement && total > 0) {
        totalElement.innerHTML = `
            <i class="fas fa-heart" aria-hidden="true"></i>
            <span>This post has been shared <strong>${total}</strong> time${total !== 1 ? 's' : ''}</span>
        `;
    }
}

function showShareSuccess(platform) {
    // Find the sharing button for this platform
    const button = document.querySelector(`[data-platform="${platform}"]`);
    if (!button) return;

    // Create a temporary success indicator
    const successIndicator = document.createElement('div');
    successIndicator.className = 'share-success-indicator';
    successIndicator.innerHTML = '<i class="fas fa-check"></i> Shared!';
    successIndicator.style.cssText = `
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--green);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-size: 0.9rem;
        font-weight: 600;
        z-index: 10;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

    // Position relative to button
    button.style.position = 'relative';
    button.appendChild(successIndicator);

    // Animate in
    requestAnimationFrame(() => {
        successIndicator.style.opacity = '1';
    });

    // Remove after delay
    setTimeout(() => {
        successIndicator.style.opacity = '0';
        setTimeout(() => {
            if (successIndicator.parentNode) {
                successIndicator.parentNode.removeChild(successIndicator);
            }
        }, 300);
    }, 1500);
}

// Optional: Track sharing analytics for reporting
function getShareAnalytics() {
    const sharingSection = document.querySelector('.social-sharing-section');
    if (!sharingSection) return null;

    const totalShares = document.querySelector('.sharing-total strong');
    const platformCounts = {};

    document.querySelectorAll('.sharing-stats .share-count').forEach((countEl) => {
        const button = countEl.closest('.sharing-button');
        if (button) {
            const platform = button.dataset.platform;
            const count = parseInt(countEl.textContent) || 0;
            platformCounts[platform] = count;
        }
    });

    return {
        total: totalShares ? parseInt(totalShares.textContent) : 0,
        platforms: platformCounts
    };
}

// Export for potential use by other scripts
window.SharingAnalytics = {
    trackShare,
    updateShareCounts,
    showShareSuccess,
    getShareAnalytics
};