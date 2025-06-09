import os
import json
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from datetime import datetime
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

# --- API Endpoint for Relaying All Events from Event MS ---
@app.route('/user_portal/events', methods=['GET'])
def get_all_events_from_service():
    try:
        service_response = requests.get(f"{EVENT_SERVICE_URL}/events", timeout=10)
        service_response.raise_for_status()
        events_data = service_response.json()
        return jsonify(events_data), 200
    except requests.exceptions.Timeout:
        app.logger.error(f"Timeout when calling Event Management Service at {EVENT_SERVICE_URL}/events")
        return jsonify({"error": "Event Service timed out.", "details": "The service for fetching event data is taking too long to respond."}), 504
    except requests.exceptions.ConnectionError:
        app.logger.error(f"Connection error when calling Event Management Service at {EVENT_SERVICE_URL}/events")
        return jsonify({"error": "Could not connect to Event Service.", "details": "Unable to establish a connection with the service responsible for event data."}), 503
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error communicating with Event Management Service: {e}")
        return jsonify({"error": "Could not fetch events from Event Service.", "details": str(e)}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error fetching events: {e}")
        return jsonify({"error": "An unexpected error occurred while fetching events.", "details": str(e)}), 500

# --- API Endpoints for User Participations (interacting with Participation Service) ---
@app.route('/users/<int:user_id>/participation', methods=['GET'])
def get_user_participations(user_id):
    try:
        # CORRECTED ENDPOINT: Calling the renamed endpoint on the Participation Service
        participation_response = requests.get(f"{PARTICIPATION_SERVICE_URL}/users/{user_id}/participant-records", timeout=10)
        participation_response.raise_for_status()
        participations = participation_response.json()

        if not participations:
            return jsonify([]), 200

        all_events_response = requests.get(f"{EVENT_SERVICE_URL}/events", timeout=10)
        all_events_response.raise_for_status()
        all_events_list = all_events_response.json()
        
        events_map = {str(event['id']): event for event in all_events_list}

        augmented_participations = []
        for p_record in participations:
            event_detail = events_map.get(str(p_record.get('event_id')))
            
            aug_p = {
                "participation_id": p_record.get('id'), "event_id": p_record.get('event_id'),
                "user_id": p_record.get('user_id'), "user_name_display": p_record.get('user_name', f"User {user_id}"),
                "user_email_display": p_record.get('email_id', "N/A"), "user_status": p_record.get('status'),
                "details_from_participation_service": p_record 
            }

            if event_detail:
                aug_p.update({
                    "name": event_detail.get('name'), "date": event_detail.get('time') or event_detail.get('date'),
                    "location": event_detail.get('venue') or event_detail.get('location'),
                    "description": event_detail.get('details') or event_detail.get('description'),
                    "base_cover_charge_per_head": event_detail.get('subscription', {}).get('coverCharges') if event_detail.get('subscription', {}).get('coverChargesType') == 'per_head' else 0,
                    "cover_charge_type": event_detail.get('subscription', {}).get('coverChargesType', 'per_head')
                })
            else:
                aug_p["name"] = f"Event ID {p_record.get('event_id')} Details Not Found"
            
            augmented_participations.append(aug_p)
        
        return jsonify(augmented_participations), 200
    except requests.exceptions.RequestException as e:
        error_details_str = str(e)
        if e.response is not None:
            try: error_details_str = e.response.json().get('details', str(e))
            except: pass
        return jsonify({"error": "Could not fetch participation details.", "details": error_details_str}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error fetching user participations: {e}")
        return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500

@app.route('/users/<int:user_id>/participation/<int:event_id>', methods=['GET'])
def get_specific_user_participation(user_id, event_id):
    try:
        # CORRECTED ENDPOINT
        participation_response = requests.get(f"{PARTICIPATION_SERVICE_URL}/users/{user_id}/participant-records", timeout=10)
        participation_response.raise_for_status()
        all_user_participations = participation_response.json()
        
        specific_participation = None
        for p_record in all_user_participations:
            if str(p_record.get('event_id')) == str(event_id):
                specific_participation = p_record
                break
        
        if specific_participation:
            event_detail_response = requests.get(f"{EVENT_SERVICE_URL}/events/{event_id}", timeout=5)
            if event_detail_response.ok:
                specific_participation['event_details_for_modal'] = event_detail_response.json() 
            else:
                specific_participation['event_details_for_modal'] = None
            return jsonify(specific_participation), 200
        else:
            return jsonify({"error": "Participation record not found for this user and event"}), 404

    except requests.exceptions.RequestException as e:
        error_details_str = str(e)
        if e.response is not None:
            try: error_details_str = e.response.json().get('details', str(e))
            except: pass
        return jsonify({"error": "Could not fetch specific participation record.", "details": error_details_str}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error fetching specific participation: {e}")
        return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500

@app.route('/users/<int:user_id>/participation/<int:event_id>', methods=['POST'])
def manage_user_participation(user_id, event_id):
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid JSON payload"}), 400

    frontend_details = data.get('details', {})
    status = data.get('status')
    if not status: return jsonify({"error": "Missing 'status' field"}), 400

    user_name_from_frontend = frontend_details.get('participantName')
    if not user_name_from_frontend: return jsonify({"error": "Participant name is required"}), 400

    tower = frontend_details.get('towerNumber')
    floor = frontend_details.get('floorNumber')
    if not all([tower, floor is not None]): 
        return jsonify({"error": "Tower number and floor number are required"}), 400
        
    wing = frontend_details.get('wing', 'NA')
    flat_type = frontend_details.get('flatType', 'N/A')
    flat_detail_str = f"{tower}-{wing}-{flat_type}-{floor}"

    participation_payload = {
        "user_id": user_id, "user_name": user_name_from_frontend, "email_id": frontend_details.get('email'),
        "phone_number": frontend_details.get('phoneNumber'), "event_id": event_id, "status": status,
        "tower_number": tower, "wing": wing, "flat_type": flat_type, "floor_number": int(floor),
        "cover_charge_paid": frontend_details.get('coverChargePaid'),
        "additional_contribution": frontend_details.get('additionalContribution'),
        "veg_heads": frontend_details.get('vegHeads'), "non_veg_heads": frontend_details.get('nonVegHeads'),
        "flat_detail": flat_detail_str
    }

    existing_participation_id = None
    try:
        # CORRECTED ENDPOINT
        check_response = requests.get(f"{PARTICIPATION_SERVICE_URL}/users/{user_id}/participant-records", timeout=5)
        if check_response.ok:
            user_participations = check_response.json()
            for p in user_participations:
                if str(p.get('event_id')) == str(event_id) and p.get('flat_detail') == flat_detail_str:
                    existing_participation_id = p.get('id')
                    break
    except requests.exceptions.RequestException as e:
        app.logger.warning(f"Could not check for existing participation: {e}. Will attempt POST/create.")

    try:
        if existing_participation_id:
            app.logger.info(f"Updating existing record ID: {existing_participation_id}")
            # CORRECTED ENDPOINT for UPDATE
            service_response = requests.put(
                f"{PARTICIPATION_SERVICE_URL}/participant-records/{existing_participation_id}",
                json=participation_payload, timeout=10
            )
        else:
            app.logger.info(f"Creating new participant record")
            # CORRECTED ENDPOINT for CREATE
            service_response = requests.post(
                f"{PARTICIPATION_SERVICE_URL}/participant-records",
                json=participation_payload, timeout=10
            )
        
        service_response.raise_for_status()
        return service_response.json(), service_response.status_code

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error calling Participation Service: {e}")
        error_message = "Failed to submit participation to Participation Service."
        details_str = str(e)
        status_code = 503 
        if e.response is not None:
            status_code = e.response.status_code
            try:
                ps_error = e.response.json()
                error_message = ps_error.get("error", error_message)
                details_str = ps_error.get("details", details_str)
            except ValueError: 
                details_str = e.response.text[:200] if e.response.text else str(e) 
        return jsonify({"error": error_message, "details": details_str}), status_code
    except Exception as e:
        app.logger.error(f"Unexpected error submitting participation: {e}")
        return jsonify({"error": "An unexpected error occurred.", "details": str(e)}), 500

# --- Frontend Serving ---
@app.route('/portal/<int:user_id>')
def user_portal_page(user_id):
    return render_template('index.html', user_id=user_id)

@app.route('/')
def landing_page():
    return "Welcome to the User Portal (Stateless). Access via /portal/&lt;user_id&gt; (e.g., /portal/1)"

@app.route('/static/<path:filename>')
def serve_static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Changed port to 5001 as per your docker-compose file for this service
    app.run(host='0.0.0.0', port=5001, debug=True)
