import os
from flask import Flask, render_template, jsonify, send_from_directory, redirect, url_for

# Initialize Flask app
# The template_folder and static_folder are correctly set if your
# 'templates' and 'static' directories are at the same level as this app.py
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Configuration for External Services ---
# These URLs should point to your actual running services.

# Event Service URL (from your original event service app.py, likely on port 5000)
EVENT_SERVICE_BASE_URL = os.environ.get('EVENT_SERVICE_URL', 'http://localhost:5000')

# Auth Service URL (from your uploaded Auth Service app.py, running on port 5004)
# This service provides the /users endpoints.
AUTH_SERVICE_BASE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://localhost:5004') # Updated port and purpose

# --- Routes for Admin Portal ---

@app.route('/')
def admin_portal_home():
    """
    Serves the main Admin Portal HTML page.
    Authentication is assumed to be handled by an external Auth Service,
    which then redirects the authenticated admin user here.
    """
    return render_template('index.html')

@app.route('/config')
def get_portal_configuration():
    """
    Provides frontend JavaScript with necessary configuration,
    such as the base URLs for external services.
    """
    return jsonify({
        "eventServiceBaseUrl": EVENT_SERVICE_BASE_URL,
        "authServiceBaseUrl": AUTH_SERVICE_BASE_URL # Changed key for clarity
        # Add other service URLs as needed
    })

# --- Static File Serving ---
@app.route('/static/<path:filename>')
def serve_static_files(filename):
    """Serves static files (CSS, JS, images) from the 'static' folder."""
    return send_from_directory(app.static_folder, filename)


if __name__ == '__main__':
    # The Admin Portal backend itself runs on a different port (e.g., 5001)
    # from the Event Service (e.g., 5000) and Auth Service (e.g., 5004).
    # Debug should be False in a production environment.
    app.run(host='0.0.0.0', port=5003, debug=True)
