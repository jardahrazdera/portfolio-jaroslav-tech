// File: src/core/static/core/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // --- Mobile Menu Logic ---
    const hamburgerMenu = document.getElementById('hamburger-menu');
    const navLinks = document.querySelector('.nav-links');

    if (hamburgerMenu) {
        hamburgerMenu.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', () => {
            if (navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
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
});
