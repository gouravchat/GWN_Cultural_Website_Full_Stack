import os
from flask import Flask, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask_cors import CORS

PARTICIPATION_SERVICE_SCRIPT_NAME = os.environ.get('FLASK_SCRIPT_NAME', '')

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/data/participations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

app.config['APPLICATION_ROOT'] = PARTICIPATION_SERVICE_SCRIPT_NAME

@app.before_request
def set_script_name_from_proxy():
    if 'X-Forwarded-Prefix' in request.headers:
        request.environ['SCRIPT_NAME'] = request.headers['X-Forwarded-Prefix']
    elif PARTICIPATION_SERVICE_SCRIPT_NAME:
        request.environ['SCRIPT_NAME'] = PARTICIPATION_SERVICE_SCRIPT_NAME
    else:
        request.environ['SCRIPT_NAME'] = ''

class Participation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    user_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    email_id = db.Column(db.String(120), nullable=True)
    event_id = db.Column(db.Integer, nullable=False, index=True)
    event_date = db.Column(db.Date, nullable=True)
    tower = db.Column(db.String(50), nullable=False)
    flat_no = db.Column(db.String(50), nullable=False)
    total_payable = db.Column(db.Float, nullable=False, default=0.0)
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)
    payment_remaining = db.Column(db.Float, nullable=False, default=0.0)
    additional_contribution = db.Column(db.Float, default=0.0)
    contribution_comments = db.Column(db.Text, nullable=True)
    num_tickets = db.Column(db.Integer, default=1) # New field for number of tickets
    veg_heads = db.Column(db.Integer, default=0)
    non_veg_heads = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending_payment', nullable=False) # Changed default status
    transaction_id = db.Column(db.String(255), nullable=True) # New field for transaction ID
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('event_id', 'flat_no', 'tower', name='uq_event_flat_tower_participation'),)

    def to_dict(self):
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
            'num_tickets': self.num_tickets, # Include num_tickets in dict
            'veg_heads': self.veg_heads,
            'non_veg_heads': self.non_veg_heads,
            'status': self.status,
            'transaction_id': self.transaction_id, # Include in dict
            'registered_at': self.registered_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@app.route('/participations', methods=['POST'])
