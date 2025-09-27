/**
 * Reading Analytics for Blog Posts
 * Privacy-friendly analytics that tracks reading engagement without storing personal data.
 * Version: 2025-09-26-v2
 */
(function() {
    // Don't run analytics in Django admin
    if (window.location.pathname.includes('/admin/')) {
        return;
    }

    // Reading analytics for blog posts
    let startTime = Date.now();
    let maxScrollPercent = 0;
    let readingCompleted = false;

    // Get post slug from URL
    const pathParts = window.location.pathname.split('/').filter(p => p);

    // Find 'post' in the path and get the slug after it
    // Expected format: /en/blog/post/slug/ or /blog/post/slug/
    let postSlug = null;
    const postIndex = pathParts.indexOf('post');
    if (postIndex >= 0 && postIndex < pathParts.length - 1) {
        postSlug = pathParts[postIndex + 1];
    }

    if (!postSlug) {
        console.debug('PostView Analytics: Could not extract post slug from', window.location.pathname);
        return;
    }


    // Track scroll progress
    function updateScrollProgress() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrollPercent = Math.round((scrollTop / docHeight) * 100);

        maxScrollPercent = Math.max(maxScrollPercent, scrollPercent);

        // Consider reading completed if user scrolled past 80%
        if (scrollPercent > 80) {
            readingCompleted = true;
        }
    }

    // Get CSRF token from page
    function getCSRFToken() {
        // Try to get CSRF token from meta tag
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            return csrfMeta.getAttribute('content');
        }

        // Try to get from cookie
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        return cookieValue || null;
    }

    // Send reading data to server
    function sendReadingData() {
        const readingTime = Math.round((Date.now() - startTime) / 1000);

        // Only send if user spent at least 10 seconds reading
        if (readingTime < 10) return;

        const currentLang = window.location.pathname.split('/')[1] || 'en';
        const trackingUrl = `/${currentLang}/blog/api/track-reading/`;
        const trackingData = {
            post_slug: postSlug,
            reading_time_seconds: readingTime,
            max_scroll_percent: maxScrollPercent,
            completed_reading: readingCompleted
        };

        // Prepare headers
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        };

        // Add CSRF token if available
        const csrfToken = getCSRFToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        fetch(trackingUrl, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(trackingData),
            credentials: 'same-origin' // Include cookies
        }).then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        }).catch(err => {
            console.error('PostView Analytics: Failed to track reading data:', err);
        });
    }

    // Throttled scroll handler
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(updateScrollProgress, 100);
    });

    // Send data on page unload using sendBeacon (more reliable)
    window.addEventListener('beforeunload', function() {
        const readingTime = Math.round((Date.now() - startTime) / 1000);

        // Only send if user spent at least 10 seconds reading
        if (readingTime < 10) return;

        const currentLang = window.location.pathname.split('/')[1] || 'en';
        const trackingUrl = `/${currentLang}/blog/api/track-reading/`;
        const trackingData = {
            post_slug: postSlug,
            reading_time_seconds: readingTime,
            max_scroll_percent: maxScrollPercent,
            completed_reading: readingCompleted
        };

        // Use sendBeacon for beforeunload (more reliable than fetch)
        if (navigator.sendBeacon) {
            const formData = new FormData();
            formData.append('data', JSON.stringify(trackingData));
            navigator.sendBeacon(trackingUrl, formData);
        } else {
            // Fallback to synchronous XMLHttpRequest
            try {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', trackingUrl, false); // synchronous
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.send(JSON.stringify(trackingData));
            } catch (e) {
                console.debug('PostView Analytics: Fallback request failed:', e);
            }
        }
    });

    // Also send data periodically for long reading sessions
    setInterval(sendReadingData, 60000); // Every minute
})();