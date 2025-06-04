# app-admin-db/admin_db_service.py
import os
import re
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configure SQLite database for this service (Admin-specific DB)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///admin_db_data.db' # Separate database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model for Admin Users
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email_id = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # Storing hashed password
    registered_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        """Converts Admin object to a dictionary for JSON serialization (without password_hash)."""
        return {
            'id': self.id,
            'username': self.username,
            'email_id': self.email_id,
            'registered_on': self.registered_on.isoformat()
        }

# API Endpoints for Admin Data

@app.route('/admins', methods=['POST'])
def create_admin():
    """API endpoint to create a new admin user (max 3 admins)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    required_fields = ['username', 'email_id', 'password']
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    username = data['username']
    email_id = data['email_id']
    password = data['password']

    # Admin count check
    if Admin.query.count() >= 3:
        return jsonify({"error": "Maximum number of 3 admins already registered."}), 403 # Forbidden

    # Validation
    if not re.fullmatch(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_id):
        return jsonify({"error": "Invalid email ID format."}), 400
    if not (1 <= len(password) <= 6 and password.isalnum()):
        return jsonify({"error": "Password must be alphanumeric and between 1 and 6 characters long."}), 400

    try:
        existing_admin_username = Admin.query.filter_by(username=username).first()
        if existing_admin_username:
            return jsonify({"error": f"Admin with username '{username}' already exists."}), 409

        existing_admin_email = Admin.query.filter_by(email_id=email_id).first()
        if existing_admin_email:
            return jsonify({"error": f"Admin with email ID '{email_id}' already exists."}), 409

        hashed_password = generate_password_hash(password)

        new_admin = Admin(
            username=username,
            email_id=email_id,
            password_hash=hashed_password
        )
        db.session.add(new_admin)
        db.session.commit()
        return jsonify({"message": "Admin created successfully", "admin_username": new_admin.username}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Admin DB Service error during admin creation: {e}")
        return jsonify({"error": "Internal server error or data conflict.", "details": str(e)}), 500

@app.route('/admins/login', methods=['POST'])
def admin_login():
    """Authenticates an admin user."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return jsonify({"error": "Username and password are required."}), 400

    try:
        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password_hash, password):
            return jsonify({"message": "Admin login successful", "admin_username": admin.username}), 200
        else:
            return jsonify({"error": "Invalid username or password."}), 401
    except Exception as e:
        print(f"Admin DB Service error during admin login: {e}")
        return jsonify({"error": "Internal server error during admin login.", "details": str(e)}), 500

@app.route('/admins', methods=['GET'])
def get_all_admins():
    """API endpoint to get all admin details."""
    try:
        admins = Admin.query.all()
        if admins:
            return jsonify([admin.to_dict() for admin in admins]), 200
        else:
            return jsonify({"message": "No admins found"}), 200
    except Exception as e:
        print(f"Admin DB Service error during get all admins: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


# This ensures tables are created when the Flask app starts
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True) # Running on port 5004
