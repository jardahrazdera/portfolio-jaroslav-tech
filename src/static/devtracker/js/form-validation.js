/**
 * DevTracker Form Validation
 * Client-side form validation for better user experience
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize validation for all forms
    const forms = document.querySelectorAll('form[data-validate="true"]');
    forms.forEach(form => {
        initializeFormValidation(form);
    });
});

function initializeFormValidation(form) {
    const inputs = form.querySelectorAll('input, textarea, select');
    
    inputs.forEach(input => {
        // Add real-time validation
        input.addEventListener('blur', () => validateField(input));
        input.addEventListener('input', () => clearFieldError(input));
    });
    
    // Validate on form submit
    form.addEventListener('submit', (e) => {
        if (!validateForm(form)) {
            e.preventDefault();
        }
    });
}

function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input, textarea, select');
    
    inputs.forEach(input => {
        if (!validateField(input)) {
            isValid = false;
        }
    });
    
    return isValid;
}

function validateField(input) {
    const value = input.value.trim();
    let isValid = true;
    let errorMessage = '';
    
    // Required field validation
    if (input.hasAttribute('required') && !value) {
        errorMessage = 'This field is required.';
        isValid = false;
    }
    
    // Email validation
    else if (input.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            errorMessage = 'Please enter a valid email address.';
            isValid = false;
        }
    }
    
    // URL validation
    else if (input.type === 'url' && value) {
        try {
            new URL(value);
        } catch (e) {
            errorMessage = 'Please enter a valid URL.';
            isValid = false;
        }
    }
    
    // Number validation (for hours field)
    else if (input.type === 'number' && value) {
        const num = parseFloat(value);
        const min = parseFloat(input.getAttribute('min'));
        const max = parseFloat(input.getAttribute('max'));
        
        if (isNaN(num)) {
            errorMessage = 'Please enter a valid number.';
            isValid = false;
        } else if (min !== null && num < min) {
            errorMessage = `Value must be at least ${min}.`;
            isValid = false;
        } else if (max !== null && num > max) {
            errorMessage = `Value must be no more than ${max}.`;
            isValid = false;
        }
    }
    
    // Text length validation
    else if ((input.type === 'text' || input.tagName === 'TEXTAREA') && value) {
        const maxLength = input.getAttribute('maxlength');
        if (maxLength && value.length > parseInt(maxLength)) {
            errorMessage = `Maximum ${maxLength} characters allowed.`;
            isValid = false;
        }
    }
    
    // Password confirmation validation
    if (input.name === 'password2') {
        const password1 = form.querySelector('[name="password1"]');
        if (password1 && value !== password1.value) {
            errorMessage = 'Passwords do not match.';
            isValid = false;
        }
    }
    
    // Display validation result
    if (isValid) {
        showFieldSuccess(input);
    } else {
        showFieldError(input, errorMessage);
    }
    
    return isValid;
}

function showFieldError(input, message) {
    clearFieldError(input);
    
    input.classList.add('field-error');
    
    const errorElement = document.createElement('div');
    errorElement.className = 'field-error-message';
    errorElement.textContent = message;
    
    input.parentNode.appendChild(errorElement);
}

function showFieldSuccess(input) {
    clearFieldError(input);
    input.classList.add('field-success');
}

function clearFieldError(input) {
    input.classList.remove('field-error', 'field-success');
    
    const existingError = input.parentNode.querySelector('.field-error-message');
    if (existingError) {
        existingError.remove();
    }
}

// Password strength indicator
function addPasswordStrengthIndicator(passwordInput) {
    const strengthIndicator = document.createElement('div');
    strengthIndicator.className = 'password-strength';
    strengthIndicator.innerHTML = `
        <div class="strength-bar">
            <div class="strength-fill"></div>
        </div>
        <span class="strength-text">Password strength: <span class="strength-level">Weak</span></span>
    `;
    
    passwordInput.parentNode.appendChild(strengthIndicator);
    
    passwordInput.addEventListener('input', () => {
        updatePasswordStrength(passwordInput, strengthIndicator);
    });
}

function updatePasswordStrength(input, indicator) {
    const password = input.value;
    let score = 0;
    
    // Length check
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    
    // Character variety checks
    if (/[a-z]/.test(password)) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^a-zA-Z0-9]/.test(password)) score += 1;
    
    const strengthFill = indicator.querySelector('.strength-fill');
    const strengthLevel = indicator.querySelector('.strength-level');
    
    const levels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
    const colors = ['#f38ba8', '#fab387', '#f9e2af', '#a6e3a1', '#94e2d5', '#89b4fa'];
    
    const level = Math.min(score, 5);
    strengthFill.style.width = `${(level / 5) * 100}%`;
    strengthFill.style.backgroundColor = colors[level];
    strengthLevel.textContent = levels[level];
}

// Initialize password strength indicators
document.addEventListener('DOMContentLoaded', function() {
    const passwordInputs = document.querySelectorAll('input[type="password"][name*="password1"]');
    passwordInputs.forEach(input => {
        addPasswordStrengthIndicator(input);
    });
});