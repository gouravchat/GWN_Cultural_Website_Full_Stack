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
    const otpInput = document.getElementById('otp');

    // Field containers
    const loginFields = document.querySelectorAll('.login-field');
    const registerFields = document.querySelectorAll('.register-field');

    // OTP related elements
    const sendOtpButton = document.getElementById('sendOtpButton');
    const otpGroup = document.getElementById('otp-group');

    // --- State ---
    let isLoginMode = true;

    // --- Functions ---

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
            otpInput.required = false;

        } else {
            // Setup for Register mode
            formTitle.textContent = 'Register';
            submitButton.textContent = 'Register';
            toggleText.textContent = 'Already have an account?';
            toggleAuthModeLink.textContent = 'Login here';
            
            loginFields.forEach(field => field.style.display = 'none');
            registerFields.forEach(field => {
                // Show all register fields except the OTP group initially
                if (field.id !== 'otp-group') {
                    field.style.display = 'block';
                }
            });
            sendOtpButton.style.display = 'block'; // Show Send OTP button
            otpGroup.style.display = 'none'; // Hide OTP field initially
            
            // Set required attributes for registration
            identifierInput.required = false;
            usernameInput.required = true;
            emailInput.required = true;
            phoneNumberInput.required = true;
            otpInput.required = true; // Will be validated on submit
        }
        
        // Clear previous messages and reset form state
        messageElement.textContent = '';
        messageElement.className = 'message';
        authForm.reset();
    }

    /**
     * Handles the click event for the 'Send OTP' button.
     */
    async function handleSendOtp() {
        const phoneNumber = phoneNumberInput.value.trim();
        if (!phoneNumber) {
            messageElement.textContent = 'Please enter a phone number to receive an OTP.';
            messageElement.className = 'message error';
            return;
        }

        sendOtpButton.disabled = true;
        sendOtpButton.textContent = 'Sending...';
        messageElement.textContent = '';
        messageElement.className = 'message';

        try {
            const response = await fetch('/send-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_number: phoneNumber })
            });
            const data = await response.json();
            
            if (response.ok) {
                messageElement.textContent = data.message;
                messageElement.className = 'message success';
                otpGroup.style.display = 'block'; // Show the OTP input field
            } else {
                messageElement.textContent = 'Error: ' + data.error;
                messageElement.className = 'message error';
            }
        } catch (error) {
            console.error('Error sending OTP:', error);
            messageElement.textContent = 'An network error occurred while sending OTP.';
            messageElement.className = 'message error';
        } finally {
            sendOtpButton.disabled = false;
            sendOtpButton.textContent = 'Send OTP';
        }
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
                password: passwordInput.value,
                otp: otpInput.value.trim()
            };
        }

        try {
            const response = await fetch(endpoint, {
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

    sendOtpButton.addEventListener('click', handleSendOtp);
    authForm.addEventListener('submit', handleFormSubmit);

    // --- Initial Setup ---
    toggleMode(); // Call once to set the initial state to login
    toggleMode(); // Call again to reset to the correct initial state and clear form
});
