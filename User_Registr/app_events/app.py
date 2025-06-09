# app-events/event_service.py
import os
import json
from flask import Flask, request, jsonify, send_from_directory # Import send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Configure SQLite database for this service
# The database file 'event_data.db' will be created inside the container's /app directory
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///event_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Configuration for File Uploads ---
UPLOAD_FOLDER = 'static/event_photos'
# Create the upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

# Allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# --- End Configuration for File Uploads ---


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
            'photo_url': self.photo_url, # Include photo_url in the dictionary
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
    """
    API endpoint to create a new event.
    This now expects multipart/form-data with 'eventData' (JSON string) and optionally 'eventPhoto' (file).
    """
    subscription_data = request.form.to_dict() if request.form else request.get_json()

    # Validate required fields (adjust as per your schema)
    subscription_required_fields = ['name', 'details', 'time', 'venue']
    for field in subscription_required_fields:
        if field not in subscription_data or subscription_data[field] is None:
            return jsonify({"error": f"Missing required subscription field: {field}"}), 400

    # Validate charges are numbers (if you use these fields)
    charge_fields = ['coverCharges', 'vegFoodCharges', 'nonVegFoodCharges', 'additionalCharges']
    for field in charge_fields:
        if field in subscription_data:
            try:
                subscription_data[field] = float(subscription_data[field])
                if subscription_data[field] < 0:
                    return jsonify({"error": f"'{field}' cannot be negative."}), 400
            except ValueError:
                return jsonify({"error": f"Invalid number format for '{field}'."}), 400

    # Validate charge types (if you use these fields)
    allowed_charge_types = ['per_head', 'per_family']
    for field in ['coverChargesType', 'vegFoodChargesType', 'nonVegFoodChargesType', 'additionalChargesType']:
        if field in subscription_data and subscription_data[field] not in allowed_charge_types:
            return jsonify({"error": f"Invalid value for '{field}'. Allowed: {', '.join(allowed_charge_types)}"}), 400

    # REMOVE photo upload logic
    # photo_url = None
    # if 'eventPhoto' in request.files:
    #     file = request.files['eventPhoto']
    #     if file.filename == '':
    #         pass
    #     elif file and allowed_file(file.filename):
    #         pass
    #     else:
    #         pass

    # Create event object WITHOUT photo_url
    event = {
        "name": subscription_data["name"],
        "details": subscription_data.get("details", ""),
        "time": subscription_data["time"],
        "venue": subscription_data.get("venue", ""),
        "coverCharges": subscription_data.get("coverCharges", 0),
        "vegFoodCharges": subscription_data.get("vegFoodCharges", 0),
        "nonVegFoodCharges": subscription_data.get("nonVegFoodCharges", 0),
        "additionalCharges": subscription_data.get("additionalCharges", 0),
        "coverChargesType": subscription_data.get("coverChargesType", ""),
        "vegFoodChargesType": subscription_data.get("vegFoodChargesType", ""),
        "nonVegFoodChargesType": subscription_data.get("nonVegFoodChargesType", ""),
        "additionalChargesType": subscription_data.get("additionalChargesType", "")
        # "photo_url": photo_url,  # REMOVED
    }

    # ...save event to DB or file as per your logic...

    return jsonify({"message": "Event created successfully", "event": event}), 201

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

# --- New Route to Serve Static Event Photos ---
@app.route('/static/event_photos/<filename>')
def serve_event_photo(filename):
    """
    Serves event photos from the UPLOAD_FOLDER.
    This route needs to be accessible via the app_service proxy.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# --- End New Route ---

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
