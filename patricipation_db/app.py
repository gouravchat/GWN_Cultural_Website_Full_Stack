import os
import logging
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, OperationalError
from datetime import datetime, date
#cors
from flask_cors import CORS

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

# Rename 'app' for clarity and to avoid conflicts if imported
app = Flask(__name__)

CORS(app)  # Enable CORS for all routes

# --- Configuration ---
# Creates a 'data' subdirectory in the same directory as this script
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
if not os.path.exists(db_path):
    app.logger.info(f"Creating data directory at: {db_path}")
    os.makedirs(db_path)

# Defines the path for the database file
#db_file_path = os.path.join(db_path, 'participant_records.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////records.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Rename 'db' for clarity
database = SQLAlchemy(app)

# --- Database Model (Aligned with HTML Form) ---
# Represents a participant's registration record
class ParticipantInfo(database.Model):
    __tablename__ = 'participant_records'
    
    id = database.Column(database.Integer, primary_key=True)
    user_id = database.Column(database.Integer, nullable=False, index=True)
    user_name = database.Column(database.String(100), nullable=False)
    phone_number = database.Column(database.String(20), nullable=True)
    email_id = database.Column(database.String(120), nullable=True)
    event_id = database.Column(database.Integer, nullable=False, index=True)
    event_date = database.Column(database.Date, nullable=True)
    
    # Simplified address fields to match the form
    tower = database.Column(database.String(50), nullable=False)
    flat_no = database.Column(database.String(50), nullable=False)
    
    # Financial and meal choice fields from the form
    total_payable = database.Column(database.Float, nullable=False, default=0.0)
    amount_paid = database.Column(database.Float, nullable=False, default=0.0)
    payment_remaining = database.Column(database.Float, nullable=False, default=0.0)
    additional_contribution = database.Column(database.Float, default=0.0)
    contribution_comments = database.Column(database.Text, nullable=True)
    veg_heads = database.Column(database.Integer, default=0)
    non_veg_heads = database.Column(database.Integer, default=0)
    
    status = database.Column(database.String(50), default='confirmed', nullable=False)
    registered_at = database.Column(database.DateTime, default=datetime.utcnow)
    updated_at = database.Column(database.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensures a flat can only be registered once per event
    __table_args__ = (database.UniqueConstraint('event_id', 'flat_no', 'tower', name='uq_event_flat_tower_participation'),)

    def to_dict(self):
        """Serializes the ParticipantInfo object to a dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'phone_number': self.phone_number,
            'email_id': self.email_id,
            'event_id': self.event_id,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'tower': self.tower,
            'flat_no': self.flat_no,
            'total_payable': self.total_payable,
            'amount_paid': self.amount_paid,
            'payment_remaining': self.payment_remaining,
            'additional_contribution': self.additional_contribution,
            'contribution_comments': self.contribution_comments,
            'veg_heads': self.veg_heads,
            'non_veg_heads': self.non_veg_heads,
            'status': self.status,
            'registered_at': self.registered_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# --- API Endpoints with Robust Error Handling ---
@app.route('/participant-records', methods=['POST'])
def create_participant_record():
    """Endpoint to create a new participant record from the HTML form data structure."""
    app.logger.info("Received request for POST /participant-records")
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "No input data provided"}), 400

    # Extract nested details
    details = payload.get('registrationDetails', {})
    if not details:
        return jsonify({"error": "Missing 'registrationDetails' in payload"}), 400

    # Validate required fields from the nested structure
    required_fields = ['tower', 'flatNo', 'username']
    missing_fields = [field for field in required_fields if field not in details]
    if missing_fields:
        return jsonify({"error": f"Missing required fields in registrationDetails: {', '.join(missing_fields)}"}), 400

    try:
        new_record = ParticipantInfo(
            event_id=payload.get('eventId'),
            user_id=payload.get('userId'),
            user_name=details.get('username'),
            phone_number=payload.get('phoneNumber'), # Assuming phone number is at the top level
            email_id=payload.get('email'),           # Assuming email is at the top level
            
            # Address details from the form
            tower=details.get('tower'),
            flat_no=details.get('flatNo'),
            
            # Financial details from the form
            total_payable=payload.get('totalAmount', 0.0),
            amount_paid=payload.get('amountPaid', 0.0),
            payment_remaining=payload.get('remainingBalance', 0.0),
            additional_contribution=details.get('additionalContribution', 0.0),
            contribution_comments=details.get('contributionComments'),

            # Meal choices from the form
            veg_heads=details.get('vegHeads', 0),
            non_veg_heads=details.get('nonVegHeads', 0),

            status=payload.get('status', 'confirmed')
        )
        database.session.add(new_record)
        database.session.commit()
        app.logger.info(f"Successfully created participant record with ID: {new_record.id}")
        return jsonify({"message": "Participant record created successfully", "participant_info": new_record.to_dict()}), 201
    except IntegrityError as e:
        database.session.rollback()
        if 'uq_event_flat_tower_participation' in str(e.orig):
             return jsonify({"error": "This flat is already registered for this event."}), 409
        app.logger.error(f"Database integrity error: {e}")
        return jsonify({"error": "Database error: Could not save record due to a conflict.", "details": str(e)}), 400
    except Exception as e:
        database.session.rollback()
        app.logger.error(f"Unhandled error creating participant record: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

@app.route('/users/<int:user_id>/participant-records', methods=['GET'])
def get_records_by_user(user_id):
    """Endpoint to get all records for a specific user."""
    try:
        records = ParticipantInfo.query.filter_by(user_id=user_id).order_by(ParticipantInfo.registered_at.desc()).all()
        return jsonify([p.to_dict() for p in records]), 200
    except Exception as e:
        return jsonify({"error": "A database error occurred.", "details": str(e)}), 500

@app.route('/events/<int:event_id>/participant-records', methods=['GET'])
def get_records_by_event(event_id):
    """Endpoint to get all records for a specific event."""
    try:
        records = ParticipantInfo.query.filter_by(event_id=event_id).order_by(ParticipantInfo.tower, ParticipantInfo.flat_no).all()
        return jsonify([p.to_dict() for p in records]), 200
    except Exception as e:
        return jsonify({"error": "A database error occurred.", "details": str(e)}), 500

@app.route('/participant-records/<int:record_id>', methods=['GET'])
def get_record_by_id(record_id):
    """Endpoint to get a single record by its ID."""
    record = ParticipantInfo.query.get(record_id)
    if not record:
        return jsonify({"error": "Participant record not found"}), 404
    return jsonify(record.to_dict()), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "healthy", "service": "ParticipationService"}), 200

# --- Database Initialization ---
with app.app_context():
    # This creates tables if they don't exist. If you made schema changes (like adding phone_number),
    # you MUST delete the old `db_data` Docker volume and let it recreate to apply the new schema.
    database.create_all()
    print("Database tables for users created/checked.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)


