import os
import json
import logging
import requests
from flask import Flask, render_template, jsonify, send_from_directory, request, redirect

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger(__name__)

# --- Get the script name from environment variable (similar to User Portal) ---
ADMIN_PORTAL_SCRIPT_NAME = os.environ.get('FLASK_SCRIPT_NAME', '')
app_logger.info(f"Admin Portal SCRIPT_NAME set to: '{ADMIN_PORTAL_SCRIPT_NAME}'")


# --- Flask App Initialization ---
app = Flask(__name__,
            static_url_path=ADMIN_PORTAL_SCRIPT_NAME + '/static',
            template_folder='templates',
            static_folder='static')
from flask_cors import CORS
CORS(app)
app_logger.info("Flask app initialized with CORS enabled.")

# --- Configuration for External Services (Internal Docker network URLs) ---
EVENT_SERVICE_URL = os.environ.get('EVENT_SERVICE_URL', 'http://event-service:5000')
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', 'http://auth_api:5002')
PARTICIPATION_SERVICE_URL = os.environ.get('PARTICIPATION_SERVICE_URL', 'http://participation-service:5005')
DB_API_URL = os.environ.get('DB_API_URL', 'http://db_api:5004')

app_logger.info(f"Internal Service URLs configured: Event='{EVENT_SERVICE_URL}', Auth='{AUTH_SERVICE_URL}', Participation='{PARTICIPATION_SERVICE_URL}', DB API='{DB_API_URL}'")


# CRITICAL: External facing URLs for redirects
AUTH_SERVICE_EXTERNAL_URL = os.environ.get('AUTH_SERVICE_EXTERNAL_URL', 'https://localhost/auth')
app_logger.info(f"External Redirect URLs configured: Auth='{AUTH_SERVICE_EXTERNAL_URL}'")


# --- Crucial: Set APPLICATION_ROOT and SCRIPT_NAME for Nginx proxying ---
app.config['APPLICATION_ROOT'] = ADMIN_PORTAL_SCRIPT_NAME
app_logger.debug(f"Flask APPLICATION_ROOT set to: '{app.config['APPLICATION_ROOT']}'")

@app.before_request
def set_script_name_from_proxy():
    if 'X-Forwarded-Prefix' in request.headers:
        request.environ['SCRIPT_NAME'] = request.headers['X-Forwarded-Prefix']
        app_logger.debug(f"SCRIPT_NAME set from X-Forwarded-Prefix: '{request.environ['SCRIPT_NAME']}'")
    elif ADMIN_PORTAL_SCRIPT_NAME:
        request.environ['SCRIPT_NAME'] = ADMIN_PORTAL_SCRIPT_NAME
        app_logger.debug(f"SCRIPT_NAME set from ADMIN_PORTAL_SCRIPT_NAME env var: '{request.environ['SCRIPT_NAME']}'")
    else:
        request.environ['SCRIPT_NAME'] = ''
        app_logger.debug("SCRIPT_NAME set to empty (no X-Forwarded-Prefix or env var).")


# ==============================================================================
# == ADMIN PORTAL API ENDPOINTS (Proxying to actual microservices)
# ==============================================================================

@app.route(f'{ADMIN_PORTAL_SCRIPT_NAME}/api/events', methods=['GET', 'POST', 'DELETE']) # Added DELETE method
def handle_events():
    app_logger.debug(f"Request received for /api/events with method: {request.method}")
    try:
        if request.method == 'GET':
            app_logger.info("Admin Portal: Attempting to fetch all events from Event Service.")
            # CRITICAL FIX: Ensure GET call to Event Service uses /events/events
            response = requests.get(f"{EVENT_SERVICE_URL}/events/events", timeout=10)
            response.raise_for_status()
            app_logger.info(f"Successfully fetched events. Status: {response.status_code}")
            return jsonify(response.json()), response.status_code
        elif request.method == 'POST':
            app_logger.info("Admin Portal: Attempting to create event via Event Service.")
            app_logger.debug(f"Received form data: {request.form.to_dict()}")
            app_logger.debug(f"Received files: {list(request.files.keys())}")

            files = {name: (file.filename, file.stream, file.content_type) for name, file in request.files.items()}
            data = request.form.to_dict()

            headers = {'Authorization': request.headers.get('Authorization')} if 'Authorization' in request.headers else {}
            if headers.get('Authorization'):
                app_logger.debug(f"Forwarding Authorization header: {headers['Authorization']}")

            # CRITICAL FIX: Ensure POST call to Event Service uses /events/events
            response = requests.post(f"{EVENT_SERVICE_URL}/events/events", data=data, files=files, headers=headers, timeout=10)
            response.raise_for_status()
            app_logger.info(f"Event creation successful. Status: {response.status_code}")
            return jsonify(response.json()), response.status_code
        elif request.method == 'DELETE':
            event_id = request.path.split('/')[-1] # Extract ID from URL path
            app_logger.info(f"Admin Portal: Attempting to delete event {event_id} via Event Service.")
            response = requests.delete(f"{EVENT_SERVICE_URL}/events/events/{event_id}", timeout=10)
            response.raise_for_status()
            app_logger.info(f"Event deletion successful. Status: {response.status_code}")
            return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        app_logger.error(f"Error handling events via Event Service: {e}. Details: {e.response.text if e.response else 'No response body'}", exc_info=True)
        status_code = e.response.status_code if e.response is not None else 503
        error_message = f"Event service unavailable or API error: {str(e)}"
        try:
            error_details = e.response.json()
            error_message = error_details.get("error", error_message)
        except (json.JSONDecodeError, AttributeError):
            pass
        return jsonify({"error": error_message}), status_code
    except Exception as e:
        app_logger.critical(f"Unhandled error in handle_events: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected internal server error occurred: {str(e)}"}), 500


