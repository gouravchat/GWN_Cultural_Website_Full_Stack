document.addEventListener('DOMContentLoaded', function () {
    // --- Element Selectors ---
    const authForm = document.getElementById('authForm');
    const formTitle = document.getElementById('formTitle');
    const submitButton = document.getElementById('submitButton');
    const messageElement = document.getElementById('message');
    
    const toggleAuthModeLink = document.getElementById('toggleAuthMode');
    const toggleText = document.getElementById('toggleText');

    // Input fields
    const identifierInput = document.getElementById('identifier');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const phoneNumberInput = document.getElementById('phone_number');
    const passwordInput = document.getElementById('password');

    // Field containers
    const loginFields = document.querySelectorAll('.login-field');
    const registerFields = document.querySelectorAll('.register-field'); // Fixed typo: 'a=' removed

    // --- State ---
    let isLoginMode = true;

    // --- Determine Base URL for API Calls ---
    // If the browser's current URL is https://your-domain.com/auth/, then
    // window.location.pathname will be /auth/
    // We want the API calls to go to /auth/login or /auth/register
    const authApiBaseUrl = window.location.pathname.startsWith('/auth') ? '/auth' : '';

    /**
     * Toggles the form between Login and Register modes.
     */
    function toggleMode() {
        isLoginMode = !isLoginMode;
        
        if (isLoginMode) {
            // Setup for Login mode
            formTitle.textContent = 'Login';
            submitButton.textContent = 'Login';
            toggleText.textContent = "Don't have an account?";
            toggleAuthModeLink.textContent = 'Register here';
            
            loginFields.forEach(field => field.style.display = 'block');
            registerFields.forEach(field => field.style.display = 'none');
            
            // Set required attributes for login
            identifierInput.required = true;
            usernameInput.required = false;
            emailInput.required = false;
            phoneNumberInput.required = false;

        } else {
            // Setup for Register mode
            formTitle.textContent = 'Register';
            submitButton.textContent = 'Register';
            toggleText.textContent = 'Already have an account?';
            toggleAuthModeLink.textContent = 'Login here';
            
            loginFields.forEach(field => field.style.display = 'none');
            registerFields.forEach(field => {
                field.style.display = 'block';
            });
            
            // Set required attributes for registration
            identifierInput.required = false;
            usernameInput.required = true;
            emailInput.required = true;
            phoneNumberInput.required = true;
        }
        
        // Clear previous messages and reset form state
        messageElement.textContent = '';
        messageElement.className = 'message';
        authForm.reset();
    }

    /**
     * Handles the form submission for both login and registration.
     * @param {Event} e The form submission event.
     */
    async function handleFormSubmit(e) {
        e.preventDefault();
        messageElement.textContent = '';
        messageElement.className = 'message';
        submitButton.disabled = true;
        submitButton.textContent = isLoginMode ? 'Logging in...' : 'Registering...';

        let payload = {};
        let endpoint = isLoginMode ? '/login' : '/register';

        // Prepend the base URL for API calls
        const fullEndpoint = authApiBaseUrl + endpoint;

        if (isLoginMode) {
            payload = {
                identifier: identifierInput.value.trim(),
                password: passwordInput.value
            };
        } else {
            payload = {
                username: usernameInput.value.trim(),
                email: emailInput.value.trim(),
                phone_number: phoneNumberInput.value.trim(),
                password: passwordInput.value
            };
        }

        try {
            const response = await fetch(fullEndpoint, { // Use fullEndpoint here
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();

            if (response.ok) {
                messageElement.textContent = data.message;
                messageElement.className = 'message success';
                if (data.redirect_url) {
                    messageElement.textContent += ' Redirecting...';
                    setTimeout(() => { window.location.href = data.redirect_url; }, 1000);
                }
            } else {
                messageElement.textContent = 'Error: ' + (data.error || 'An unknown error occurred.');
                messageElement.className = 'message error';
                submitButton.disabled = false;
                submitButton.textContent = isLoginMode ? 'Login' : 'Register';
            }
        } catch (error) {
            console.error('Authentication error:', error);
            messageElement.textContent = 'A network error occurred. Please try again.';
            messageElement.className = 'message error';
            submitButton.disabled = false;
            submitButton.textContent = isLoginMode ? 'Login' : 'Register';
        }
    }

    // --- Event Listeners ---
    toggleAuthModeLink.addEventListener('click', function (e) {
        e.preventDefault();
        toggleMode();
    });

    authForm.addEventListener('submit', handleFormSubmit);

    // --- Initial Setup ---
    // Set the initial state to login
    loginFields.forEach(field => field.style.display = 'block');
    registerFields.forEach(field => field.style.display = 'none');
    identifierInput.required = true;
});
