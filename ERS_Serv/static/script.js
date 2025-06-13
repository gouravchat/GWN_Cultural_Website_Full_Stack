document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    // URLs for the backend microservices. Ensure these ports match your running services.
    const EVENT_SERVICE_URL = 'http://localhost:5000'; // Your Event Service
    const USER_DB_URL = 'http://localhost:5004';       // Your User DB Service
    const PARTICIPATION_SERVICE_URL = 'http://localhost:5005'; // Your Participation Service

    // --- Global State ---
    // An object to hold the context of the registration process for a single session.
    const currentRegistration = {
        user: null,
        event: null,
        formData: {},
        totalAmount: 0,
        amountPaid: 0,
        remainingBalance: 0,
    };

    // --- DOM Element Selectors ---
    const eventSelectionSection = document.getElementById('eventSelectionSection');
    const registrationFormSection = document.getElementById('registrationFormSection');
    const paymentSection = document.getElementById('paymentSection');
    const statusSection = document.getElementById('statusSection');
    const registrationForm = document.getElementById('registrationForm');
    const payingNowInput = document.getElementById('payingNow');
    const userInfoHeader = document.getElementById('userInfoHeader');

    // --- API Functions ---
    /**
     * A generic helper function to make API calls and handle common errors.
     * @param {string} url - The URL to fetch.
     * @returns {Promise<object|null>} - The JSON response or null if an error occurred.
     */
    async function fetchApi(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                console.error(`API Error: ${response.status} ${response.statusText} for URL: ${url}`);
                return null;
            }
            return await response.json();
        } catch (error) {
            console.error(`Failed to fetch from ${url}:`, error);
            return null;
        }
    }

    // Specific API functions using the generic helper
    const fetchAllEvents = () => fetchApi(`${EVENT_SERVICE_URL}/events`);
    const fetchEventById = (eventId) => fetchApi(`${EVENT_SERVICE_URL}/events/${eventId}`);
    const fetchUserById = (userId) => fetchApi(`${USER_DB_URL}/users/${userId}`);

    /**
     * Submits the final participation record to the backend service.
     * @param {object} participationRecord - The data payload to send.
     */
    async function submitParticipation(participationRecord) {
        try {
            const response = await fetch(`${PARTICIPATION_SERVICE_URL}/participant-records`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(participationRecord),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Submission failed');
            }
            showStatus('success', currentRegistration);
        } catch (error) {
            alert(`Error: ${error.message}`);
            showStatus('cancel');
        }
    }

    // --- UI Functions ---
    /**
     * Displays the welcome header with the fetched user information.
     * @param {object} user - The user object from the API.
     */
    function displayUserInfo(user) {
        if (!user) return;
        document.getElementById('usernameDisplay').textContent = user.username;
        document.getElementById('userEmailDisplay').textContent = user.email;
        const avatar = document.getElementById('userAvatar');
        avatar.textContent = user.username.charAt(0).toUpperCase();
        userInfoHeader.classList.remove('hidden');
    }

    /**
     * Renders event cards on the page, enabling or disabling the registration
     * button based on whether a user context is known.
     * @param {Array} events - An array of event objects.
     * @param {boolean} userIsKnown - A flag to determine if buttons should be active.
     */
    function renderEvents(events, userIsKnown) {
        const eventList = document.getElementById('eventList');
        eventList.innerHTML = '';
        if (!events || events.length === 0) {
            eventList.innerHTML = '<p class="text-gray-500">No upcoming events found.</p>';
            return;
        }
        events.forEach(event => {
            const card = document.createElement('div');
            card.className = 'bg-white p-6 rounded-xl shadow-md card-hover-effect flex flex-col justify-between';
            
            const buttonDisabled = !userIsKnown ? 'disabled' : '';
            const buttonTooltip = !userIsKnown ? 'title="Please access via the User Portal to register"' : '';
            const buttonClasses = !userIsKnown ? 'bg-gray-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700';

            card.innerHTML = `
                <div>
                    <h3 class="text-xl font-semibold text-gray-900">${event.name}</h3>
                    <p class="text-sm text-gray-500 mt-1">${new Date(event.time_str).toLocaleDateString('en-IN', { dateStyle: 'full', timeStyle: 'short' })}</p>
                    <p class="text-lg font-medium text-indigo-600 mt-4">Cover Charge: ₹${event.subscription.coverCharges.toFixed(2)}</p>
                </div>
                <button 
                    onclick="handleEventSelection('${event.id}')" 
                    class="register-btn mt-6 w-full text-white font-semibold py-2 px-4 rounded-lg transition-colors ${buttonClasses}" 
                    ${buttonDisabled} ${buttonTooltip}>
                    Register Now
                </button>
            `;
            eventList.appendChild(card);
        });
    }

    /**
     * Shows a specific section of the page (e.g., form, payment) and hides others.
     * @param {string} sectionId - The ID of the section to display.
     */
    function showSection(sectionId) {
        ['eventSelectionSection', 'registrationFormSection', 'paymentSection', 'statusSection'].forEach(id => {
            document.getElementById(id).classList.toggle('hidden', id !== sectionId);
        });
    }

    /**
     * Populates the registration form with user and event data.
     * @param {object} user - The fetched user object.
     * @param {object} event - The fetched event object.
     */
    function populateRegistrationForm(user, event) {
        currentRegistration.user = user;
        currentRegistration.event = event;

        // Correctly populate the Tower dropdown menu.
        const towerSelect = document.getElementById('tower');
        towerSelect.innerHTML = ''; // Clear any previous options
        ['Alpine1 LW', 'Alpine1 RW', 'Alpine2 LW', 'Alpine2 RW', 'Alpine3'].forEach(towerName => {
            const option = document.createElement('option');
            option.value = towerName;
            option.textContent = towerName;
            towerSelect.appendChild(option);
        });

        // Fill in form fields with data.
        document.getElementById('formEventName').textContent = event.name;
        document.getElementById('username').value = user.username;
        document.getElementById('email').value = user.email;
        document.getElementById('phoneNumber').value = user.phone_number;
        
        const coverCharges = event.subscription?.coverCharges || 0;
        const vegCharges = event.food?.veg_charges || 0;
        const nonVegCharges = event.food?.non_veg_charges || 0;

        document.getElementById('coverCharges').value = `₹${coverCharges.toFixed(2)}`;
        document.getElementById('vegCharges').value = `₹${vegCharges.toFixed(2)}`;
        document.getElementById('nonVegCharges').value = `₹${nonVegCharges.toFixed(2)}`;
        
        showSection('registrationFormSection');
    }
    
    // Make handleEventSelection globally accessible for the inline onclick attribute.
    window.handleEventSelection = async (eventId) => {
        if (!currentRegistration.user) {
            alert("User context is missing. Please access this page from your User Portal.");
            return;
        }
        const event = await fetchEventById(eventId);
        if (event) {
            populateRegistrationForm(currentRegistration.user, event);
        }
    }

    function updateRemainingAmount() {
        const totalPayable = currentRegistration.totalAmount;
        const payingNow = parseFloat(payingNowInput.value) || 0;
        const remaining = totalPayable - payingNow;
        document.getElementById('paymentRemainingAmount').textContent = `₹${remaining.toFixed(2)}`;
    }

    function showStatus(type, details) {
        const statusMessage = document.getElementById('statusMessage');
        let content = '';
        if (type === 'success') {
            content = `
                <h2 class="text-3xl font-bold text-gray-900 mt-4">Registration Confirmed!</h2>
                <p class="text-gray-600 mt-2">Your registration for <strong>${details.event.name}</strong> is complete.</p>
                <div class="mt-6 border-t pt-4 text-left w-full max-w-sm mx-auto space-y-2">
                    <div class="flex justify-between"><span>Total Payable:</span><span class="font-medium">₹${details.totalAmount.toFixed(2)}</span></div>
                    <div class="flex justify-between text-green-600"><span>Amount Paid:</span><span class="font-bold">₹${details.amountPaid.toFixed(2)}</span></div>
                    <div class="flex justify-between text-red-600"><span>Remaining Balance:</span><span class="font-bold">₹${details.remainingBalance.toFixed(2)}</span></div>
                </div>
            `;
        } else {
            content = `<h2 class="text-3xl font-bold text-gray-900 mt-4">Registration Cancelled</h2>`;
        }
        content += `<a href="/" class="mt-8 inline-block bg-indigo-600 text-white font-semibold py-2 px-6 rounded-lg hover:bg-indigo-700">Back to Home</a>`;
        statusMessage.innerHTML = content;
        showSection('statusSection');
    }

    // --- Event Listeners ---
    
    // Handles the "Proceed to Payment" button click.
    registrationForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        currentRegistration.formData = {
            username: currentRegistration.user.username,
            tower: document.getElementById('tower').value,
            flatNo: document.getElementById('flatNo').value,
            vegHeads: parseInt(document.getElementById('vegHeads').value, 10) || 0,
            nonVegHeads: parseInt(document.getElementById('nonVegHeads').value, 10) || 0,
            additionalContribution: parseFloat(document.getElementById('additionalContribution').value) || 0,
            contributionComments: document.getElementById('contributionComments').value,
        };

        const { vegHeads, nonVegHeads, additionalContribution } = currentRegistration.formData;
        const totalHeads = vegHeads + nonVegHeads;
        const coverTotal = (currentRegistration.event.subscription?.coverCharges || 0) * totalHeads;
        const vegTotal = (currentRegistration.event.food?.veg_charges || 0) * vegHeads;
        const nonVegTotal = (currentRegistration.event.food?.non_veg_charges || 0) * nonVegHeads;
        const grandTotal = coverTotal + vegTotal + nonVegTotal + additionalContribution;
        currentRegistration.totalAmount = grandTotal;
        
        document.getElementById('paymentEventName').textContent = currentRegistration.event.name;
        document.getElementById('paymentBreakdown').innerHTML = `
            <div class="flex justify-between"><span>Cover Charges (${totalHeads} heads)</span><span>₹${coverTotal.toFixed(2)}</span></div>
            <div class="flex justify-between"><span>Veg Charges (${vegHeads} heads)</span><span>₹${vegTotal.toFixed(2)}</span></div>
            <div class="flex justify-between"><span>Non-Veg Charges (${nonVegHeads} heads)</span><span>₹${nonVegTotal.toFixed(2)}</span></div>
            <div class="flex justify-between"><span>Additional Contribution</span><span>₹${additionalContribution.toFixed(2)}</span></div>
        `;
        document.getElementById('paymentTotalPayable').textContent = `₹${grandTotal.toFixed(2)}`;
        
        payingNowInput.value = grandTotal.toFixed(2);
        payingNowInput.max = grandTotal.toFixed(2);
        updateRemainingAmount();
        
        showSection('paymentSection');
    });

    payingNowInput.addEventListener('input', updateRemainingAmount);

    document.getElementById('confirmPayment').addEventListener('click', function() {
        const amountPaid = parseFloat(payingNowInput.value) || 0;
        if (amountPaid > currentRegistration.totalAmount) {
            alert("Amount paid cannot be greater than the total payable amount.");
            return;
        }
        
        const remainingBalance = currentRegistration.totalAmount - amountPaid;

        currentRegistration.amountPaid = amountPaid;
        currentRegistration.remainingBalance = remainingBalance;

        const participationRecord = {
            eventId: currentRegistration.event.id,
            userId: currentRegistration.user.id,
            totalAmount: currentRegistration.totalAmount,
            amountPaid: currentRegistration.amountPaid,
            remainingBalance: remainingBalance,
            registrationDetails: currentRegistration.formData
        };
        
        submitParticipation(participationRecord);
    });

    // Wire up cancellation buttons
    document.getElementById('cancelRegistration').addEventListener('click', () => showSection('eventSelectionSection'));
    document.getElementById('cancelPayment').addEventListener('click', () => showSection('registrationFormSection'));
    
    // --- Page Initialization ---
    const initializePage = async () => {
        const urlParams = new URLSearchParams(window.location.search);
        const userId = urlParams.get('userId');

        if (userId) {
            const user = await fetchUserById(userId);
            if (user) {
                currentRegistration.user = user;
                displayUserInfo(user);
                const events = await fetchAllEvents();
                renderEvents(events, true); // Enable registration
                showSection('eventSelectionSection');
            } else {
                alert(`User with ID ${userId} could not be found. Showing public event list.`);
                const events = await fetchAllEvents();
                renderEvents(events, false); // Disable registration
                showSection('eventSelectionSection');
            }
        } 
        else {
            const events = await fetchAllEvents();
            renderEvents(events, false); // Disable registration
            showSection('eventSelectionSection');
        }
    };

    initializePage();
});
