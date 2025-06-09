// This script assumes it's linked from landing_page.html
// and that the following global constants are defined in a <script> tag
// BEFORE this script is loaded, by being injected via Flask/Jinja2:
//
// const AUTH_SERVICE_LOGIN_URL = "{{ auth_service_login_url|safe }}";
// const EVENT_SERVICE_API_BASE_URL = "{{ event_service_url|safe }}";
//
// If these are not defined globally, this script will fail or use defaults.

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const targetElement = document.querySelector(this.getAttribute('href'));
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// Mobile menu toggle
const mobileMenuButton = document.getElementById('mobile-menu-button');
const mobileMenu = document.getElementById('mobile-menu');
const closeMobileMenuButton = document.getElementById('close-mobile-menu');

function closeMobileMenuOnClick() {
    if (mobileMenu) {
        mobileMenu.classList.add('hidden');
    }
}

if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.addEventListener('click', () => {
        mobileMenu.classList.remove('hidden');
    });
}

if (closeMobileMenuButton && mobileMenu) {
    closeMobileMenuButton.addEventListener('click', () => {
        mobileMenu.classList.add('hidden');
    });
}

// Close mobile menu when a link inside it is clicked
if (mobileMenu) {
    mobileMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', closeMobileMenuOnClick);
    });
}


