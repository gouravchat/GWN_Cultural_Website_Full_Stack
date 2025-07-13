import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from flask_cors import CORS
import razorpay
import hmac
import hashlib
from flask_sqlalchemy import SQLAlchemy # NEW: Import SQLAlchemy
from datetime import datetime

app = Flask(__name__, template_template_folder='templates', static_folder='static')
CORS(app)

# --- Database Configuration ---
DB_DIR = '/app/data/db' # Directory within the container where the DB file will live
DATABASE_FILE = 'payments.db' # Name of the SQLite database file for payments
FULL_DB_PATH = os.path.join(DB_DIR, DATABASE_FILE)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{FULL_DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app) # Initialize SQLAlchemy with the Flask app

# --- Payment Model Definition ---
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    razorpay_order_id = db.Column(db.String(50), unique=True, nullable=False)
    razorpay_payment_id = db.Column(db.String(50), unique=True, nullable=True) # Nullable until payment is successful
    razorpay_signature = db.Column(db.String(255), nullable=True)

    user_id = db.Column(db.String(50), nullable=False) # Assuming user_id can be string
    participation_id = db.Column(db.String(50), nullable=False) # Assuming participation_id can be string

    amount = db.Column(db.Integer, nullable=False) # Stored in smallest unit (paise)
    currency = db.Column(db.String(10), nullable=False, default='INR')

    status = db.Column(db.String(20), nullable=False, default='created') # e.g., 'created', 'pending', 'authorized', 'captured', 'failed', 'refunded'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # Automatically updates on change

    raw_response = db.Column(db.Text, nullable=True) # To store full Razorpay JSON response for auditing

    def __repr__(self):
        return f'<Payment {self.razorpay_order_id} - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'razorpay_order_id': self.razorpay_order_id,
            'razorpay_payment_id': self.razorpay_payment_id,
            'user_id': self.user_id,
            'participation_id': self.participation_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# --- Database Initialization Function ---
def init_db():
    with app.app_context():
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)
            print(f"Created database directory: {DB_DIR}")
        
        db.create_all() # Creates tables for all defined models
        print("Payment database initialized (tables created/verified).")

# --- Configuration from Environment Variables ---
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
FLASK_RUN_PORT = int(os.environ.get('FLASK_RUN_PORT', 5009))
FLASK_SCRIPT_NAME = os.environ.get('FLASK_SCRIPT_NAME', '/payment')

USER_PORTAL_SUCCESS_URL = os.environ.get('USER_PORTAL_SUCCESS_URL', 'http://localhost:5001/user-portal/payment-success')
USER_PORTAL_FAILURE_URL = os.environ.get('USER_PORTAL_FAILURE_URL', 'http://localhost:5001/user-portal/payment-failure')

# Initialize Razorpay client
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    client.set_app_details("NestAlpineCulturalSociety", "1.0")
    print("Razorpay client initialized.")
else:
    client = None
    print("WARNING: Razorpay credentials not set. Payment functionality will be disabled.")

# Call DB initialization during app startup
init_db()

# --- Routes ---

@app.route(f'{FLASK_SCRIPT_NAME}/create-order', methods=['POST'])
def create_order():
    """
    Endpoint to create a Razorpay order and record it in the local database.
    """
    if not client:
        return jsonify({"error": "Payment service not configured."}), 503

    data = request.get_json()
    user_id = data.get('user_id')
    participation_id = data.get('participation_id')
    amount_in_paise = data.get('amount')
    currency = data.get('currency', 'INR')

    if not all([user_id, participation_id, amount_in_paise]):
        return jsonify({"error": "Missing user_id, participation_id, or amount."}), 400
    
    try:
        amount_in_paise = int(amount_in_paise)
        if amount_in_paise <= 0:
            raise ValueError("Amount must be positive.")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount."}), 400

    try:
        # 1. Create Razorpay Order
        order_payload = {
            "amount": amount_in_paise,
            "currency": currency,
            "receipt": f"receipt_{user_id}_{participation_id}_{datetime.now().timestamp()}",
            "notes": {
                "user_id": str(user_id),
                "participation_id": str(participation_id)
            }
        }
        order = client.order.create(order_payload)
        
        # 2. Record the order in our local database with 'created' status
        new_payment = Payment(
            razorpay_order_id=order['id'],
            user_id=user_id,
            participation_id=participation_id,
            amount=amount_in_paise,
            currency=currency,
            status='created', # Initial status
            raw_response=jsonify(order).get_data(as_text=True) # Store initial response
        )
        db.session.add(new_payment)
        db.session.commit()

        print(f"Razorpay order created and recorded: {order['id']}")
        return jsonify(order), 200
    except Exception as e:
        db.session.rollback() # Rollback if database insert fails
        print(f"Error creating Razorpay order or recording in DB: {e}")
        return jsonify({"error": "Failed to create payment order.", "details": str(e)}), 500


