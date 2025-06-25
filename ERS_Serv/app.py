from flask import Flask, request, jsonify, render_template, url_for
from flask_cors import CORS
import requests
from datetime import datetime, timezone
import os
import uuid
import logging
import json # Ensure json is imported for JSONDecodeError
from werkzeug.exceptions import HTTPException # Import for custom error handling
import traceback # Import traceback to print full stack traces

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger(__name__)

# --- Get script name for this ERS service from environment variable ---
ERS_SCRIPT_NAME = os.environ.get('FLASK_SCRIPT_NAME', '')

# --- Flask App Initialization ---
app = Flask(__name__,
            static_url_path=ERS_SCRIPT_NAME + '/static',
            static_folder='static',
            template_folder='templates')
CORS(app)


# --- Crucial: Set APPLICATION_ROOT and SCRIPT_NAME for Nginx proxying ---
app.config['APPLICATION_ROOT'] = ERS_SCRIPT_NAME

@app.before_request
def set_script_name_from_proxy():
    if 'X-Forwarded-Prefix' in request.headers:
        request.environ['SCRIPT_NAME'] = request.headers['X-Forwarded-Prefix']
    elif ERS_SCRIPT_NAME:
        request.environ['SCRIPT_NAME'] = ERS_SCRIPT_NAME
    else:
        request.environ['SCRIPT_NAME'] = ''

# --- Service URLs from Environment Variables for INTERNAL Docker network calls ---
USER_SERVICE_INTERNAL_URL = os.environ.get('DB_API_URL', 'http://db_api:5004')
EVENT_SERVICE_INTERNAL_URL = os.environ.get('EVENT_SERVICE_URL', 'http://event-service:5000')
PARTICIPATION_SERVICE_INTERNAL_URL = os.environ.get('PARTICIPATION_SERVICE_URL', 'http://participation-service:5005')

# NEW: User Portal Root URL for redirection after logout (from environment variable)
USER_PORTAL_ROOT_URL = os.environ.get('USER_PORTAL_ROOT_URL', 'https://localhost/user-portal') # Default for local testing


app_logger.info(f"ERS_SCRIPT_NAME: {ERS_SCRIPT_NAME}")
app_logger.info(f"USER_SERVICE_INTERNAL_URL: {USER_SERVICE_INTERNAL_URL}")
app_logger.info(f"EVENT_SERVICE_INTERNAL_URL: {EVENT_SERVICE_INTERNAL_URL}")
app_logger.info(f"PARTICIPATION_SERVICE_INTERNAL_URL: {PARTICIPATION_SERVICE_INTERNAL_URL}")
app_logger.info(f"USER_PORTAL_ROOT_URL: {USER_PORTAL_ROOT_URL}")


# Helper function to fetch user data internally
def get_user_data_internal(user_id):
    """Fetches user data from the internal DB_API service."""
    try:
        user_response = requests.get(f"{USER_SERVICE_INTERNAL_URL}/users/{user_id}", verify=False, timeout=2)
        user_response.raise_for_status()
        user_data = user_response.json()
        return {
            "id": user_data.get('id'),
            "username": user_data.get('username'),
            "email": user_data.get('email'),
            "phone_number": user_data.get('phone_number')
        }
    except requests.exceptions.RequestException as e:
        app_logger.error(f"Error fetching user data from DB_API for user {user_id}: {e}")
        return {
            "id": user_id,
            "username": f"DummyUser{user_id}",
            "email": f"dummy{user_id}@example.com",
            "phone_number": f"999{str(user_id).zfill(7)}"
        }

