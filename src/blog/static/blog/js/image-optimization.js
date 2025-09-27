/**
 * Advanced Image Optimization and Lazy Loading
 * Provides WebP detection, intersection observer lazy loading,
 * progressive image enhancement, and preload optimization
 */

class ImageOptimizer {
    constructor() {
        this.supportsWebP = false;
        this.supportsIntersectionObserver = 'IntersectionObserver' in window;
        this.imageObserver = null;
        this.preloadedImages = new Set();
        this.performanceMetrics = {
            totalImages: 0,
            lazyLoaded: 0,
            webpServed: 0,
            loadTimes: []
        };

        this.init();
    }

    async init() {
        // Check WebP support
        this.supportsWebP = await this.detectWebPSupport();

        // Initialize lazy loading
        this.initializeLazyLoading();

        // Preload critical images
        this.preloadCriticalImages();

        // Set up performance monitoring
        this.setupPerformanceMonitoring();

        console.log('ImageOptimizer initialized', {
            webpSupport: this.supportsWebP,
            intersectionObserver: this.supportsIntersectionObserver
        });
    }

    /**
     * Detect WebP support using a data URI test
     */
    detectWebPSupport() {
        return new Promise((resolve) => {
            const webpTestImage = 'data:image/webp;base64,UklGRiIAAABXRUJQVlA4IBYAAAAwAQCdASoBAAEADsD+JaQAA3AAAAAA';
            const img = new Image();

            img.onload = img.onerror = () => {
                resolve(img.height === 1);
            };

            img.src = webpTestImage;
        });
    }

