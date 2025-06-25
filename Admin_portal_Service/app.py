import os
import json
import logging
import requests
import csv # Import the csv module
from io import StringIO # Import StringIO for in-memory CSV creation
from flask import Flask, render_template, jsonify, send_from_directory, request, redirect, Response # Import Response for CSV download

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

            response = requests.post(f"{EVENT_SERVICE_URL}/events/events", data=data, files=files, headers=headers, timeout=10)
            response.raise_for_status()
            app_logger.info(f"Event creation successful. Status: {response.status_code}")
            return jsonify(response.json()), response.status_code
        elif request.method == 'DELETE':
            event_id = request.path.split('/')[-1]
            if not event_id.isdigit():
                app_logger.error(f"Invalid event ID for delete: {event_id}")
                return jsonify({"error": "Invalid event ID provided for deletion."}), 400
                
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
        
        app_logger.debug(f"DB API Response Status for users: {response.status_code}")
        app_logger.debug(f"DB API Response Headers for users: {response.headers}")
        app_logger.debug(f"DB API Response Text for users: {response.text}")

        response.raise_for_status()

        users_data = response.json()
        
        if not isinstance(users_data, list):
            app_logger.warning(f"DB API for users returned non-list data (type: {type(users_data)}). Converting to list.")
            if isinstance(users_data, dict):
                users_data = [users_data]
            else:
                users_data = []

        app_logger.info(f"Successfully fetched {len(users_data)} users from DB API. Data preview: {str(users_data)[:100]}...")
        return jsonify(users_data), response.status_code
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
    except json.JSONDecodeError as e:
        app_logger.error(f"Failed to decode JSON from DB API response: {e}. Raw response: {response.text}", exc_info=True)
        return jsonify({"error": "Failed to parse user data from DB API. Invalid JSON response."}), 500
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
        url = f"{PARTICIPATION_SERVICE_URL}/participations"
        app_logger.info(f"Admin Portal: Fetching ALL participations from Participation Service at URL: '{url}'")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        all_participations = response.json()
        if not isinstance(all_participations, list):
            app_logger.warning(f"Participation Service returned non-list data: {type(all_participations)}. Attempting to convert.")
            all_participations = [all_participations] if isinstance(all_participations, dict) else []

        app_logger.info(f"Successfully fetched {len(all_participations)} participations from Participation Service. Now filtering internally.")

        # Step 2: Filter participations based on requested_event_id and search_query
        filtered_participations = []
        for p in all_participations:
            if requested_event_id and p.get('event_id') != requested_event_id:
                continue

            if search_query:
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
                    continue

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
# == NEW: CSV DUMP ENDPOINT FOR PARTICIPATIONS
# ==============================================================================
@app.route(f'{ADMIN_PORTAL_SCRIPT_NAME}/api/participations/download_csv', methods=['GET'])
def download_participations_csv():
    app_logger.debug(f"Request received for /api/participations/download_csv with query params: {request.args}")
    try:
        requested_event_id = request.args.get('eventId', type=int)
        search_query = request.args.get('query', '').lower()

        if not requested_event_id:
            return jsonify({"error": "Event ID is required to download participation CSV."}), 400

        # Reuse the logic from get_participations to fetch filtered data
        # We call it directly here, but ensure it returns the raw list of dicts.
        # Alternatively, refactor get_participations to be a helper function.
        # For simplicity, we'll adapt by calling the Participation_Service directly here as well,
        # and then filtering. This avoids circular dependencies if get_participations was to change.

        # Fetch ALL participations (or potentially filter at source if Participation_Service supports it)
        url = f"{PARTICIPATION_SERVICE_URL}/participations"
        app_logger.info(f"Admin Portal CSV: Fetching ALL participations from Participation Service for CSV generation at '{url}'")
        response = requests.get(url, timeout=15) # Increased timeout for potentially large data
        response.raise_for_status()
        all_participations = response.json()

        if not isinstance(all_participations, list):
            all_participations = [all_participations] if isinstance(all_participations, dict) else []

        # Apply filtering for requested_event_id and search_query
        filtered_participations = []
        for p in all_participations:
            if p.get('event_id') != requested_event_id:
                continue

            if search_query:
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
                    continue
            filtered_participations.append(p)
        
        if not filtered_participations:
            return jsonify({"message": f"No participation data found for event ID {requested_event_id} with given filters."}), 200

        # Define CSV headers (order matters for CSV output)
        # These headers should match the keys in your participation dictionaries
        fieldnames = [
            "id", "user_id", "user_name", "email_id", "phone_number",
            "event_id", "event_date", "tower", "flat_no",
            "num_tickets", "veg_heads", "non_veg_heads",
            "total_payable", "amount_paid", "payment_remaining",
            "additional_contribution", "contribution_comments",
            "status", "transaction_id", "registered_at", "updated_at"
        ]
        
        # Create an in-memory text buffer for the CSV data
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader() # Write the header row
        for row in filtered_participations:
            # Ensure all keys from fieldnames exist in row, provide empty string if missing
            cleaned_row = {field: row.get(field, '') for field in fieldnames}
            writer.writerow(cleaned_row)
        
        csv_output = output.getvalue()
        output.close()

        # Set response headers for file download
        filename = f"participations_event_{requested_event_id}.csv"
        response = Response(
            csv_output,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        app_logger.info(f"Generated CSV for event ID {requested_event_id}. Size: {len(csv_output)} bytes.")
        return response

    except requests.exceptions.RequestException as e:
        app_logger.error(f"Error fetching data for CSV via Participation Service: {e}. Details: {e.response.text if e.response else 'No response body'}", exc_info=True)
        status_code = e.response.status_code if e.response is not None else 503
        error_message = f"Participation service unavailable or API error during CSV generation: {str(e)}"
        try:
            error_details = e.response.json()
            error_message = error_details.get("error", error_message)
        except (json.JSONDecodeError, AttributeError):
            pass
        return jsonify({"error": error_message}), status_code
    except Exception as e:
        app_logger.critical(f"Unhandled error in download_participations_csv: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected internal server error occurred during CSV generation: {str(e)}"}), 500


# ==============================================================================
# == LOGOUT ENDPOINT (Similar to User Portal's logout flow)
# ==============================================================================

@app.route(f'{ADMIN_PORTAL_SCRIPT_NAME}/logout', methods=['GET', 'POST'])
def logout():
    app_logger.info(f"Admin is logging out. Redirecting to external Auth Service: {AUTH_SERVICE_EXTERNAL_URL}.")
    # IMPORTANT: As per latest script.js, this endpoint returns JSON,
    # and JS handles the browser redirect. So, this Flask redirect is technically
    # not directly used by the frontend for navigation anymore, but it's fine.
    # The actual redirect is handled client-side.
    return jsonify({"message": "Logout successful on Admin Portal backend."}), 200 # Return JSON for client-side fetch


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
    app.run(host='0.0.0.0', port=5003, debug=True)