// Ensure this script runs only after the entire HTML document has been loaded and parsed.
document.addEventListener('DOMContentLoaded', function () {
    // --- Global Configuration (Injected from Flask) ---
    const AUTH_SERVICE_EXTERNAL_URL = AUTH_SERVICE_EXTERNAL_URL_JS;
    console.log('DEBUG (Global): AUTH_SERVICE_EXTERNAL_URL_JS:', AUTH_SERVICE_EXTERNAL_URL);

    const adminPortalApiBaseUrl = window.location.pathname.startsWith('/admin-portal') ? '/admin-portal' : '';
    console.log('DEBUG (Global): adminPortalApiBaseUrl:', adminPortalApiBaseUrl);

    let currentCalendarDate = new Date();

    // --- Global Data Stores ---
    let allUsersData = [];
    console.log('DEBUG (Global): allUsersData initialized as empty array.');

    // --- Lucide Icons Initialization ---
    function initLucideIcons() {
        if (typeof lucide !== 'undefined' && typeof lucide.createIcons === 'function') {
            lucide.createIcons();
            console.log('DEBUG: Lucide icons initialized.');
        } else {
            console.warn("WARNING: Lucide icons library not found or createIcons method is missing. Icons may not render.");
        }
    }
    initLucideIcons();

    // --- DOM Element References ---
    const sidebar = document.querySelector('aside');
    const menuButton = document.getElementById('menu-button');
    let sidebarOverlay = document.getElementById('sidebar-overlay');

    console.log("DEBUG: Sidebar element found:", !!sidebar, sidebar);
    console.log("DEBUG: Menu button element found:", !!menuButton, menuButton);
    console.log("DEBUG: Sidebar overlay element found:", !!sidebarOverlay, sidebarOverlay);


    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const pageSections = document.querySelectorAll('.page-section');
    const pageTitle = document.getElementById('pageTitle');
    const createEventForm = document.getElementById('createEventForm');
    const cancelCreateEventButton = document.getElementById('cancelCreateEvent');
    const addNewEventFromManageButton = document.getElementById('addNewEventButton');

    const messageBoxEl = document.getElementById('messageBox');
    const messageTextEl = document.getElementById('messageText');
    const messageIconEl = document.getElementById('messageIcon');

    const navDashboard = document.getElementById('navDashboard');

    const manageEventsTableBody = document.getElementById('manageEventsTableBody');
    const overallUsersTableBody = document.getElementById('overallUsersTableBody');
    const userSearchInput = document.getElementById('userSearchInput');

    // Calendar Specific References
    const calendarGrid = document.getElementById('calendarGrid');
    const calendarMonthYear = document.getElementById('calendarMonthYear');
    const calendarPrevMonth = document.getElementById('calendarPrevMonth');
    // CRITICAL FIX: Corrected typo in calendarNextMonth assignment
    const calendarNextMonth = document.getElementById('calendarNextMonth'); 


    // Console logs for calendar buttons
    console.log("DEBUG: Calendar Prev Month button found:", !!calendarPrevMonth, calendarPrevMonth);
    console.log("DEBUG: Calendar Next Month button found:", !!calendarNextMonth, calendarNextMonth);


    const selectEventForRegistrants = document.getElementById('selectEventForRegistrants');
    const eventRegistrantsTableBody = document.getElementById('eventRegistrantsTableBody');
    const participationSearchInput = document.getElementById('participationSearchInput');

    // Dashboard stat elements
    let totalEventsCountEl = document.getElementById('totalEventsCount');
    let totalUsersCountEl = document.getElementById('totalUsersCount');
    let upcomingEventsCountEl = document.getElementById('upcomingEventsCount');
    let totalParticipantsCountEl = document.getElementById('totalParticipantsCount');

    const downloadCsvButton = document.getElementById('downloadCsvButton');


    // If the sidebar overlay doesn't exist in HTML, create it dynamically.
    if (!sidebarOverlay) {
        console.log("DEBUG: Sidebar overlay not found, creating dynamically.");
        sidebarOverlay = document.createElement('div');
        sidebarOverlay.id = 'sidebar-overlay';
        sidebarOverlay.className = 'fixed inset-0 bg-black/60 z-30 hidden md:hidden'; // Tailwind 'hidden' by default
        document.body.appendChild(sidebarOverlay);
    } else {
        console.log("DEBUG: Sidebar overlay found in HTML.");
    }


    // --- Toast Message Function ---
    let toastTimeout;
    function showToast(type, message, duration = 3000) {
        console.log(`DEBUG (Toast): Showing toast - Type: ${type}, Message: "${message}", Duration: ${duration}ms`);
        if (!messageBoxEl || !messageTextEl || !messageIconEl) {
            console.warn("WARNING: Message box elements (messageBox, messageText, messageIcon) not found. Toast cannot be shown.");
            return;
        }

        messageTextEl.textContent = message;
        messageBoxEl.className = 'message-box';
        messageBoxEl.classList.add(type);

        let iconName = 'info';
        if (type === 'success') iconName = 'check-circle';
        if (type === 'error') iconName = 'alert-circle';

        messageIconEl.innerHTML = '';
        const newIconElement = document.createElement('i');
        newIconElement.setAttribute('data-lucide', iconName);
        messageIconEl.appendChild(newIconElement);
        initLucideIcons();

        messageBoxEl.classList.add('show');
        clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {
            messageBoxEl.classList.remove('show');
            console.log("DEBUG (Toast): Toast hidden after timeout.");
        }, duration);
    }

    // --- API Helper Function ---
    async function apiRequest(endpoint, method = 'GET', body = null) {
        const url = `${adminPortalApiBaseUrl}${endpoint}`;
        console.log(`DEBUG (API): Sending ${method} request to: ${url}`);

        const options = {
            method,
            headers: {}
        };

        if (body && method !== 'GET' && method !== 'HEAD') {
            if (body instanceof FormData) {
                options.body = body;
                console.log("DEBUG (API): Request body is FormData.");
            } else {
                options.headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(body);
                console.log("DEBUG (API): Request body is JSON:", body);
            }
        }

        try {
            const response = await fetch(url, options);
            console.log(`DEBUG (API): Received response for ${url}. Status: ${response.status}`);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: "Unknown server error", details: response.statusText }));
                console.error(`ERROR (API): API Call Failed for ${url}. Status: ${response.status}, Details:`, errorData);
                throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
            }

            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                console.log("DEBUG (API): Response is JSON.");
                return await response.json();
            }
            console.log("DEBUG (API): Response is not JSON, returning as text.");
            return await response.text();
        } catch (error) {
            console.error('ERROR (API): API Request Exception:', error);
            showToast('error', `API Request Failed: ${error.message}`);
            throw error;
        }
    }


    // --- Event Management Functions ---
    async function fetchAllEvents() {
        console.log("DEBUG (Events): Fetching all events for calendar and management table...");
        try {
            const events = await apiRequest('/api/events', 'GET');
            console.log("DEBUG (Events): Received events from API:", events);
            if (Array.isArray(events)) {
                renderCalendar(currentCalendarDate, events);
                populateManageEventsTable(events);
                populateEventDropdownForRegistrants(events);
            } else {
                showToast('error', 'Received invalid event data format from service.');
                renderCalendar(currentCalendarDate, []);
                populateManageEventsTable([]);
            }
        } catch (error) {
            console.error("ERROR (Events): Failed to fetch all events.", error);
            renderCalendar(currentCalendarDate, []);
            populateManageEventsTable([]);
        }
    }

    function populateManageEventsTable(events) {
        console.log("DEBUG (Events): Populating manage events table with", events.length, "events.");
        if (!manageEventsTableBody) {
            console.warn("WARNING: manageEventsTableBody element not found.");
            return;
        }
        manageEventsTableBody.innerHTML = '';

        const tableHead = document.querySelector('#manage-eventsView table thead tr');
        if (tableHead) {
            tableHead.innerHTML = `
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Event Name</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date & Time</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Close Date</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cover Charges (Type)</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Veg Food (Type)</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Non-Veg Food (Type)</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            `;
        }

        if (!events || events.length === 0) {
            manageEventsTableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">No events found.</td></tr>';
            console.log("DEBUG (Events): No events to display in management table.");
            return;
        }

        events.sort((a, b) => new Date(b.time || b.eventDateTime) - new Date(a.time || a.eventDateTime));

        events.forEach(event => {
            const eventName = event.name || 'Unnamed Event';
            const eventDateTimeStr = event.time || 'N/A';
            const closeDateStr = event.close_date || 'N/A';
            const eventLocation = event.venue || 'N/A';

            const coverCharges = event.subscription?.coverCharges ?? event.coverCharges ?? 0.0;
            const coverChargesType = event.subscription?.coverChargesType || 'per_head';
            
            const vegFoodCharges = event.food?.vegFoodCharges ?? 0.0;
            const vegFoodChargesType = event.food?.vegFoodChargesType || 'per_head';

            const nonVegFoodCharges = event.food?.nonVegFoodCharges ?? 0.0;
            const nonVegFoodChargesType = event.food?.nonVegFoodChargesType || 'per_head';

            let formattedDateTime = 'N/A';
            try {
                if (eventDateTimeStr !== 'N/A') {
                    formattedDateTime = new Date(eventDateTimeStr).toLocaleString([], {
                        year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                    });
                }
            } catch (e) {
                console.warn("WARNING: Could not format event date for event:", eventName, e);
            }

            let formattedCloseDate = 'N/A';
            try {
                if (closeDateStr !== 'N/A') {
                    if (closeDateStr.includes('T')) {
                        formattedCloseDate = new Date(closeDateStr).toLocaleString([], {
                            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                        });
                    } else {
                        formattedCloseDate = new Date(closeDateStr).toLocaleDateString([], {
                            year: 'numeric', month: 'short', day: 'numeric'
                        });
                    }
                }
            } catch (e) {
                console.warn("WARNING: Could not format close date for event:", eventName, e);
            }

            const row = `
                <tr data-event-id="${event.id}">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${eventName}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formattedDateTime}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formattedCloseDate}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${eventLocation}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">INR ${coverCharges.toFixed(2)} (${coverChargesType.replace('_', ' ')})</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">INR ${vegFoodCharges.toFixed(2)} (${vegFoodChargesType.replace('_', ' ')})</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">INR ${nonVegFoodCharges.toFixed(2)} (${nonVegFoodChargesType.replace('_', ' ')})</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                        <button class="btn btn-icon text-blue-600 hover:text-blue-800 edit-event-btn" title="Edit (Not Implemented)"><i data-lucide="edit"></i></button>
                        <button class="btn btn-icon text-red-600 hover:text-red-800 delete-event-btn" data-event-id="${event.id}" title="Delete Event"><i data-lucide="trash-2"></i></button>
                    </td>
                </tr>
            `;
            manageEventsTableBody.insertAdjacentHTML('beforeend', row);
        });
        initLucideIcons();

        document.querySelectorAll('.delete-event-btn').forEach(button => {
            button.addEventListener('click', async function() {
                const eventId = this.dataset.eventId;
                if (confirm(`Are you sure you want to delete event ID: ${eventId}? This action cannot be undone.`)) {
                    console.log(`DEBUG (Events): Deleting event ID: ${eventId}`);
                    try {
                        const result = await apiRequest(`/api/events/${eventId}`, 'DELETE');
                        showToast('success', `Event ID ${eventId} deleted successfully!`);
                        fetchAllEvents();
                    } catch (error) {
                        console.error('ERROR (Events): Failed to delete event:', error);
                        showToast('error', `Failed to delete event: ${error.message}`);
                    }
                }
            });
        });
    }

    if (createEventForm) {
        createEventForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            console.log("DEBUG (Events): Create Event form submitted.");

            const formData = new FormData(this);
            const dataToForward = new FormData();

            dataToForward.append('name', formData.get('eventName'));
            dataToForward.append('time', `${formData.get('eventDate')}T${formData.get('eventTime')}:00`);

            let closeDate = formData.get('eventRegistrationCloseDate');
            if (!closeDate) {
                console.log("DEBUG (Events): eventRegistrationCloseDate not provided, calculating default.");
                const eventDT = new Date(`${formData.get('eventDate')}T${formData.get('eventTime')}`);
                const oneDayBefore = new Date(eventDT);
                oneDayBefore.setDate(eventDT.getDate() - 1);
                closeDate = oneDayBefore.toISOString().split('T')[0];
            }
            dataToForward.append('close_date', closeDate);

            dataToForward.append('venue', formData.get('eventLocation'));
            dataToForward.append('details', formData.get('eventDescription'));
            dataToForward.append('coverCharges', formData.get('eventPrice') || '0');
            dataToForward.append('coverChargesType', 'per_head');
            
            dataToForward.append('vegFoodCharges', formData.get('vegFoodCharges') || '0');
            dataToForward.append('vegFoodChargesType', 'per_head');

            dataToForward.append('nonVegFoodCharges', formData.get('nonVegFoodCharges') || '0');
            dataToForward.append('nonVegFoodChargesType', 'per_head');

            const eventImageFile = formData.get('eventImage');
            if (eventImageFile && eventImageFile.size > 0) {
                dataToForward.append('photo', eventImageFile);
                console.log("DEBUG (Events): Appending event image file to FormData.");
            } else {
                console.log("DEBUG (Events): No event image file selected or file is empty.");
            }

            try {
                const result = await apiRequest('/api/events', 'POST', dataToForward);
                showToast('success', `Event "${formData.get('eventName')}" created successfully!`);
                this.reset();
                window.location.hash = '#manage-events';
                fetchAllEvents();
            }
            catch (error) {
                console.error('ERROR (Events): Event creation failed:', error);
            }
        });
    }

    if (cancelCreateEventButton) {
        cancelCreateEventButton.addEventListener('click', function() {
            console.log("DEBUG (Events): Create event cancelled.");
            if (createEventForm) createEventForm.reset();
            showToast('info', 'Event creation cancelled.');
            window.location.hash = '#dashboard';
        });
    }

    if (addNewEventFromManageButton) {
        addNewEventFromManageButton.addEventListener('click', function() {
            console.log("DEBUG (Events): Navigating to create event view.");
            window.location.hash = '#create-event';
        });
    }

    // --- Calendar Logic ---
    function renderCalendar(dateToDisplay, events = []) {
        console.log("DEBUG (Calendar): Rendering calendar for", dateToDisplay.toLocaleDateString(), "with", events.length, "events.");
        if (!calendarGrid || !calendarMonthYear) {
            console.warn("WARNING: Calendar elements not found.");
            return;
        }

        calendarGrid.innerHTML = `
            <div class="calendar-header">Sun</div><div class="calendar-header">Mon</div>
            <div class="calendar-header">Tue</div><div class="calendar-header">Wed</div>
            <div class="calendar-header">Thu</div><div class="calendar-header">Fri</div>
            <div class="calendar-header">Sat</div>
        `;

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const month = dateToDisplay.getMonth();
        const year = dateToDisplay.getFullYear();
        calendarMonthYear.textContent = dateToDisplay.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

        const firstDayOfMonth = new Date(year, month, 1);
        const lastDayOfMonth = new Date(year, month + 1, 0);
        const daysInMonth = lastDayOfMonth.getDate();
        const startDayOfWeek = firstDayOfMonth.getDay();

        for (let i = 0; i < startDayOfWeek; i++) {
            calendarGrid.insertAdjacentHTML('beforeend', '<div class="calendar-day other-month"></div>');
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const dayCell = document.createElement('div');
            dayCell.classList.add('calendar-day');
            const currentDate = new Date(year, month, day);
            currentDate.setHours(0,0,0,0);

            if (currentDate.getTime() === today.getTime()) {
                dayCell.classList.add('today');
            }

            dayCell.innerHTML = `<span class="day-number">${day}</span><div class="events-container"></div>`;

            const eventsOnThisDay = events.filter(event => {
                const eventDateStr = event.time || event.eventDateTime;
                if (!eventDateStr) return false;

                const eventDate = new Date(eventDateStr);
                return eventDate.getFullYear() === year &&
                       eventDate.getMonth() === month &&
                       eventDate.getDate() === day;
            });


            const eventsContainer = dayCell.querySelector('.events-container');
            eventsOnThisDay.forEach(event => {
                const eventSpan = document.createElement('span');
                eventSpan.className = 'event';
                eventSpan.title = `${event.name} - ${new Date(event.time || event.eventDateTime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
                eventSpan.textContent = event.name.substring(0, 15) + (event.name.length > 15 ? '...' : '');
                eventsContainer.appendChild(eventSpan);
            });

            calendarGrid.appendChild(dayCell);
        }
        initLucideIcons();
    }

    if (calendarPrevMonth) {
        calendarPrevMonth.addEventListener('click', () => {
            console.log("DEBUG (Calendar): Previous Month button clicked.");
            currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
            fetchAllEvents();
        });
    }
    if (calendarNextMonth) {
        // CRITICAL FIX: Corrected typo in variable usage.
        calendarNextMonth.addEventListener('click', () => {
            console.log("DEBUG (Calendar): Next Month button clicked.");
            currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
            fetchAllEvents();
        });
    }


    // --- User Management Functions ---
    async function fetchAllUsers() {
        console.log("DEBUG (Users): Fetching all users...");
        try {
            const userData = await apiRequest('/api/users', 'GET');
            console.log("DEBUG (Users): Received user data:", userData);
            if (Array.isArray(userData)) {
                allUsersData = userData;
                populateUsersTable(allUsersData);
            } else {
                showToast('error', 'Received invalid user data format from service.');
                populateUsersTable([]);
            }
        } catch (error) {
            console.error("ERROR (Users): Failed to fetch all users.", error);
            populateUsersTable([]);
        }
    }

    function populateUsersTable(users) {
        console.log("DEBUG (Users): Populating users table with", users.length, "users.");
        if (!overallUsersTableBody) {
            console.warn("WARNING: overallUsersTableBody element not found.");
            return;
        }
        overallUsersTableBody.innerHTML = '';
        if (!users || users.length === 0) {
            overallUsersTableBody.innerHTML = '<tr><td colspan="4" class="text-center py-4">No users found.</td></tr>';
            console.log("DEBUG (Users): No users to display in table.");
            return;
        }
        users.forEach(user => {
            const row = `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${user.username || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.email || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.phone_number || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.role || 'N/A'}</td>
                </tr>
            `;
            overallUsersTableBody.insertAdjacentHTML('beforeend', row);
        });
        initLucideIcons();
    }

    if (userSearchInput) {
        let searchTimeout;
        userSearchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const searchTerm = e.target.value.trim();
                console.log("DEBUG (Users): User search input changed:", searchTerm);
                let filteredUsers = [];
                if (searchTerm) {
                    try {
                        const regex = new RegExp(searchTerm, 'i');
                        filteredUsers = allUsersData.filter(user =>
                            (user.username && regex.test(user.username)) ||
                            (user.email && regex.test(user.email)) ||
                            (user.phone_number && regex.test(user.phone_number)) ||
                            (user.role && regex.test(user.role))
                        );
                        console.log("DEBUG (Users): Filtered users:", filteredUsers.length);
                    } catch (regexError) {
                        console.error("ERROR (Users): Invalid regex in search term:", regexError);
                        showToast('error', 'Invalid search pattern. Please check your regex syntax.');
                        filteredUsers = [];
                    }
                } else {
                    filteredUsers = allUsersData;
                }
                populateUsersTable(filteredUsers);
            }, 300);
        });
    }

    // --- Event Registrants / Participation Management Functions ---
    async function populateEventDropdownForRegistrants(events = null) {
        console.log("DEBUG (Registrants): Populating event dropdown.");
        if (!selectEventForRegistrants) {
            console.warn("WARNING: selectEventForRegistrants element not found.");
            return;
        }
        if (!events) {
             try {
                events = await apiRequest('/api/events', 'GET');
                console.log("DEBUG (Registrants): Fetched events for dropdown.");
             } catch (e) {
                console.error("ERROR (Registrants): Failed to fetch events for dropdown:", e);
                events = [];
             }
        }

        selectEventForRegistrants.innerHTML = '<option value="">-- Choose an Event --</option>';
        if (Array.isArray(events)) {
            events.sort((a, b) => new Date(a.time || a.eventDateTime) - new Date(b.time || b.eventDateTime));
            events.forEach(event => {
                const option = document.createElement('option');
                option.value = event.id;
                const displayDate = event.time ? new Date(event.time).toLocaleDateString() : 'N/A';
                option.textContent = `${event.name} (${displayDate})`;
                selectEventForRegistrants.appendChild(option);
            });
        }
    }

    async function fetchParticipations(eventId, searchTerm = '') {
        console.log(`DEBUG (Registrants): Fetching participations for event ID: ${eventId}, Search: "${searchTerm}"`);
        if (!eventId) {
            populateParticipationsTable([]);
            console.log("DEBUG (Registrants): Event ID not selected, clearing registrants table.");
            return;
        }

        try {
            let url = `/api/participations?eventId=${encodeURIComponent(eventId)}`;
            if (searchTerm) {
                url += `&query=${encodeURIComponent(searchTerm)}`;
            }
            showToast('info', `Fetching registrants for event ID ${eventId} with query "${searchTerm}"...`);

            const participations = await apiRequest(url, 'GET');
            showToast('success', `Found ${participations.length} registrants.`);
            populateParticipationsTable(participations);
            console.log("DEBUG (Registrants): Received participations:", participations);
        } catch (error) {
            console.error("ERROR (Registrants): Failed to fetch participations.", error);
            populateParticipationsTable([]);
        }
    }

    function populateParticipationsTable(participations) {
        console.log("DEBUG (Registrants): Populating registrants table with", participations.length, "registrants.");
        if (!eventRegistrantsTableBody) {
            console.warn("WARNING: eventRegistrantsTableBody element not found.");
            return;
        }
        eventRegistrantsTableBody.innerHTML = '';

        const tableHead = document.querySelector('#registrantsView table thead tr');
        if (tableHead) {
            tableHead.innerHTML = `
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Participant Name</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Registered At</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tickets</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Heads (V/NV)</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Payable (INR)</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Paid (INR)</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Remaining (INR)</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Add. Contrib. (INR)</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Comments</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Transaction ID</th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Updated</th>
            `;
        }


        if (!participations || participations.length === 0) {
            eventRegistrantsTableBody.innerHTML = '<tr><td colspan="14" class="text-center py-4">Select an event or search to view registrants.</td></tr>';
            console.log("DEBUG (Registrants): No registrants to display.");
            return;
        }

        participations.forEach(p => {
            const registeredAtFormatted = p.registered_at ? new Date(p.registered_at).toLocaleString() : 'N/A';
            const updatedAtFormatted = p.updated_at ? new Date(p.updated_at).toLocaleString() : 'N/A';

            const row = `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${p.user_name || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${p.email_id || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${p.flat_no ? `${p.tower}-${p.flat_no}` : 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${registeredAtFormatted}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full
                            ${p.status === 'confirmed' ? 'bg-green-100 text-green-800' :
                              p.status === 'pending_payment' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'}">
                            ${p.status || 'N/A'}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${p.num_tickets || 0}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${p.veg_heads || 0} / ${p.non_veg_heads || 0}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">INR ${(p.total_payable || 0).toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">INR ${(p.amount_paid || 0).toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">INR ${(p.payment_remaining || 0).toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">INR ${(p.additional_contribution || 0).toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${p.contribution_comments || 'None'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${p.transaction_id || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${updatedAtFormatted}</td>
                </tr>
            `;
            eventRegistrantsTableBody.insertAdjacentHTML('beforeend', row);
        });
        initLucideIcons();
    }


    if (selectEventForRegistrants) {
        selectEventForRegistrants.addEventListener('change', function() {
            const eventId = this.value;
            const currentSearchTerm = participationSearchInput.value.trim();
            fetchParticipations(eventId, currentSearchTerm);
            console.log("DEBUG (Registrants): Event dropdown changed to ID:", eventId);
        });
    } else {
        console.warn("WARNING: selectEventForRegistrants element not found for change listener.");
    }

    if (participationSearchInput) {
        let participationSearchTimeout;
        participationSearchInput.addEventListener('input', (e) => {
            clearTimeout(participationSearchTimeout);
            searchTimeout = setTimeout(() => {
                const eventId = selectEventForRegistrants ? selectEventForRegistrants.value : '';
                fetchParticipations(eventId, e.target.value.trim());
                console.log("DEBUG (Registrants): Participation search input changed:", e.target.value);
            }, 500);
        });
    } else {
        console.warn("WARNING: participationSearchInput element not found for input listener.");
    }

    // --- Download CSV Button Event Listener ---
    if (downloadCsvButton) {
        downloadCsvButton.addEventListener('click', function() {
            const eventId = selectEventForRegistrants.value;
            const searchTerm = participationSearchInput.value.trim();

            if (!eventId) {
                showToast('error', 'Please select an event to download participation data.');
                return;
            }

            let downloadUrl = `${adminPortalApiBaseUrl}/api/participations/download_csv?eventId=${encodeURIComponent(eventId)}`;
            if (searchTerm) {
                downloadUrl += `&query=${encodeURIComponent(searchTerm)}`;
            }

            showToast('info', `Preparing CSV for event ID ${eventId}. Your download should start shortly...`);
            window.location.href = downloadUrl;
        });
    }


    // --- Navigation Logic ---
    const toggleSidebar = (shouldOpen) => {
        if (!sidebar) {
            console.warn("WARNING: Sidebar element not found for toggling.");
            return;
        }
        if (!sidebarOverlay) {
            console.warn("WARNING: Sidebar overlay element not found for toggling.");
            return;
        }

        if (shouldOpen) {
            console.log("DEBUG (UI): Attempting to open sidebar. Adding translate-x-0, removing -translate-x-full.");
            sidebar.classList.remove('-translate-x-full');
            sidebar.classList.add('translate-x-0');
            sidebarOverlay.classList.remove('hidden'); // Show overlay
            document.body.classList.add('overflow-hidden'); // Prevent body scroll
            console.log("DEBUG (UI): Sidebar open state applied. Current classes:", sidebar.classList.value);
        } else {
            console.log("DEBUG (UI): Attempting to close sidebar. Adding -translate-x-full, removing translate-x-0.");
            sidebar.classList.add('-translate-x-full');
            sidebar.classList.remove('translate-x-0');
            sidebarOverlay.classList.add('hidden'); // Hide overlay
            document.body.classList.remove('overflow-hidden'); // Allow body scroll
            console.log("DEBUG (UI): Sidebar close state applied. Current classes:", sidebar.classList.value);
        }
    };

    const openSidebar = () => toggleSidebar(true);
    const closeSidebar = () => toggleSidebar(false);


    if (menuButton) {
        menuButton.addEventListener('click', function(e) {
            console.log("DEBUG (UI): Hamburger menu button clicked.");
            e.stopPropagation(); // Prevent event bubbling, especially if there's a click listener on body/document
            openSidebar();
        });
        console.log("DEBUG (UI): Menu button listener attached.");
    } else {
        console.warn("WARNING: Menu button (#menu-button) not found in HTML.");
    }
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
        console.log("DEBUG (UI): Sidebar overlay listener attached.");
    } else {
        console.warn("WARNING: Sidebar overlay (#sidebar-overlay) not found or created.");
    }

    function updateActiveView(hash) {
        let targetViewId = hash ? `${hash.substring(1)}View` : 'dashboardView';
        let activeLink = document.querySelector(`.sidebar-link[href="${hash || '#dashboard'}"]`);
        let activeTitle = "Dashboard";

        if (!document.getElementById(targetViewId)) {
            console.warn(`WARNING: Target view '${targetViewId}' not found. Defaulting to dashboardView.`);
            targetViewId = 'dashboardView';
            activeLink = navDashboard;
        }
        if (activeLink) activeTitle = activeLink.textContent?.trim() || "Admin";

        pageSections.forEach(section => {
            section.classList.add('hidden');
            if (section.id === targetViewId) {
                section.classList.remove('hidden');
                if (targetViewId === 'usersView') {
                    console.log("DEBUG (Navigation): Activating Users View, fetching all users.");
                    fetchAllUsers();
                } else if ((targetViewId === 'manageEventsView')) {
                    console.log("DEBUG (Navigation): Activating Events Management View, fetching all events.");
                    fetchAllEvents();
                } else if (targetViewId === 'dashboardView') {
                     console.log("DEBUG (Navigation): Activating Dashboard View, fetching dashboard stats and events for calendar.");
                     fetchDashboardStats();
                     fetchAllEvents();
                } else if (targetViewId === 'registrantsView') {
                    console.log("DEBUG (Navigation): Activating Registrants View, populating dropdown and fetching participations.");
                    populateEventDropdownForRegistrants();
                    fetchParticipations(selectEventForRegistrants ? selectEventForRegistrants.value : '', participationSearchInput ? participationSearchInput.value.trim() : '');
                }
            }
        });

        // Loop through all sidebar links to manage active state AND close sidebar on click
        sidebarLinks.forEach(link => {
            link.classList.remove('active'); // Deactivate all links first
            const linkHash = link.getAttribute('href');
            if (linkHash === `#${targetViewId.replace('View', '')}`) {
                link.classList.add('active'); // Activate the current link
            }

            // --- CRITICAL FIX: Ensure individual sidebar link clicks also close the menu on mobile ---
            // This listener is crucial for menu items to actually work as expected.
            // It prevents default navigation so JS can handle it, then closes sidebar.
            link.removeEventListener('click', handleSidebarLinkClick); // Remove old listeners to prevent duplicates
            link.addEventListener('click', handleSidebarLinkClick);
        });

        if (pageTitle) pageTitle.textContent = activeTitle;

        const currentViewHeading = document.querySelector(`#${targetViewId} h2`);
        if (currentViewHeading) {
            currentViewHeading.setAttribute('tabindex', '-1');
            currentViewHeading.focus({ preventScroll: true });
        }
        initLucideIcons();
    }

    // --- NEW: Centralized handler for sidebar navigation link clicks ---
    function handleSidebarLinkClick(e) {
        // Only prevent default if it's not the logout button, as logout has its own fetch logic
        if (this.id !== 'logoutButton') {
            e.preventDefault(); // Prevent default browser navigation (hash change is handled by updateActiveView)
            console.log("DEBUG (UI): Sidebar navigation link clicked:", this.getAttribute('href'));
            window.location.hash = this.getAttribute('href'); // Manually change hash to trigger updateActiveView
        }
        
        // Always close sidebar on mobile after clicking any sidebar link (including logout, handled by its own listener)
        if (window.innerWidth < 768) {
            closeSidebar();
        }
    }


    function handleNavigation() {
        console.log("DEBUG (Navigation): URL hash changed to", window.location.hash);
        updateActiveView(window.location.hash);
    }
    window.addEventListener('hashchange', handleNavigation);


    // --- Logout Button Listener ---
    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.removeEventListener('click', handleLogoutButtonClick); // Remove old listener to prevent duplicates
        logoutButton.addEventListener('click', handleLogoutButtonClick);
        console.log("DEBUG (UI): Logout button listener attached.");
    } else {
        console.warn("WARNING: Logout button (#logoutButton) not found in HTML.");
    }

    async function handleLogoutButtonClick(e) {
        e.preventDefault();
        console.log("DEBUG (Logout): Admin Portal Logout button clicked.");
        const userConfirmed = window.confirm("Are you sure you want to logout from Admin Portal?");
        if (userConfirmed) {
            try {
                const response = await fetch(`${adminPortalApiBaseUrl}/logout`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (response.ok) {
                    console.log("DEBUG (Logout): Admin Portal backend logout request successful.");
                    showToast('success', 'Logged out successfully! Redirecting...');
                    window.location.href = AUTH_SERVICE_EXTERNAL_URL;
                } else {
                    const errorData = await response.json().catch(() => ({ error: "Unknown error during logout." }));
                    console.error("ERROR (Logout): Admin Portal logout failed on backend:", errorData.error);
                    showToast('error', `Logout failed: ${errorData.error}`);
                }
            } catch (error) {
                console.error("ERROR (Logout): Network error during Admin Portal logout:", error);
                showToast('error', `Network error during logout. Please check your connection.`);
                }
        }
        if (window.innerWidth < 768) {
            closeSidebar();
        }
    }


    // --- Dashboard Stats Fetching Function ---
    async function fetchDashboardStats() {
        console.log("DEBUG (Dashboard): Fetching dashboard statistics...");
        try {
            const currentTotalUsersCountEl = document.getElementById('totalUsersCount');
            const currentTotalEventsCountEl = document.getElementById('totalEventsCount');
            const currentUpcomingEventsCountEl = document.getElementById('upcomingEventsCount');
            const currentTotalParticipantsCountEl = document.getElementById('totalParticipantsCount');

            const users = await apiRequest('/api/users', 'GET');
            console.log("DEBUG (Dashboard): Fetched total users:", users);

            if (Array.isArray(users) && currentTotalUsersCountEl) {
                currentTotalUsersCountEl.textContent = users.length;
                console.log(`DEBUG (Dashboard): Total Users (display updated): ${users.length}`);
            } else {
                if (currentTotalUsersCountEl) currentTotalUsersCountEl.textContent = 'N/A';
                console.warn("WARNING: Could not fetch total users or data is not array. Users data:", users);
            }

            const events = await apiRequest('/api/events', 'GET');
            console.log("DEBUG (Dashboard): Fetched total events:", events);

            if (Array.isArray(events) && currentTotalEventsCountEl && currentUpcomingEventsCountEl) {
                currentTotalEventsCountEl.textContent = events.length;
                console.log(`DEBUG (Dashboard): Total Events (display updated): ${events.length}`);
                const now = new Date();
                let upcomingCount = 0;
                events.forEach(event => {
                    const eventDate = new Date(event.time || event.eventDateTime);
                    if (eventDate > now) {
                        upcomingCount++;
                    }
                });
                currentUpcomingEventsCountEl.textContent = upcomingCount;
                console.log(`DEBUG (Dashboard): Upcoming Events (display updated): ${upcomingCount}`);
            } else {
                if (currentTotalEventsCountEl) currentTotalEventsCountEl.textContent = 'N/A';
                if (currentUpcomingEventsCountEl) currentUpcomingEventsCountEl.textContent = 'N/A';
                console.warn("WARNING: Could not fetch total events or data is not array. Events data:", events);
            }

            const allParticipations = await apiRequest('/api/participations', 'GET');
            console.log("DEBUG (Dashboard): Fetched total participations:", allParticipations);

            if (Array.isArray(allParticipations) && currentTotalParticipantsCountEl) {
                currentTotalParticipantsCountEl.textContent = allParticipations.length;
                console.log(`DEBUG (Dashboard): Total Participants (display updated): ${allParticipations.length}`);
            } else {
                if (currentTotalParticipantsCountEl) currentTotalParticipantsCountEl.textContent = 'N/A';
                console.warn("WARNING: Could not fetch total participants or data is not array. Participations data:", allParticipations);
            }

            showToast('success', 'Dashboard stats updated!');

        } catch (error) {
            console.error("ERROR (Dashboard): Failed to fetch dashboard stats:", error);
            showToast('error', 'Failed to load dashboard statistics.');
            if (document.getElementById('totalEventsCount')) document.getElementById('totalEventsCount').textContent = 'Error';
            if (document.getElementById('totalUsersCount')) document.getElementById('totalUsersCount').textContent = 'Error';
            if (document.getElementById('upcomingEventsCount')) document.getElementById('upcomingEventsCount').textContent = 'Error';
            if (document.getElementById('totalParticipantsCount')) document.getElementById('totalParticipantsCount').textContent = 'Error';
        }
    }


    // --- Initial Load & Responsive Sidebar Handling ---
    const applyInitialSidebarState = () => {
        if (!sidebar) {
            console.warn("WARNING: Sidebar element not found during initial state application.");
            return;
        }
        if (!sidebarOverlay) {
            console.warn("WARNING: Sidebar overlay element not found during initial state application.");
            return;
        }

        if (window.innerWidth >= 768) {
            // Desktop view: Ensure sidebar is visible and overlay is hidden
            sidebar.classList.remove('-translate-x-full'); // Make sure it's not off-screen
            sidebar.classList.add('translate-x-0'); // Ensure it's in view
            sidebar.classList.add('md:relative', 'md:translate-x-0', 'md:shadow-none'); // Apply desktop position/shadow
            sidebarOverlay.classList.add('hidden'); // Hide overlay
            document.body.classList.remove('overflow-hidden'); // Allow body scroll
            console.log("DEBUG (Responsive): Applied desktop sidebar state.");
        } else {
            // Mobile view: Ensure sidebar is hidden initially and overlay is hidden
            sidebar.classList.add('-translate-x-full'); // Hide sidebar off-screen
            sidebar.classList.remove('translate-x-0'); // Ensure it's not accidentally visible
            sidebar.classList.remove('md:relative', 'md:translate-x-0', 'md:shadow-none'); // Remove desktop classes
            sidebarOverlay.classList.add('hidden'); // Hide overlay
            document.body.classList.remove('overflow-hidden'); // Allow body scroll
            console.log("DEBUG (Responsive): Applied mobile sidebar initial state.");
        }
    };

    applyInitialSidebarState();
    window.addEventListener('resize', applyInitialSidebarState);

    console.log("DEBUG: Admin Portal JavaScript Initialized (Ready to handle interactions).");

    handleNavigation();
});