// Fetch and display upcoming events
document.addEventListener('DOMContentLoaded', function () {
    const eventsList = document.getElementById('events-list');
    const eventsLoading = document.getElementById('events-loading');
    const eventsError = document.getElementById('events-error');

    // Accessing global constants injected by Flask template.
    // Ensure these are available. If not, provide fallback or error.
    const effectiveAuthServiceLoginUrl = typeof AUTH_SERVICE_LOGIN_URL !== 'undefined' ? AUTH_SERVICE_LOGIN_URL : '';
    const effectiveEventServiceApiBaseUrl = typeof EVENT_SERVICE_API_BASE_URL !== 'undefined' ? EVENT_SERVICE_API_BASE_URL : '';


    // Ensure the base URL is available
    if (!effectiveEventServiceApiBaseUrl || effectiveEventServiceApiBaseUrl === "None" || effectiveEventServiceApiBaseUrl === "") {
        console.error('Event Service URL is not configured for the landing page.');
        if(eventsLoading) eventsLoading.style.display = 'none';
        if(eventsError) {
            eventsError.textContent = 'Event service configuration is missing. Cannot load events.';
            eventsError.classList.remove('hidden');
        }
        return;
    }

    // Your Event Service (original app.py) provides events at /events
    const ACTUAL_EVENTS_API_ENDPOINT = `${effectiveEventServiceApiBaseUrl}/events`;

    fetch(ACTUAL_EVENTS_API_ENDPOINT)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(events => {
            if(eventsLoading) eventsLoading.style.display = 'none';
            if (!Array.isArray(events)) { // Check if events is an array
                console.error('Received non-array data for events:', events);
                throw new Error('Invalid data format received for events.');
            }

            if (events.length === 0) {
                eventsList.innerHTML = `
                    <div class="col-span-full flex flex-col items-center justify-center py-16">
                        <img src="https://placehold.co/128x128/e0e0e0/757575?text=No+Events" alt="No Events" class="w-32 h-32 mb-6 opacity-70 rounded-full">
                        <div class="text-2xl font-semibold text-gray-400 mb-2">No events at the moment</div>
                        <div class="text-lg text-gray-500">Please check back soon for exciting updates!</div>
                    </div>
                `;
                return;
            }
            // Filter for upcoming events only
            const now = new Date();
            const upcomingEvents = events.filter(event => {
                try {
                    // The 'time' field from your event service is 'event_datetime_str'
                    return new Date(event.time) > now;
                } catch (e) {
                    console.warn("Could not parse date for event filtering:", event.name, event.time);
                    return false;
                }
            });

            if (upcomingEvents.length === 0) {
                eventsList.innerHTML = `
                    <div class="col-span-full flex flex-col items-center justify-center py-16">
                        <img src="https://placehold.co/128x128/e0e0e0/757575?text=All+Done" alt="No Upcoming Events" class="w-32 h-32 mb-6 opacity-70 rounded-full">
                        <div class="text-2xl font-semibold text-gray-400 mb-2">No upcoming events right now</div>
                        <div class="text-lg text-gray-500">All scheduled events have passed. Stay tuned for new announcements!</div>
                    </div>
                `;
                return;
            }

            eventsList.innerHTML = upcomingEvents.map(event => {
                let eventDateStr = 'Date N/A';
                try {
                    // 'time' is event_datetime_str from your Event Service
                    if (event.time) {
                        eventDateStr = new Date(event.time).toLocaleString([], {
                            year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
                        });
                    }
                } catch (e) { console.warn("Error formatting date for event:", event.name, event.time); }
                
                // Construct the full image URL
                let imageUrl = event.photo_url || 'https://placehold.co/500x300/65a30d/ffffff?text=Event';
                // Check if photo_url is relative (starts with '/') and prepend base URL if so
                if (event.photo_url && event.photo_url.startsWith('/') && effectiveEventServiceApiBaseUrl && effectiveEventServiceApiBaseUrl !== "None") {
                    imageUrl = effectiveEventServiceApiBaseUrl + event.photo_url;
                }


                return `
                <div class="bg-gradient-to-br from-green-100 via-yellow-100 to-pink-100 rounded-2xl shadow-xl overflow-hidden transform hover:scale-105 transition duration-300 ease-in-out animate__animated animate__fadeInUp glass">
                    <img src="${imageUrl}" alt="${event.name || 'Event Image'}" class="w-full h-56 object-cover" onerror="this.onerror=null;this.src='https://placehold.co/500x300/cccccc/ffffff?text=Image+Not+Available';">
                    <div class="p-8">
                        <h3 class="text-2xl font-semibold text-gray-900 mb-4">${event.name || 'Unnamed Event'}</h3>
                        <p class="text-gray-600 mb-5 text-sm leading-relaxed">${(event.details || 'No details available.').substring(0,150)}${event.details && event.details.length > 150 ? '...' : ''}</p>
                        <div class="flex items-center text-gray-500 text-sm mb-2">
                            <svg class="w-5 h-5 mr-2 text-green-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"></path></svg>
                            <span>${eventDateStr}</span>
                        </div>
                        <div class="flex items-center text-gray-500 text-sm">
                            <svg class="w-5 h-5 mr-2 text-green-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"></path></svg>
                            <span>${event.venue || 'Venue TBD'}</span>
                        </div>
                        <!-- Example of a dynamic link using the AUTH_SERVICE_LOGIN_URL if needed:
                        <a href="${effectiveAuthServiceLoginUrl}?event_id=${event.id}&redirect_to_event_details=true" class="mt-4 inline-block bg-green-500 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-green-600 transition">View Details & Register</a>
                        -->
                    </div>
                </div>
            `}).join('');
        })
        .catch(error => {
            if(eventsLoading) eventsLoading.style.display = 'none';
            if(eventsError) {
                eventsError.textContent = `Failed to load events: ${error.message}`;
                eventsError.classList.remove('hidden');
            }
            console.error('Error loading events:', error);
        });
});

// Any JS logic that relied on Flask-injected global constants (AUTH_SERVICE_LOGIN_URL, EVENT_SERVICE_API_BASE_URL)
// needs to ensure these constants are indeed available when this script runs.
// The `landing_page.html` (from Canvas landing_page_html_updated_v1) already includes:
// <script>
//     const AUTH_SERVICE_LOGIN_URL = "{{ auth_service_login_url|safe }}";
//     const EVENT_SERVICE_API_BASE_URL = "{{ event_service_url|safe }}";
// </script>
// This <script> block containing these constants should appear *before* linking this external JS file.
