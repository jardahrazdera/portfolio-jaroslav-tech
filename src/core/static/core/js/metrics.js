// File: src/core/static/core/js/metrics.js
// Alpine.js component for live server metrics

document.addEventListener('alpine:init', () => {
    Alpine.data('serverMetrics', () => ({
        cpu: 0,
        ram: 0,
        load: 0,
        isOnline: true,
        isLoading: true,
        pollInterval: null,

        init() {
            // Fetch immediately on load
            this.fetchMetrics();

            // Set up polling every 5 seconds
            this.pollInterval = setInterval(() => {
                this.fetchMetrics();
            }, 5000);
        },

        async fetchMetrics() {
            try {
                const response = await fetch('/api/server-stats/');

                if (!response.ok) {
                    throw new Error('API request failed');
                }

                const data = await response.json();

                // Update metrics with smooth transition
                this.cpu = data.cpu || 0;
                this.ram = data.ram || 0;
                this.load = data.load || 0;
                this.isOnline = true;
                this.isLoading = false;
            } catch (error) {
                console.error('Failed to fetch server metrics:', error);
                this.isOnline = false;
                this.isLoading = false;
            }
        },

        // Calculate stroke-dashoffset for circular progress
        getCircleProgress(percentage) {
            const radius = 36; // Matches the SVG circle radius
            const circumference = 2 * Math.PI * radius;
            const progress = Math.min(100, Math.max(0, percentage)); // Clamp between 0-100
            return circumference - (progress / 100) * circumference;
        },

        // Format network throughput
        formatNetwork(mbps) {
            if (mbps < 0.01) {
                return '0 MB/s';
            } else if (mbps < 1) {
                return `${(mbps * 1024).toFixed(0)} KB/s`;
            } else {
                return `${mbps.toFixed(2)} MB/s`;
            }
        },

        // Cleanup on component destroy
        destroy() {
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
            }
        }
    }));
});