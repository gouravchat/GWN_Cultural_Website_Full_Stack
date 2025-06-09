# app-service/app_service.py
import requests
from flask import Flask, request, jsonify, send_from_directory, redirect, url_for
import os
import json # Import json for parsing multipart form data

app = Flask(__name__, static_folder='static')

# The URL for the app-db service.
# In Docker Compose, 'db_api' is the service name, and 5001 is its internal port.
DB_API_BASE_URL = os.environ.get('DB_API_URL', 'http://db_api:5001')
# The URL for the app-auth service
# In Docker Compose, 'auth_api' is the service name, and 5002 is its internal port.
AUTH_API_BASE_URL = os.environ.get('AUTH_API_URL', 'http://auth_api:5002')
# The URL for the app-admin service
# In Docker Compose, 'admin_api' is the service name, and 5003 is its internal port.
ADMIN_API_BASE_URL = os.environ.get('ADMIN_API_URL', 'http://admin_api:5003')
# NEW: The URL for the app-events service
# In Docker Compose, 'events_api' is the service name, and 5005 is its internal port.
EVENTS_API_BASE_URL = os.environ.get('EVENTS_API_URL', 'http://events_api:5005')


# Route to serve the default HTML page (login.html)
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'login.html')
# Home page route
@app.route('/home')
def home():
    """
    Serves the home page (landing_page.html).
    """
    return send_from_directory(app.static_folder, 'landing_page.html')

# Route to serve other static HTML pages directly
@app.route('/<path:filename>')
def serve_static_html(filename):
    # This serves files like 'registration.html', 'register-success.html', 'user_details.html', 'admin_login.html', 'admin_dashboard.html'
    # Ensure only allowed static files are served to prevent directory traversal
    # List of allowed static HTML files all the entries in static folder
    allowed_files = [
        'registration.html',
        'register-success.html',
        'login.html',
        'user_details.html',
        'admin_login.html',
        'admin_dashboard.html',
        'admin_registration.html',  # Added admin_registration.html,
        'user_dashboard.html',
        'landing_page.html'
        ]
    
    if filename in allowed_files:
        return send_from_directory(app.static_folder, filename)
    # Optionally, return 404 for other requests if they are not meant to be served as static HTML
    return jsonify({"error": "File not found"}), 404

# Proxy for User Registration (to app-db service)
@app.route('/register', methods=['POST'])
def proxy_register():
    """
    Proxies registration requests to the database service (db_api).
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        db_api_response = requests.post(f"{DB_API_BASE_URL}/users", json=request.get_json())
        # Forward the response status and JSON content directly
        return jsonify(db_api_response.json()), db_api_response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Backend database service is unavailable for registration."}), 503
    except Exception as e:
        app.logger.error(f"Error during registration proxy: {e}")
        return jsonify({"error": "An unexpected error occurred during registration."}), 500

# Proxy for Login (to app-auth service)
@app.route('/login', methods=['POST'])
def proxy_login():
    """
    Proxies login requests to the authentication service (auth_api).
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        auth_api_response = requests.post(f"{AUTH_API_BASE_URL}/login", json=request.get_json())
        
        # Forward the response status and JSON content directly
        return jsonify(auth_api_response.json()), auth_api_response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Backend authentication service is unavailable."}), 503
    except Exception as e:
        app.logger.error(f"Error during login proxy: {e}")
        return jsonify({"error": "An unexpected error occurred during login."}), 500

# Proxy for getting user details by phone number (to app-db service)
@app.route('/api/users/<string:phone_number>', methods=['GET'])
def proxy_get_user(phone_number):
    """
    Proxies requests to get user details by phone number to the database service.
    """
    try:
        db_api_response = requests.get(f"{DB_API_BASE_URL}/users/{phone_number}")
        return jsonify(db_api_response.json()), db_api_response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Backend database service is unavailable."}), 503
    except Exception as e:
        app.logger.error(f"Error during get user proxy: {e}")
        return jsonify({"error": "An unexpected error occurred while fetching user details."}), 500

