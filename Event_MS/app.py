import os
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_cors import CORS # Import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure SQLite database for this service
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/data/events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Configuration for File Uploads ---
UPLOAD_FOLDER = 'static/event_photos'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# --- End Configuration for File Uploads ---

# Database Model for Event (MODIFIED with new food charge fields)
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    time_str = db.Column(db.String(50), nullable=False)
    close_date_str = db.Column(db.String(50), nullable=False)
    venue = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    photo_url = db.Column(db.String(255), nullable=True)

    cover_charges = db.Column(db.Float, default=0.0)
    cover_charges_type = db.Column(db.String(20), default='per_head')

    # NEW: Food charges fields
    food_charges = db.Column(db.Float, default=0.0)
    food_type = db.Column(db.String(20), default='veg') # e.g., 'veg', 'non_veg', 'both'
    food_charges_type = db.Column(db.String(20), default='per_head') # e.g., 'per_head', 'per_family'
    # END NEW

    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        """Converts Event object to a dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'time': self.time_str,
            'close_date': self.close_date_str,
            'venue': self.venue,
            'details': self.details,
            'photo_url': self.photo_url,
            'subscription': {
                'coverCharges': self.cover_charges,
                'coverChargesType': self.cover_charges_type,
            },
            # NEW: Include food charges in the dictionary
            'food': {
                'foodCharges': self.food_charges,
                'foodType': self.food_type,
                'foodChargesType': self.food_charges_type,
            },
            # END NEW
            'created_on': self.created_on.isoformat()
        }

# Helper function to delete expired events (remains the same)
def delete_expired_events():
    """
    Deletes events from the database whose close_date has passed.
    Note: For this mockup, we'll parse close_date_str to datetime for comparison.
    """
    try:
        now = datetime.utcnow()
        all_events = Event.query.all()
        expired_events = []
        for event in all_events:
            try:
                close_dt = datetime.fromisoformat(event.close_date_str)
                if close_dt < now:
                    expired_events.append(event)
            except ValueError:
                print(f"Warning: Could not parse close_date_str for event ID {event.id}: {event.close_date_str}")
                continue

        if expired_events:
            for event in expired_events:
                db.session.delete(event)
            db.session.commit()
            print(f"Deleted {len(expired_events)} expired events.")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting expired events: {e}")

# API Endpoints

@app.route('/')
def index():
    """Serves the main HTML page from the templates folder."""
    return render_template('index.html')

@app.route('/events', methods=['POST'])
def create_event():
    """
    API endpoint to create a new event, now supporting file upload and food charges.
    Expects FormData from the frontend.
    """
    name = request.form.get('name')
    time_str = request.form.get('time')
    close_date_str = request.form.get('close_date')
    venue = request.form.get('venue')
    details = request.form.get('details')
    cover_charges_str = request.form.get('coverCharges', '0.0')
    cover_charges_type = request.form.get('coverChargesType', 'per_head')

    # NEW: Get food charges fields from form data
    food_charges_str = request.form.get('foodCharges', '0.0')
    food_type = request.form.get('foodType', 'veg')
    food_charges_type = request.form.get('foodChargesType', 'per_head')
    # END NEW

    # Validate required fields
    required_fields = {'name', 'time', 'close_date', 'venue', 'details'}
    for field in required_fields:
        if not request.form.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Parse and validate cover charges
    try:
        cover_charges = float(cover_charges_str)
        if cover_charges < 0:
            return jsonify({"error": "'coverCharges' cannot be negative."}), 400
    except ValueError:
        return jsonify({"error": "Invalid number format for 'coverCharges'."}), 400

    if cover_charges_type not in ['per_head', 'per_family']:
        return jsonify({"error": "Invalid value for 'coverChargesType'. Allowed: 'per_head', 'per_family'"}), 400

    # NEW: Parse and validate food charges
    try:
        food_charges = float(food_charges_str)
        if food_charges < 0:
            return jsonify({"error": "'foodCharges' cannot be negative."}), 400
    except ValueError:
        return jsonify({"error": "Invalid number format for 'foodCharges'."}), 400

    if food_type not in ['veg', 'non_veg', 'both']:
        return jsonify({"error": "Invalid value for 'foodType'. Allowed: 'veg', 'non_veg', 'both'"}), 400

    if food_charges_type not in ['per_head', 'per_family']:
        return jsonify({"error": "Invalid value for 'foodChargesType'. Allowed: 'per_head', 'per_family'"}), 400
    # END NEW

    photo_url = None
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo.filename != '' and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                photo.save(file_path)
                photo_url = f"/static/event_photos/{filename}"
            except Exception as e:
                return jsonify({"error": "Failed to save photo", "details": str(e)}), 500
        elif photo.filename != '':
            return jsonify({"error": "Invalid file type or empty filename for photo."}), 400

    try:
        new_event = Event(
            name=name,
            time_str=time_str,
            close_date_str=close_date_str,
            venue=venue,
            details=details,
            cover_charges=cover_charges,
            cover_charges_type=cover_charges_type,
            # NEW: Assign new food charges fields
            food_charges=food_charges,
            food_type=food_type,
            food_charges_type=food_charges_type,
            # END NEW
            photo_url=photo_url
        )
        db.session.add(new_event)
        db.session.commit()
        return jsonify({"message": "Event created successfully", "event": new_event.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating event: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/events', methods=['GET'])
def get_all_events():
    """API endpoint to get all events."""
    delete_expired_events()
    try:
        events = Event.query.all()
        if events:
            return jsonify([event.to_dict() for event in events]), 200
        else:
            return jsonify([]), 200
    except Exception as e:
        print(f"Database service error fetching events: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    
#  get evetns by event id
@app.route('/events/<int:event_id>', methods=['GET'])
def get_event_by_id(event_id):
    """API endpoint to get an event by ID."""
    try:
        event = Event.query.get(event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404
        return jsonify(event.to_dict()), 200
    except Exception as e:
        print(f"Error fetching event by ID {event_id}: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# create delete event endpoint
@app.route('/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """API endpoint to delete an event by ID."""
    try:
        event = Event.query.get(event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404
        db.session.delete(event)
        db.session.commit()
        return jsonify({"message": "Event deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting event: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# --- Database Initialization ---
with app.app_context():
    db.create_all()
    delete_expired_events()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)