# Helper function to fetch event data internally
def get_event_data_internal(event_id):
    """Fetches event data from the internal Event Service."""
    try:
        event_response = requests.get(f"{EVENT_SERVICE_INTERNAL_URL}/events/events/{event_id}", verify=False, timeout=2)
        event_response.raise_for_status()
        event_data = event_response.json()

        subscription_data = event_data.get('subscription', {})
        food_data = event_data.get('food', {})

        return {
            "id": event_data.get('id'),
            "name": event_data.get('name'),
            "time": event_data.get('time'),
            "close_date": event_data.get('close_date'),
            "venue": event_data.get('venue'),
            "details": event_data.get('details'),
            "cover_charges": subscription_data.get('coverCharges', 0.0),
            "cover_charges_type": subscription_data.get('coverChargesType', 'per_head'),
            # Updated: Retrieve new food charge fields
            "veg_food_charges": food_data.get('vegFoodCharges', 0.0),
            "veg_food_charges_type": food_data.get('vegFoodChargesType', 'per_head'),
            "non_veg_food_charges": food_data.get('nonVegFoodCharges', 0.0),
            "non_veg_food_charges_type": food_data.get('nonVegFoodChargesType', 'per_head')
        }
    except requests.exceptions.RequestException as e:
        app_logger.error(f"Error fetching event data from Event Service for event {event_id}: {e}")
        return {
            "id": event_id,
            "name": "Dummy Event",
            "time": "18:00",
            "close_date": "2025-12-30",
            "venue": "Virtual",
            "details": "This is a dummy event.",
            "cover_charges": 50.0,
            "cover_charges_type": "per_head",
            # Dummy values for new food fields
            "veg_food_charges": 15.0,
            "veg_food_charges_type": "per_head",
            "non_veg_food_charges": 25.0,
            "non_veg_food_charges_type": "per_head"
        }

# --- Frontend Serving Endpoint ---
@app.route(f'{ERS_SCRIPT_NAME}/portal/<int:user_id>/<int:event_id>')
@app.route(f'{ERS_SCRIPT_NAME}/portal/<int:user_id>')
@app.route(f'{ERS_SCRIPT_NAME}/portal/')
def serve_frontend(user_id=None, event_id=None):
    if user_id is None:
        user_id = 4
    if event_id is None:
        event_id = 1

    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    host_with_port = request.headers.get('X-Forwarded-Host', request.host)
    
    external_root = f"{scheme}://{host_with_port}"

    user_info = get_user_data_internal(user_id)
    event_info = get_event_data_internal(event_id)

    user_api_external_url = f"{external_root}/user-portal/api/users/{user_id}"
    events_api_external_url = f"{external_root}/events/events/{event_id}"
    part_api_external_url = f"{external_root}/participations/participations" 

    ers_calculate_price_api = f"{external_root}{ERS_SCRIPT_NAME}/calculate_price"
    ers_start_participation_api = f"{external_root}{ERS_SCRIPT_NAME}/start_participation"
    ers_edit_participation_api = f"{external_root}{ERS_SCRIPT_NAME}/edit_participation"
    ers_delete_participation_api = f"{external_root}{ERS_SCRIPT_NAME}/delete_participation"
    ers_payment_callback_api = f"{external_root}{ERS_SCRIPT_NAME}/payment_callback"
    
    # NEW API endpoint for checking participation
    ers_check_participation_api = f"{external_root}{ERS_SCRIPT_NAME}/check_participation"


    return render_template(
        'index.html',
        user_id=user_id,
        event_id=event_id,
        user_data_json=user_info,
        event_data_json=event_info,
        USER_API_URL=user_api_external_url,
        EVENTS_API_URL=events_api_external_url,
        PART_API_URL=part_api_external_url,
        ERS_CALCULATE_PRICE_API=ers_calculate_price_api,
        ERS_START_PARTICIPATION_API=ers_start_participation_api,
        ERS_EDIT_PARTICIPATION_API=ers_edit_participation_api,
        ERS_DELETE_PARTICIPATION_API=ers_delete_participation_api,
        ERS_PAYMENT_CALLBACK_API=ers_payment_callback_api,
        ERS_CHECK_PARTICIPATION_API=ers_check_participation_api,
        USER_PORTAL_ROOT_URL=USER_PORTAL_ROOT_URL # Pass new URL for user portal to template
    )

