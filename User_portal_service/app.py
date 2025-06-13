import os
import json
import logging
import requests
from flask import Flask, jsonify, render_template, send_from_directory, redirect
from flask_cors import CORS

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Service URLs from Environment Variables ---
DB_API_URL = os.environ.get('DB_API_URL', 'http://db_api:5004')
EVENT_SERVICE_URL = os.environ.get('EVENT_SERVICE_URL', 'http://event-service:5000')
# Added AUTH_SERVICE_URL for proper logout redirection
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://localhost:5002') 

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

@app.route('/logout')
def logout():
    """
    Handles user logout by redirecting to the main authentication service.
    This provides a single, server-controlled logout point.
    """
    app.logger.info(f"User is logging out. Redirecting to {AUTH_SERVICE_URL}.")
    # Redirects the browser to the authentication service's login/logout page.
    return redirect(AUTH_SERVICE_URL)

# ==============================================================================
# == FRONTEND SERVING
# ==============================================================================
@app.route('/portal/<int:user_id>')
def user_portal_page(user_id):
    """Serves the main single-page application for the user portal."""
    return render_template('index.html', user_id=user_id)

@app.route('/')
def portal_root():
    """A root endpoint to confirm the service is running."""
    return "User Portal Service is active. Access via /portal/&lt;user_id&gt;"

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serves static files (JS, CSS) for the portal."""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
