// static/script.js for Enhanced User Portal

document.addEventListener('DOMContentLoaded', () => {
    const bodyElement = document.body;
    const userId = bodyElement.dataset.userId;

    if (!userId) {
        showToast('Error: User ID not found. Portal cannot be initialized.', 'error');
        console.error('User ID is missing from body data attribute.');
        return;
    }
    console.log(`Portal initialized for User ID: ${userId}`);

    // --- DOM Elements ---
    const profileDisplay = document.getElementById('profileDisplay'), 
          profileUsernameSpan = document.getElementById('profileUsername'), 
          profileEmailSpan = document.getElementById('profileEmail'), 
          profileBioSpan = document.getElementById('profileBio'), 
          editProfileBtn = document.getElementById('editProfileBtn'), 
          profileEditForm = document.getElementById('profileEditForm'), 
          editUsernameInput = document.getElementById('editUsername'), 
          editEmailInput = document.getElementById('editEmail'), 
          editBioTextarea = document.getElementById('editBio'), 
          cancelEditBtn = document.getElementById('cancelEditBtn');

    const sidebarUserAvatar = document.getElementById('sidebarUserAvatar'), 
          sidebarUsername = document.getElementById('sidebarUsername'), 
          sidebarUserEmail = document.getElementById('sidebarUserEmail'), 
          logoutButton = document.getElementById('logoutButton');

    const allEventsListDiv = document.getElementById('allEventsList'), 
          noAllEventsMessage = document.getElementById('noAllEventsMessage'), 
          refreshAllEventsBtn = document.getElementById('refreshAllEventsBtn');

    const myParticipationListDiv = document.getElementById('myParticipationList'), 
          noMyParticipationMessage = document.getElementById('noMyParticipationMessage'), 
          refreshMyParticipationBtn = document.getElementById('refreshMyParticipationBtn');
    
    // Participation Modal Elements
    const eventParticipationModal = document.getElementById('eventParticipationModal');
    const closeParticipationModalBtn = document.getElementById('closeParticipationModalBtn');
    const participationForm = document.getElementById('participationForm');
    const modalEventNameSpan = document.getElementById('modalEventName');
    const modalEventIdInput = document.getElementById('modalEventId');
    
    // Hidden inputs for costs per head
    const modalBaseCoverChargePerHeadInput = document.getElementById('modalBaseCoverChargePerHead');
    const modalVegFoodCostPerHeadInput = document.getElementById('modalVegFoodCostPerHead');
    const modalNonVegFoodCostPerHeadInput = document.getElementById('modalNonVegFoodCostPerHead');

    // Display elements for costs & totals in modal
    const displayBaseCoverChargePerHead = document.getElementById('displayBaseCoverChargePerHead');
    const displayVegFoodCostPerHead = document.getElementById('displayVegFoodCostPerHead');
    const displayNonVegFoodCostPerHead = document.getElementById('displayNonVegFoodCostPerHead');
    const calculatedCoverChargeComponentDisplay = document.getElementById('calculatedCoverChargeComponentDisplay');
    const calculatedFoodChargeComponentDisplay = document.getElementById('calculatedFoodChargeComponentDisplay');
    const subTotalChargesDisplay = document.getElementById('subTotalChargesDisplay');
    const totalPayableDisplay = document.getElementById('totalPayableDisplay');

    // Form fields in modal
    const participantNameInput = document.getElementById('participantName');
    const towerNumberSelect = document.getElementById('towerNumber');
    const wingSelect = document.getElementById('wing');
    const flatTypeSelect = document.getElementById('flatType');
    const floorNumberInput = document.getElementById('floorNumber');
    const vegHeadsInput = document.getElementById('vegHeads');
    const nonVegHeadsInput = document.getElementById('nonVegHeads');
    const additionalContributionInput = document.getElementById('additionalContribution');
    const amountPaidNowInput = document.getElementById('amountPaidNow'); 
    const participationStatusSelect = document.getElementById('participationStatus');
    const cancelParticipationBtn = document.getElementById('cancelParticipationBtn');
    const payableCalculatorInputs = document.querySelectorAll('.payable-calculator-input');

    const navLinks = document.querySelectorAll('.nav-link');
    const contentSections = document.querySelectorAll('.content-section');
    document.getElementById('currentYear').textContent = new Date().getFullYear();
    
    // Initialize Lucide icons if the library is loaded
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }


    const API_BASE_URL = ''; // Assuming portal backend is on the same host/port
    let currentUserData = null;
    let allEventsDataStore = {}; // Store all fetched event details by event ID

    // --- Default food costs (if not provided by Event MS) ---
    const DEFAULT_VEG_FOOD_COST = 10.00;
    const DEFAULT_NON_VEG_FOOD_COST = 12.00;

    // --- Navigation ---
    function showSection(sectionId) {
        contentSections.forEach(section => section.classList.add('hidden'));
        navLinks.forEach(link => {
            link.classList.remove('bg-indigo-600', 'text-white'); // Tailwind classes
            link.classList.add('hover:bg-gray-700'); // Tailwind classes
        });
        const activeSection = document.getElementById(sectionId);
        const activeLink = document.querySelector(`.nav-link[data-section="${sectionId}"]`);
        if (activeSection) activeSection.classList.remove('hidden');
        if (activeLink) {
            activeLink.classList.add('bg-indigo-600', 'text-white'); // Tailwind classes
            activeLink.classList.remove('hover:bg-gray-700'); // Tailwind classes
        }
        window.location.hash = sectionId; // Update URL hash for direct linking/bookmarking
    }

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = link.dataset.section;
            showSection(sectionId);
        });
    });

    // Handle initial section based on URL hash or default to profile
    const initialHash = window.location.hash.substring(1);
    if (initialHash && document.getElementById(initialHash)) {
        showSection(initialHash);
    } else {
        showSection('profile'); // Default section
    }

    // --- API Functions ---
    async function fetchUserProfile() {
        try {
            const response = await fetch(`${API_BASE_URL}/users/${userId}`);
            if (!response.ok) {
                if (response.status === 404) { // User profile doesn't exist yet
                    showToast('Profile not found. Please complete your profile to get started.', 'info');
                    profileUsernameSpan.textContent = 'N/A'; 
                    profileEmailSpan.textContent = 'N/A'; 
                    profileBioSpan.textContent = 'No bio information. Please edit your profile.';
                    sidebarUsername.textContent = 'New User'; 
                    sidebarUserEmail.textContent = 'Setup required';
                    // Show the edit form by default if no profile exists
                    profileDisplay.classList.add('hidden');
                    profileEditForm.classList.remove('hidden');
                    editUsernameInput.value = ''; 
                    editEmailInput.value = ''; 
                    editBioTextarea.value = '';
                    return null; 
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            currentUserData = data; // Store current user data
            displayUserProfile(data);
            return data;
        } catch (error) {
            console.error('Error fetching user profile:', error);
            showToast('Failed to load user profile. Please try again.', 'error');
            profileUsernameSpan.textContent = 'Error loading'; 
            profileEmailSpan.textContent = 'Error loading'; 
            profileBioSpan.textContent = 'Could not load profile data.';
            return null;
        }
    }

    async function updateUserProfile(profileData) {
        // Determine if it's a new profile (POST) or update (PUT)
        // A simple check: if currentUserData has an ID, it's an update.
        const endpoint = currentUserData && currentUserData.id ? `${API_BASE_URL}/users/${userId}` : `${API_BASE_URL}/users`;
        const method = currentUserData && currentUserData.id ? 'PUT' : 'POST';
        
        // If it's a new user (POST), include the user ID in the body if your backend expects it
        const bodyPayload = method === 'POST' ? { ...profileData, id: parseInt(userId) } : profileData;


        try {
            const response = await fetch(endpoint, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyPayload) 
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            showToast(data.message || (method === 'POST' ? "Profile created successfully!" : "Profile updated successfully!"), 'success');
            currentUserData = data.user || data; // Update stored user data (response might be {user: ...} or just user data)
            displayUserProfile(currentUserData);
            profileEditForm.classList.add('hidden');
            profileDisplay.classList.remove('hidden');
        } catch (error) {
            console.error('Error updating user profile:', error);
            showToast(`Failed to update profile: ${error.message}`, 'error');
        }
    }

    async function fetchAllEvents() {
        try {
            const response = await fetch(`${API_BASE_URL}/user_portal/events`); // Endpoint on your User Portal backend
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const events = await response.json();
            // Store events in allEventsDataStore by their ID for easy lookup when opening modal
            allEventsDataStore = events.reduce((acc, event) => {
                acc[event.id] = event;
                return acc;
            }, {});
            displayAllEvents(events);
        } catch (error) {
            console.error('Error fetching all events:', error);
            showToast('Failed to load events. Please try refreshing.', 'error');
            allEventsListDiv.innerHTML = ''; // Clear previous content
            noAllEventsMessage.classList.remove('hidden');
            noAllEventsMessage.textContent = 'Could not load events. Please try again later.';
        }
    }

    async function fetchMyParticipations() {
        try {
            const response = await fetch(`${API_BASE_URL}/users/${userId}/participation`); // Endpoint on your User Portal backend
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const participations = await response.json();
            displayMyParticipations(participations);
        } catch (error) {
            console.error('Error fetching my participations:', error);
            showToast('Failed to load your event participations.', 'error');
            myParticipationListDiv.innerHTML = ''; // Clear previous content
            noMyParticipationMessage.classList.remove('hidden');
            noMyParticipationMessage.textContent = 'Could not load your participations. Please try again.';
        }
    }
    
    async function submitParticipation(eventId, participationData) {
        // This POST request goes to the User Portal backend
        const endpoint = `${API_BASE_URL}/users/${userId}/participation/${eventId}`;
        try {
            const response = await fetch(endpoint, {
                method: 'POST', // User Portal backend will determine if it's a new or update to Participation Service
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(participationData)
            });
            if (!response.ok) {
                 const errorData = await response.json();
                 // Attempt to provide more specific error if available from backend
                 throw new Error(errorData.error || `HTTP error! status: ${response.status} - ${errorData.details || 'Unknown error'}`);
            }
            const data = await response.json();
            showToast(data.message || 'Participation submitted successfully!', 'success');
            closeParticipationModal();
            fetchMyParticipations(); // Refresh the list of user's participations
            fetchAllEvents(); // Refresh all events in case status indicators on event cards need update
        } catch (error) {
            console.error('Error submitting participation:', error);
            showToast(`Failed to submit participation: ${error.message}`, 'error');
        }
    }

    // --- Display Functions ---
    function displayUserProfile(data) {
        if (!data) return;
        profileUsernameSpan.textContent = data.username || 'N/A';
        profileEmailSpan.textContent = data.email || 'N/A';
        profileBioSpan.textContent = data.bio || 'No bio provided.';
        
        sidebarUsername.textContent = data.username || 'User';
        sidebarUserEmail.textContent = data.email || 'No email';
        // Simple avatar placeholder using username initial
        const initial = (data.username || 'U').charAt(0).toUpperCase();
        sidebarUserAvatar.src = `https://placehold.co/40x40/A78BFA/FFFFFF?text=${initial}`;

        // Pre-fill edit form as well
        editUsernameInput.value = data.username || '';
        editEmailInput.value = data.email || '';
        editBioTextarea.value = data.bio || '';
    }

    function displayAllEvents(events) {
        allEventsListDiv.innerHTML = ''; 
        if (!events || events.length === 0) {
            noAllEventsMessage.classList.remove('hidden');
            noAllEventsMessage.textContent = 'No upcoming events found. Check back later!';
            return;
        }
        noAllEventsMessage.classList.add('hidden');

        events.forEach(event => {
            const card = document.createElement('div');
            // Tailwind classes for card styling
            card.className = 'bg-white p-5 rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 flex flex-col'; 
            
            // Use the structure from Event MS app.py (event.subscription.coverCharges)
            const coverCharges = event.subscription?.coverCharges || 0;
            const coverChargesType = event.subscription?.coverChargesType || "per_head";
            const baseCoverDisplay = (coverCharges > 0 && coverChargesType === "per_head") 
                                    ? `$${parseFloat(coverCharges).toFixed(2)}/head` 
                                    : (coverCharges > 0 ? `$${parseFloat(coverCharges).toFixed(2)}/${coverChargesType.replace('_', ' ')}` : 'Free or TBD');

            // Adjust date display: Event MS uses 'time' for event date/time string.
            const eventDateStr = event.time || event.date; // Fallback to 'date' if 'time' is missing
            const eventDateDisplay = eventDateStr ? new Date(eventDateStr).toLocaleDateString() : 'Date TBD';
            
            // Adjust location display: Event MS uses 'venue'.
            const eventLocationDisplay = event.venue || event.location || 'Location TBD';

            // Adjust description display: Event MS uses 'details'.
            const eventDescription = event.details || event.description || 'No description available.';


            card.innerHTML = `
                <h3 class="text-xl font-semibold text-indigo-700 mb-2">${event.name || 'Unnamed Event'}</h3>
                <p class="text-sm text-gray-500 mb-1 flex items-center"><i data-lucide="calendar" class="w-4 h-4 mr-2"></i>${eventDateDisplay}</p>
                <p class="text-sm text-gray-500 mb-3 flex items-center"><i data-lucide="map-pin" class="w-4 h-4 mr-2"></i>${eventLocationDisplay}</p>
                <p class="text-gray-600 text-sm mb-4 flex-grow">${eventDescription.substring(0,100)}${eventDescription.length > 100 ? '...' : ''}</p>
                <p class="text-sm text-gray-700 font-medium mb-3">Cover: ${baseCoverDisplay}</p>
                <button data-event-id="${event.id}" class="register-event-btn mt-auto w-full px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition duration-150 text-sm flex items-center justify-center space-x-2">
                    <i data-lucide="edit" class="w-4 h-4"></i><span>Register / View Status</span>
                </button>
            `;
            allEventsListDiv.appendChild(card);
        });
        if (typeof lucide !== 'undefined') lucide.createIcons(); // Re-initialize icons for newly added elements

        // Add event listeners for new register buttons
        document.querySelectorAll('.register-event-btn').forEach(button => {
            button.addEventListener('click', () => {
                const eventId = button.dataset.eventId;
                openParticipationModal(eventId); // Pass only eventId
            });
        });
    }
    
    function displayMyParticipations(participations) {
        myParticipationListDiv.innerHTML = '';
        if (!participations || participations.length === 0) {
            noMyParticipationMessage.classList.remove('hidden');
            noMyParticipationMessage.textContent = "You haven't participated in any events yet.";
            return;
        }
        noMyParticipationMessage.classList.add('hidden');

        participations.forEach(event => { // `event` here is a participation record
            const card = document.createElement('div');
            card.className = 'bg-white p-5 rounded-xl shadow-lg flex flex-col'; // Tailwind classes
            let statusColor = 'text-gray-500', statusBg = 'bg-gray-100'; // Tailwind classes
            if (event.user_status === 'attending') { statusColor = 'text-green-700'; statusBg = 'bg-green-100'; }
            else if (event.user_status === 'interested') { statusColor = 'text-blue-700'; statusBg = 'bg-blue-100'; }
            else if (event.user_status === 'not_attending') { statusColor = 'text-red-700'; statusBg = 'bg-red-100';}
            
            // Try to get original event details from allEventsDataStore for richer display
            const originalEvent = allEventsDataStore[event.event_id]; // event.event_id from Participation record
            let baseCoverDisplay = 'N/A';
            let eventDateDisplay = event.date ? new Date(event.date).toLocaleDateString() : 'Date TBD'; // Fallback from participation record
            let eventLocationDisplay = event.location || 'Location TBD'; // Fallback
            let eventDescription = event.description || 'No description.'; // Fallback

            if (originalEvent) {
                const coverCharges = originalEvent.subscription?.coverCharges || 0;
                const coverChargesType = originalEvent.subscription?.coverChargesType || "per_head";
                baseCoverDisplay = (coverCharges > 0 && coverChargesType === "per_head") 
                                        ? `$${parseFloat(coverCharges).toFixed(2)}/head` 
                                        : (coverCharges > 0 ? `$${parseFloat(coverCharges).toFixed(2)}/${coverChargesType.replace('_', ' ')}` : 'Free or TBD');
                
                const originalEventDateStr = originalEvent.time || originalEvent.date;
                if (originalEventDateStr) eventDateDisplay = new Date(originalEventDateStr).toLocaleDateString();
                if (originalEvent.venue) eventLocationDisplay = originalEvent.venue;
                if (originalEvent.details) eventDescription = originalEvent.details;
            }


            card.innerHTML = `
                <h3 class="text-xl font-semibold text-indigo-700 mb-2">${event.name || 'Unnamed Event'}</h3>
                <p class="text-sm text-gray-500 mb-1 flex items-center"><i data-lucide="calendar" class="w-4 h-4 mr-2"></i>${eventDateDisplay}</p>
                <p class="text-sm text-gray-500 mb-3 flex items-center"><i data-lucide="map-pin" class="w-4 h-4 mr-2"></i>${eventLocationDisplay}</p>
                <p class="text-gray-600 text-sm mb-4 flex-grow">${eventDescription.substring(0,100)}${eventDescription.length > 100 ? '...' : ''}</p>
                <p class="text-sm text-gray-700 font-medium mb-1">Cover: ${baseCoverDisplay}</p>
                <div class="mb-3">
                    <span class="px-3 py-1 text-xs font-semibold rounded-full ${statusColor} ${statusBg}">${event.user_status ? event.user_status.charAt(0).toUpperCase() + event.user_status.slice(1) : 'N/A'}</span>
                </div>
                 <button data-event-id="${event.event_id}" class="update-participation-btn mt-auto w-full px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition duration-150 text-sm flex items-center justify-center space-x-2">
                    <i data-lucide="edit-2" class="w-4 h-4"></i><span>Update Status</span>
                </button>
            `;
            myParticipationListDiv.appendChild(card);
        });
        if (typeof lucide !== 'undefined') lucide.createIcons();

        document.querySelectorAll('.update-participation-btn').forEach(button => {
            button.addEventListener('click', () => {
                const eventId = button.dataset.eventId;
                openParticipationModal(eventId, true /* isUpdate */);
            });
        });
    }

    // --- Event Handlers ---
    editProfileBtn.addEventListener('click', () => { 
        profileDisplay.classList.add('hidden'); 
        profileEditForm.classList.remove('hidden'); 
        // Ensure form is pre-filled if currentUserData exists
        if (currentUserData) {
            editUsernameInput.value = currentUserData.username || '';
            editEmailInput.value = currentUserData.email || '';
            editBioTextarea.value = currentUserData.bio || '';
        }
    });
    cancelEditBtn.addEventListener('click', () => { 
        profileEditForm.classList.add('hidden'); 
        profileDisplay.classList.remove('hidden'); 
        // Optionally reset form to displayed data if changes were made but not saved
        if (currentUserData) displayUserProfile(currentUserData);
    });
    profileEditForm.addEventListener('submit', (e) => { 
        e.preventDefault(); 
        updateUserProfile({ 
            username: editUsernameInput.value, 
            email: editEmailInput.value, 
            bio: editBioTextarea.value 
        }); 
    });
    refreshAllEventsBtn.addEventListener('click', fetchAllEvents);
    refreshMyParticipationBtn.addEventListener('click', fetchMyParticipations);
    logoutButton.addEventListener('click', () => { 
        showCustomConfirm("Are you sure you want to logout?", () => { 
            showToast("Logged out (simulated). Please implement actual logout.", "info"); 
            // Example: window.location.href = '/logout_route'; 
        }); 
    });

    // --- Participation Modal Logic (UPDATED to use Event MS data structure) ---
    function updatePayableAmount() {
        const baseCoverPerHead = parseFloat(modalBaseCoverChargePerHeadInput.value) || 0;
        const vegCostPerHead = parseFloat(modalVegFoodCostPerHeadInput.value) || 0;
        const nonVegCostPerHead = parseFloat(modalNonVegFoodCostPerHeadInput.value) || 0;

        const numVeg = parseInt(vegHeadsInput.value) || 0;
        const numNonVeg = parseInt(nonVegHeadsInput.value) || 0;
        const totalHeads = numVeg + numNonVeg;

        const calculatedCover = totalHeads * baseCoverPerHead;
        const calculatedFood = (numVeg * vegCostPerHead) + (numNonVeg * nonVegCostPerHead);
        const additionalContrib = parseFloat(additionalContributionInput.value) || 0;
        
        const subTotal = calculatedCover + calculatedFood;
        const totalPayable = subTotal + additionalContrib;

        calculatedCoverChargeComponentDisplay.textContent = `$${calculatedCover.toFixed(2)}`;
        calculatedFoodChargeComponentDisplay.textContent = `$${calculatedFood.toFixed(2)}`;
        subTotalChargesDisplay.textContent = `$${subTotal.toFixed(2)}`;
        totalPayableDisplay.textContent = `$${totalPayable.toFixed(2)}`;
    }

    payableCalculatorInputs.forEach(input => {
        input.addEventListener('input', updatePayableAmount);
    });
    
    async function openParticipationModal(eventId, isUpdate = false) {
        const eventDetails = allEventsDataStore[eventId]; // Get full event details
        if (!eventDetails) {
            showToast(`Event details not found for ID: ${eventId}. Please refresh events.`, 'error');
            return;
        }

        modalEventIdInput.value = eventId;
        modalEventNameSpan.textContent = eventDetails.name || 'Unnamed Event';

        // Extract costs based on Event MS structure
        let baseCover = 0;
        // Check if subscription object and its properties exist
        if (eventDetails.subscription && eventDetails.subscription.coverChargesType === 'per_head') {
            baseCover = parseFloat(eventDetails.subscription.coverCharges || 0);
        }

        let vegCost = DEFAULT_VEG_FOOD_COST; // Default value
        let nonVegCost = DEFAULT_NON_VEG_FOOD_COST; // Default value

        // Check if food object and its properties exist
        if (eventDetails.food && eventDetails.food.foodChargesType === 'per_head') {
            const foodCharge = parseFloat(eventDetails.food.foodCharges || 0);
            if (eventDetails.food.foodType === 'veg') {
                vegCost = foodCharge > 0 ? foodCharge : DEFAULT_VEG_FOOD_COST; // Use foodCharge if > 0, else default
            } else if (eventDetails.food.foodType === 'non_veg') {
                nonVegCost = foodCharge > 0 ? foodCharge : DEFAULT_NON_VEG_FOOD_COST; // Use foodCharge if > 0, else default
            } else if (eventDetails.food.foodType === 'both') {
                // If 'both', apply the charge to both if it's significant, else use defaults
                if (foodCharge > 0) {
                    vegCost = foodCharge;
                    nonVegCost = foodCharge;
                }
            }
        }
        
        // Store these parsed/defaulted costs in hidden inputs
        modalBaseCoverChargePerHeadInput.value = baseCover;
        modalVegFoodCostPerHeadInput.value = vegCost;
        modalNonVegFoodCostPerHeadInput.value = nonVegCost;
        
        // Display these costs to the user
        displayBaseCoverChargePerHead.textContent = `$${baseCover.toFixed(2)}`;
        displayVegFoodCostPerHead.textContent = `$${vegCost.toFixed(2)}`;
        displayNonVegFoodCostPerHead.textContent = `$${nonVegCost.toFixed(2)}`;
        
        participationForm.reset(); // Reset form fields first
        modalEventIdInput.value = eventId; // Re-set eventId after reset
        // Re-set hidden costs after reset
        modalBaseCoverChargePerHeadInput.value = baseCover; 
        modalVegFoodCostPerHeadInput.value = vegCost;
        modalNonVegFoodCostPerHeadInput.value = nonVegCost;

        // Pre-fill participant name from profile if available
        if (currentUserData && currentUserData.username) {
            participantNameInput.value = currentUserData.username;
        }
        
        // If updating, try to fetch existing participation details to prefill form
        if (isUpdate) {
            showToast("Fetching your existing participation details...", "info");
            try {
                // This endpoint on User Portal needs to fetch specific participation details
                const response = await fetch(`${API_BASE_URL}/users/${userId}/participation/${eventId}`); 
                if (!response.ok) {
                    if (response.status === 404) { // Participation not found for this event for this user
                        showToast("No prior participation found for this event. Please fill as new.", "info");
                        // Set defaults for a new registration but with intent to update
                        vegHeadsInput.value = '0'; 
                        nonVegHeadsInput.value = '0';
                        additionalContributionInput.value = '0'; 
                        amountPaidNowInput.value = '0'; // User will enter calculated total or partial
                        participationStatusSelect.value = 'interested'; // Sensible default for "update"
                    } else {
                        throw new Error(`Failed to fetch existing participation: ${response.status}`);
                    }
                } else {
                    const existingParticipation = await response.json();
                    // Assuming the User Portal backend returns the 'details' object from the Participation service
                    if (existingParticipation && existingParticipation.details) {
                        const details = existingParticipation.details;
                        participantNameInput.value = details.participantName || currentUserData?.username || '';
                        towerNumberSelect.value = details.towerNumber || '';
                        wingSelect.value = details.wing || 'NA';
                        flatTypeSelect.value = details.flatType || '';
                        floorNumberInput.value = details.floorNumber || '';
                        vegHeadsInput.value = details.vegHeads || '0';
                        nonVegHeadsInput.value = details.nonVegHeads || '0';
                        additionalContributionInput.value = details.additionalContribution || '0';
                        amountPaidNowInput.value = details.coverChargePaid || '0'; // This is the crucial recorded payment
                        participationStatusSelect.value = existingParticipation.status || 'interested';
                    } else { // Fallback if 'details' structure isn't as expected (e.g., older participation record)
                         showToast("Partial existing data found. Please review carefully.", "info");
                         // Attempt to prefill from top-level fields if details object is missing/different
                         amountPaidNowInput.value = existingParticipation.cover_charge_paid_amount || '0';
                         participationStatusSelect.value = existingParticipation.status || 'interested';
                         vegHeadsInput.value = existingParticipation.veg_heads || '0'; // Assuming these might exist at top level
                         nonVegHeadsInput.value = existingParticipation.non_veg_heads || '0';
                         additionalContributionInput.value = existingParticipation.additional_contribution_amount || '0';
                    }
                }
            } catch (err) {
                console.error("Error fetching existing participation:", err);
                showToast("Could not fetch existing participation details. Please fill manually.", "error");
                // Sensible defaults on error
                amountPaidNowInput.value = '0';
                participationStatusSelect.value = 'interested';
            }
        } else { // New registration
            vegHeadsInput.value = '0';
            nonVegHeadsInput.value = '0';
            additionalContributionInput.value = '0';
            amountPaidNowInput.value = '0'; // Default to 0, user will enter calculated total or partial
            participationStatusSelect.value = 'attending'; // Default to attending for new registration
        }
        
        updatePayableAmount(); // Perform initial calculation
        eventParticipationModal.classList.add('active');
    }

    function closeParticipationModal() {
        eventParticipationModal.classList.remove('active');
        // No need to reset form here, it's reset at the start of openParticipationModal
    }

    closeParticipationModalBtn.addEventListener('click', closeParticipationModal);
    cancelParticipationBtn.addEventListener('click', closeParticipationModal);
    // Close modal if user clicks on the overlay backdrop
    eventParticipationModal.addEventListener('click', (e) => { 
        if (e.target === eventParticipationModal) closeParticipationModal(); 
    });

    participationForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const eventId = modalEventIdInput.value;

        // Data to be sent to the User Portal backend
        // The User Portal backend then transforms this for the Participation Service
        const participationPayload = {
            status: participationStatusSelect.value,
            details: { // This 'details' object is what your User Portal app.py should expect
                // user_name, email_id can be added by User Portal backend from User model
                towerNumber: towerNumberSelect.value,
                wing: wingSelect.value,
                flatType: flatTypeSelect.value,
                floorNumber: parseInt(floorNumberInput.value),
                // This is the amount user records as paid for the whole participation.
                // Your User Portal backend will map this to `cover_charge_paid` for the Participation Service.
                coverChargePaid: parseFloat(amountPaidNowInput.value), 
                additionalContribution: parseFloat(additionalContributionInput.value || 0),
                vegHeads: parseInt(vegHeadsInput.value || 0),
                nonVegHeads: parseInt(nonVegHeadsInput.value || 0),
                participantName: participantNameInput.value // Sending name for backend to use if User model doesn't have a preferred display name
            }
        };
        submitParticipation(eventId, participationPayload);
    });

    // --- Utility Functions (Toast and Confirm) ---
    const toastContainer = document.getElementById('toastContainer');
    function showToast(message, type = 'info', duration = 3000) {
        if (!toastContainer) {
            console.warn("Toast container not found. Cannot display toast:", message);
            return;
        }
        const toast = document.createElement('div');
        toast.className = `toast-message ${type}`; // Tailwind classes are applied via CSS file
        toast.textContent = message;
        toastContainer.appendChild(toast);

        // Animate in (handled by CSS @keyframes toast-in)
        // Auto-dismiss
        setTimeout(() => {
            toast.style.animation = 'toast-out 0.5s forwards'; // CSS @keyframes toast-out
            toast.addEventListener('animationend', () => {
                toast.remove();
            });
        }, duration);
    }

    function showCustomConfirm(message, onConfirm, onCancel) {
        const overlayId = 'custom-confirm-overlay';
        // Prevent multiple confirm dialogs
        if (document.getElementById(overlayId)) return;

        const overlay = document.createElement('div');
        overlay.id = overlayId;
        // Using Tailwind classes directly for simplicity here, or define in CSS file
        overlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-[9999]'; 
        
        const dialog = document.createElement('div');
        dialog.className = 'bg-white p-6 rounded-lg shadow-xl max-w-sm w-full'; // Tailwind classes
        
        const messageP = document.createElement('p');
        messageP.className = 'text-lg text-gray-700 mb-6'; // Tailwind classes
        messageP.textContent = message;
        
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'flex justify-end space-x-3'; // Tailwind classes

        const confirmButton = document.createElement('button');
        confirmButton.className = 'px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition'; // Tailwind classes
        confirmButton.textContent = 'Confirm';
        confirmButton.onclick = () => {
            overlay.remove();
            if (onConfirm) onConfirm();
        };

        const cancelButton = document.createElement('button');
        cancelButton.className = 'px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition'; // Tailwind classes
        cancelButton.textContent = 'Cancel';
        cancelButton.onclick = () => {
            overlay.remove();
            if (onCancel) onCancel();
        };

        buttonContainer.appendChild(cancelButton);
        buttonContainer.appendChild(confirmButton);
        dialog.appendChild(messageP);
        dialog.appendChild(buttonContainer);
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
    }

    // --- Initial Load ---
    async function initializePortal() {
        await fetchUserProfile(); 
        await fetchAllEvents();
        await fetchMyParticipations();
    }

    initializePortal();

}); // End DOMContentLoaded
 