@app.route(f'{ERS_SCRIPT_NAME}/calculate_price', methods=['POST'])
def calculate_price():
    data = request.json
    user_id = data.get('user_id')
    event_id = data.get('event_id')
    num_tickets = data.get('num_tickets', 0)
    veg_heads = data.get('veg_heads', 0)
    non_veg_heads = data.get('non_veg_heads', 0)
    additional_contribution = data.get('additional_contribution', 0.0)

    app_logger.debug(f"Calculate Price - Incoming Data: {data}")

    if not user_id or not event_id:
        return jsonify({"error": "User ID and Event ID are required"}), 400

    event_data = get_event_data_internal(event_id)
    
    app_logger.debug(f"Calculate Price - Fetched Event Data: {event_data}")

    cover_charges = event_data.get('cover_charges', 0.0)
    cover_charges_type = event_data.get('cover_charges_type', 'per_head')
    
    # Updated: Get specific veg and non-veg food charges and types
    veg_food_charges = event_data.get('veg_food_charges', 0.0)
    veg_food_charges_type = event_data.get('veg_food_charges_type', 'per_head')
    non_veg_food_charges = event_data.get('non_veg_food_charges', 0.0)
    non_veg_food_charges_type = event_data.get('non_veg_food_charges_type', 'per_head')

    total_cover_cost = 0.0
    if cover_charges_type == 'per_head':
        total_cover_cost = cover_charges * num_tickets
    elif cover_charges_type == 'per_family':
        total_cover_cost = cover_charges

    total_food_cost = 0.0
    # Calculate veg food cost
    if veg_food_charges_type == 'per_head':
        total_food_cost += veg_food_charges * veg_heads
    elif veg_food_charges_type == 'per_family':
        total_food_cost += veg_food_charges
    
    # Calculate non-veg food cost
    if non_veg_food_charges_type == 'per_head':
        total_food_cost += non_veg_food_charges * non_veg_heads
    elif non_veg_food_charges_type == 'per_family':
        total_food_cost += non_veg_food_charges

    total_payable = total_cover_cost + total_food_cost + additional_contribution 

    app_logger.debug(f"Calculate Price - Final Total Payable: {total_payable}")

    response_payload = {
        "user_id": user_id,
        "event_id": event_id,
        "num_tickets": num_tickets,
        "veg_heads": veg_heads,
        "non_veg_heads": non_veg_heads,
        "calculated_price": total_payable,
        "cover_charges": cover_charges,
        "cover_charges_type": cover_charges_type,
        # Updated: Include specific veg and non-veg food charges and types in response
        "veg_food_charges": veg_food_charges,
        "veg_food_charges_type": veg_food_charges_type,
        "non_veg_food_charges": non_veg_food_charges,
        "non_veg_food_charges_type": non_veg_food_charges_type
    }
    if "Dummy Event" in event_data.get('name', ''):
        response_payload["warning"] = "Could not fetch actual event prices. Using defaults."

    return jsonify(response_payload), 200