    /**
     * Initialize Intersection Observer for lazy loading
     */
    initializeLazyLoading() {
        if (!this.supportsIntersectionObserver) {
            // Fallback: load all images immediately
            this.loadAllImagesImmediately();
            return;
        }

        const observerConfig = {
            root: null,
            rootMargin: '50px 0px', // Start loading 50px before entering viewport
            threshold: 0.01
        };

        this.imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadImage(entry.target);
                    this.imageObserver.unobserve(entry.target);
                }
            });
        }, observerConfig);

        // Observe all lazy-loadable images
        this.observeImages();
    }

    /**
     * Find and observe all images that should be lazy loaded
     */
    observeImages() {
        // Query for images with data-src (lazy loading candidates)
        const lazyImages = document.querySelectorAll('img[data-src], picture[data-loaded="false"]');

        lazyImages.forEach(element => {
            this.imageObserver.observe(element);
            this.performanceMetrics.totalImages++;
        });

        // Also observe images in picture elements
        const pictureElements = document.querySelectorAll('picture');
        pictureElements.forEach(picture => {
            const img = picture.querySelector('img[data-src]');
            if (img && !img.src) {
                this.imageObserver.observe(picture);
            }
        });
    }

    /**
     * Load an individual image with format optimization
     */
    loadImage(element) {
        const startTime = performance.now();

        if (element.tagName === 'PICTURE') {
            this.loadPictureElement(element, startTime);
        } else if (element.tagName === 'IMG') {
            this.loadImgElement(element, startTime);
        }
    }

    /**
     * Load a picture element with WebP support detection
     */
    loadPictureElement(picture, startTime) {
        const img = picture.querySelector('img');
        const sources = picture.querySelectorAll('source');

        // Choose the best source based on WebP support
        let selectedSource = null;

        if (this.supportsWebP) {
            selectedSource = Array.from(sources).find(source =>
                source.type === 'image/webp'
            );
        }

        if (!selectedSource) {
            selectedSource = Array.from(sources).find(source =>
                source.type === 'image/jpeg' || !source.type
            );
        }

        if (selectedSource && selectedSource.dataset.srcset) {
            selectedSource.srcset = selectedSource.dataset.srcset;
            selectedSource.removeAttribute('data-srcset');
        }

        if (img && img.dataset.src) {
            img.onload = () => this.onImageLoad(img, startTime);
            img.onerror = () => this.onImageError(img);

            img.src = img.dataset.src;
            img.removeAttribute('data-src');

            // Add loading class for CSS transitions
            img.classList.add('loading');
        }

        picture.dataset.loaded = 'true';
    }

    /**
     * Load a regular img element with format optimization
     */
    loadImgElement(img, startTime) {
        const dataSrc = img.dataset.src;
        const dataSrcset = img.dataset.srcset;

        if (!dataSrc) return;

        // If WebP is supported and we have WebP alternatives, use them
        let finalSrc = dataSrc;
        let finalSrcset = dataSrcset;

        if (this.supportsWebP) {
            const webpSrc = img.dataset.webpSrc;
            const webpSrcset = img.dataset.webpSrcset;

            if (webpSrc) finalSrc = webpSrc;
            if (webpSrcset) finalSrcset = webpSrcset;
        }

        img.onload = () => this.onImageLoad(img, startTime);
        img.onerror = () => this.onImageError(img);

        // Set srcset first, then src
        if (finalSrcset) {
            img.srcset = finalSrcset;
            img.removeAttribute('data-srcset');
            img.removeAttribute('data-webp-srcset');
        }

        img.src = finalSrc;
        img.removeAttribute('data-src');
        img.removeAttribute('data-webp-src');

        // Add loading class for CSS transitions
        img.classList.add('loading');
    }

    /**
     * Handle successful image load
     */
    onImageLoad(img, startTime) {
        const loadTime = performance.now() - startTime;

        // Update performance metrics
        this.performanceMetrics.lazyLoaded++;
        this.performanceMetrics.loadTimes.push(loadTime);

        if (img.src.includes('.webp')) {
            this.performanceMetrics.webpServed++;
        }

        // Remove loading class and add loaded class for CSS transitions
        img.classList.remove('loading');
        img.classList.add('loaded');

        // Dispatch custom event for tracking
        img.dispatchEvent(new CustomEvent('imageLoaded', {
            detail: { loadTime, webp: img.src.includes('.webp') }
        }));
    }

    /**
     * Handle image load error with fallback
     */
    onImageError(img) {
        console.warn('Image failed to load:', img.src);

        // Try fallback to JPEG if WebP failed
        if (img.src.includes('.webp') && img.dataset.src) {
            img.src = img.dataset.src;
            return;
        }

        // Set error state
        img.classList.add('error');
        img.alt = img.alt || 'Image failed to load';
    }

    /**
     * Preload critical images that are above the fold
     */
    preloadCriticalImages() {
        // Find images marked as critical (hero images, featured images)
        const criticalImages = document.querySelectorAll('[data-critical="true"]');

        criticalImages.forEach(element => {
            if (element.tagName === 'PICTURE') {
                this.preloadPictureElement(element);
            } else if (element.tagName === 'IMG') {
                this.preloadImgElement(element);
            }
        });

        // Preload hero/featured images automatically
        const heroImages = document.querySelectorAll('.hero-image, .featured-image, [class*="hero"]');
        heroImages.forEach(img => {
            if (this.isInViewport(img) || this.isAboveFold(img)) {
                this.preloadImgElement(img);
            }
        });
    }

    /**
     * Preload a picture element
     */
    preloadPictureElement(picture) {
        const img = picture.querySelector('img');
        if (img && img.dataset.src) {
            this.preloadImgElement(img);
        }
    }

    /**
     * Preload an individual image
     */
    preloadImgElement(img) {
        if (this.preloadedImages.has(img.dataset.src || img.src)) {
            return;
        }

        const preloadSrc = this.supportsWebP && img.dataset.webpSrc
            ? img.dataset.webpSrc
            : img.dataset.src || img.src;

        if (preloadSrc) {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.as = 'image';
            link.href = preloadSrc;
            link.type = preloadSrc.includes('.webp') ? 'image/webp' : 'image/jpeg';

            document.head.appendChild(link);
            this.preloadedImages.add(preloadSrc);
        }
    }

    /**
     * Check if element is currently in viewport
     */
    isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    /**
     * Check if element is above the fold (top 800px)
     */
    isAboveFold(element) {
        const rect = element.getBoundingClientRect();
        return rect.top < 800;
    }

    /**
     * Fallback for browsers without Intersection Observer
     */
    loadAllImagesImmediately() {
        const lazyImages = document.querySelectorAll('img[data-src], picture[data-loaded="false"]');

        lazyImages.forEach(element => {
            this.loadImage(element);
        });
    }

    /**
     * Setup performance monitoring and reporting
     */
    setupPerformanceMonitoring() {
        // Report metrics after page load
        window.addEventListener('load', () => {
            setTimeout(() => {
                this.reportPerformanceMetrics();
            }, 2000);
        });

        // Report metrics before page unload
        window.addEventListener('beforeunload', () => {
            this.reportPerformanceMetrics();
        });
    }

    /**
     * Report performance metrics (can be sent to analytics)
     */
    reportPerformanceMetrics() {
        const metrics = {
            ...this.performanceMetrics,
            averageLoadTime: this.performanceMetrics.loadTimes.length
                ? this.performanceMetrics.loadTimes.reduce((a, b) => a + b, 0) / this.performanceMetrics.loadTimes.length
                : 0,
            webpUsagePercent: this.performanceMetrics.totalImages
                ? (this.performanceMetrics.webpServed / this.performanceMetrics.totalImages) * 100
                : 0
        };

        console.log('Image Optimization Metrics:', metrics);

        // Dispatch event for analytics tracking
        window.dispatchEvent(new CustomEvent('imageOptimizationMetrics', {
            detail: metrics
        }));
    }

    /**
     * Manually trigger lazy loading for dynamically added images
     */
    observeNewImages(container = document) {
        if (!this.imageObserver) return;

        const newImages = container.querySelectorAll('img[data-src]:not([data-observed]), picture[data-loaded="false"]:not([data-observed])');

        newImages.forEach(element => {
            element.dataset.observed = 'true';
            this.imageObserver.observe(element);
            this.performanceMetrics.totalImages++;
        });
    }

    /**
     * Get current performance metrics
     */
    getMetrics() {
        return {
            ...this.performanceMetrics,
            averageLoadTime: this.performanceMetrics.loadTimes.length
                ? this.performanceMetrics.loadTimes.reduce((a, b) => a + b, 0) / this.performanceMetrics.loadTimes.length
                : 0
        };
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.imageOptimizer = new ImageOptimizer();
    });
} else {
    window.imageOptimizer = new ImageOptimizer();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ImageOptimizer;
}