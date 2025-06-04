# app-events/event_service.py
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Configure SQLite database for this service
# The database file 'event_data.db' will be created inside the container's /app directory
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///event_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model for Event
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    close_date = db.Column(db.DateTime, nullable=False) # Subscription close date
    venue = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    photo_url = db.Column(db.String(255), nullable=True) # URL to event photo
    
    # Subscription configuration fields
    cover_charges = db.Column(db.Float, default=0.0)
    cover_charges_type = db.Column(db.String(20), default='per_head') # 'per_head', 'per_family'
    veg_food_charges = db.Column(db.Float, default=0.0)
    veg_food_charges_type = db.Column(db.String(20), default='per_head')
    non_veg_food_charges = db.Column(db.Float, default=0.0)
    non_veg_food_charges_type = db.Column(db.String(20), default='per_head')
    additional_charges = db.Column(db.Float, default=0.0)
    additional_charges_type = db.Column(db.String(20), default='per_head')

    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        """Converts Event object to a dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'time': self.time.isoformat(),
            'close_date': self.close_date.isoformat(),
            'venue': self.venue,
            'details': self.details,
            'photo_url': self.photo_url,
            'subscription': {
                'coverCharges': self.cover_charges,
                'coverChargesType': self.cover_charges_type,
                'vegFoodCharges': self.veg_food_charges,
                'vegFoodChargesType': self.veg_food_charges_type,
                'nonVegFoodCharges': self.non_veg_food_charges,
                'nonVegFoodChargesType': self.non_veg_food_charges_type,
                'additionalCharges': self.additional_charges,
                'additionalChargesType': self.additional_charges_type
            },
            'created_on': self.created_on.isoformat()
        }

# API Endpoints for Event Data

@app.route('/events', methods=['POST'])
def create_event():
    """API endpoint to create a new event."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    required_fields = ['name', 'time', 'close_date', 'venue', 'details', 'subscription']
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return jsonify({"error": f"Missing required event fields: {', '.join(missing)}"}), 400

    # Validate dates
    try:
        event_time = datetime.fromisoformat(data['time'])
        close_date = datetime.fromisoformat(data['close_date'])
    except ValueError:
        return jsonify({"error": "Invalid date/time format. Use ISO 8601 format (e.g.,YYYY-MM-DDTHH:MM)."}), 400

    if close_date >= event_time:
        return jsonify({"error": "Subscription Close Date must be before the Event Time."}), 400
    
    # Validate subscription settings
    subscription_data = data['subscription']
    subscription_required_fields = [
        'coverCharges', 'coverChargesType', 'vegFoodCharges', 'vegFoodChargesType',
        'nonVegFoodCharges', 'nonVegFoodChargesType', 'additionalCharges', 'additionalChargesType'
    ]
    for field in subscription_required_fields:
        if field not in subscription_data or subscription_data[field] is None:
            return jsonify({"error": f"Missing required subscription field: {field}"}), 400
    
    # Validate charges are numbers
    charge_fields = ['coverCharges', 'vegFoodCharges', 'nonVegFoodCharges', 'additionalCharges']
    for field in charge_fields:
        try:
            subscription_data[field] = float(subscription_data[field])
            if subscription_data[field] < 0:
                return jsonify({"error": f"'{field}' cannot be negative."}), 400
        except ValueError:
            return jsonify({"error": f"Invalid number format for '{field}'."}), 400

    # Validate charge types
    allowed_charge_types = ['per_head', 'per_family']
    for field in ['coverChargesType', 'vegFoodChargesType', 'nonVegFoodChargesType', 'additionalChargesType']:
        if subscription_data[field] not in allowed_charge_types:
            return jsonify({"error": f"Invalid value for '{field}'. Allowed: {', '.join(allowed_charge_types)}"}), 400

    try:
        new_event = Event(
            name=data['name'],
            time=event_time,
            close_date=close_date,
            venue=data['venue'],
            details=data['details'],
            photo_url=data.get('photo_url'), # Optional
            cover_charges=subscription_data['coverCharges'],
            cover_charges_type=subscription_data['coverChargesType'],
            veg_food_charges=subscription_data['vegFoodCharges'],
            veg_food_charges_type=subscription_data['vegFoodChargesType'],
            non_veg_food_charges=subscription_data['nonVegFoodCharges'],
            non_veg_food_charges_type=subscription_data['nonVegFoodChargesType'],
            additional_charges=subscription_data['additionalCharges'],
            additional_charges_type=subscription_data['additionalChargesType']
        )
        db.session.add(new_event)
        db.session.commit()
        return jsonify({"message": "Event created successfully", "event_id": new_event.id}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Database service error during event creation: {e}")
        return jsonify({"error": "Internal server error or data conflict.", "details": str(e)}), 500

@app.route('/events', methods=['GET'])
def get_all_events():
    """API endpoint to get all events."""
    # Ensure expired events are removed before fetching
    delete_expired_events()
    try:
        events = Event.query.all()
        if events:
            return jsonify([event.to_dict() for event in events]), 200
        else:
            return jsonify({"message": "No events found"}), 200
    except Exception as e:
        print(f"Database service error fetching events: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """API endpoint to get a single event by ID."""
    try:
        event = Event.query.get(event_id)
        if event:
            # Check if event is expired
            if event.close_date < datetime.utcnow():
                db.session.delete(event)
                db.session.commit()
                return jsonify({"error": "Event has expired and been removed."}), 404
            return jsonify(event.to_dict()), 200
        else:
            return jsonify({"error": "Event not found"}), 404
    except Exception as e:
        print(f"Database service error fetching event {event_id}: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

def delete_expired_events():
    """
    Deletes events from the database whose close_date has passed.
    This function is called internally before fetching events.
    """
    try:
        now = datetime.utcnow()
        expired_events = Event.query.filter(Event.close_date < now).all()
        if expired_events:
            for event in expired_events:
                db.session.delete(event)
            db.session.commit()
            print(f"Deleted {len(expired_events)} expired events.")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting expired events: {e}")

# This ensures tables are created when the Flask app starts
with app.app_context():
    db.create_all()
    # Optionally, delete expired events on startup
    delete_expired_events()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True) # Running on a new port 5005
