document.addEventListener('DOMContentLoaded', function () {
    // --- Element Selectors ---
    const authForm = document.getElementById('authForm');
    const formTitle = document.getElementById('formTitle');
    const submitButton = document.getElementById('submitButton');
    const messageElement = document.getElementById('message');
    
    const toggleAuthModeLink = document.getElementById('toggleAuthMode');
    const toggleText = document.getElementById('toggleText');

    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
    const forgotPasswordContainer = document.getElementById('forgotPasswordContainer');
    const forgotPasswordForm = document.getElementById('forgotPasswordForm');
    const forgotEmailInput = document.getElementById('forgotEmail');
    const sendOtpButton = document.getElementById('sendOtpButton');
    const forgotMessageElement = document.getElementById('forgotMessage');
    const backToLoginLink = document.getElementById('backToLoginLink');
    const resetPasswordButton = document.getElementById('resetPasswordButton'); // Although hidden, good to have it selected

    // Input fields (existing)
    const identifierInput = document.getElementById('identifier');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const phoneNumberInput = document.getElementById('phone_number');
    const passwordInput = document.getElementById('password');

    // Field containers (existing)
    const loginFields = document.querySelectorAll('.login-field');
    const registerFields = document.querySelectorAll('.register-field');

    // --- State ---
    let isLoginMode = true; // True for Login/Register form, False for Forgot Password form

    // --- Determine Base URL for API Calls ---
    const authApiBaseUrl = window.location.pathname.startsWith('/auth') ? '/auth' : '';

    /**
     * Toggles the form between Login and Register modes.
     */
    function toggleMode() {
        isLoginMode = !isLoginMode;
        
        // Hide forgot password container
        forgotPasswordContainer.classList.remove('active');
        document.querySelector('.login-container').style.display = 'block'; // Show login/register container

        if (isLoginMode) {
            // Setup for Login mode
            formTitle.textContent = 'NACS User/Admin Login';
            submitButton.textContent = 'NACS User/Admin Login';
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
        forgotMessageElement.textContent = ''; // Clear forgot password message too
        forgotMessageElement.className = 'message';
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
                submitButton.textContent = isLoginMode ? 'NACS User/Admin Login' : 'Register';
            }
        } catch (error) {
            console.error('Authentication error:', error);
            messageElement.textContent = 'A network error occurred. Please try again.';
            messageElement.className = 'message error';
            submitButton.disabled = false;
            submitButton.textContent = isLoginMode ? 'NACS User/Admin Login' : 'Register';
        }
    }

    /**
     * Handles sending password details via email.
     * @param {Event} e The button click event.
     */
    async function handleSendDetails(e) {
        e.preventDefault();
        forgotMessageElement.textContent = '';
        forgotMessageElement.className = 'message';
        sendOtpButton.disabled = true;
        sendOtpButton.textContent = 'Sending...';

        const email = forgotEmailInput.value.trim();
        if (!email) {
            forgotMessageElement.textContent = 'Please enter your email address.';
            forgotMessageElement.className = 'message error';
            sendOtpButton.disabled = false;
            sendOtpButton.textContent = 'Send Details';
            return;
        }

        try {
            const response = await fetch(authApiBaseUrl + '/forgot_password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            });
            const data = await response.json();

            if (response.ok) {
                forgotMessageElement.textContent = data.message;
                forgotMessageElement.className = 'message success';
            } else {
                forgotMessageElement.textContent = 'Error: ' + (data.error || 'An unknown error occurred.');
                forgotMessageElement.className = 'message error';
            }
        } catch (error) {
            console.error('Forgot password error:', error);
            forgotMessageElement.textContent = 'A network error occurred. Please try again.';
            forgotMessageElement.className = 'message error';
        } finally {
            sendOtpButton.disabled = false;
            sendOtpButton.textContent = 'Send Details';
        }
    }

    // --- Event Listeners ---
    toggleAuthModeLink.addEventListener('click', function (e) {
        e.preventDefault();
        toggleMode();
    });

    forgotPasswordLink.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector('.login-container').style.display = 'none'; // Hide login/register form
        forgotPasswordContainer.classList.add('active'); // Show forgot password form
        forgotEmailInput.value = ''; // Clear previous email
        forgotMessageElement.textContent = ''; // Clear any previous messages
        forgotMessageElement.className = 'message';
    });

    backToLoginLink.addEventListener('click', function (e) {
        e.preventDefault();
        forgotPasswordContainer.classList.remove('active'); // Hide forgot password form
        document.querySelector('.login-container').style.display = 'block'; // Show login/register form
        authForm.reset(); // Clear login/register form
        messageElement.textContent = ''; // Clear any messages
        messageElement.className = 'message';
        isLoginMode = true; // Ensure we are in login mode
        formTitle.textContent = 'NACS User/Admin Login';
        submitButton.textContent = 'NACS User/Admin Login';
        toggleText.textContent = "Don't have an account?";
        toggleAuthModeLink.textContent = 'Register here';
        loginFields.forEach(field => field.style.display = 'block');
        registerFields.forEach(field => field.style.display = 'none');
        identifierInput.required = true;
    });

    sendOtpButton.addEventListener('click', handleSendDetails);

    authForm.addEventListener('submit', handleFormSubmit);

    // Initial Setup
    // Set the initial state to login
    loginFields.forEach(field => field.style.display = 'block');
    registerFields.forEach(field => field.style.display = 'none');
    identifierInput.required = true;
});