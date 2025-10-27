/**
 * Blog Bookmarking System
 * Alpine.js component for managing bookmarked posts using localStorage
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('bookmarkManager', () => ({
        bookmarkedPosts: [],

        init() {
            this.loadBookmarks();
            // Listen for storage changes from other tabs
            window.addEventListener('storage', (e) => {
                if (e.key === 'blog_bookmarks') {
                    this.loadBookmarks();
                }
            });
        },

        loadBookmarks() {
            try {
                const stored = localStorage.getItem('blog_bookmarks');
                this.bookmarkedPosts = stored ? JSON.parse(stored) : [];
            } catch (error) {
                console.warn('Error loading bookmarks:', error);
                this.bookmarkedPosts = [];
            }
        },

        saveBookmarks() {
            try {
                localStorage.setItem('blog_bookmarks', JSON.stringify(this.bookmarkedPosts));
                // Dispatch custom event for other components to listen
                window.dispatchEvent(new CustomEvent('bookmarks-updated', {
                    detail: { bookmarks: this.bookmarkedPosts }
                }));
            } catch (error) {
                console.warn('Error saving bookmarks:', error);
            }
        },

        isBookmarked(postId) {
            return this.bookmarkedPosts.some(post => post.id === postId);
        },

        toggleBookmark(postData) {
            const existingIndex = this.bookmarkedPosts.findIndex(post => post.id === postData.id);

            if (existingIndex >= 0) {
                // Remove bookmark
                this.bookmarkedPosts.splice(existingIndex, 1);
                this.showToast(`Removed "${postData.title}" from bookmarks`, 'removed');
            } else {
                // Add bookmark with timestamp
                const bookmarkData = {
                    ...postData,
                    bookmarkedAt: new Date().toISOString()
                };
                this.bookmarkedPosts.unshift(bookmarkData); // Add to beginning
                this.showToast(`Saved "${postData.title}" for later`, 'added');
            }

            this.saveBookmarks();
        },

        removeBookmark(postId) {
            const index = this.bookmarkedPosts.findIndex(post => post.id === postId);
            if (index >= 0) {
                const post = this.bookmarkedPosts[index];
                this.bookmarkedPosts.splice(index, 1);
                this.saveBookmarks();
                this.showToast(`Removed "${post.title}" from bookmarks`, 'removed');
            }
        },

        clearAllBookmarks() {
            if (this.bookmarkedPosts.length === 0) return;

            if (confirm(`Are you sure you want to remove all ${this.bookmarkedPosts.length} bookmarked posts?`)) {
                this.bookmarkedPosts = [];
                this.saveBookmarks();
                this.showToast('All bookmarks cleared', 'removed');
            }
        },

        getBookmarkCount() {
            return this.bookmarkedPosts.length;
        },

        getBookmarkedPosts() {
            // Return posts sorted by bookmark date (newest first)
            return [...this.bookmarkedPosts].sort((a, b) =>
                new Date(b.bookmarkedAt) - new Date(a.bookmarkedAt)
            );
        },

        formatBookmarkDate(dateString) {
            try {
                const date = new Date(dateString);
                const now = new Date();
                const diffTime = Math.abs(now - date);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                if (diffDays === 1) return 'Yesterday';
                if (diffDays < 7) return `${diffDays} days ago`;
                if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks ago`;

                return date.toLocaleDateString();
            } catch (error) {
                return 'Recently';
            }
        },

        showToast(message, type = 'info') {
            // Create toast notification
            const toast = document.createElement('div');
            toast.className = `bookmark-toast bookmark-toast-${type}`;
            toast.innerHTML = `
                <div class="toast-content">
                    <i class="fas ${type === 'added' ? 'fa-bookmark' : 'fa-bookmark-o'}" aria-hidden="true"></i>
                    <span>${message}</span>
                </div>
            `;

            // Add to page
            document.body.appendChild(toast);

            // Animate in
            requestAnimationFrame(() => {
                toast.classList.add('show');
            });

            // Remove after delay
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }, 3000);
        },

        exportBookmarks() {
            if (this.bookmarkedPosts.length === 0) {
                this.showToast('No bookmarks to export', 'info');
                return;
            }

            const exportData = {
                exportDate: new Date().toISOString(),
                bookmarks: this.bookmarkedPosts,
                count: this.bookmarkedPosts.length
            };

            const dataStr = JSON.stringify(exportData, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);

            const link = document.createElement('a');
            link.href = url;
            link.download = `blog-bookmarks-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            this.showToast(`Exported ${this.bookmarkedPosts.length} bookmarks`, 'added');
        }
    }));

    // Global bookmark data component for individual bookmark buttons
    Alpine.data('bookmarkButton', (postData) => ({
        post: postData,
        isAnimating: false,

        init() {
            // Listen for bookmark updates
            window.addEventListener('bookmarks-updated', () => {
                this.$nextTick(() => {
                    // Force reactivity update
                    this.$el.dispatchEvent(new Event('bookmark-changed'));
                });
            });
        },

        get isBookmarked() {
            const manager = this.getBookmarkManager();
            return manager ? manager.isBookmarked(this.post.id) : false;
        },

        get bookmarkIcon() {
            return this.isBookmarked ? 'fas fa-bookmark' : 'far fa-bookmark';
        },

        get bookmarkText() {
            return this.isBookmarked ? 'Saved' : 'Save for Later';
        },

        getBookmarkManager() {
            // Find the bookmark manager component in the DOM
            const managerEl = document.querySelector('[x-data*="bookmarkManager"]');
            return managerEl ? Alpine.$data(managerEl) : null;
        },

        async toggleBookmark() {
            if (this.isAnimating) return;

            const manager = this.getBookmarkManager();
            if (!manager) {
                console.warn('Bookmark manager not found');
                return;
            }

            this.isAnimating = true;

            // Add animation class
            this.$el.classList.add('bookmark-animating');

            // Toggle bookmark after short delay for animation
            setTimeout(() => {
                manager.toggleBookmark(this.post);
                this.isAnimating = false;
                this.$el.classList.remove('bookmark-animating');
            }, 150);
        }
    }));
});

// Initialize bookmark manager on page load
document.addEventListener('DOMContentLoaded', () => {
    // Add global bookmark manager if not present
    if (!document.querySelector('[x-data*="bookmarkManager"]')) {
        const manager = document.createElement('div');
        manager.setAttribute('x-data', 'bookmarkManager()');
        manager.style.display = 'none';
        document.body.appendChild(manager);
    }
});