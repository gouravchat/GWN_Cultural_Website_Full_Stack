import os
import json
from flask import Flask, request, jsonify, send_from_directory, render_template, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_cors import CORS

# Get the script name from environment variable, which Nginx will pass
EVENT_SERVICE_SCRIPT_NAME = os.environ.get('FLASK_SCRIPT_NAME', '')

app = Flask(__name__,
            static_url_path=EVENT_SERVICE_SCRIPT_NAME + '/static',
            static_folder='static')
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/data/events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Configuration for File Uploads ---
# --- Configuration for File Uploads ---
# CRITICAL CHANGE: Set UPLOAD_FOLDER to a sub-directory within the *persistent* volume (/app/data)
# This path is relative to the app's WORKDIR (/app)
UPLOAD_SUBDIR = 'event_photos' # Subdirectory name within /app/data
UPLOAD_BASE_DIR = 'data' # This maps to /app/data which is the mounted volume
UPLOAD_FOLDER_RELATIVE_TO_APP = os.path.join(UPLOAD_BASE_DIR, UPLOAD_SUBDIR)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), UPLOAD_FOLDER_RELATIVE_TO_APP)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

    food_charges = db.Column(db.Float, default=0.0)
    food_type = db.Column(db.String(20), default='veg')
    food_charges_type = db.Column(db.String(20), default='per_head')

    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
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
            'food': {
                'foodCharges': self.food_charges,
                'foodType': self.food_type,
                'foodChargesType': self.food_charges_type,
            },
            'created_on': self.created_on.isoformat()
        }

def delete_expired_events():
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

app.config['APPLICATION_ROOT'] = EVENT_SERVICE_SCRIPT_NAME

@app.before_request
def set_script_name_from_proxy():
    if 'X-Forwarded-Prefix' in request.headers:
        request.environ['SCRIPT_NAME'] = request.headers['X-Forwarded-Prefix']
    elif EVENT_SERVICE_SCRIPT_NAME:
        request.environ['SCRIPT_NAME'] = EVENT_SERVICE_SCRIPT_NAME
    else:
        request.environ['SCRIPT_NAME'] = ''

@app.route(f'{EVENT_SERVICE_SCRIPT_NAME}/') # Main index route
def index():
    event_api_base = url_for('get_all_events', _external=False)
    if event_api_base.endswith('/events'):
        event_api_base = event_api_base.rsplit('/events', 1)[0]
    return render_template('index.html', EVENT_API_BASE_URL=event_api_base)

@app.route(f'{EVENT_SERVICE_SCRIPT_NAME}/events', methods=['POST']) # Create event API
def create_event():
    name = request.form.get('name')
    time_str = request.form.get('time')
    close_date_str = request.form.get('close_date')
    venue = request.form.get('venue')
    details = request.form.get('details')
    cover_charges_str = request.form.get('coverCharges', '0.0')
    cover_charges_type = request.form.get('coverChargesType', 'per_head')

    food_charges_str = request.form.get('foodCharges', '0.0')
    food_type = request.form.get('foodType', 'veg')
    food_charges_type = request.form.get('foodChargesType', 'per_head')

    required_fields = {'name', 'time', 'close_date', 'venue', 'details'}
    for field in required_fields:
        if not request.form.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        cover_charges = float(cover_charges_str)
        if cover_charges < 0:
            return jsonify({"error": "'coverCharges' cannot be negative."}), 400
    except ValueError:
        return jsonify({"error": "Invalid number format for 'coverCharges'."}), 400

    if cover_charges_type not in ['per_head', 'per_family']:
        return jsonify({"error": "Invalid value for 'coverChargesType'. Allowed: 'per_head', 'per_family'"}), 400

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

    photo_url_to_save = None
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo.filename != '' and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                photo.save(file_path)
                photo_url_to_save = f"/static/event_photos/{filename}"
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
            food_charges=food_charges,
            food_type=food_type,
            food_charges_type=food_charges_type,
            photo_url=photo_url_to_save
        )
        db.session.add(new_event)
        db.session.commit()
        
        event_dict = new_event.to_dict()
        if event_dict['photo_url']:
            static_filename = event_dict['photo_url'].replace('/static/', '')
            event_dict['photo_url'] = url_for('static', filename=static_filename, _external=False) # Changed 'serve_static' to 'static'
        return jsonify({"message": "Event created successfully", "event": event_dict}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating event: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route(f'{EVENT_SERVICE_SCRIPT_NAME}/events', methods=['GET']) # Get all events API
def get_all_events():
    delete_expired_events()
    try:
        events = Event.query.all()
        if events:
            events_data = []
            for event in events:
                event_dict = event.to_dict()
                if event_dict['photo_url']:
                    if event_dict['photo_url'].startswith('/static/'):
                         static_filename = event_dict['photo_url'].replace('/static/', '')
                         event_dict['photo_url'] = url_for('static', filename=static_filename, _external=False) # Changed 'serve_static' to 'static'
                events_data.append(event_dict)
            return jsonify(events_data), 200
        else:
            return jsonify({"message": "No events found"}), 200
    except Exception as e:
        print(f"Database service error fetching events: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    
@app.route(f'{EVENT_SERVICE_SCRIPT_NAME}/events/<int:event_id>', methods=['GET']) # Get event by ID API
def get_event_by_id(event_id):
    try:
        event = Event.query.get(event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404
        event_dict = event.to_dict()
        if event_dict['photo_url'] and event_dict['photo_url'].startswith('/static/'):
             static_filename = event_dict['photo_url'].replace('/static/', '')
             event_dict['photo_url'] = url_for('static', filename=static_filename, _external=False) # Changed 'serve_static' to 'static'
        return jsonify(event_dict), 200
    except Exception as e:
        print(f"Error fetching event by ID {event_id}: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# Explicitly define static route. Flask's constructor handles this when static_url_path is set.
# Flask's built-in static handler expects paths relative to its static_folder.
# So if the Nginx passes /events/static/photo.jpg, Flask sees /static/photo.jpg internally.
# The @app.route needs to reflect that.
# REMOVED: No prefix here for internal route
@app.route('/static/<path:filename>') # <--- Uncommented this line
def serve_static(filename):
    """Serves static files (e.g., event photos) for the Event service."""
    # This path is relative to the static_folder specified in Flask constructor.
    # It will correctly handle requests like /static/event_photos/image.jpg internally.
    return send_from_directory(app.static_folder, filename)

@app.route(f'{EVENT_SERVICE_SCRIPT_NAME}/events/<int:event_id>', methods=['DELETE']) # Delete event API
def delete_event(event_id):
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

with app.app_context():
    db.create_all()
    delete_expired_events()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