@app.route(f'{FLASK_SCRIPT_NAME}/verify-payment', methods=['POST'])
def verify_payment():
    """
    Endpoint to verify a payment after it's made on the client-side
    and update its status in the local database.
    """
    if not client:
        return jsonify({"error": "Payment service not configured."}), 503
    
    data = request.get_json()
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_signature = data.get('razorpay_signature')
    
    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return jsonify({"error": "Missing Razorpay payment verification details."}), 400

    # Retrieve the payment record from our database
    payment_record = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
    if not payment_record:
        print(f"Payment record not found for order ID: {razorpay_order_id}")
        return redirect(f"{USER_PORTAL_FAILURE_URL}?error=record_not_found&order_id={razorpay_order_id}", code=302)

    try:
        # Verify the payment signature with Razorpay
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        client.utility.verify_payment_signature(params_dict)

        # Payment is verified, now fetch details from Razorpay and update local DB
        payment_details = client.payment.fetch(razorpay_payment_id)
        
        # Update our local payment record
        payment_record.razorpay_payment_id = razorpay_payment_id
        payment_record.razorpay_signature = razorpay_signature
        payment_record.status = payment_details.get('status', 'captured') # 'captured' for success
        payment_record.raw_response = jsonify(payment_details).get_data(as_text=True)
        db.session.commit()

        # --- IMPORTANT: Call Participation Service to mark as paid ---
        # Assuming your Participation Service is running and accessible
        # Example (requires 'requests' library to be installed in Payment Service)
        # import requests
        # participation_api_url = f"http://participation-service:5005/participations/{payment_record.participation_id}"
        # try:
        #     # You would likely need an API key or internal auth here
        #     resp = requests.put(participation_api_url, json={'status': 'paid', 'payment_id': razorpay_payment_id})
        #     if resp.status_code == 200:
        #         print(f"Participation {payment_record.participation_id} updated to paid.")
        #     else:
        #         print(f"Failed to update participation status: {resp.status_code} {resp.text}")
        # except requests.exceptions.RequestException as req_e:
        #     print(f"Error calling Participation Service: {req_e}")
        
        print(f"Payment {razorpay_payment_id} for order {razorpay_order_id} verified and updated locally.")
        
        # Redirect to User Portal success page
        return redirect(f"{USER_PORTAL_SUCCESS_URL}?user_id={payment_record.user_id}&participation_id={payment_record.participation_id}&payment_id={razorpay_payment_id}", code=302)

    except razorpay.errors.SignatureVerificationError as e:
        print(f"Signature verification failed: {e}")
        payment_record.status = 'failed_signature'
        payment_record.raw_response = str(e) # Store error
        db.session.commit()
        return redirect(f"{USER_PORTAL_FAILURE_URL}?error=signature_mismatch&order_id={razorpay_order_id}", code=302)
    except Exception as e:
        db.session.rollback() # Rollback any pending DB changes in case of unexpected error
        print(f"Error verifying payment or updating DB: {e}")
        payment_record.status = 'failed_internal'
        payment_record.raw_response = str(e) # Store error
        db.session.commit()
        return redirect(f"{USER_PORTAL_FAILURE_URL}?error=internal_error&details={str(e)}", code=302)


