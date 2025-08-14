// File: src/core/static/core/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Mobile Menu Logic ---
    const hamburgerMenu = document.getElementById('hamburger-menu');
    const mobileMenu = document.getElementById('mobile-menu');

    if (hamburgerMenu && mobileMenu) {
        hamburgerMenu.addEventListener('click', function(event) {
            event.preventDefault();
            event.stopPropagation();
            
            // Toggle active state
            mobileMenu.classList.toggle('active');
            hamburgerMenu.classList.toggle('active');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (event) => {
            if (!hamburgerMenu.contains(event.target) && !mobileMenu.contains(event.target)) {
                mobileMenu.classList.remove('active');
                hamburgerMenu.classList.remove('active');
            }
        });
        
        // Close menu when clicking on navigation links
        document.querySelectorAll('.mobile-nav-links a').forEach(link => {
            link.addEventListener('click', () => {
                mobileMenu.classList.remove('active');
                hamburgerMenu.classList.remove('active');
            });
        });
        
        // Close menu on window resize to desktop size
        window.addEventListener('resize', () => {
            if (window.innerWidth >= 1024) {
                mobileMenu.classList.remove('active');
                hamburgerMenu.classList.remove('active');
            }
        });
    }

    // Select ALL theme toggle buttons by a class name instead of a single ID.
    const themeToggleButtons = document.querySelectorAll('.theme-toggle-btn');
    const body = document.body;

    // Function to update theme icon based on current theme
    const updateThemeIcon = () => {
        const isLightTheme = body.classList.contains('light-theme');
        const moonParts = document.querySelectorAll('#moon-part');
        const sunParts = document.querySelectorAll('#sun-part');
        
        if (isLightTheme) {
            // Light theme: show moon icon (to switch to dark)
            moonParts.forEach(part => part.style.display = 'block');
            sunParts.forEach(part => part.style.display = 'none');
        } else {
            // Dark theme: show sun icon (to switch to light)
            moonParts.forEach(part => part.style.display = 'none');
            sunParts.forEach(part => part.style.display = 'block');
        }
    };

    // Function to apply the saved theme on page load
    const applySavedTheme = () => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            body.classList.add('light-theme');
        } else {
            body.classList.remove('light-theme');
        }
        updateThemeIcon();
    };

    // Add a click event listener to EACH button found.
    themeToggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            body.classList.toggle('light-theme');
            // Save the new theme preference to localStorage
            if (body.classList.contains('light-theme')) {
                localStorage.setItem('theme', 'light');
            } else {
                localStorage.setItem('theme', 'dark');
            }
            // Update the icon after theme change
            updateThemeIcon();
        });
    });

    // Apply the saved theme when the page is loaded
    applySavedTheme();
});
