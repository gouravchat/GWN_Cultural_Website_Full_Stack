// JavaScript for Admin Portal
document.addEventListener('DOMContentLoaded', function () {
    // --- Global Configuration ---
    let SERVICE_CONFIG = {
        eventServiceBaseUrl: '', // To be populated from /config
        authServiceBaseUrl: ''   // To be populated from /config
    };
    let currentCalendarDate = new Date(); // For calendar navigation

    // --- Initialize Lucide Icons ---
    function initLucideIcons() {
        if (typeof lucide !== 'undefined' && typeof lucide.createIcons === 'function') {
            lucide.createIcons();
        } else {
            console.warn("Lucide icons library not found or createIcons method is missing.");
        }
    }
    initLucideIcons(); // Initial call

    // --- Elements ---
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const pageSections = document.querySelectorAll('.page-section');
    const pageTitle = document.getElementById('pageTitle');
    const createEventForm = document.getElementById('createEventForm');
    const cancelCreateEventButton = document.getElementById('cancelCreateEvent');
    const addNewEventFromManageButton = document.getElementById('addNewEventButton');

    const messageBoxEl = document.getElementById('messageBox'); // Renamed to avoid conflict
    const messageTextEl = document.getElementById('messageText'); // Renamed
    const messageIconEl = document.getElementById('messageIcon'); // Renamed

    const tabButtons = document.querySelectorAll('.tab-button');
    // const tabContents = document.querySelectorAll('.tab-content'); // Not directly used, logic targets specific content

    const navDashboard = document.getElementById('navDashboard');

    const manageEventsTableBody = document.getElementById('manageEventsTableBody');
    const overallUsersTableBody = document.getElementById('overallUsersTableBody');
    const userSearchInput = document.getElementById('userSearchInput');

    const calendarGrid = document.getElementById('calendarGrid');
    const calendarMonthYear = document.getElementById('calendarMonthYear');
    const calendarPrevMonth = document.getElementById('calendarPrevMonth');
    const calendarNextMonth = document.getElementById('calendarNextMonth');

    // --- Toast Message Function ---
    let toastTimeout;
    function showToast(type, message, duration = 3000) {
        if (!messageBoxEl || !messageTextEl || !messageIconEl) {
            console.warn("Message box elements not found. Toast not shown.");
            return;
        }

        messageTextEl.textContent = message;
        messageBoxEl.className = 'message-box'; // Reset classes
        messageBoxEl.classList.add(type);

        let iconName = 'info';
        if (type === 'success') iconName = 'check-circle';
        if (type === 'error') iconName = 'alert-circle';

        messageIconEl.innerHTML = '';
        const newIconElement = document.createElement('i');
        newIconElement.setAttribute('data-lucide', iconName);
        messageIconEl.appendChild(newIconElement);
        initLucideIcons(); // Refresh icons

        messageBoxEl.classList.add('show');
        clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {
            messageBoxEl.classList.remove('show');
        }, duration);
    }

    // --- API Helper ---
    async function apiRequest(url, method = 'GET', body = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                // Add Authorization header if needed, e.g., from a token stored after login
                // 'Authorization': `Bearer ${localStorage.getItem('adminAuthToken')}`
            }
        };
        if (body && method !== 'GET' && method !== 'HEAD') {
            if (body instanceof FormData) {
                delete options.headers['Content-Type']; // Browser sets it for FormData
                options.body = body;
            } else {
                options.body = JSON.stringify(body);
            }
        }

        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: "Unknown server error", details: response.statusText }));
                console.error(`API Error ${response.status}:`, errorData);
                throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
            }
            // Handle cases where response might be empty (e.g., 204 No Content)
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return await response.json();
            }
            return await response.text(); // Or handle as appropriate
        } catch (error) {
            console.error('API Request Failed:', error);
            showToast('error', `API Request Failed: ${error.message}`);
            throw error; // Re-throw to be caught by caller
        }
    }


    // --- Configuration Fetching ---
    async function fetchAppConfig() {
        try {
            const config = await apiRequest('/config'); // Uses the apiRequest helper
            SERVICE_CONFIG = config;
            console.log("Service config loaded:", SERVICE_CONFIG);
            // After config is loaded, fetch initial data for the default view
            if (window.location.hash === '' || window.location.hash === '#dashboard' || !window.location.hash) {
                fetchAllEvents(); // For calendar and manage events table
            }
            // Populate event dropdown for registrants tab (could be done on demand too)
            populateEventDropdownForRegistrants();
        } catch (error) {
            // Error already shown by apiRequest
            showToast('error', 'Failed to load critical application configuration. Portal may not function correctly.');
        }
    }

    // --- Event Management ---
    async function fetchAllEvents() {
        if (!SERVICE_CONFIG.eventServiceBaseUrl) {
            showToast('error', 'Event service URL not configured.');
            return;
        }
        try {
            const events = await apiRequest(`${SERVICE_CONFIG.eventServiceBaseUrl}/events`);
            console.log("Fetched events:", events);
            if (Array.isArray(events)) {
                renderCalendar(currentCalendarDate, events);
                populateManageEventsTable(events);
                populateEventDropdownForRegistrants(events); // Update dropdown with fresh event list
            } else {
                showToast('error', 'Received invalid event data format from service.');
                renderCalendar(currentCalendarDate, []); // Render empty calendar
                populateManageEventsTable([]); // Render empty table
            }
        } catch (error) {
            // Error toast shown by apiRequest
            renderCalendar(currentCalendarDate, []); // Render empty calendar on error
            populateManageEventsTable([]); // Render empty table on error
        }
    }

    function populateManageEventsTable(events) {
        if (!manageEventsTableBody) return;
        manageEventsTableBody.innerHTML = ''; // Clear existing rows
        if (!events || events.length === 0) {
            manageEventsTableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4">No events found.</td></tr>';
            return;
        }

        // Sort events by date, most recent first (assuming 'time' or 'eventDateTime' contains sortable date)
        // The external event service returns 'time' which is actually 'event_datetime_str'
        events.sort((a, b) => new Date(b.time || b.eventDateTime) - new Date(a.time || a.eventDateTime));


        events.forEach(event => {
            // Map data from Event Service to what the table expects
            const eventName = event.name || event.eventName || 'Unnamed Event';
            const eventDateTimeStr = event.time || event.eventDateTime || 'N/A'; // 'time' from original service
            const eventLocation = event.venue || event.eventLocation || 'N/A'; // 'venue' from original service
            const eventPrice = typeof (event.coverCharges ?? event.eventPrice) === 'number' ? `$${(event.coverCharges ?? event.eventPrice).toFixed(2)}` : 'N/A';

            let formattedDateTime = 'N/A';
            try {
                if (eventDateTimeStr !== 'N/A') {
                    formattedDateTime = new Date(eventDateTimeStr).toLocaleString([], {
                        year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                    });
                }
            } catch (e) { console.warn("Could not format date for event:", eventName, e); }


            const row = `
                <tr data-event-id="${event.id}">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${eventName}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formattedDateTime}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${eventLocation}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${eventPrice}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                        <button class="btn btn-icon text-blue-600 hover:text-blue-800 edit-event-btn" title="Edit (Not Implemented)"><i data-lucide="edit"></i></button>
                        <button class="btn btn-icon text-red-600 hover:text-red-800 delete-event-btn" title="Delete (Not Implemented)"><i data-lucide="trash-2"></i></button>
                    </td>
                </tr>
            `;
            manageEventsTableBody.insertAdjacentHTML('beforeend', row);
        });
        initLucideIcons(); // Refresh icons in the table
    }

    if (createEventForm) {
        createEventForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            if (!SERVICE_CONFIG.eventServiceBaseUrl) {
                showToast('error', 'Event service URL not configured.');
                return;
            }

            const formData = new FormData(this);
            // The external Event Service (original app.py from user upload) expects specific field names for FormData
            const serviceFormData = new FormData();
            serviceFormData.append('name', formData.get('eventName'));
            serviceFormData.append('time', `${formData.get('eventDate')}T${formData.get('eventTime')}:00`); // ISO like format, add seconds
            
            let closeDate = formData.get('eventRegistrationCloseDate');
            if (!closeDate) { // If not provided, default to event date or one day before
                const eventDT = new Date(`${formData.get('eventDate')}T${formData.get('eventTime')}`);
                const oneDayBefore = new Date(eventDT.setDate(eventDT.getDate() -1));
                closeDate = oneDayBefore.toISOString().split('T')[0]; // YYYY-MM-DD
            }
            serviceFormData.append('close_date', closeDate);

            serviceFormData.append('venue', formData.get('eventLocation'));
            serviceFormData.append('details', formData.get('eventDescription'));
            serviceFormData.append('coverCharges', formData.get('eventPrice') || '0'); // Ensure it's a string for FormData
            // The original service expects cover_charges_type, food_charges, food_type, food_charges_type
            // Send defaults or add to form
            serviceFormData.append('cover_charges_type', 'per_head');
            serviceFormData.append('food_charges', '0');
            serviceFormData.append('food_type', 'none');
            serviceFormData.append('food_charges_type', 'per_head');

            if (formData.get('eventImage')) { // Assuming 'eventImage' is a URL
                serviceFormData.append('photo_url_from_form', formData.get('eventImage')); // Original service checks 'photo' file or this
            }
            // For direct file upload (if you add <input type="file" name="photo"> to form)
            // const photoFile = document.getElementById('eventPhotoFile').files[0];
            // if (photoFile) serviceFormData.append('photo', photoFile);


            try {
                // Note: apiRequest handles FormData correctly by removing Content-Type header
                const result = await apiRequest(`${SERVICE_CONFIG.eventServiceBaseUrl}/events`, 'POST', serviceFormData);
                showToast('success', `Event "${formData.get('eventName')}" created successfully!`);
                this.reset();
                window.location.hash = '#manage-events'; // Navigate to manage events
                fetchAllEvents(); // Refresh event lists
            } catch (error) {
                // Toast is already shown by apiRequest
            }
        });
    }

    if (cancelCreateEventButton) {
        cancelCreateEventButton.addEventListener('click', function() {
            if (createEventForm) createEventForm.reset();
            showToast('info', 'Event creation cancelled.');
            window.location.hash = '#dashboard';
        });
    }

    if (addNewEventFromManageButton) {
        addNewEventFromManageButton.addEventListener('click', function() {
            window.location.hash = '#create-event';
        });
    }

    // --- Calendar Logic ---
    function renderCalendar(dateToDisplay, events = []) {
        if (!calendarGrid || !calendarMonthYear) return;

        calendarGrid.innerHTML = `
            <div class="calendar-header">Sun</div><div class="calendar-header">Mon</div>
            <div class="calendar-header">Tue</div><div class="calendar-header">Wed</div>
            <div class="calendar-header">Thu</div><div class="calendar-header">Fri</div>
            <div class="calendar-header">Sat</div>
        `; // Reset grid but keep headers

        const today = new Date();
        today.setHours(0, 0, 0, 0); // Normalize today for comparison

        const month = dateToDisplay.getMonth();
        const year = dateToDisplay.getFullYear();
        calendarMonthYear.textContent = dateToDisplay.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

        const firstDayOfMonth = new Date(year, month, 1);
        const lastDayOfMonth = new Date(year, month + 1, 0);
        const daysInMonth = lastDayOfMonth.getDate();
        const startDayOfWeek = firstDayOfMonth.getDay(); // 0 (Sun) - 6 (Sat)

        // Add empty cells for days before the first of the month
        for (let i = 0; i < startDayOfWeek; i++) {
            calendarGrid.insertAdjacentHTML('beforeend', '<div class="calendar-day other-month"></div>');
        }

        // Add days of the month
        for (let day = 1; day <= daysInMonth; day++) {
            const dayCell = document.createElement('div');
            dayCell.classList.add('calendar-day');
            const currentDate = new Date(year, month, day);
            currentDate.setHours(0,0,0,0); // Normalize current date for comparison

            if (currentDate.getTime() === today.getTime()) {
                dayCell.classList.add('today');
            }

            dayCell.innerHTML = `<span class="day-number">${day}</span><div class="events-container"></div>`;
            
            // Filter events for the current day
            const eventsOnThisDay = events.filter(event => {
                const eventDate = new Date(event.time || event.eventDateTime); // 'time' from original service
                return eventDate.getFullYear() === year &&
                       eventDate.getMonth() === month &&
                       eventDate.getDate() === day;
            });

            const eventsContainer = dayCell.querySelector('.events-container');
            eventsOnThisDay.forEach(event => {
                const eventSpan = document.createElement('span');
                eventSpan.className = 'event';
                eventSpan.title = `${event.name} - ${new Date(event.time || event.eventDateTime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
                eventSpan.textContent = event.name.substring(0, 15) + (event.name.length > 15 ? '...' : ''); // Shorten name
                eventsContainer.appendChild(eventSpan);
            });

            calendarGrid.appendChild(dayCell);
        }
        initLucideIcons(); // For any icons in calendar
    }

    if (calendarPrevMonth) {
        calendarPrevMonth.addEventListener('click', () => {
            currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
            fetchAllEvents(); // Re-fetch events for the new month view (or filter existing if all are loaded)
        });
    }
    if (calendarNextMonth) {
        calendarNextMonth.addEventListener('click', () => {
            currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
            fetchAllEvents();
        });
    }


    // --- User Management ---
    async function fetchAllUsers(searchTerm = '') {
        if (!SERVICE_CONFIG.authServiceBaseUrl) {
            showToast('error', 'Auth service URL not configured.');
            return;
        }
        try {
            let url = `${SERVICE_CONFIG.authServiceBaseUrl}/users`;
            if (searchTerm) {
                // The Auth service GET /users takes a 'query' param
                url += `?query=${encodeURIComponent(searchTerm)}`;
            }
            // The Auth service API for GET /users (with or without query) might return a single user or an array.
            // We need to handle both cases for the table.
            constuserData = await apiRequest(url);
            let usersArray = [];
            if(userData && !Array.isArray(userData) && userData.id) { // Single user object returned
                usersArray = [userData];
            } else if (Array.isArray(userData)) { // Array of users returned
                usersArray = userData;
            }

            populateUsersTable(usersArray);
        } catch (error) {
            // Error toast shown by apiRequest
            populateUsersTable([]); // Show empty table on error
        }
    }

    function populateUsersTable(users) {
        if (!overallUsersTableBody) return;
        overallUsersTableBody.innerHTML = '';
        if (!users || users.length === 0) {
            overallUsersTableBody.innerHTML = '<tr><td colspan="4" class="text-center py-4">No users found.</td></tr>';
            return;
        }
        users.forEach(user => {
            const row = `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${user.username || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.email || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.phone_number || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.role || 'N/A'}</td>
                    <!-- Actions for users (e.g., edit role, delete) would go here if implemented -->
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
                fetchAllUsers(e.target.value.trim());
            }, 500); // Debounce search
        });
    }

    // --- Event Registrants (Placeholder/Future) ---
    const selectEventForRegistrants = document.getElementById('selectEventForRegistrants');
    const eventRegistrantsTableBody = document.getElementById('eventRegistrantsTableBody');

    async function populateEventDropdownForRegistrants(events = null) {
        if (!selectEventForRegistrants) return;
        if (!events) { // If events not passed, fetch them
             if (!SERVICE_CONFIG.eventServiceBaseUrl) return;
             try {
                events = await apiRequest(`${SERVICE_CONFIG.eventServiceBaseUrl}/events`);
             } catch (e) { events = []; }
        }
        
        selectEventForRegistrants.innerHTML = '<option value="">-- Choose an Event --</option>'; // Clear and add default
        if (Array.isArray(events)) {
            // Sort events by date for the dropdown
            events.sort((a, b) => new Date(a.time || a.eventDateTime) - new Date(b.time || b.eventDateTime));
            events.forEach(event => {
                const option = document.createElement('option');
                option.value = event.id; // Assuming event object has an 'id'
                option.textContent = `${event.name} (${new Date(event.time || event.eventDateTime).toLocaleDateString()})`;
                selectEventForRegistrants.appendChild(option);
            });
        }
    }

    if (selectEventForRegistrants && eventRegistrantsTableBody) {
        selectEventForRegistrants.addEventListener('change', function() {
            const eventId = this.value;
            eventRegistrantsTableBody.innerHTML = ''; // Clear

            if (eventId) {
                showToast('info', `Fetching registrants for event ID ${eventId}... (Placeholder)`);
                // TODO: Implement API call to Participation Service when available
                // For now, show placeholder:
                setTimeout(() => {
                    eventRegistrantsTableBody.innerHTML = `<tr><td colspan="4" class="text-center py-4">Registrant data for event ID ${eventId} would be shown here. (Participation Service not yet integrated)</td></tr>`;
                }, 500);
            } else {
                eventRegistrantsTableBody.innerHTML = `<tr><td colspan="4" class="text-center py-4">Select an event to view registrants.</td></tr>`;
            }
        });
    }


    // --- Navigation Logic ---
    function updateActiveView(hash) {
        let targetViewId = hash ? hash.substring(1) + 'View' : 'dashboardView';
        let activeLink = document.querySelector(`.sidebar-link[href="${hash || '#dashboard'}"]`);
        let activeTitle = "Dashboard";

        if (!document.getElementById(targetViewId)) {
            targetViewId = 'dashboardView';
            activeLink = navDashboard;
        }
        if (activeLink) activeTitle = activeLink.textContent?.trim() || "Admin";

        pageSections.forEach(section => {
            section.classList.add('hidden');
            if (section.id === targetViewId) {
                section.classList.remove('hidden');
                // Fetch data for the newly active section if needed
                if (targetViewId === 'usersView' && overallUsersTableBody.innerHTML.includes('Loading users...')) {
                    fetchAllUsers();
                } else if ((targetViewId === 'manageEventsView' && manageEventsTableBody.innerHTML.includes('Loading events...')) || targetViewId === 'dashboardView') {
                    fetchAllEvents();
                }
            }
        });

        sidebarLinks.forEach(link => link.classList.remove('active'));
        if (activeLink) activeLink.classList.add('active');
        if (pageTitle) pageTitle.textContent = activeTitle;

        const currentViewHeading = document.querySelector(`#${targetViewId} h2`);
        if (currentViewHeading) {
            currentViewHeading.setAttribute('tabindex', '-1');
            currentViewHeading.focus({ preventScroll: true });
        }
        initLucideIcons(); // Re-scan for icons in newly visible section
    }

    function handleNavigation() {
        updateActiveView(window.location.hash);
    }
    window.addEventListener('hashchange', handleNavigation);

    // Sidebar link clicks
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            if (this.id === 'logoutButton') {
                e.preventDefault();
                showToast('info', 'Logging out... (Placeholder)');
                // Implement actual logout: clear tokens, redirect to Auth service logout/login page
                console.log("Logout action triggered.");
                // Example: localStorage.removeItem('adminAuthToken'); window.location.href = 'AUTH_SERVICE_LOGIN_URL';
                return;
            }
            // Hashchange will handle other links
        });
    });

    // --- Tab Switching Logic ---
    tabButtons.forEach(button => {
        button.addEventListener('click', function () {
            const parentNav = this.closest('nav');
            if (!parentNav) return;
            parentNav.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            const targetTabId = this.dataset.tab;
            const tabContentContainer = parentNav.nextElementSibling || parentNav.closest('.bg-white')?.querySelector('.p-4, .p-6');
            if (tabContentContainer) {
                tabContentContainer.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                    if (content.id === targetTabId) content.classList.add('active');
                });
            }
            initLucideIcons(); // Re-scan for icons in newly active tab
        });
    });

    // --- Initial Load ---
    fetchAppConfig().then(() => {
        handleNavigation(); // Initial view setup after config is loaded
    });

    console.log("Admin Portal JavaScript Initialized");
});
