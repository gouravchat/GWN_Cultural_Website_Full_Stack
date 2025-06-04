# app-participation/participation_service.py
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import UniqueConstraint

app = Flask(__name__)

# Configure SQLite database for this service
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///participation_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model for Event Participation
class Participation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_phone_number = db.Column(db.String(20), nullable=False)
    event_id = db.Column(db.Integer, nullable=False)
    num_veg_attendees = db.Column(db.Integer, nullable=False, default=0)
    num_non_veg_attendees = db.Column(db.Integer, nullable=False, default=0)
    contribution = db.Column(db.Float, nullable=True, default=0.0) # Optional contribution
    total_payable_amount = db.Column(db.Float, nullable=False)
    current_payment_amount = db.Column(db.Float, nullable=False, default=0.0)
    participation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending') # e.g., 'pending', 'paid', 'partially_paid'

    # Ensure a user can only participate in an event once
    __table_args__ = (UniqueConstraint('user_phone_number', 'event_id', name='_user_event_uc'),)

    def to_dict(self):
        """Converts Participation object to a dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_phone_number': self.user_phone_number,
            'event_id': self.event_id,
            'num_veg_attendees': self.num_veg_attendees,
            'num_non_veg_attendees': self.num_non_veg_attendees,
            'contribution': self.contribution,
            'total_payable_amount': self.total_payable_amount,
            'current_payment_amount': self.current_payment_amount,
            'participation_date': self.participation_date.isoformat(),
            'status': self.status
        }

# API Endpoints for Event Participation

@app.route('/participations', methods=['POST'])
def create_participation():
    """API endpoint to create a new event participation record."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    required_fields = ['userPhoneNumber', 'eventId', 'numVegAttendees', 'numNonVegAttendees', 
                       'totalPayableAmount', 'currentPaymentAmount']
    
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    user_phone_number = data['userPhoneNumber']
    event_id = data['eventId']
    num_veg_attendees = data['numVegAttendees']
    num_non_veg_attendees = data['numNonVegAttendees']
    contribution = data.get('contribution', 0.0) # Optional, default to 0.0
    total_payable_amount = data['totalPayableAmount']
    current_payment_amount = data['currentPaymentAmount']

    # Basic validation for attendee numbers and amounts
    if not isinstance(num_veg_attendees, int) or num_veg_attendees < 0:
        return jsonify({"error": "numVegAttendees must be a non-negative integer."}), 400
    if not isinstance(num_non_veg_attendees, int) or num_non_veg_attendees < 0:
        return jsonify({"error": "numNonVegAttendees must be a non-negative integer."}), 400
    if not isinstance(total_payable_amount, (int, float)) or total_payable_amount < 0:
        return jsonify({"error": "totalPayableAmount must be a non-negative number."}), 400
    if not isinstance(current_payment_amount, (int, float)) or current_payment_amount < 0:
        return jsonify({"error": "currentPaymentAmount must be a non-negative number."}), 400
    if not isinstance(contribution, (int, float)) or contribution < 0:
        return jsonify({"error": "Contribution must be a non-negative number."}), 400

    try:
        # Check if participation already exists for this user and event
        existing_participation = Participation.query.filter_by(
            user_phone_number=user_phone_number,
            event_id=event_id
        ).first()

        if existing_participation:
            return jsonify({"error": "User already registered for this event. Use PUT to update payment.", "participation": existing_participation.to_dict()}), 409 # Conflict

        # Determine initial status
        status = 'paid' if current_payment_amount >= total_payable_amount else 'partially_paid' if current_payment_amount > 0 else 'pending'

        new_participation = Participation(
            user_phone_number=user_phone_number,
            event_id=event_id,
            num_veg_attendees=num_veg_attendees,
            num_non_veg_attendees=num_non_veg_attendees,
            contribution=contribution,
            total_payable_amount=total_payable_amount,
            current_payment_amount=current_payment_amount,
            status=status
        )
        db.session.add(new_participation)
        db.session.commit()
        return jsonify({"message": "Participation recorded successfully", "participation": new_participation.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Database service error during participation creation: {e}")
        return jsonify({"error": "Internal server error or data conflict.", "details": str(e)}), 500

@app.route('/participations/<string:user_phone_number>/<int:event_id>/payment', methods=['PUT'])
def update_participation_payment(user_phone_number, event_id):
    """API endpoint to update the payment amount for an existing participation."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    payment_amount = data.get('paymentAmount')
    if not isinstance(payment_amount, (int, float)) or payment_amount < 0:
        return jsonify({"error": "paymentAmount must be a non-negative number."}), 400

    try:
        participation = Participation.query.filter_by(
            user_phone_number=user_phone_number,
            event_id=event_id
        ).first()

        if not participation:
            return jsonify({"error": "Participation record not found."}), 404

        # Update current payment amount (add to existing, or set if it's a full payment)
        # For simplicity, assuming paymentAmount is the *new total* payment.
        # If it's an incremental payment, you'd do: participation.current_payment_amount += payment_amount
        participation.current_payment_amount = payment_amount

        # Update status based on new payment amount
        if participation.current_payment_amount >= participation.total_payable_amount:
            participation.status = 'paid'
        elif participation.current_payment_amount > 0:
            participation.status = 'partially_paid'
        else:
            participation.status = 'pending' # Should not happen if payment_amount is non-negative

        db.session.commit()
        return jsonify({"message": "Payment updated successfully", "participation": participation.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Database service error during payment update: {e}")
        return jsonify({"error": "Internal server error during payment update.", "details": str(e)}), 500

@app.route('/participations', methods=['GET'])
def get_all_participations():
    """API endpoint to get all participation records (for admin/debugging)."""
    try:
        participations = Participation.query.all()
        if participations:
            return jsonify([p.to_dict() for p in participations]), 200
        else:
            return jsonify({"message": "No participation records found"}), 200
    except Exception as e:
        print(f"Database service error during get all participations: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/participations/<string:user_phone_number>/<int:event_id>', methods=['GET'])
def get_single_participation(user_phone_number, event_id):
    """API endpoint to get a single participation record by user phone and event ID."""
    try:
        participation = Participation.query.filter_by(
            user_phone_number=user_phone_number,
            event_id=event_id
        ).first()
        if participation:
            return jsonify(participation.to_dict()), 200
        else:
            return jsonify({"error": "Participation record not found"}), 404
    except Exception as e:
        print(f"Database service error during get single participation: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


# This ensures tables are created when the Flask app starts
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=True) # Running on a new port, e.g., 5006