# --- NEW: Endpoint to start (create) a new participation record ---
@app.route(f'{ERS_SCRIPT_NAME}/start_participation', methods=['POST'])
def start_participation():
    data = request.json
    user_id = data.get('user_id')
    event_id = data.get('event_id')
    num_tickets = data.get('num_tickets', 1)
    veg_heads = data.get('veg_heads', 0)
    non_veg_heads = data.get('non_veg_heads', 0)
    additional_contribution = data.get('additional_contribution', 0.0)
    tower = data.get('tower')
    flat_no = data.get('flat_no')

    app_logger.debug(f"Start Participation - Incoming Data: {data}")

    if not user_id or not event_id:
        return jsonify({"error": "User ID and Event ID are required"}), 400
    if not tower or not flat_no:
        return jsonify({"error": "Tower Number and Flat Number are required"}), 400

    user_info = get_user_data_internal(user_id)
    event_data = get_event_data_internal(event_id)

    # Recalculate payable amount based on current input and event data
    cover_charges = event_data.get('cover_charges', 0.0)
    cover_charges_type = event_data.get('cover_charges_type', 'per_head')
    
    # Updated: Get specific veg and non-veg food charges and types
    veg_food_charges = event_data.get('veg_food_charges', 0.0)
    veg_food_charges_type = event_data.get('veg_food_charges_type', 'per_head')
    non_veg_food_charges = event_data.get('non_veg_food_charges', 0.0)
    non_veg_food_charges_type = event_data.get('non_veg_food_charges_type', 'per_head')

    total_cover_cost = 0.0
    if cover_charges_type == 'per_head':
        total_cover_cost = cover_charges * num_tickets
    elif cover_charges_type == 'per_family':
        total_cover_cost = cover_charges

    total_food_cost = 0.0
    # Calculate veg food cost
    if veg_food_charges_type == 'per_head':
        total_food_cost += veg_food_charges * veg_heads
    elif veg_food_charges_type == 'per_family':
        total_food_cost += veg_food_charges
    
    # Calculate non-veg food cost
    if non_veg_food_charges_type == 'per_head':
        total_food_cost += non_veg_food_charges * non_veg_heads
    elif non_veg_food_charges_type == 'per_family':
        total_food_cost += non_veg_food_charges
    
    total_payable = total_cover_cost + total_food_cost + additional_contribution

    now = datetime.now(timezone.utc)
    registered_at = now.isoformat()
    updated_at = now.isoformat()

    participation_data = {
        'user_id': user_id,
        'user_name': user_info.get('username'),
        'phone_number': user_info.get('phone_number'),
        'email_id': user_info.get('email'),
        'event_id': event_id,
        'event_date': event_data.get('close_date'),
        'tower': tower,
        'flat_no': flat_no,
        'total_payable': total_payable,
        'amount_paid': 0.0, # Initial state: 0 paid
        'payment_remaining': total_payable, # Initially full amount remaining
        'additional_contribution': additional_contribution,
        'contribution_comments': data.get('contribution_comments', ''),
        'num_tickets': num_tickets,
        'veg_heads': veg_heads,
        'non_veg_heads': non_veg_heads,
        'status': 'pending_payment', # Set status to pending payment
        'transaction_id': None, # No transaction ID yet
        'registered_at': registered_at,
        'updated_at': updated_at
    }

    try:
        response = requests.post(
            f"{PARTICIPATION_SERVICE_INTERNAL_URL}/participations",
            json=participation_data,
            verify=False
        )

        if response.status_code == 201:
            created_participation = response.json()
            return jsonify({
                "message": "Participation created. Redirecting to payment.",
                "participation_id": created_participation.get('id'),
                "participation_details": created_participation
            }), 201
        else:
            app_logger.error(f"Error creating participation in Part DB: {response.status_code} - {response.text}")
            return jsonify({"error": f"Failed to create participation in Part DB: {response.status_code} - {response.text}"}), 500

    except requests.exceptions.ConnectionError as e:
        app_logger.error(f"Could not connect to Participations API for start: {e}. Make sure it's running.")
        return jsonify({"error": f"Could not connect to Participations API: {str(e)}. Make sure it's running."}), 500
    except Exception as e:
        app_logger.error(f"Unhandled error in start_participation: {e}")
        return jsonify({"error": f"Error starting participation: {str(e)}"}), 500

