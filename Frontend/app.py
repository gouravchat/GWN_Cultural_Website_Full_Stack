import os
from flask import Flask, render_template, jsonify, request,send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy # NEW: Import SQLAlchemy
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Database configuration with Flask-SQLAlchemy
# Use os.path.abspath and os.path.join to construct a reliable path
# The database file will now be stored inside the /app/data/db directory within the container.
# Ensure the 'data/db' path matches your Docker volume mount.
DB_DIR = '/app/data/db' # Directory within the container where the DB file will live
DATABASE_FILE = 'feedback.db' # Name of the SQLite database file
FULL_DB_PATH = os.path.join(DB_DIR, DATABASE_FILE)

# Configure SQLAlchemy
# 'sqlite:///' followed by the absolute path to the database file
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{FULL_DB_PATH}' #
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Recommended to disable for performance and to suppress warnings

db = SQLAlchemy(app) # Initialize SQLAlchemy with the Flask app

# Define the FeedbackEntry Model (ORM representation of the 'feedback' table)
class FeedbackEntry(db.Model): #
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) # Store as DateTime object

    def __repr__(self):
        return f'<FeedbackEntry {self.name} - {self.timestamp}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() # Convert datetime to ISO string for JSON
        }

# Function to initialize the database (create tables based on models)
def init_db():
    with app.app_context():
        # Ensure the directory exists first
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR, exist_ok=True)
            print(f"Created database directory: {DB_DIR}")

        # This will create tables for all models defined in your application
        # if they don't already exist.
        db.create_all() #
        print("Database initialized (tables created/verified).")


# Get URLs from environment variables set in docker-compose.yml
AUTH_SERVICE_LOGIN_URL_FOR_CLIENT = os.environ.get('AUTH_SERVICE_LOGIN_URL', 'http://localhost:5002/')
EVENT_SERVICE_URL_FOR_CLIENT = os.environ.get('EVENT_SERVICE_URL', 'http://localhost:5000')

# IMPORTANT: Call init_db() directly, outside of the if __name__ == '__main__': block.
# This ensures it runs when Gunicorn imports the app.
init_db()


@app.route('/')
def landing_page():
    """Serves the main landing page and injects configuration for client-side use."""
    print(f"Auth URL for client: {AUTH_SERVICE_LOGIN_URL_FOR_CLIENT}")
    print(f"Event URL for client: {EVENT_SERVICE_URL_FOR_CLIENT}")
    return render_template(
        'index.html',
        auth_service_login_url=AUTH_SERVICE_LOGIN_URL_FOR_CLIENT,
        event_service_url=EVENT_SERVICE_URL_FOR_CLIENT
    )

# Modified: Endpoint for handling contact form submissions (stores in DB using ORM)
@app.route('/contact', methods=['POST'])
def handle_contact_form():
    if not request.is_json:
        print("Request not JSON")
        return jsonify({"message": "Request must be JSON"}), 400

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')

    if not all([name, email, message]):
        print("Missing required fields")
        return jsonify({"message": "Name, email, and message are required."}), 400

    print(f"Received contact form submission from {name} ({email}): {message}")

    try:
        # Create a new FeedbackEntry object
        new_feedback = FeedbackEntry(
            name=name,
            email=email,
            message=message
            # timestamp is set by default=datetime.utcnow in the model
        )
        db.session.add(new_feedback) # Add the new object to the session
        db.session.commit() # Commit the session to save it to the database

        print("Feedback saved to database successfully (using Flask-SQLAlchemy).")
        return jsonify({"message": "Your message has been received and stored. Thank you!"}), 200

    except Exception as e:
        # Rollback the session in case of an error
        db.session.rollback()
        print(f"Error saving feedback to database: {e}")
        return jsonify({"message": "Failed to save message. Please try again later."}), 500

# Modified: Endpoint to retrieve feedback (for internal use, e.g., by Admin Portal)
@app.route('/feedback', methods=['GET'])
def get_feedback():
    try:
        # Query all feedback entries, ordered by timestamp descending
        feedback_entries = FeedbackEntry.query.order_by(FeedbackEntry.timestamp.desc()).all() #
        # Convert list of model objects to list of dictionaries for JSON response
        return jsonify([entry.to_dict() for entry in feedback_entries]), 200
    except Exception as e:
        print(f"Error retrieving feedback: {e}")
        return jsonify({"message": "Failed to retrieve feedback."}), 500


@app.route('/config')
def get_landing_page_config_for_client():
    return jsonify({
        "authServiceLoginUrl": AUTH_SERVICE_LOGIN_URL_FOR_CLIENT,
        "eventServiceUrl": EVENT_SERVICE_URL_FOR_CLIENT,
    })

@app.route('/static/<path:filename>')
def serve_static_files(filename):
    return send_from_directory(app.static_folder, filename)

# This block should be used ONLY for local development without Gunicorn/Docker
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=8080, debug=True)