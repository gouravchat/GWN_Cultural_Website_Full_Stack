document.addEventListener('DOMContentLoaded', () => {
    // --- Basic Setup ---
    const bodyElement = document.body;
    const userId = bodyElement.dataset.userId;
    
    // Determine the base URL for API calls and internal redirects within the portal.
    // This dynamically determines the API base URL based on the current window location.
    // If we're at https://your-domain.com/user-portal/portal/<user_id>,
    // then userPortalApiBaseUrl will be '/user-portal'.
    const userPortalApiBaseUrl = window.location.pathname.startsWith('/user-portal') ? '/user-portal' : '';

    // Define the base URL for the Event Registration Service (ERS)
    // This should also be Nginx-proxied path if ERS is behind Nginx
    const ERS_LANDING_PAGE_URL = 'https://localhost/event-registration'; // Assuming Nginx proxies ERS at /event-registration
    // Updated AUTH_SERVICE_URL to correctly point to Nginx-proxied auth service
    const AUTH_SERVICE_URL = 'https://localhost/auth'; // Nginx proxies Auth Service at /auth

    // --- Safeguard ---
    if (!userId || userId.trim() === '' || userId === '{{ user_id }}') { // Check against raw Jinja string just in case
        // Use a custom modal or message box instead of alert()
        console.error("User ID not found. Redirecting to login.");
        // Redirect to the Nginx-proxied auth service login page
        window.location.href = `${AUTH_SERVICE_URL}/`; 
        return;
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
    const showSection = (targetId) => {
        contentSections.forEach(s => s.classList.toggle('hidden', s.id !== targetId));
        navLinks.forEach(l => l.classList.toggle('bg-gray-700', l.getAttribute('href') === `#${targetId}`));
        if (mobileHeaderTitle) {
            const activeLink = document.querySelector(`.nav-link[href="#${targetId}"] span`);
            if (activeLink) mobileHeaderTitle.textContent = activeLink.textContent;
        }
        window.location.hash = targetId;
        if (window.innerWidth < 768) closeSidebar();
    };
    
    const openSidebar = () => { if(sidebar) sidebar.classList.remove('-translate-x-full'); if(sidebarOverlay) sidebarOverlay.classList.remove('hidden'); };
    const closeSidebar = () => { if(sidebar) sidebar.classList.add('-translate-x-full'); if(sidebarOverlay) sidebarOverlay.classList.add('hidden'); }; // Fixed typo: add -> classList.add

    navLinks.forEach(link => link.addEventListener('click', e => {
        e.preventDefault();
        showSection(e.currentTarget.getAttribute('href').substring(1));
    }));
    
    if (menuButton) menuButton.addEventListener('click', openSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

    // Logout button event listener
    if (logoutButton) logoutButton.addEventListener('click', async () => {
        // Instead of a simple confirm(), use a custom modal for better UX if possible.
        // For now, let's use a basic confirm as per previous instructions.
        const userConfirmed = window.confirm("Are you sure you want to logout?"); // Use window.confirm instead of alert
        if (userConfirmed) {
            try {
                // Post to the Nginx-proxied logout endpoint for the User Portal
                // This will trigger the redirect set in User_Portal/app.py
                const response = await fetch(`${userPortalApiBaseUrl}/logout`, {
                    method: 'POST', // Use POST for logout for security best practice
                    headers: { 'Content-Type': 'application/json' }
                });
                if (response.ok) {
                    console.log("Logged out successfully from User Portal.");
                    // The backend /logout endpoint will handle the redirect
                    // So, client-side redirect not needed here, unless backend doesn't redirect.
                    // If backend redirect fails, then fall back to:
                    window.location.href = `${AUTH_SERVICE_URL}/`; 
                } else {
                    const errorData = await response.json();
                    console.error("Logout failed:", errorData.error);
                    // Display error message to user, e.g., via a toast
                }
            } catch (error) {
                console.error("Network error during logout:", error);
                // Display network error to user
            }
        }
    });

    // --- Data Display ---
    const displayUserProfile = (userData) => {
        const displayName = userData.username || 'N/A';
        const initial = displayName.charAt(0).toUpperCase();
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
    };

    const displayAllEvents = (events) => {
        eventsLoading.classList.add('hidden');
        eventsGrid.innerHTML = '';
        if (!events || events.length === 0) {
            eventsGrid.innerHTML = '<p class="col-span-full text-center">No events found.</p>';
            return;
        }
        events.forEach(event => {
            const card = document.createElement('div');
            card.className = 'card p-5 flex flex-col space-y-3';
            const eventDate = new Date(event.time).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
            card.innerHTML = `
                <h3 class="font-bold text-lg text-indigo-700">${event.name}</h3>
                <p class="text-sm text-gray-500">${eventDate}</p>
                <p class="text-sm flex-grow">${(event.details || '').substring(0,100)}...</p>
                <button data-event-id="${event.id}" class="participate-btn mt-auto bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700">Participate</button>
            `;
            eventsGrid.appendChild(card);
        });

        // This is the key logic for redirecting to the ERS
        document.querySelectorAll('.participate-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const eventId = e.currentTarget.dataset.eventId;
                // Construct the full URL for the ERS, passing the dynamic
                // userId and the selected eventId as query parameters.
                const registrationUrl = `${ERS_LANDING_PAGE_URL}/register?userId=${userId}&eventId=${eventId}`;
                window.location.href = registrationUrl;
            });
        });

        if (typeof lucide !== 'undefined') lucide.createIcons();
    };

    // --- API Calls ---
    const fetchUserProfile = async () => {
        try {
            // Prepend userPortalApiBaseUrl to API calls
            const response = await fetch(`${userPortalApiBaseUrl}/api/users/${userId}`);
            if (!response.ok) throw new Error('Failed to fetch profile');
            const data = await response.json();
            displayUserProfile(data);
        } catch(error) {
            console.error("Profile fetch error:", error);
            profileSection.innerHTML = `<p class="text-red-500">Could not load profile data.</p>`;
        }
    };

    const fetchAllEvents = async () => {
        eventsLoading.classList.remove('hidden');
        try {
            // Prepend userPortalApiBaseUrl to API calls
            const response = await fetch(`${userPortalApiBaseUrl}/api/events`);
            if (!response.ok) throw new Error('Failed to fetch events');
            const data = await response.json();
            displayAllEvents(data);
        } catch(error) {
            console.error("Events fetch error:", error);
            eventsLoading.classList.add('hidden');
            eventsGrid.innerHTML = `<p class="text-red-500 col-span-full">Could not load events.</p>`;
        }
    };
    
    // --- Initial Load ---
    const initializePortal = async () => {
        const initialSection = window.location.hash.substring(1) || 'profile';
        showSection(initialSection);
        await fetchUserProfile();
        await fetchAllEvents();
        if (typeof lucide !== 'undefined') lucide.createIcons();
    };

    initializePortal();
});