def create_participation():
    data = request.get_json()
    
    required_fields = ['user_id', 'user_name', 'event_id', 'tower', 'flat_no', 'total_payable'] # Removed amount_paid, payment_remaining as they will be updated later
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try: # not required, but added for better error handling
        existing_participation = Participation.query.filter_by(
            event_id=data['event_id'],
            flat_no=data['flat_no'],
            tower=data['tower']
        ).first()
        
        # if existing_participation:
        #     return jsonify({"error": "This flat is already registered for this event."}), 409

        # Set initial status to 'pending_payment'
        new_participation = Participation(
            user_id=data['user_id'],
            user_name=data['user_name'],
            phone_number=data.get('phone_number'),
            email_id=data.get('email_id'),
            event_id=data['event_id'],
            event_date=datetime.fromisoformat(data['event_date']).date() if data.get('event_date') else None,
            tower=data['tower'],
            flat_no=data['flat_no'],
            total_payable=float(data['total_payable']),
            amount_paid=0.0, # Initial amount paid is 0
            payment_remaining=float(data['total_payable']), # Initially total payable is remaining
            additional_contribution=float(data.get('additional_contribution', 0.0)),
            contribution_comments=data.get('contribution_comments'),
            num_tickets=int(data.get('num_tickets', 1)), # Default to 1 if not provide
            veg_heads=int(data.get('veg_heads', 0)),
            non_veg_heads=int(data.get('non_veg_heads', 0)),
            status='pending_payment' # Default status for new participation
        )
        db.session.add(new_participation)
        db.session.commit()
        return jsonify({"message": "Participation recorded successfully, awaiting payment confirmation", "participation": new_participation.to_dict()}), 201
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": f"Invalid data format: {e}"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error creating participation: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/participations', methods=['GET'])
def get_participations():
    event_id = request.args.get('event_id', type=int)
    user_id = request.args.get('user_id', type=int)

    query = Participation.query

    if event_id:
        query = query.filter_by(event_id=event_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    participations = query.all()
    return jsonify([p.to_dict() for p in participations]), 200

@app.route('/participations/<int:participation_id>', methods=['GET'])
def get_participation_by_id(participation_id):
    participation = Participation.query.get(participation_id)
    if not participation:
        return jsonify({"error": "Participation record not found"}), 404
    return jsonify(participation.to_dict()), 200

from datetime import datetime, timezone

@app.route('/participations/<int:participation_id>', methods=['PUT'])
def update_participation(participation_id):
    participation = Participation.query.get(participation_id)
    if not participation:
        return jsonify({"error": "Participation record not found"}), 404
    
    data = request.get_json()
    
    try:
        for key, value in data.items():
            if hasattr(participation, key):
                if key == 'event_date' and value:
                    # Assuming event_date is meant to be a date object (no time)
                    setattr(participation, key, datetime.fromisoformat(value).date())
                elif key in ['updated_at', 'registered_at'] and value: # <-- ADDED THIS BLOCK
                    # Parse ISO formatted string to a timezone-aware datetime object
                    # Ensure the datetime object is timezone-aware if your DB expects it
                    dt_object = datetime.fromisoformat(value)
                    if dt_object.tzinfo is None:
                        # Assuming UTC if no timezone info is present in the string
                        dt_object = dt_object.replace(tzinfo=timezone.utc)
                    setattr(participation, key, dt_object)
                elif key in ['total_payable', 'amount_paid', 'payment_remaining', 'additional_contribution']:
                    setattr(participation, key, float(value))
                elif key in ['veg_heads', 'non_veg_heads', 'num_tickets']: # Added num_tickets here for int conversion
                    setattr(participation, key, int(value))
                else:
                    setattr(participation, key, value)
        
        # Commit the changes to the database
        db.session.commit()
        
        # Return the updated participation details
        # You might need to serialize 'participation' object back to a dict/JSON here
        updated_participation_data = {
            "id": participation.id,
            "user_id": participation.user_id,
            "user_name": participation.user_name,
            "phone_number": participation.phone_number,
            "email_id": participation.email_id,
            "event_id": participation.event_id,
            "event_date": participation.event_date.isoformat() if participation.event_date else None,
            "tower": participation.tower,
            "flat_no": participation.flat_no,
            "num_tickets": participation.num_tickets,
            "veg_heads": participation.veg_heads,
            "non_veg_heads": participation.non_veg_heads,
            "additional_contribution": participation.additional_contribution,
            "total_payable": participation.total_payable,
            "amount_paid": participation.amount_paid,
            "payment_remaining": participation.payment_remaining,
            "status": participation.status,
            "transaction_id": participation.transaction_id,
            "registered_at": participation.registered_at.isoformat() if participation.registered_at else None,
            "updated_at": participation.updated_at.isoformat() if participation.updated_at else None
        }
        
        return jsonify(updated_participation_data), 200

    except ValueError as e:
        db.session.rollback() # Rollback changes on error
        return jsonify({"error": f"Data validation error: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback() # Rollback changes on any other error
        return jsonify({"error": f"Internal server error during update: {str(e)}"}), 500

# NEW ENDPOINT: Confirm payment with Transaction ID
@app.route('/participations/<int:participation_id>/confirm_payment', methods=['POST'])
def confirm_payment(participation_id):
    participation = Participation.query.get(participation_id)
    if not participation:
        return jsonify({"error": "Participation record not found"}), 404

    data = request.get_json()
    transaction_id = data.get('transaction_id')
    amount_paid = float(data.get('amount_paid', 0.0))

    if not transaction_id:
        return jsonify({"error": "Transaction ID is required for payment confirmation"}), 400
    if amount_paid <= 0:
        return jsonify({"error": "Amount paid must be greater than zero"}), 400

    try:
        # Check if already confirmed or partially paid
        if participation.status == 'confirmed' and participation.payment_remaining == 0:
            return jsonify({"message": "Payment already fully confirmed for this participation."}), 200
        
        # Update payment details
        participation.amount_paid += amount_paid
        participation.payment_remaining = max(0, participation.total_payable - participation.amount_paid) # Ensure it doesn't go below 0
        participation.transaction_id = transaction_id # Store the latest transaction ID
        
        if participation.payment_remaining <= 0:
            participation.status = 'confirmed' # Mark as confirmed if fully paid
        else:
            participation.status = 'partially_paid' # Or a new status for partial payment

        db.session.commit()
        return jsonify({"message": "Payment confirmed and participation updated", "participation": participation.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error confirming payment: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route('/participations/<int:participation_id>', methods=['DELETE'])
def delete_participation(participation_id):
    participation = Participation.query.get(participation_id)
    if not participation:
        return jsonify({"error": "Participation record not found"}), 404
    
    try:
        db.session.delete(participation)
        db.session.commit()
        return jsonify({"message": "Participation record deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting participation: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


# --- Database Initialization ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)