import os
import json
import logging
import requests
from flask import Flask, jsonify, render_template, send_from_directory, redirect, request
from flask_cors import CORS

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Get the script name from environment variable ---
USER_PORTAL_SCRIPT_NAME = os.environ.get('FLASK_SCRIPT_NAME', '')

# --- Flask App Initialization ---
app = Flask(__name__,
            static_url_path=USER_PORTAL_SCRIPT_NAME + '/static',
            static_folder='static')
CORS(app)

# --- Service URLs from Environment Variables ---
DB_API_URL = os.environ.get('DB_API_URL', 'http://db_api:5004')
EVENT_SERVICE_URL = os.environ.get('EVENT_SERVICE_URL', 'http://event-service:5000')

# CRITICAL: Read AUTH_SERVICE_URL and ERS_LANDING_PAGE_URL from environment variables
# These will be set by docker-compose.yml using ${HOST_IP_OR_DOMAIN}
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'https://localhost/auth') # Default for local testing
ERS_LANDING_PAGE_URL = os.environ.get('ERS_LANDING_PAGE_URL', 'https://localhost/event-registration') # Default for local testing


# --- Crucial: Set APPLICATION_ROOT and SCRIPT_NAME for Nginx proxying ---
app.config['APPLICATION_ROOT'] = USER_PORTAL_SCRIPT_NAME

@app.before_request
def set_script_name_from_proxy():
    if 'X-Forwarded-Prefix' in request.headers:
        request.environ['SCRIPT_NAME'] = request.headers['X-Forwarded-Prefix']
    elif USER_PORTAL_SCRIPT_NAME:
        request.environ['SCRIPT_NAME'] = USER_PORTAL_SCRIPT_NAME
    else:
        request.environ['SCRIPT_NAME'] = ''


# ==============================================================================
# == API ENDPOINTS
# ==============================================================================

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    """Fetches a user's profile from the User DB service."""
    try:
        url = f"{DB_API_URL}/users/{user_id}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        user_data = response.json()
        if 'hashed_password' in user_data:
            del user_data['hashed_password']
        return jsonify(user_data), 200
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching profile for user {user_id}: {e}")
        return jsonify({"error": "Could not fetch user profile."}), 503

@app.route('/api/events', methods=['GET'])
def get_all_events():
    """Fetches the list of all events from the Event Service."""
    try:
        url = f"{EVENT_SERVICE_URL}/events"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching events: {e}")
        return jsonify({"error": "Could not fetch events."}), 503

# ==============================================================================
# == LOGOUT ENDPOINT
# ==============================================================================

@app.route(f'{USER_PORTAL_SCRIPT_NAME}/logout', methods=['GET', 'POST'])
def logout():
    """
    Handles user logout by redirecting to the main authentication service.
    This provides a single, server-controlled logout point.
    """
    app.logger.info(f"User is logging out. Redirecting to {AUTH_SERVICE_URL}.")
    return redirect(AUTH_SERVICE_URL)

# ==============================================================================
# == FRONTEND SERVING
# ==============================================================================
@app.route(f'{USER_PORTAL_SCRIPT_NAME}/portal/<int:user_id>')
def user_portal_page(user_id):
    """Serves the main single-page application for the user portal."""
    # Pass dynamic URLs to the template for JavaScript to use
    return render_template(
        'index.html',
        user_id=user_id,
        AUTH_SERVICE_URL=AUTH_SERVICE_URL,        # Pass AUTH_SERVICE_URL to template
        ERS_LANDING_PAGE_URL=ERS_LANDING_PAGE_URL # Pass ERS_LANDING_PAGE_URL to template
    )

@app.route(f'{USER_PORTAL_SCRIPT_NAME}/')
def portal_root():
    """A root endpoint to confirm the service is running."""
    return "User Portal Service is active. Access via /portal/&lt;user_id&gt;"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