# --- NEW: Endpoint to edit (update) an existing participation record ---
@app.route(f'{ERS_SCRIPT_NAME}/edit_participation', methods=['PUT'])
def edit_participation():
    data = request.json
    participation_id = data.get('id')
    user_id = data.get('user_id')
    event_id = data.get('event_id')
    num_tickets = data.get('num_tickets', 1)
    veg_heads = data.get('veg_heads', 0)
    non_veg_heads = data.get('non_veg_heads', 0)
    additional_contribution = data.get('additional_contribution', 0.0)
    tower = data.get('tower')
    flat_no = data.get('flat_no')

    app_logger.debug(f"Edit Participation - Incoming Data for ID {participation_id}: {data}")

    if not participation_id:
        return jsonify({"error": "Participation ID is required for editing"}), 400
    if not user_id or not event_id or not tower or not flat_no: # Basic validation
         return jsonify({"error": "User ID, Event ID, Tower and Flat Number are required"}), 400

    user_info = get_user_data_internal(user_id) # Fetch to get latest user details
    event_data = get_event_data_internal(event_id) # Fetch to get latest event details

    # Calculate new total payable based on updated heads and current event details
    cover_charges = event_data.get('cover_charges', 0.0)
    cover_charges_type = event_data.get('cover_charges_type', 'per_head')
    
    # Updated: Get specific veg and non-veg food charges and types
    veg_food_charges = event_data.get('veg_food_charges', 0.0)
    veg_food_charges_type = event_data.get('veg_food_charges_type', 'per_head')
    non_veg_food_charges = event_data.get('non_veg_food_charges', 0.0)
    non_veg_food_charges_type = event_data.get('non_veg_food_charges_type', 'per_head')

    total_cover_cost = 0.0
    if cover_charges_type == 'per_head':
        total_cover_cost = cover_charges * num_tickets
    elif cover_charges_type == 'per_family':
        total_cover_cost = cover_charges

    total_food_cost = 0.0
    # Calculate veg food cost
    if veg_food_charges_type == 'per_head':
        total_food_cost += veg_food_charges * veg_heads
    elif veg_food_charges_type == 'per_family':
        total_food_cost += veg_food_charges
    
    # Calculate non-veg food cost
    if non_veg_food_charges_type == 'per_head':
        total_food_cost += non_veg_food_charges * non_veg_heads
    elif non_veg_food_charges_type == 'per_family':
        total_food_cost += non_veg_food_charges
    
    new_total_payable = total_cover_cost + total_food_cost + additional_contribution

    # Fetch current participation to determine payment changes
    try:
        current_part_response = requests.get(
            f"{PARTICIPATION_SERVICE_INTERNAL_URL}/participations/{participation_id}",
            verify=False,
            timeout=2
        )
        current_part_response.raise_for_status()
        current_participation_details = current_part_response.json()
        
        current_amount_paid = current_participation_details.get('amount_paid', 0.0)
        
        # Calculate new remaining payment based on new total payable and old amount paid
        new_payment_remaining = new_total_payable - current_amount_paid
        
        # Ensure status is 'pending_payment' if there's still a remaining amount
        # or if it was previously confirmed but now has a new balance.
        # If new_payment_remaining is 0 and it was confirmed, keep it confirmed.
        new_status = current_participation_details.get('status', 'pending_payment')
        if new_payment_remaining > 0 and new_status == 'confirmed':
            new_status = 'payment_adjustment_required' # Custom status or back to pending
        elif new_payment_remaining > 0 and new_status == 'pending_payment':
            pass # Keep as pending_payment
        elif new_payment_remaining <= 0 and new_status != 'cancelled':
            new_status = 'confirmed' # If new payable is zero or less, and not cancelled, it's confirmed
        
        app_logger.debug(f"Old total: {current_participation_details.get('total_payable')}, New total: {new_total_payable}, Old paid: {current_amount_paid}, New remaining: {new_payment_remaining}")

    except requests.exceptions.RequestException as e:
        app_logger.error(f"Error fetching existing participation {participation_id} for edit: {e}")
        return jsonify({"error": f"Failed to fetch existing participation: {str(e)}"}), 500

    updated_data = {
        'user_id': user_id, # Ensure these are included, even if not changed
        'user_name': user_info.get('username'),
        'phone_number': user_info.get('phone_number'),
        'email_id': user_info.get('email'),
        'event_id': event_id, # Ensure these are included, even if not changed
        'event_date': event_data.get('close_date'),
        'tower': tower,
        'flat_no': flat_no,
        'num_tickets': num_tickets, # Only these are meant for 'editing heads'
        'veg_heads': veg_heads,
        'non_veg_heads': non_veg_heads,
        'additional_contribution': additional_contribution,
        'total_payable': new_total_payable, # Update total payable
        'payment_remaining': new_payment_remaining, # Update remaining
        'status': new_status, # Update status based on remaining payment
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    # Note: amount_paid and transaction_id are not changed during this "edit heads" flow.
    # They would be handled by a separate "process payment" or "process refund" flow.

    try:
        response = requests.put(
            f"{PARTICIPATION_SERVICE_INTERNAL_URL}/participations/{participation_id}",
            json=updated_data,
            verify=False
        )

        if response.status_code == 200:
            updated_participation = response.json()
            return jsonify({
                "message": "Participation updated successfully.",
                "participation_details": updated_participation
            }), 200
        else:
            app_logger.error(f"Error updating participation in Part DB: {response.status_code} - {response.text}")
            return jsonify({"error": f"Failed to update participation in Part DB: {response.status_code} - {response.text}"}), 500

    except requests.exceptions.ConnectionError as e:
        app_logger.error(f"Could not connect to Participations API for edit: {e}. Make sure it's running.")
        return jsonify({"error": f"Could not connect to Participations API: {str(e)}. Make sure it's running."}), 500
    except Exception as e:
        app_logger.error(f"Unhandled error in edit_participation: {e}")
        return jsonify({"error": f"Error editing participation: {str(e)}"}), 500

# --- NEW: Endpoint to delete a participation record ---
@app.route(f'{ERS_SCRIPT_NAME}/delete_participation/<int:participation_id>', methods=['DELETE'])
def delete_participation(participation_id):
    app_logger.debug(f"Delete Participation - Incoming ID: {participation_id}")

    try:
        response = requests.delete(
            f"{PARTICIPATION_SERVICE_INTERNAL_URL}/participations/{participation_id}",
            verify=False
        )

        if response.status_code == 200:
            return jsonify({"message": f"Participation {participation_id} deleted successfully."}), 200
        elif response.status_code == 404:
            return jsonify({"error": f"Participation {participation_id} not found."}), 404
        else:
            app_logger.error(f"Error deleting participation in Part DB: {response.status_code} - {response.text}")
            return jsonify({"error": f"Failed to delete participation in Part DB: {response.status_code} - {response.text}"}), 500

    except requests.exceptions.ConnectionError as e:
        app_logger.error(f"Could not connect to Participations API for delete: {e}. Make sure it's running.")
        return jsonify({"error": f"Could not connect to Participations API: {str(e)}. Make sure it's running."}), 500
    except Exception as e:
        app_logger.error(f"Unhandled error in delete_participation: {e}")
        return jsonify({"error": f"Error deleting participation: {str(e)}"}), 500

# --- NEW: Simulated Payment Callback Endpoint ---
# This endpoint would be called by the external payment microservice upon payment completion.
@app.route(f'{ERS_SCRIPT_NAME}/payment_callback', methods=['POST'])
def payment_callback():
    data = request.json
    participation_id = data.get('participation_id')
    payment_status = data.get('payment_status') # 'success' or 'failed'
    transaction_id = data.get('transaction_id')

    app_logger.info(f"Payment Callback Received: Participation ID: {participation_id}, Status: {payment_status}, TXN: {transaction_id}")

    if not participation_id or not payment_status:
        return jsonify({"error": "Participation ID and payment status are required"}), 400

    try:
        # Fetch the current participation details to update them
        current_part_response = requests.get(
            f"{PARTICIPATION_SERVICE_INTERNAL_URL}/participations/{participation_id}",
            verify=False, timeout=2
        )
        current_part_response.raise_for_status()
        current_participation = current_part_response.json()

        update_data = {
            'status': 'confirmed' if payment_status == 'success' else 'payment_failed',
            'transaction_id': transaction_id,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        # If payment was successful, update amount_paid and payment_remaining
        if payment_status == 'success':
            # This logic assumes the payment gateway sends the actual amount paid
            # For simplicity, let's assume if 'success', the total_payable was paid.
            # In a real system, the actual paid amount should come from the gateway.
            update_data['amount_paid'] = current_participation.get('total_payable', 0.0) # Assuming full payment for simplicity
            update_data['payment_remaining'] = 0.0 # No remaining payment

        response = requests.put(
            f"{PARTICIPATION_SERVICE_INTERNAL_URL}/participations/{participation_id}",
            json=update_data,
            verify=False
        )

        if response.status_code == 200:
            updated_participation = response.json()
            return jsonify({
                "message": f"Payment for participation {participation_id} processed: {payment_status}",
                "participation_details": updated_participation
            }), 200
        else:
            app_logger.error(f"Error updating participation status in Part DB: {response.status_code} - {response.text}")
            return jsonify({"error": f"Failed to update participation status in Part DB: {response.status_code} - {response.text}"}), 500

    except requests.exceptions.RequestException as e:
        app_logger.error(f"Could not connect to Participations API for callback: {e}. Make sure it's running.")
        return jsonify({"error": f"Could not connect to Participations API: {str(e)}. Make sure it's running."}), 500
    except Exception as e:
        app_logger.error(f"Unhandled error in payment_callback: {e}")
        return jsonify({"error": f"Error processing payment callback: {str(e)}"}), 500

# --- NEW: Endpoint to check for existing participation by user_id and event_id ---
@app.route(f'{ERS_SCRIPT_NAME}/check_participation', methods=['GET'])
def check_participation():
    user_id = request.args.get('user_id', type=int)
    event_id = request.args.get('event_id', type=int)

    app_logger.debug(f"Check Participation - User ID: {user_id}, Event ID: {event_id}")

    if not user_id or not event_id:
        return jsonify({"error": "User ID and Event ID are required as query parameters."}), 400

    try:
        # Fetch all participations from the internal Participation Service
        # Assuming the PART_API without specific IDs or user_id query parameters returns a list of all participations
        response = requests.get(f"{PARTICIPATION_SERVICE_INTERNAL_URL}/participations", verify=False)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        
        all_participations = []
        try:
            # Attempt to parse JSON. If response is empty, it will likely raise JSONDecodeError.
            # We explicitly check for empty string to treat it as an empty list.
            if response.text.strip(): # Check if the response body is not empty or just whitespace
                all_participations = response.json()
            else:
                app_logger.warning(f"Participation API returned an empty (non-JSON) response for /participations.")
                all_participations = [] # Treat empty response as empty list
        except json.JSONDecodeError:
            app_logger.error(f"Participation API returned invalid JSON for /participations. Response: {response.text}")
            # If it's not empty but also not JSON, re-raise or handle as an error
            raise ValueError(f"Invalid JSON response from Participation API: {response.text}")

        # Ensure all_participations is a list before proceeding
        if not isinstance(all_participations, list):
            app_logger.error(f"Participation API returned unexpected data type (not a list): {all_participations}. Attempting to proceed assuming it's a single object.")
            # If it's a single object (e.g., {"id": 1, ...}) wrap it in a list
            if isinstance(all_participations, dict):
                all_participations = [all_participations]
            else:
                raise ValueError("Participation API returned unprocessable data.")


        # Filter the participations in the ERS backend
        found_participation = None
        for part in all_participations:
            # Safely get values, handling cases where 'user_id' or 'event_id' might be missing in a dict
            if part.get('user_id') == user_id and part.get('event_id') == event_id:
                found_participation = part
                break # Found the first match, assuming one participation per user per event

        if found_participation:
            app_logger.debug(f"Found existing participation: {found_participation.get('id')}")
            return jsonify(found_participation), 200
        else:
            app_logger.debug(f"No participation found for User ID: {user_id}, Event ID: {event_id}")
            return jsonify({"message": "No existing participation found for this user and event."}), 404

    except requests.exceptions.RequestException as e:
        app_logger.error(f"Could not connect to Participations API for check_participation or API error: {e}")
        return jsonify({"error": f"Could not connect to Participations API or API error: {str(e)}. Make sure it's running and returns data."}), 500
    except ValueError as e: # Catch the custom ValueError for invalid JSON/data
        app_logger.error(f"Data processing error in check_participation: {e}")
        return jsonify({"error": f"Data processing error from Participation API: {str(e)}"}), 500
    except Exception as e:
        app_logger.error(f"Unhandled error in check_participation: {e}")
        return jsonify({"error": f"Error checking participation: {str(e)}"}), 500


# --- Global Error Handler for Flask ---
@app.errorhandler(Exception)
def handle_exception(e):
    # Log the full traceback for any unhandled exception
    app_logger.error(f"An unhandled error occurred: {e}", exc_info=True) # exc_info=True prints traceback

    # If it's an HTTP exception (like 404, 400, etc.), return its default response
    if isinstance(e, HTTPException):
        return e.get_response()

    # For all other unhandled exceptions, return a generic 500 error
    response = jsonify({"error": "An unexpected server error occurred. Please try again later."})
    response.status_code = 500
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007, debug=True)