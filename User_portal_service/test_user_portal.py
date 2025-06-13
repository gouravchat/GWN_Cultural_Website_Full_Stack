import os
import json
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
import requests 
from flask_cors import CORS

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

app = Flask(__name__)
CORS(app) 

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key_for_stateless_portal')

# --- Service URLs ---
EVENT_SERVICE_URL = os.environ.get('EVENT_SERVICE_URL', 'http://localhost:5000') 
PARTICIPATION_SERVICE_URL = os.environ.get('PARTICIPATION_SERVICE_URL', 'http://localhost:5005') 
DB_API_URL = os.environ.get('DB_API_URL', 'http://localhost:5004')

# --- API Endpoint to get user profile data ---
@app.route('/api/users/<int:user_id>')
def get_user_profile(user_id):
    """
    Fetches a user's profile from the DB service and removes sensitive data.
    """
    try:
        url = f"{DB_API_URL}/users/{user_id}"
        app.logger.info(f"Proxying user profile request to: {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        user_data = response.json()
        
        # Remove the hashed password before sending data to the client
        if 'hashed_password' in user_data:
            del user_data['hashed_password']

        return jsonify(user_data), 200

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({"error": "User profile not found."}), 404
        return jsonify({"error": "Database service error."}), e.response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "The user profile service is unavailable."}), 503

# --- API Endpoint for Relaying All Events ---
@app.route('/user_portal/events', methods=['GET'])
def get_all_events_from_service():
    """Fetches all events by calling the Event Management Service."""
    try:
        service_response = requests.get(f"{EVENT_SERVICE_URL}/events", timeout=10)
        service_response.raise_for_status()
        return jsonify(service_response.json()), 200
    except requests.exceptions.RequestException as e:
        status = e.response.status_code if e.response is not None else 503
        return jsonify({"error": "Could not retrieve events."}), status

# --- API Endpoints for User Participation ---
@app.route('/users/<int:user_id>/participation', methods=['GET'])
def get_user_participations(user_id):
    """Gets all participation records for a specific user."""
    try:
        url = f"{PARTICIPATION_SERVICE_URL}/users/{user_id}/participant-records"
        service_response = requests.get(url, timeout=10)
        service_response.raise_for_status()
        return service_response.json(), service_response.status_code
    except requests.exceptions.RequestException as e:
        status = e.response.status_code if e.response is not None else 503
        return jsonify({"error": f"Failed to retrieve participations for user {user_id}."}), status

@app.route('/users/<int:user_id>/participation/<int:event_id>', methods=['POST'])
def handle_specific_participation(user_id, event_id):
    """Handles POSTing a new/updated participation record."""
    data = request.get_json()
    if not data or not isinstance(data.get("details"), dict):
        return jsonify({"error": "Invalid payload format."}), 400
    
    details = data["details"]

    try:
        user_profile_resp = requests.get(f"{DB_API_URL}/users/{user_id}", timeout=5)
        user_profile = user_profile_resp.json() if user_profile_resp.ok else {}
    except requests.RequestException:
        user_profile = {}
    
    # FIXED: Construct the full, correct payload for the Participation Service
    flat_detail_str = f"{details.get('towerNumber', 'N/A')}-{details.get('wing', 'N/A')}-{details.get('flatType', 'N/A')}-{details.get('floorNumber', 'N/A')}"

    participation_payload = {
        "user_id": user_id,
        "event_id": event_id,
        "user_name": details.get("participantName") or user_profile.get("username"),
        "email_id": details.get("email") or user_profile.get("email"),
        "phone_number": user_profile.get("phone_number"),
        "tower_number": details.get("towerNumber"),
        "wing": details.get("wing"),
        "flat_type": details.get("flatType"),
        "floor_number": details.get("floorNumber"),
        "flat_detail": flat_detail_str,
        "cover_charge_paid": details.get("coverChargePaid", 0.0),
        "additional_contribution": details.get("additionalContribution", 0.0),
        "veg_heads": details.get("vegHeads", 0),
        "non_veg_heads": details.get("nonVegHeads", 0),
        "status": data.get("status", "interested")
    }
    
    post_url = f"{PARTICIPATION_SERVICE_URL}/participant-records"
    app.logger.info(f"Submitting to Participation Service: {post_url} with payload: {participation_payload}")
    try:
        service_response = requests.post(post_url, json=participation_payload, timeout=10)
        service_response.raise_for_status()
        return service_response.json(), service_response.status_code
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error submitting participation: {e}")
        return jsonify({"error": "Failed to submit participation."}), 500

# --- Frontend Serving --
@app.route('/portal/<int:user_id>')
def user_portal_page(user_id):
    return render_template('index.html', user_id=user_id)

@app.route('/')
def portal_root():
    return "Welcome to the User Portal. Access via /portal/&lt;user_id&gt;"

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
