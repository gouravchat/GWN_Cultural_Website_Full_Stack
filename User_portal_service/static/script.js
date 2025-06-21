document.addEventListener('DOMContentLoaded', () => {
    // --- Basic Setup ---
    const bodyElement = document.body;
    const userId = bodyElement.dataset.userId;
    
    // Determine the base URL for API calls and internal redirects within the portal.
    // This dynamically determines the API base URL based on the current window location.
    // If we're at https://your-domain.com/user-portal/portal/<user_id>,
    // then userPortalApiBaseUrl will be '/user-portal'.
    const userPortalApiBaseUrl = window.location.pathname.startsWith('/user-portal') ? '/user-portal' : '';

    // CRITICAL: Read these URLs from the global JavaScript constants injected by Flask
    // These constants (AUTH_SERVICE_URL_JS, ERS_LANDING_PAGE_URL_JS) are set in index.html
    // by the Flask backend using Jinja2 templating.
    const AUTH_SERVICE_URL = AUTH_SERVICE_URL_JS;
    const ERS_LANDING_PAGE_URL = ERS_LANDING_PAGE_URL_JS;

    // --- Safeguard ---
    // If no userId is found, the user is likely not authenticated. Redirect them.
    // The `userId === '{{ user_id }}'` check handles cases where Jinja2 failed to inject.
    if (!userId || userId.trim() === '' || userId === '{{ user_id }}') { 
        console.error("User ID not found. Redirecting to login.");
        // Redirect to the Nginx-proxied auth service login page
        window.location.href = `${AUTH_SERVICE_URL}/`; 
        return; // Stop further script execution
    }

    // --- DOM Element Selectors ---
    const sidebar = document.getElementById('sidebar');
    const menuButton = document.getElementById('menu-button');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const mobileHeaderTitle = document.getElementById('mobile-header-title');
    const navLinks = document.querySelectorAll('.nav-link');
    const contentSections = document.querySelectorAll('.content-section');
    const logoutButton = document.getElementById('logoutButton');
    
    const profileSection = document.getElementById('profile');
    const eventsGrid = document.getElementById('events-grid');
    const eventsLoading = document.getElementById('events-loading');
    
    // --- UI Logic (Navigation, Sidebar) ---
    /**
     * Shows the specified content section and updates navigation.
     * @param {string} targetId The ID of the section to show (e.g., 'profile', 'events').
     */
    const showSection = (targetId) => {
        // Hide all content sections except the target
        contentSections.forEach(s => s.classList.toggle('hidden', s.id !== targetId));
        // Highlight the active navigation link
        navLinks.forEach(l => l.classList.toggle('bg-gray-700', l.getAttribute('href') === `#${targetId}`));
        // Update mobile header title based on active section
        if (mobileHeaderTitle) {
            const activeLink = document.querySelector(`.nav-link[href="#${targetId}"] span`);
            if (activeLink) mobileHeaderTitle.textContent = activeLink.textContent;
        }
        // Update URL hash for direct linking/bookmarking
        window.location.hash = targetId;
        // Close sidebar on mobile after selection
        if (window.innerWidth < 768) closeSidebar();
    };
    
    /** Opens the mobile sidebar. */
    const openSidebar = () => { 
        if(sidebar) sidebar.classList.remove('-translate-x-full'); 
        if(sidebarOverlay) sidebarOverlay.classList.remove('hidden'); 
    };

    /** Closes the mobile sidebar. */
    const closeSidebar = () => { 
        if(sidebar) sidebar.classList.add('-translate-x-full'); 
        if(sidebarOverlay) sidebarOverlay.classList.add('hidden'); 
    };

    // Add click listeners to navigation links
    navLinks.forEach(link => link.addEventListener('click', e => {
        e.preventDefault(); // Prevent default anchor jump
        showSection(e.currentTarget.getAttribute('href').substring(1)); // Get section ID from href
    }));
    
    // Add event listeners for mobile menu toggle
    if (menuButton) menuButton.addEventListener('click', openSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

    // Logout button event listener
    if (logoutButton) logoutButton.addEventListener('click', async () => {
        // Use window.confirm for a simple confirmation dialog (replace with custom modal for better UX)
        const userConfirmed = window.confirm("Are you sure you want to logout?"); 
        if (userConfirmed) {
            try {
                // Send a POST request to the Nginx-proxied logout endpoint for the User Portal
                const response = await fetch(`${userPortalApiBaseUrl}/logout`, {
                    method: 'POST', 
                    headers: { 'Content-Type': 'application/json' }
                });
                if (response.ok) {
                    console.log("Logged out successfully from User Portal.");
                    // Explicit client-side redirect using the dynamically read AUTH_SERVICE_URL
                    // This ensures the browser navigates to the login page correctly.
                    window.location.href = `${AUTH_SERVICE_URL}/`; 
                } else {
                    const errorData = await response.json();
                    console.error("Logout failed:", errorData.error);
                    // TODO: Implement a user-facing error message (e.g., a toast notification)
                }
            } catch (error) {
                console.error("Network error during logout:", error);
                // TODO: Implement a user-facing network error message
            }
        }
    });

    // --- Data Display Functions ---
    /**
     * Displays the fetched user profile data in the profile section.
     * @param {object} userData - The user profile data.
     */
    const displayUserProfile = (userData) => {
        const displayName = userData.username || 'N/A';
        const initial = displayName.charAt(0).toUpperCase(); // Get first letter for avatar
        const profileContent = `
            <div class="flex flex-col sm:flex-row items-center sm:space-x-6">
                <div class="mb-4 sm:mb-0">
                    <img src="https://placehold.co/96x96/A78BFA/FFFFFF?text=${initial}" alt="User Avatar" class="w-24 h-24 rounded-full border-4 border-white shadow-md">
                </div>
                <div class="text-center sm:text-left">
                    <h3 class="text-2xl font-bold text-gray-900">${displayName}</h3>
                    <p class="text-md text-gray-500 mt-1">${userData.email || 'N/A'}</p>
                </div>
            </div>
            <hr class="my-8">
            <div>
                <h4 class="text-lg font-semibold text-gray-700 mb-4">Account Details</h4>
                <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
                    <div><dt class="text-sm font-medium text-gray-500">User ID</dt><dd class="mt-1 text-sm text-gray-900">${userId}</dd></div>
                    <div><dt class="text-sm font-medium text-gray-500">Role</dt><dd class="mt-1 text-sm text-gray-900">${userData.role || 'N/A'}</dd></div>
                    <div class="sm:col-span-2"><dt class="text-sm font-medium text-gray-500">Phone Number</dt><dd class="mt-1 text-sm text-gray-900">${userData.phone_number || 'N/A'}</dd></div>
                </dl>
            </div>`;
        profileSection.innerHTML = profileContent;
        // Re-create Lucide icons if any were added dynamically
        if (typeof lucide !== 'undefined') lucide.createIcons();
    };

    /**
     * Displays the fetched list of events in the events grid.
     * @param {Array<object>} events - An array of event objects.
     */
    const displayAllEvents = (events) => {
        eventsLoading.classList.add('hidden'); // Hide loading spinner
        eventsGrid.innerHTML = ''; // Clear previous events
        if (!events || events.length === 0) {
            eventsGrid.innerHTML = '<p class="col-span-full text-center text-gray-600">No events found.</p>';
            return;
        }
        events.forEach(event => {
            const card = document.createElement('div');
            card.className = 'card p-5 flex flex-col space-y-3'; // Tailwind classes for card styling
            // Format event date
            const eventDate = new Date(event.time).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
            card.innerHTML = `
                <h3 class="font-bold text-lg text-indigo-700">${event.name}</h3>
                <p class="text-sm text-gray-500">${eventDate}</p>
                <p class="text-sm flex-grow">${(event.details || '').substring(0,100)}...</p>
                <button data-event-id="${event.id}" class="participate-btn mt-auto bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 transition duration-300 ease-in-out">Participate</button>
            `;
            eventsGrid.appendChild(card);
        });

        // Add event listeners to newly created participate buttons
        document.querySelectorAll('.participate-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const eventId = e.currentTarget.dataset.eventId;
                // Construct the full URL for the Event Registration Service (ERS)
                // Dynamically pass userId and eventId as query parameters.
                const registrationUrl = `${ERS_LANDING_PAGE_URL}/portal/${userId}/${eventId}`;
                window.location.href = registrationUrl;
            });
        });

        // Create Lucide icons if any were added dynamically (e.g., in event details)
        if (typeof lucide !== 'undefined') lucide.createIcons();
    };

    // --- API Calls ---
    /** Fetches the user's profile data from the backend API. */
    const fetchUserProfile = async () => {
        try {
            // Prepend userPortalApiBaseUrl to API calls (e.g., /user-portal/api/users/123)
            const response = await fetch(`${userPortalApiBaseUrl}/api/users/${userId}`);
            if (!response.ok) {
                // If response is not OK, throw an error with more detail if possible
                const errorText = await response.text();
                throw new Error(`Failed to fetch profile: ${response.status} ${response.statusText} - ${errorText}`);
            }
            const data = await response.json();
            displayUserProfile(data);
        } catch(error) {
            console.error("Profile fetch error:", error);
            profileSection.innerHTML = `<p class="text-red-500 col-span-full text-center">Could not load profile data. Please try again later.</p>`;
            // TODO: Implement a toast notification for the user
        }
    };

    /** Fetches all events from the backend API. */
    const fetchAllEvents = async () => {
        eventsLoading.classList.remove('hidden'); // Show loading spinner
        try {
            // Prepend userPortalApiBaseUrl to API calls (e.g., /user-portal/api/events)
            const response = await fetch(`${userPortalApiBaseUrl}/api/events`);
            if (!response.ok) {
                // If response is not OK, throw an error with more detail
                const errorText = await response.text();
                throw new Error(`Failed to fetch events: ${response.status} ${response.statusText} - ${errorText}`);
            }
            const data = await response.json();
            displayAllEvents(data);
        } catch(error) {
            console.error("Events fetch error:", error);
            eventsLoading.classList.add('hidden'); // Hide loading spinner on error
            eventsGrid.innerHTML = `<p class="text-red-500 col-span-full text-center">Could not load events. Please try again later.</p>`;
            // TODO: Implement a toast notification for the user
        }
    };
    
    // --- Initial Load Logic ---
    /** Initializes the User Portal by showing the default section and fetching initial data. */
    const initializePortal = async () => {
        // Determine initial section from URL hash or default to 'profile'
        const initialSection = window.location.hash.substring(1) || 'profile';
        showSection(initialSection); // Show the initial section
        
        // Fetch data concurrently
        await Promise.all([
            fetchUserProfile(),
            fetchAllEvents()
        ]);

        // Create Lucide icons that were part of the initial HTML load
        if (typeof lucide !== 'undefined') lucide.createIcons();
    };

    // Initialize the portal when the DOM is fully loaded
    initializePortal();
});
