document.addEventListener('DOMContentLoaded', () => {
    const eventForm = document.getElementById('eventForm');
    const formMessage = document.getElementById('formMessage');
    const eventsList = document.getElementById('eventsList');
    const noEventsMessage = document.getElementById('noEventsMessage');
    const refreshEventsButton = document.getElementById('refreshEvents');

    // CRITICAL: Read the API base URL from the global JavaScript constant injected by Flask
    const EVENT_API_BASE_URL = EVENT_API_BASE_URL_JS; 

    // Function to display messages
    const displayMessage = (message, type) => {
        formMessage.textContent = message;
        formMessage.className = `message ${type}`;
        setTimeout(() => {
            formMessage.textContent = '';
            formMessage.className = 'message';
        }, 3000);
    };

    // Function to fetch and display events
    const fetchEvents = async () => {
        try {
            // CRITICAL: Use the dynamic EVENT_API_BASE_URL for the GET /events API call
            // This should result in /events/events or /events if base is ""
            const response = await fetch(`${EVENT_API_BASE_URL}/events`); 
            const data = await response.json(); 

            eventsList.innerHTML = ''; // Clear existing events
            if (response.ok && Array.isArray(data) && data.length > 0) {
                noEventsMessage.style.display = 'none';
                data.forEach(event => {
                    const eventCard = document.createElement('div');
                    eventCard.className = 'event-card';

                    // Prepare food charges display string
                    let foodChargesDisplay = '';
                    if (event.food) {
                        // Display Veg Food Charges if greater than 0
                        if (event.food.vegFoodCharges > 0) {
                            foodChargesDisplay += `
                                <p><strong>Veg Food Charges:</strong> INR ${event.food.vegFoodCharges.toFixed(2)} (${event.food.vegFoodChargesType.replace('_', ' ')})</p>
                            `;
                        }
                        // Display Non-Veg Food Charges if greater than 0
                        if (event.food.nonVegFoodCharges > 0) {
                            foodChargesDisplay += `
                                <p><strong>Non-Veg Food Charges:</strong> INR ${event.food.nonVegFoodCharges.toFixed(2)} (${event.food.nonVegFoodChargesType.replace('_', ' ')})</p>
                            `;
                        }
                    }

                    eventCard.innerHTML = `
                        <h3>${event.name}</h3>
                        ${event.photo_url ? `<img src="${event.photo_url}" alt="${event.name}" style="max-width: 100%; height: auto; border-radius: 4px; margin-bottom: 10px;">` : ''}
                        <p><strong>Date & Time:</strong> ${new Date(event.time).toLocaleString()}</p>
                        <p><strong>Close Date:</strong> ${new Date(event.close_date).toLocaleString()}</p>
                        <p><strong>Venue:</strong> ${event.venue}</p>
                        <p><strong>Details:</strong> ${event.details}</p>
                        <p><strong>Cover Charges:</strong> INR ${event.subscription.coverCharges.toFixed(2)} (${event.subscription.coverChargesType.replace('_', ' ')})</p>
                        ${foodChargesDisplay}
                    `;
                    eventsList.appendChild(eventCard);
                });
            } else if (response.ok && data.message === "No events found") {
                noEventsMessage.style.display = 'block';
            } else {
                displayMessage(`Error fetching events: ${data.error || 'Unknown error'}`, 'error');
                noEventsMessage.style.display = 'block';
            }
        } catch (error) {
            console.error('Error fetching events:', error);
            if (error instanceof SyntaxError && error.message.includes('Unexpected token')) {
                displayMessage('Failed to fetch events. Received unexpected response (not JSON). Check console for details.', 'error');
            } else {
                displayMessage('Failed to fetch events. Please try again.', 'error');
            }
            noEventsMessage.style.display = 'block';
        }
    };

    // Handle form submission
    eventForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(eventForm);

        // Ensure numerical values are parsed correctly
        if (formData.has('coverCharges')) {
            formData.set('coverCharges', parseFloat(formData.get('coverCharges')));
        }
        // Updated to handle vegFoodCharges
        if (formData.has('vegFoodCharges')) {
            formData.set('vegFoodCharges', parseFloat(formData.get('vegFoodCharges')));
        }
        // Added for nonVegFoodCharges
        if (formData.has('nonVegFoodCharges')) {
            formData.set('nonVegFoodCharges', parseFloat(formData.get('nonVegFoodCharges')));
        }
        
        const photoFile = formData.get('photo');
        if (photoFile && photoFile.size === 0) {
            formData.delete('photo');
        }

        try {
            // CRITICAL: Use the dynamic EVENT_API_BASE_URL for the POST /events API call
            // This should result in /events/events
            const response = await fetch(`${EVENT_API_BASE_URL}/events`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                displayMessage('Event created successfully!', 'success');
                eventForm.reset();
                fetchEvents();
            } else {
                displayMessage(`Error: ${data.error || 'Failed to create event'}`, 'error');
            }
        } catch (error) {
            console.error('Error creating event:', error);
            if (error instanceof SyntaxError && error.message.includes('Unexpected token')) {
                displayMessage('Failed to create event. Received unexpected response (not JSON). Check console for details.', 'error');
            } else {
                displayMessage('Failed to create event. Please check your network.', 'error');
            }
        }
    });

    // Handle refresh button click
    refreshEventsButton.addEventListener('click', fetchEvents);

    // Initial load of events when the page loads
    fetchEvents();
});