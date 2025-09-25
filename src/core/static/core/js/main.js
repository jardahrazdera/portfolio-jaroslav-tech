// File: src/core/static/core/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Mobile Menu Logic ---
    const hamburgerMenu = document.getElementById('hamburger-menu');
    const navLinks = document.querySelector('.nav-links');

    if (hamburgerMenu) {
        hamburgerMenu.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            
            // Hide/show CV Download button when menu is open
            const cvActions = document.querySelector('.cv-actions');
            if (cvActions) {
                if (navLinks.classList.contains('active')) {
                    cvActions.style.display = 'none';
                } else {
                    cvActions.style.display = '';
                }
            }
        });
    }

    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', () => {
            if (navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                
                // Show CV Download button again when menu closes
                const cvActions = document.querySelector('.cv-actions');
                if (cvActions) {
                    cvActions.style.display = '';
                }
            }
        });
    });

    // Select ALL theme toggle buttons by a class name instead of a single ID.
    const themeToggleButtons = document.querySelectorAll('.theme-toggle-btn');
    const body = document.body;

    // Function to apply the saved theme on page load
    const applySavedTheme = () => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            body.classList.add('light-theme');
        } else {
            body.classList.remove('light-theme');
        }
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
        });
    });

    // Apply the saved theme when the page is loaded
    applySavedTheme();

    // --- Back to Top Button Logic with Progress Ring ---
    const backToTopButton = document.getElementById('back-to-top');
    const progressRing = document.querySelector('.progress-ring-circle');
    const scrollPercentage = document.getElementById('scroll-percentage');
    
    if (backToTopButton) {
        // Show button immediately
        backToTopButton.style.display = 'flex';
        
        if (progressRing) {
            // Calculate progress ring circumference (2 * π * radius)
            const radius = 25; // r="25" from SVG
            const circumference = 2 * Math.PI * radius;
            
            // Set initial stroke-dasharray and stroke-dashoffset
            progressRing.style.strokeDasharray = `${circumference} ${circumference}`;
            progressRing.style.strokeDashoffset = circumference;
        }
        
        // Update progress based on scroll position
        window.addEventListener('scroll', function() {
            const scrolled = window.pageYOffset;
            
            if (progressRing) {
                // Update progress ring
                const maxHeight = document.documentElement.scrollHeight - window.innerHeight;
                const scrollProgress = Math.max(0, Math.min(1, scrolled / maxHeight));
                const circumference = 2 * Math.PI * 25;
                const offset = circumference - (scrollProgress * circumference);
                progressRing.style.strokeDashoffset = offset;

                // Update percentage text
                if (scrollPercentage) {
                    const percentage = Math.round(scrollProgress * 100);
                    scrollPercentage.innerText = `${percentage}%`;
                }
            }
        });
    }

    // --- Smooth Scrolling for Navigation Links ---
    // Get the current page path
    const currentPath = window.location.pathname;
    const homePaths = ['/', '/en/', '/cs/']; // All possible home page paths
    
    // Check if we're on the home page
    const isHomePage = homePaths.includes(currentPath);
    
    // Handle navigation link clicks for smooth scrolling
    document.querySelectorAll('.nav-links a[href*="#"]').forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            const hashIndex = href.indexOf('#');
            
            if (hashIndex !== -1) {
                const hash = href.substring(hashIndex);
                
                // If we're on the home page, prevent default and scroll smoothly
                if (isHomePage && hash !== '#') {
                    const targetElement = document.querySelector(hash);
                    if (targetElement) {
                        e.preventDefault();
                        targetElement.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                        
                        // Update URL hash without jumping
                        history.pushState(null, null, hash);
                        
                        // Close mobile menu if open
                        if (navLinks.classList.contains('active')) {
                            navLinks.classList.remove('active');
                        }
                    }
                }
                // If we're not on home page, let the default behavior happen
                // (navigate to home page with hash)
            }
        });
    });
    
    // Handle hash on page load (when coming from another page)
    if (window.location.hash && isHomePage) {
        setTimeout(() => {
            const targetElement = document.querySelector(window.location.hash);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }, 100); // Small delay to ensure page is fully loaded
    }
    
    // --- Smooth Scroll to Top for Logo Click ---
    document.querySelectorAll('.logo').forEach(logo => {
        logo.addEventListener('click', function(e) {
            // Only apply smooth scroll if we're on the home page
            if (isHomePage) {
                const href = this.getAttribute('href');
                // Check if the link points to the home page (no hash fragment)
                if (href && (href === '/' || href === '/en/' || href === '/cs/' || href.endsWith('/'))) {
                    e.preventDefault();
                    
                    // Smooth scroll to top
                    window.scrollTo({
                        top: 0,
                        behavior: 'smooth'
                    });
                    
                    // Update URL to remove any hash
                    history.pushState(null, null, href);
                    
                    // Close mobile menu if open
                    if (navLinks.classList.contains('active')) {
                        navLinks.classList.remove('active');
                    }
                }
            }
            // If we're not on home page, let the default behavior happen
            // (navigate to home page)
        });
    });
});