# Razorpay Webhook Endpoint
@app.route(f'{FLASK_SCRIPT_NAME}/webhook', methods=['POST'])
def razorpay_webhook():
    """
    Receives webhook notifications from Razorpay and updates local database status.
    """
    if not RAZORPAY_KEY_SECRET:
        print("Webhook: Razorpay Key Secret not set, cannot verify webhook signature.")
        return jsonify({"status": "error", "message": "Webhook secret not configured"}), 500

    webhook_secret = RAZORPAY_KEY_SECRET # Razorpay uses the Key Secret for webhook signature
    
    payload = request.data.decode('utf-8')
    razorpay_webhook_signature = request.headers.get('X-Razorpay-Signature')

    if not razorpay_webhook_signature:
        print("Webhook: Missing X-Razorpay-Signature header.")
        return jsonify({"status": "error", "message": "Missing signature"}), 400

    try:
        client.utility.verify_webhook_signature(payload, razorpay_webhook_signature, webhook_secret)
        
        event = request.get_json()
        event_type = event['event']
        
        # Extract common entity type (payment, refund, order, etc.)
        entity = None
        if 'payment' in event['payload']:
            entity = event['payload']['payment']['entity']
        elif 'refund' in event['payload']:
            entity = event['payload']['refund']['entity']
        elif 'order' in event['payload']:
            entity = event['payload']['order']['entity']
        
        if not entity:
            print(f"Webhook: Unrecognized entity payload for event {event_type}")
            return jsonify({"status": "ignored", "message": "Unrecognized entity"}), 200

        print(f"Received Razorpay webhook event: {event_type} for entity ID: {entity.get('id', 'N/A')}")

        # Update local payment record based on event type
        if event_type == 'payment.captured' or event_type == 'payment.authorized':
            razorpay_order_id = entity.get('order_id')
            payment_record = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
            if payment_record:
                payment_record.razorpay_payment_id = entity.get('id')
                payment_record.status = entity.get('status', 'captured')
                payment_record.raw_response = jsonify(entity).get_data(as_text=True)
                db.session.commit()
                print(f"Payment {entity['id']} updated to '{payment_record.status}' via webhook.")
                # Also, crucial to update Participation Service here if it wasn't done by verify_payment
            else:
                # If payment.captured webhook arrives before create_order response,
                # or if record was somehow missed, you might create a new record here
                print(f"Webhook: Payment record not found for order {razorpay_order_id}. Consider creating a new one.")

        elif event_type == 'payment.failed':
            razorpay_order_id = entity.get('order_id')
            payment_record = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
            if payment_record:
                payment_record.razorpay_payment_id = entity.get('id')
                payment_record.status = entity.get('status', 'failed')
                payment_record.raw_response = jsonify(entity).get_data(as_text=True)
                db.session.commit()
                print(f"Payment {entity['id']} updated to '{payment_record.status}' via webhook.")
            else:
                print(f"Webhook: Failed payment record not found for order {razorpay_order_id}.")

        elif event_type == 'refund.processed':
            refund_id = entity.get('id')
            payment_id = entity.get('payment_id')
            # Find the payment record associated with this refund's payment_id
            payment_record = Payment.query.filter_by(razorpay_payment_id=payment_id).first()
            if payment_record:
                payment_record.status = 'refunded' # Or add a 'refund_status' column
                payment_record.raw_response = jsonify(entity).get_data(as_text=True) # Store refund details too
                db.session.commit()
                print(f"Refund {refund_id} processed for payment {payment_id}. Status updated.")
            else:
                print(f"Webhook: Payment record not found for refund of payment {payment_id}.")

        # Add more event handlers as needed

        return jsonify({"status": "success", "message": "Webhook processed"}), 200

    except ValueError as e:
        print(f"Webhook: Invalid payload or signature mismatch: {e}")
        return jsonify({"status": "error", "message": "Invalid signature or payload"}), 400
    except Exception as e:
        print(f"Webhook: An unexpected error occurred: {e}")
        db.session.rollback() # Rollback any pending DB changes
        return jsonify({"status": "error", "message": "Internal server error"}), 500


# Serve static files (CSS, JS specific to payment page, if any)
@app.route('/static/<path:filename>')
def serve_static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/')
def home():
    """Simple health check or basic info for the payment service."""
    return "Payment Service is running."


if __name__ == '__main__':
    # When running directly for development/testing
    app.run(host='0.0.0.0', port=FLASK_RUN_PORT, debug=True)