# Proxy for updating user details (to app-db service)
@app.route('/api/users/<string:phone_number>', methods=['PUT'])
def proxy_update_user(phone_number):
    """
    Proxies requests to update user details to the database service.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    try:
        db_api_response = requests.put(f"{DB_API_BASE_URL}/users/{phone_number}", json=request.get_json())
        return jsonify(db_api_response.json()), db_api_response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Backend database service is unavailable."}), 503
    except Exception as e:
        app.logger.error(f"Error during update user proxy: {e}")
        return jsonify({"error": "An unexpected error occurred while updating user details."}), 500

# NEW: Proxy for Admin Registration (to app-admin service)
@app.route('/admin/register', methods=['POST'])
def proxy_admin_register():
    """
    Proxies admin registration requests to the admin service (app-admin).
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        admin_api_response = requests.post(f"{ADMIN_API_BASE_URL}/admin/register", json=request.get_json())
        return jsonify(admin_api_response.json()), admin_api_response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Backend admin service is unavailable for registration."}), 503
    except Exception as e:
        app.logger.error(f"Error during admin registration proxy: {e}")
        return jsonify({"error": "An unexpected error occurred during admin registration."}), 500

# NEW: Proxy for Admin Login (to app-admin service)
@app.route('/admin/login', methods=['POST'])
def proxy_admin_login():
    """
    Proxies admin login requests to the admin service (app-admin).
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        admin_api_response = requests.post(f"{ADMIN_API_BASE_URL}/admin/login", json=request.get_json())
        return jsonify(admin_api_response.json()), admin_api_response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Backend admin service is unavailable for login."}), 503
    except Exception as e:
        app.logger.error(f"Error during admin login proxy: {e}")
        return jsonify({"error": "An unexpected error occurred during admin login."}), 500

# NEW: Proxy for getting all users (for admin dashboard)
@app.route('/api/admin/users', methods=['GET'])
def proxy_get_all_users_for_admin():
    """
    Proxies requests to get all user details to the database service for admin view.
    """
    try:
        db_api_response = requests.get(f"{DB_API_BASE_URL}/users")
        return jsonify(db_api_response.json()), db_api_response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Backend database service is unavailable."}), 503
    except Exception as e:
        app.logger.error(f"Error during get all users proxy for admin: {e}")
        return jsonify({"error": "An unexpected error occurred while fetching all user details."}), 500

# UPDATED: Proxy for creating an event (to app-events service)
@app.route('/api/events', methods=['POST'])
def proxy_create_event():
    """
    Proxies event creation requests to the events service.
    Handles multipart/form-data for file uploads.
    """
    # Ensure the request is multipart/form-data for file uploads
    if request.content_type and 'multipart/form-data' in request.content_type:
        try:
            # Forward the entire request data (including files) to the events_api
            # requests.request handles multipart/form-data automatically if request.data and files are passed
            events_api_response = requests.request(
                method=request.method,
                url=f"{EVENTS_API_BASE_URL}/events",
                headers={k: v for k, v in request.headers if k != 'Host'}, # Exclude Host header
                data=request.data, # This contains the raw multipart data
                stream=True # Important for handling large file uploads efficiently
            )
            # Forward the response status and JSON content directly
            return jsonify(events_api_response.json()), events_api_response.status_code
        except requests.exceptions.ConnectionError:
            return jsonify({"error": "Backend events service is unavailable for event creation."}), 503
        except Exception as e:
            app.logger.error(f"Error during event creation proxy: {e}")
            return jsonify({"error": "An unexpected error occurred during event creation."}), 500
    elif request.is_json:
        # This block handles cases where no file is uploaded, and the request is pure JSON
        event_data = request.get_json()
        try:
            events_api_response = requests.post(f"{EVENTS_API_BASE_URL}/events", json=event_data)
            return jsonify(events_api_response.json()), events_api_response.status_code
        except requests.exceptions.ConnectionError:
            return jsonify({"error": "Backend events service is unavailable for event creation."}), 503
        except Exception as e:
            app.logger.error(f"Error during event creation proxy: {e}")
            return jsonify({"error": "An unexpected error occurred during event creation."}), 500
    else:
        return jsonify({"error": "Unsupported Content-Type. Expected application/json or multipart/form-data."}), 415

# NEW: Proxy for getting all events (to app-events service)
@app.route('/api/events', methods=['GET'])
def proxy_get_all_events():
    """
    Proxies requests to get all events to the events service.
    """
    try:
        events_api_response = requests.get(f"{EVENTS_API_BASE_URL}/events")
        return jsonify(events_api_response.json()), events_api_response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Backend events service is unavailable."}), 503
    except Exception as e:
        app.logger.error(f"Error during get all events proxy: {e}")
        return jsonify({"error": "An unexpected error occurred while fetching events."}), 500

# NEW: Proxy for getting a single event by ID (to app-events service)
@app.route('/api/events/<int:event_id>', methods=['GET'])
def proxy_get_event(event_id):
    """
    Proxies requests to get a single event by ID to the events service.
    """
    try:
        events_api_response = requests.get(f"{EVENTS_API_BASE_URL}/events/{event_id}")
        return jsonify(events_api_response.json()), events_api_response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Backend events service is unavailable."}), 503
    except Exception as e:
        app.logger.error(f"Error during get event by ID proxy: {e}")
        return jsonify({"error": "An unexpected error occurred while fetching event details."}), 500

# NEW: Proxy for getting combined event details and participants (to app-events and app-db services)
@app.route('/api/admin/event-details/<int:event_id>', methods=['GET'])
def get_event_details_and_participants(event_id):
    """
    Fetches event details from the events service and then
    fetches participant details for that event from the participation service,
    and then fetches user details for each participant from the db service.
    Combines all this data and returns it.
    """
    try:
        # 1. Fetch event details from events_api
        event_response = requests.get(f"{EVENTS_API_BASE_URL}/events/{event_id}")
        event_response.raise_for_status()
        event_data = event_response.json()

        # 2. Fetch participation details for this event from events_api
        # Assuming events_api has an endpoint like /events/<event_id>/participations
        # If events_api doesn't have this, you'll need to implement it or fetch from a dedicated participation service.
        # For now, let's assume it returns an empty list if no participations, or a list of user_ids.
        # This part might need adjustment based on your actual events_api participation handling.
        participations_response = requests.get(f"{EVENTS_API_BASE_URL}/events/{event_id}/participations")
        participations_response.raise_for_status()
        participations_data = participations_response.json()

        # 3. For each participation, fetch user details from db_api
        participants_with_details = []
        for participation in participations_data:
            user_id = participation.get('user_id') # Assuming user_id is the phone_number
            if user_id:
                user_response = requests.get(f"{DB_API_BASE_URL}/users/{user_id}")
                user_response.raise_for_status()
                user_details = user_response.json()
                
                # Combine user and participation details
                participants_with_details.append({
                    "user_details": user_details,
                    "participation_details": participation
                })
            else:
                app.logger.warning(f"Participation record found without user_id: {participation}")

        return jsonify({
            "event": event_data,
            "participants": participants_with_details
        }), 200

    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Error fetching combined event data: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            return jsonify({"error": "Event or related data not found."}), 404
        return jsonify({"error": "Failed to fetch event details and participants.", "details": e.response.text}), e.response.status_code
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"Connection error fetching combined event data: {e}")
        return jsonify({"error": "Backend service unavailable while fetching event details and participants."}), 503
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during combined event data fetch: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

# NEW: Proxy for serving static event photos from events_api
@app.route('/static/event_photos/<filename>')
def serve_event_photo_proxy(filename):
    """
    Proxies requests for static event photos to the events_api service.
    This allows the browser to fetch images that were uploaded and stored by events_api.
    """
    url = f"{EVENTS_API_BASE_URL}/static/event_photos/{filename}"
    try:
        resp = requests.get(url, stream=True)
        # Return the raw response content and headers to the client
        response = app.response_class(resp.content, mimetype=resp.headers.get('Content-Type'))
        response.status_code = resp.status_code
        return response
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Events service (for photos) is unavailable"}), 503
    except Exception as e:
        app.logger.error(f"An unexpected error occurred while fetching photo: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred while fetching photo: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