@app.route(f'{ADMIN_PORTAL_SCRIPT_NAME}/api/users', methods=['GET'])
def get_all_users():
    app_logger.debug(f"Request received for /api/users with query params: {request.args}")
    try:
        search_query = request.args.get('query', '')
        url = f"{DB_API_URL}/users"
        params = {'query': search_query} if search_query else {}

        app_logger.info(f"Admin Portal: Attempting to fetch users from DB API Service at URL: '{url}' with params: {params}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        app_logger.info(f"Successfully fetched users from DB API. Status: {response.status_code}. Data preview: {str(response.json())[:100]}...")
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        app_logger.error(f"Error fetching users via DB API Service: {e}. Details: {e.response.text if e.response else 'No response body'}", exc_info=True)
        status_code = e.response.status_code if e.response is not None else 503
        error_message = f"DB API service unavailable or error: {str(e)}"
        try:
            error_details = e.response.json()
            error_message = error_details.get("error", error_message)
        except (json.JSONDecodeError, AttributeError):
            pass
        return jsonify({"error": error_message}), status_code
    except Exception as e:
        app_logger.critical(f"Unhandled error in get_all_users: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected internal server error occurred: {str(e)}"}), 500


@app.route(f'{ADMIN_PORTAL_SCRIPT_NAME}/api/participations', methods=['GET'])
def get_participations():
    app_logger.debug(f"Request received for /api/participations with query params: {request.args}")
    try:
        requested_event_id = request.args.get('eventId', type=int)
        search_query = request.args.get('query', '').lower()

        # Step 1: Fetch ALL participations from the Participation Service
        url = f"{PARTICIPATION_SERVICE_URL}/participations" # No eventId param here, fetch all
        app_logger.info(f"Admin Portal: Fetching ALL participations from Participation Service at URL: '{url}'")
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        all_participations = response.json()
        if not isinstance(all_participations, list):
            # Handle cases where the API might return a single object or non-list
            app_logger.warning(f"Participation Service returned non-list data: {type(all_participations)}. Attempting to convert.")
            all_participations = [all_participations] if isinstance(all_participations, dict) else []

        app_logger.info(f"Successfully fetched {len(all_participations)} participations from Participation Service. Now filtering internally.")

        # Step 2: Filter participations based on requested_event_id and search_query
        filtered_participations = []
        for p in all_participations:
            # Filter by event_id if provided by the frontend
            if requested_event_id and p.get('event_id') != requested_event_id:
                continue # Skip if event_id doesn't match

            # Apply search query filter
            if search_query:
                # Assuming search on user_name, email_id, tower, flat_no
                match = False
                if p.get('user_name') and search_query in p['user_name'].lower():
                    match = True
                elif p.get('email_id') and search_query in p['email_id'].lower():
                    match = True
                elif p.get('tower') and search_query in p['tower'].lower():
                    match = True
                elif p.get('flat_no') and search_query in p['flat_no'].lower():
                    match = True
                
                if not match:
                    continue # Skip if no search query match

            filtered_participations.append(p)
        
        app_logger.info(f"After internal filtering, returning {len(filtered_participations)} participations.")
        return jsonify(filtered_participations), 200

    except requests.exceptions.RequestException as e:
        app_logger.error(f"Error fetching participations via Participation Service: {e}. Details: {e.response.text if e.response else 'No response body'}", exc_info=True)
        status_code = e.response.status_code if e.response is not None else 503
        error_message = f"Participation service unavailable or API error: {str(e)}"
        try:
            error_details = e.response.json()
            error_message = error_details.get("error", error_message)
        except (json.JSONDecodeError, AttributeError):
            pass
        return jsonify({"error": error_message}), status_code
    except Exception as e:
        app_logger.critical(f"Unhandled error in get_participations: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected internal server error occurred: {str(e)}"}), 500


# ==============================================================================
# == LOGOUT ENDPOINT (Similar to User Portal's logout flow)
# ==============================================================================

@app.route(f'{ADMIN_PORTAL_SCRIPT_NAME}/logout', methods=['GET', 'POST'])
def logout():
    app_logger.info(f"Admin is logging out. Redirecting to external Auth Service: {AUTH_SERVICE_EXTERNAL_URL}.")
    return redirect(AUTH_SERVICE_EXTERNAL_URL)


# ==============================================================================
# == FRONTEND SERVING
# ==============================================================================
@app.route(f'{ADMIN_PORTAL_SCRIPT_NAME}/')
def admin_portal_home():
    app_logger.info(f"Serving admin_portal_home at path: '{request.path}'")
    return render_template(
        'index.html',
        AUTH_SERVICE_EXTERNAL_URL=AUTH_SERVICE_EXTERNAL_URL
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006,debug=True)