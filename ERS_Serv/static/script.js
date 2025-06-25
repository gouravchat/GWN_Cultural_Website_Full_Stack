document.addEventListener('DOMContentLoaded', () => {
    // Dynamically inject API URLs and initial data from Flask backend
    // The API_CONFIG is expected to be defined by Flask in index.html.
    // This fallback block is only for scenarios where that injection fails.
    if (typeof API_CONFIG === 'undefined' || Object.keys(API_CONFIG).length === 0) {
        console.error("API_CONFIG is not defined or is empty. Ensuring index.html injects it correctly, or defining a fallback.");
        // Determine the base path for ERS APIs for this fallback.
        // If Flask's ERS_SCRIPT_NAME is empty, these would be directly under localhost.
        const fallbackBaseUrl = 'https://localhost'; 

        window.API_CONFIG = {
            // External APIs (their paths might be fixed regardless of ERS_SCRIPT_NAME)
            USERS_API: `${fallbackBaseUrl}/user-portal/api/users/4`,
            EVENTS_API: `${fallbackBaseUrl}/events/events/1`,
            PART_API: `${fallbackBaseUrl}/participations/participations`,

            // ERS's own APIs - will default to base path if not explicitly routed by Nginx
            ERS_CALCULATE_PRICE_API: `${fallbackBaseUrl}/calculate_price`,
            ERS_START_PARTICIPATION_API: `${fallbackBaseUrl}/start_participation`,
            ERS_EDIT_PARTICIPATION_API: `${fallbackBaseUrl}/edit_participation`,
            ERS_DELETE_PARTICIPATION_API: `${fallbackBaseUrl}/delete_participation`,
            ERS_PAYMENT_CALLBACK_API: `${fallbackBaseUrl}/payment_callback`,
            ERS_CHECK_PARTICIPATION_API: `${fallbackBaseUrl}/check_participation`
        };
        console.log("Using fallback API_CONFIG:", window.API_CONFIG);
        // Explicit check for ERS_CHECK_PARTICIPATION_API in fallback scenario
        console.warn("Fallback: ERS_CHECK_PARTICIPATION_API is set to:", window.API_CONFIG.ERS_CHECK_PARTICIPATION_API);

    } else {
        // This block confirms that Flask successfully injected API_CONFIG.
        // The URLs here will already include the ERS_SCRIPT_NAME (e.g., /user-portal or /ers)
        console.log("API_CONFIG successfully loaded from Flask:", API_CONFIG);
        // Explicit check for ERS_CHECK_PARTICIPATION_API in Flask-injected scenario
        console.log("Flask-injected: ERS_CHECK_PARTICIPATION_API is set to:", API_CONFIG.ERS_CHECK_PARTICIPATION_API);
    }

    // NEW: User Portal Root URL - ensure it's available from Flask injection
    const USER_PORTAL_ROOT_URL_JS = typeof window.USER_PORTAL_ROOT_URL_JS !== 'undefined' ? window.USER_PORTAL_ROOT_URL_JS : 'https://localhost/user-portal';
    console.log("User Portal Root URL for Redirection:", USER_PORTAL_ROOT_URL_JS);


    const userIdInput = document.getElementById('userId');
    const eventIdInput = document.getElementById('eventId');
    const numTicketsInput = document.getElementById('numTickets');
    const vegHeadsInput = document.getElementById('vegHeads');
    const nonVegHeadsInput = document.getElementById('nonVegHeads');
    const additionalContributionInput = document.getElementById('additionalContribution');
    const towerNumberInput = document.getElementById('towerNumber');
    const flatNumberInput = document.getElementById('flatNumber');

    const calculatePriceBtn = document.getElementById('calculatePriceBtn');
    const priceCalculationResult = document.getElementById('price-calculation-result');
    
    const submitParticipationBtn = document.getElementById('submitParticipationBtn');
    const deleteParticipationBtn = document.getElementById('deleteParticipationBtn');

    const paymentOutcomeSection = document.getElementById('payment-outcome-section');
    const paymentStatusDisplay = document.getElementById('payment-status-display');
    const qrCodeImage = document.getElementById('qrCodeImage');
    const participationList = document.getElementById('participation-list');
    const refreshParticipationsBtn = document.getElementById('refresh-participations');
    const currentParticipationSection = document.getElementById('current-participation-list'); // Corrected
    const addParticipationSection = document.getElementById('add-participation-section');
    const eventTilesContainer = document.getElementById('event-tiles-container');

    // NEW: Logout Button element
    const ersLogoutBtn = document.getElementById('ersLogoutBtn');


    let currentCalculatedPrice = 0;
    let currentParticipationId = null;
    let currentUserId = parseInt(userIdInput.value); // Ensure it's parsed once on load
    let currentEventId = parseInt(eventIdInput.value); // Ensure it's parsed once on load

    // Helper to get form data
    function getParticipationFormData() {
        return {
            user_id: parseInt(userIdInput.value),
            event_id: parseInt(eventIdInput.value),
            num_tickets: parseInt(numTicketsInput.value),
            veg_heads: parseInt(vegHeadsInput.value),
            non_veg_heads: parseInt(nonVegHeadsInput.value),
            additional_contribution: parseFloat(additionalContributionInput.value || 0),
            tower: towerNumberInput.value,
            flat_no: flatNumberInput.value.trim()
        };
    }

    // Function to display user information
    function displayUserInfo(userInfo) {
        // Corrected reference to currentParticipationSection from HTML for insertBefore
        let userInfoDiv = document.getElementById('user-info-display');
        if (!userInfoDiv) { 
            userInfoDiv = document.createElement('div');
            userInfoDiv.id = 'user-info-display';
            // Ensure 'current-participation-list' is the correct parent if it's there,
            // otherwise attach to 'current-participation' or a general container.
            // Based on latest HTML, 'current-participation-list' is the parent for 'participation-list'
            // and 'user-info-display' is a separate section.
            // Let's assume user-info-display is always there or you want to append to a main container.
            // For now, let's keep it simple if it's a fixed div in HTML, no append needed.
        }
        userInfoDiv.innerHTML = `
            <h3>User Details:</h3>
            <p><strong>Username:</strong> ${userInfo.username || 'N/A'}</p>
            <p><strong>ID:</strong> ${userInfo.id || 'N/A'}</p>
            <p><strong>Email:</strong> ${userInfo.email || 'N/A'}</p>
            <p><strong>Phone:</strong> ${userInfo.phone_number || 'N/A'}</p>
        `;
    }

    // Function to display event information as an appealing tile
    function displayEventInfo(eventInfo) {
        eventTilesContainer.innerHTML = ''; 

        const eventTile = document.createElement('div');
        eventTile.classList.add('event-tile'); 

        // Build food charges display dynamically
        let foodChargesHtml = '';
        if (eventInfo.veg_food_charges && eventInfo.veg_food_charges > 0) {
            foodChargesHtml += `<p><strong>Veg Food Charges:</strong> INR ${(eventInfo.veg_food_charges || 0).toFixed(2)} (${eventInfo.veg_food_charges_type || 'N/A'})</p>`;
        }
        if (eventInfo.non_veg_food_charges && eventInfo.non_veg_food_charges > 0) {
            foodChargesHtml += `<p><strong>Non-Veg Food Charges:</strong> INR ${(eventInfo.non_veg_food_charges || 0).toFixed(2)} (${eventInfo.non_veg_food_charges_type || 'N/A'})</p>`;
        }
        if (foodChargesHtml === '') {
            foodChargesHtml = '<p><strong>Food Charges:</strong> Not applicable</p>';
        }

        eventTile.innerHTML = `
            <div class="event-header">
                <h3>${eventInfo.name || 'N/A'}</h3>
                <span class="event-id">ID: ${eventInfo.id || 'N/A'}</span>
            </div>
            <div class="event-body">
                <p><strong>Date:</strong> ${eventInfo.close_date || 'N/A'} at ${eventInfo.time || 'N/A'}</p>
                <p><strong>Venue:</strong> ${eventInfo.venue || 'N/A'}</p>
                <p class="event-details-text"><strong>Details:</strong> ${eventInfo.details || 'N/A'}</p>
            </div>
            <div class="event-footer">
                <p><strong>Cover Charges:</strong> INR ${(eventInfo.cover_charges || 0).toFixed(2)} (${eventInfo.cover_charges_type || 'N/A'})</p>
                ${foodChargesHtml}
                <div class="event-actions">
                    <button class="start-edit-participation-btn" data-event-id="${eventInfo.id}">Start/Edit Participation</button>
                    <button class="contribute-btn" data-event-id="${eventInfo.id}">Contribute</button>
                </div>
            </div>
        `;
        eventTilesContainer.appendChild(eventTile);

        // Add event listeners for the new buttons
        eventTile.querySelector('.start-edit-participation-btn').addEventListener('click', async () => {
            eventIdInput.value = eventInfo.id; // Update event ID in form
            // Ensure userIdInput.value is used, as it might be dynamically set by Flask
            const userIdForLookup = parseInt(userIdInput.value); 
            const eventIdForLookup = parseInt(eventInfo.id);
            
            console.log(`Start/Edit button clicked for User ID: ${userIdForLookup}, Event ID: ${eventIdForLookup}`);

            // Explicitly make the section visible
            addParticipationSection.style.display = 'block'; 
            console.log("addParticipationSection display set to 'block'.");

            // Attempt to pre-fill form if an existing participation exists for this user/event
            await loadExistingParticipationForEdit(userIdForLookup, eventIdForLookup);
            addParticipationSection.scrollIntoView({ behavior: 'smooth' });
            clearFormResults();
        });

        eventTile.querySelector('.contribute-btn').addEventListener('click', () => {
            eventIdInput.value = eventInfo.id;
            additionalContributionInput.focus();
            // Explicitly make the section visible
            addParticipationSection.style.display = 'block'; 
            addParticipationSection.scrollIntoView({ behavior: 'smooth' });
            clearFormResults();
            alert("Redirecting to simulated payment page for additional contribution...");
        });
    }

    function clearFormResults() {
        priceCalculationResult.innerHTML = '';
        paymentOutcomeSection.style.display = 'none';
        paymentStatusDisplay.innerHTML = '';
        qrCodeImage.style.display = 'none';
    }

    // Function to load existing participation data into the form for editing
    // NOW USES THE NEW ERS_CHECK_PARTICIPATION_API ENDPOINT
    async function loadExistingParticipationForEdit(userId, eventId) {
        console.log(`Inside loadExistingParticipationForEdit. Checking for User ID: ${userId}, Event ID: ${eventId}`);
        try {
            // Call the new ERS check_participation endpoint
            // console print the API URL and parameters for debugging
            const checkUrl = `${API_CONFIG.ERS_CHECK_PARTICIPATION_API}?user_id=${userId}&event_id=${eventId}`;
            console.log(`Calling ERS_CHECK_PARTICIPATION_API: ${checkUrl}`);
            const response = await fetch(checkUrl, { 
                method: 'GET', 
                referrerPolicy: 'unsafe-url' 
            }); 
            console.log("Check Participation API response status:", response.status, response.statusText);
            
            if (!response.ok) {
                if (response.status === 404) {
                    console.log("Backend confirmed: No existing participation found for this user and event. Resetting form for new entry.");
                    resetParticipationForm();
                    currentParticipationId = null;
                    return; // Exit, as it's a new entry
                }
                // For other non-OK statuses, try to parse error data
                const errorData = await response.json().catch(() => ({ error: "Unknown error, could not parse response." }));
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            
            // If response is OK (200), an existing participation was found
            const existingParticipation = await response.json();
            console.log("Existing participation found (from ERS_CHECK_PARTICIPATION_API):", existingParticipation);

            // Pre-fill the form with existing data
            currentParticipationId = existingParticipation.id;
            userIdInput.value = existingParticipation.user_id || userId; // Keep current user ID if backend doesn't provide
            eventIdInput.value = existingParticipation.event_id || eventId; // Keep current event ID if backend doesn't provide
            numTicketsInput.value = existingParticipation.num_tickets || 1;
            vegHeadsInput.value = existingParticipation.veg_heads || 0;
            nonVegHeadsInput.value = existingParticipation.non_veg_heads || 0;
            additionalContributionInput.value = existingParticipation.additional_contribution || 0;
            towerNumberInput.value = existingParticipation.tower || '';
            flatNumberInput.value = existingParticipation.flat_no || '';
            console.log("Form pre-filled with existing participation data.");

        } catch (error) {
            console.error('Error in loadExistingParticipationForEdit catch block (via ERS_CHECK_PARTICIPATION_API):', error);
            resetParticipationForm();
            currentParticipationId = null;
            // Provide a more user-friendly message based on the error
            alert(`Failed to check for existing participation: ${error.message}. Please try again. If the issue persists, check server logs.`);
        }
    }

    function resetParticipationForm() {
        // Keep userId and eventId as they are context for the form
        // (they are set from URL params or default in Flask, and should persist)
        numTicketsInput.value = '1';
        vegHeadsInput.value = '0';
        nonVegHeadsInput.value = '0';
        additionalContributionInput.value = '0';
        towerNumberInput.value = '';
        flatNumberInput.value = '';
        currentParticipationId = null; // Clear current participation ID
        clearFormResults();
    }


    // Function to fetch initial app data (User, Event)
    async function initializeAppData() {
        displayUserInfo(INITIAL_USER_DATA);
        displayEventInfo(INITIAL_EVENT_DATA);
        fetchParticipations(); // Always load participations on init
    }

    // Function to fetch and display current participations
    async function fetchParticipations() {
        participationList.innerHTML = '<p>Loading participations...</p>';
        try {
            const response = await fetch(API_CONFIG.PART_API, { method: 'GET', referrerPolicy: 'unsafe-url' });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const participations = await response.json();

            // Filter client-side for the current user's participations
            // Ensure currentUserId is correctly parsed from userIdInput on initial load.
            const userParticipations = participations.filter(part => part.user_id == currentUserId);

            if (userParticipations.length === 0) {
                participationList.innerHTML = '<p>No current participations found for this user.</p>';
                return;
            }

            participationList.innerHTML = '';
            userParticipations.forEach(part => {
                const div = document.createElement('div');
                div.classList.add('participation-item');
                div.innerHTML = `
                    <p><strong>ID:</strong> ${part.id || 'N/A'}</p>
                    <p><strong>User:</strong> ${part.user_name || 'N/A'} (ID: ${part.user_id || 'N/A'})</p>
                    <p><strong>Contact:</strong> ${part.phone_number || 'N/A'} / ${part.email_id || 'N/A'}</p>
                    <p><strong>Event:</strong> ${part.event_id || 'N/A'} (Date: ${part.event_date || 'N/A'})</p>
                    <p><strong>Address:</strong> Tower ${part.tower || 'N/A'}, Flat ${part.flat_no || 'N/A'}</p>
                    <p><strong>Total Payable:</strong> INR ${(part.total_payable || 0).toFixed(2)}</p>
                    <p><strong>Amount Paid:</strong> INR ${(part.amount_paid || 0).toFixed(2)}</p>
                    <p><strong>Remaining Payment:</strong> INR ${(part.payment_remaining || 0).toFixed(2)}</p>
                    <p><strong>Add. Contribution:</strong> INR ${(part.additional_contribution || 0).toFixed(2)}</p>
                    <p><strong>Comments:</strong> ${part.contribution_comments || 'None'}</p>
                    <p><strong>Attendees (V/NV):</strong> ${part.veg_heads || 0} / ${part.non_veg_heads || 0}</p>
                    <p><strong>Status:</strong> ${part.status || 'N/A'}</p>
                    <p><strong>Transaction ID:</strong> ${part.transaction_id || 'N/A'}</p>
                    <p><strong>Registered At:</strong> ${part.registered_at ? new Date(part.registered_at).toLocaleString() : 'N/A'}</p>
                    <p><strong>Last Updated:</strong> ${part.updated_at ? new Date(part.updated_at).toLocaleString() : 'N/A'}</p>
                    <div class="participation-item-actions">
                        <button class="edit-item-btn" data-participation-id="${part.id}">Edit</button>
                        <button class="delete-item-btn" data-participation-id="${part.id}" style="background-color: #dc3545;">Delete</button>
                    </div>
                `;
                participationList.appendChild(div);
            });

            // Add event listeners for edit/delete buttons on each participation item
            document.querySelectorAll('.edit-item-btn').forEach(button => {
                button.addEventListener('click', async (event) => {
                    const participationId = event.target.dataset.participationId;
                    console.log(`Editing participation ID: ${participationId}`);
                    // Fetch full details of this specific participation and pre-fill the form
                    await fetchParticipationAndPreFillForm(participationId);
                    addParticipationSection.scrollIntoView({ behavior: 'smooth' });
                });
            });

            document.querySelectorAll('.delete-item-btn').forEach(button => {
                button.addEventListener('click', async (event) => {
                    const participationId = event.target.dataset.participationId;
                    console.log(`Deleting participation ID: ${participationId}`);
                    if (confirm(`Are you sure you want to delete participation ID ${participationId}?`)) {
                        await deleteParticipation(participationId);
                    }
                });
            });

        }
        catch (error) {
            console.error('Error fetching participations:', error);
            participationList.innerHTML = `<p class="error-message">Error loading participations: ${error.message}. Please ensure the Part API is running and accessible via Nginx at ${API_CONFIG.PART_API}.</p>`;
        }
    }

    // Function to fetch a single participation and pre-fill the form
    // This is called when "Edit" is clicked on an already listed participation
    async function fetchParticipationAndPreFillForm(participationId) {
        console.log(`Fetching participation ID ${participationId} for pre-fill.`);
        try {
            // Explicitly make the section visible when editing an existing item
            addParticipationSection.style.display = 'block'; 
            console.log("addParticipationSection display set to 'block' for edit.");

            const response = await fetch(`${API_CONFIG.PART_API}/${participationId}`, { method: 'GET', referrerPolicy: 'unsafe-url' });
            if (!response.ok) {
                // Try to get error message from response if available
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }
            const partDetails = await response.json();
            
            // Set currentParticipationId for subsequent updates
            currentParticipationId = partDetails.id;

            userIdInput.value = partDetails.user_id || INITIAL_USER_DATA.id; // Keep current user ID if backend doesn't provide
            eventIdInput.value = partDetails.event_id || INITIAL_EVENT_DATA.id; // Keep current event ID if backend doesn't provide
            numTicketsInput.value = partDetails.num_tickets || 1;
            vegHeadsInput.value = partDetails.veg_heads || 0;
            nonVegHeadsInput.value = partDetails.non_veg_heads || 0;
            additionalContributionInput.value = partDetails.additional_contribution || 0;
            towerNumberInput.value = partDetails.tower || '';
            flatNumberInput.value = partDetails.flat_no || '';

            // Also, fetch current calculated price if necessary for display
            calculatePriceBtn.click(); // Simulate click to get updated price
            clearFormResults(); // Clear previous payment status if any

            console.log(`Form pre-filled for participation ID ${participationId}:`, partDetails);
        } catch (error) {
            console.error(`Error fetching participation ${participationId} for edit:`, error);
            alert(`Could not load participation for editing: ${error.message}`);
            resetParticipationForm(); // Clear form on error
        }
    }


    // Step 1: Calculate Price
    calculatePriceBtn.addEventListener('click', async () => {
        const formData = getParticipationFormData();

        // Check for valid numeric inputs (non-negative)
        if (isNaN(formData.num_tickets) || formData.num_tickets < 0 || 
            isNaN(formData.veg_heads) || formData.veg_heads < 0 || 
            isNaN(formData.non_veg_heads) || formData.non_veg_heads < 0 ||
            isNaN(formData.additional_contribution) || formData.additional_contribution < 0) { // Added check for additional_contribution
            
            priceCalculationResult.innerHTML = '<p class="error-message">Please enter valid numeric values for all attendee counts, tickets, and contribution (non-negative).</p>';
            clearFormResults();
            return;
        }

        // Removed the specific validation that prevented numTickets from being 0 if there were attendees.
        // The backend calculation will handle costs based on 0 tickets and/or positive attendees.

        try {
            const response = await fetch(API_CONFIG.ERS_CALCULATE_PRICE_API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
                referrerPolicy: 'unsafe-url'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            currentCalculatedPrice = data.calculated_price;

            // Dynamically build food charges display for the calculation result
            let foodCalculationResultHtml = '';
            if (data.veg_food_charges > 0) {
                foodCalculationResultHtml += `<p>Veg Food Charges: INR ${data.veg_food_charges.toFixed(2)} (${data.veg_food_charges_type})</p>`;
            }
            if (data.non_veg_food_charges > 0) {
                foodCalculationResultHtml += `<p>Non-Veg Food Charges: INR ${data.non_veg_food_charges.toFixed(2)} (${data.non_veg_food_charges_type})</p>`;
            }
            if (foodCalculationResultHtml === '') {
                foodCalculationResultHtml = '<p>Food Charges: Not applicable</p>';
            }

            priceCalculationResult.innerHTML = `
                <p><strong>Calculated Total Price:</strong> INR ${currentCalculatedPrice.toFixed(2)}</p>
                <p>Cover Charges: INR ${data.cover_charges.toFixed(2)} (${data.cover_charges_type})</p>
                ${foodCalculationResultHtml}
                ${data.warning ? `<p class="error-message">Warning: ${data.warning}</p>` : ''}
            `;
            // Do not show payment section here, only display calculated price
            paymentOutcomeSection.style.display = 'none'; // Ensure payment section is hidden until submit
        } catch (error) {
            console.error('Error calculating price:', error);
            priceCalculationResult.innerHTML = `<p class="error-message">Error calculating price: ${error.message}. Please ensure the ERS backend is running and accessible via Nginx at ${API_CONFIG.ERS_CALCULATE_PRICE_API}.</p>`;
            clearFormResults();
        }
    });

    // Step 2: Submit for Payment / Update Participation
    submitParticipationBtn.addEventListener('click', async () => {
        const formData = getParticipationFormData();
        
        if (!formData.tower || !formData.flat_no) {
            alert('Please select Tower Number and enter Flat Number.');
            return;
        }

        if (currentParticipationId) {
            // EDIT EXISTING PARTICIPATION
            try {
                const response = await fetch(API_CONFIG.ERS_EDIT_PARTICIPATION_API, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id: currentParticipationId, // Pass the ID for update
                        ...formData // All other form data
                    }),
                    referrerPolicy: 'unsafe-url'
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                paymentOutcomeSection.style.display = 'block';
                paymentStatusDisplay.innerHTML = `
                    <p><strong>Participation Updated!</strong></p>
                    <p>${data.message}</p>
                    <pre>${JSON.stringify(data.participation_details, null, 2)}</pre>
                `;
                qrCodeImage.style.display = 'none'; // QR not relevant for just an update
                fetchParticipations(); // Refresh list to show updated entry
                // Optionally reset the form after update
                resetParticipationForm();

            } catch (error) {
                console.error('Error updating participation:', error);
                paymentOutcomeSection.style.display = 'block';
                paymentStatusDisplay.innerHTML = `<p class="error-message">Error updating participation: ${error.message}.</p>`;
                qrCodeImage.style.display = 'none';
            }

        } else {
            // START NEW PARTICIPATION (and then simulate payment redirection)
            try {
                const response = await fetch(API_CONFIG.ERS_START_PARTICIPATION_API, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData),
                    referrerPolicy: 'unsafe-url'
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                currentParticipationId = data.participation_id; // Store new ID
                paymentOutcomeSection.style.display = 'block';
                paymentStatusDisplay.innerHTML = `
                    <p><strong>New Participation Created!</strong></p>
                    <p>${data.message}</p>
                    <p>Participation ID: ${currentParticipationId}</p>
                    <pre>${JSON.stringify(data.participation_details, null, 2)}</pre>
                `;
                
                // Simulate redirection to payment microservice
                alert(`Redirecting to payment for Participation ID: ${currentParticipationId} for INR ${data.participation_details.total_payable.toFixed(2)}`);

                // For this simulation, we'll immediately "confirm" after the alert
                await simulatePaymentConfirmation(currentParticipationId);
                
                resetParticipationForm(); // Reset form after successful submission
                fetchParticipations(); // Refresh the list to show the newly added/confirmed participation

            } catch (error) {
                console.error('Error starting new participation:', error);
                paymentOutcomeSection.style.display = 'block';
                paymentStatusDisplay.innerHTML = `<p class="error-message">Error starting participation: ${error.message}.</p>`;
                qrCodeImage.style.display = 'none';
            }
        }
    });

    // Simulated payment confirmation (this would be a backend callback normally)
    async function simulatePaymentConfirmation(participationId) {
        console.log(`Simulating payment confirmation for participation ID: ${participationId}`);
        try {
            const response = await fetch(API_CONFIG.ERS_PAYMENT_CALLBACK_API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    participation_id: participationId,
                    payment_status: 'success', // or 'failed'
                    transaction_id: `TXN_${Date.now()}` // Simulated transaction ID
                }),
                referrerPolicy: 'unsafe-url'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("Simulated Payment Callback Result:", data);
            paymentStatusDisplay.innerHTML += `<p class="success-message">Payment Confirmed by Callback: ${data.message}</p>`;
            qrCodeImage.style.display = 'block'; // Show QR after simulated payment confirmation
            fetchParticipations(); // Refresh list to show status change
        } catch (error) {
            console.error('Error during simulated payment confirmation:', error);
            paymentStatusDisplay.innerHTML += `<p class="error-message">Simulated Payment Confirmation Failed: ${error.message}</p>`;
            qrCodeImage.style.display = 'none';
        }
    }

    // Delete Participation
    async function deleteParticipation(participationId) {
        try {
            const response = await fetch(`${API_CONFIG.ERS_DELETE_PARTICIPATION_API}/${participationId}`, {
                method: 'DELETE',
                referrerPolicy: 'unsafe-url'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            alert(data.message);
            fetchParticipations(); // Refresh list after deletion
            resetParticipationForm(); // Clear form if current participation was deleted
        } catch (error) {
            console.error('Error deleting participation:', error);
            alert(`Failed to delete participation: ${error.message}`);
        }
    }

    // Add event listener for the new logout button
    if (ersLogoutBtn) {
        ersLogoutBtn.addEventListener('click', () => {
            console.log("Logout button clicked in ERS portal.");
            // Redirect to the User Portal's main page for the current user
            // Assuming currentUserId is available and correct from the Flask injection ..redirecting to main page
            const userPortalRedirectUrl = `${USER_PORTAL_ROOT_URL_JS}/portal/${currentUserId}`;
            console.log("Redirecting to:", userPortalRedirectUrl);
            window.location.href = userPortalRedirectUrl;
        });
    }

    initializeAppData(); // Call this once DOM is loaded

    refreshParticipationsBtn.addEventListener('click', fetchParticipations);

}); // End DOMContentLoaded