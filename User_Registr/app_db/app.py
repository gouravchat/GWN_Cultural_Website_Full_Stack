# app-db/db_service.py
import os
import re # Import regex module
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import UniqueConstraint # Import UniqueConstraint

app = Flask(__name__)

# Configure SQLite database for this service
# The database file 'db_data.db' will be created inside the container's /app directory
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model for User
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    email_id = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False) # In a real app, hash this!
    tower_number = db.Column(db.String(10), nullable=False)
    wing = db.Column(db.String(10), nullable=False)
    number = db.Column(db.String(10), nullable=False) # Flat number (1-12)
    type_val = db.Column(db.String(10), nullable=False) # This is Flat Type (A,B,C,D)
    user_role = db.Column(db.String(10), nullable=False) # User Role (Tenant/Owner)
    
    # New column for combined flat details, made unique
    flat_details = db.Column(db.String(50), unique=True, nullable=False)
    
    registered_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Composite unique constraint for phone_number and flat_details
    __table_args__ = (UniqueConstraint('phone_number', 'flat_details', name='_phone_flat_uc'),)

    def to_dict(self):
        """Converts User object to a dictionary for JSON serialization."""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'email_id': self.email_id,
            'password': self.password, # TEMPORARILY EXPOSED FOR DEBUGGING! REMOVE IN PRODUCTION!
            'tower_number': self.tower_number,
            'wing': self.wing,
            'number': self.number,
            'type_val': self.type_val, # Flat Type
            'user_role': self.user_role, # User Role
            'flat_details': self.flat_details, # New flat_details field
            'registered_on': self.registered_on.isoformat()
        }

# API Endpoints for User Data

@app.route('/users', methods=['POST'])
def create_user():
    """API endpoint to create a new user."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    required_fields = ['first_name', 'last_name', 'phone_number', 'email_id', 'password',
                       'tower_number', 'wing', 'number', 'type_val', 'user_role']
    
    # Check for missing fields
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    # Define allowed values for dropdowns
    allowed_towers = ["Alpine1", "Alpine2", "Alpine3"]
    allowed_wings = ["left", "right", "NA"]
    allowed_flat_types = ["A", "B", "C", "D"]
    allowed_user_roles = ["Tenant", "Owner"]

    # Backend Validation Logic
    phone_number = data['phone_number']
    email_id = data['email_id']
    password = data['password']
    tower_number = data['tower_number']
    wing = data['wing']
    flat_number_str = data['number']
    flat_type = data['type_val']
    user_role = data['user_role']

    # Phone Number Validation (basic 10-digit number)
    if not re.fullmatch(r'^\d{10}$', phone_number):
        return jsonify({"error": "Invalid phone number format. Must be 10 digits."}), 400

    # Email ID Validation
    if not re.fullmatch(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_id):
        return jsonify({"error": "Invalid email ID format."}), 400

    # Password Validation (max length 6, alphanumeric)
    if not (1 <= len(password) <= 6 and password.isalnum()):
        return jsonify({"error": "Password must be alphanumeric and between 1 and 6 characters long."}), 400

    # Tower Number Validation
    if tower_number not in allowed_towers:
        return jsonify({"error": f"Invalid tower number. Allowed values are: {', '.join(allowed_towers)}."}), 400

    # Wing Validation
    if wing not in allowed_wings:
        return jsonify({"error": f"Invalid wing. Allowed values are: {', '.join(allowed_wings)}."}), 400
    
    # Flat Type Validation (A, B, C, D)
    if flat_type not in allowed_flat_types:
        return jsonify({"error": f"Invalid flat type. Allowed values are: {', '.join(allowed_flat_types)}."}), 400

    # User Role Validation (Tenant, Owner)
    if user_role not in allowed_user_roles:
        return jsonify({"error": f"Invalid user role. Allowed values are: {', '.join(allowed_user_roles)}."}), 400

    # Flat Number Validation (1 to 12)
    try:
        flat_number_int = int(flat_number_str)
        if not (1 <= flat_number_int <= 12):
            return jsonify({"error": "Flat number must be an integer between 1 and 12."}), 400
        # Ensure 'number' is stored as a string in the DB if that's the schema expectation
        data['number'] = str(flat_number_int) 
    except ValueError:
        return jsonify({"error": "Flat number must be a valid integer."}), 400

    # Construct flat_details string
    constructed_flat_details = f"{tower_number}-{wing}-{flat_type}-{data['number']}"
    
    try:
        # Check if user already exists based on phone number or email
        existing_user_phone = User.query.filter_by(phone_number=phone_number).first()
        if existing_user_phone:
            return jsonify({"error": f"User with phone number {phone_number} already exists"}), 409 # Conflict

        existing_user_email = User.query.filter_by(email_id=email_id).first()
        if existing_user_email:
            return jsonify({"error": f"User with email ID {email_id} already exists"}), 409 # Conflict

        # Check if flat_details already exists (unique constraint)
        existing_flat_details = User.query.filter_by(flat_details=constructed_flat_details).first()
        if existing_flat_details:
            return jsonify({"error": f"Flat details '{constructed_flat_details}' already registered."}), 409 # Conflict

        # The composite unique constraint (_phone_flat_uc) on (phone_number, flat_details)
        # will be handled by SQLAlchemy's commit, raising an IntegrityError if violated.
        # We don't need an explicit query here for it, as the DB will enforce it.

        new_user = User(
            first_name=data['first_name'],
            middle_name=data.get('middle_name'),
            last_name=data['last_name'],
            phone_number=phone_number,
            email_id=email_id,
            password=password, # WARNING: Storing plaintext password. HASH THIS IN A REAL APP!
            tower_number=tower_number,
            wing=wing,
            number=data['number'],
            type_val=flat_type,
            user_role=user_role,
            flat_details=constructed_flat_details # Assign the constructed flat_details
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User created successfully", "user_id": new_user.phone_number}), 201

    except Exception as e:
        db.session.rollback()
        # Check for specific IntegrityError if needed, but a general rollback is fine for now
        print(f"Database service error: {e}")
        # More detailed error for debugging, but keep generic for user
        return jsonify({"error": "Internal server error or data conflict.", "details": str(e)}), 500

@app.route('/users/<string:phone_number>', methods=['GET'])
def get_user(phone_number):
    """API endpoint to get user details by phone number."""
    try:
        user = User.query.filter_by(phone_number=phone_number).first()
        if user:
            return jsonify(user.to_dict()), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        print(f"Database service error: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/users', methods=['GET'])
def get_all_users():
    """API endpoint to get all user details."""
    try:
        users = User.query.all()
        if users:
            return jsonify([user.to_dict() for user in users]), 200
        else:
            return jsonify({"message": "No users found"}), 200
    except Exception as e:
        print(f"Database service error: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# NEW: Update User Endpoint
@app.route('/users/<string:phone_number>', methods=['PUT'])
def update_user(phone_number):
    """
    API endpoint to update user details.
    Phone number and flat details are not editable. Password is not directly updated here.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    try:
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return jsonify({"error": "User not found."}), 404

        # Define allowed values for dropdowns for validation
        allowed_towers = ["Alpine1", "Alpine2", "Alpine3"]
        allowed_wings = ["left", "right", "NA"]
        allowed_flat_types = ["A", "B", "C", "D"]
        allowed_user_roles = ["Tenant", "Owner"]

        # Update fields, performing validation where necessary
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'middle_name' in data:
            user.middle_name = data['middle_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        
        # Email ID update with validation
        if 'email_id' in data and data['email_id'] != user.email_id:
            if not re.fullmatch(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data['email_id']):
                return jsonify({"error": "Invalid email ID format."}), 400
            # Check if new email is already in use by another user
            existing_email_user = User.query.filter(User.email_id == data['email_id'], User.phone_number != phone_number).first()
            if existing_email_user:
                return jsonify({"error": f"Email ID {data['email_id']} is already registered to another user."}), 409
            user.email_id = data['email_id']
        
        # Tower Number Validation
        if 'tower_number' in data:
            if data['tower_number'] not in allowed_towers:
                return jsonify({"error": f"Invalid tower number. Allowed values are: {', '.join(allowed_towers)}."}), 400
            user.tower_number = data['tower_number']

        # Wing Validation
        if 'wing' in data:
            if data['wing'] not in allowed_wings:
                return jsonify({"error": f"Invalid wing. Allowed values are: {', '.join(allowed_wings)}."}), 400
            user.wing = data['wing']

        # Flat Type Validation
        if 'type_val' in data:
            if data['type_val'] not in allowed_flat_types:
                return jsonify({"error": f"Invalid flat type. Allowed values are: {', '.join(allowed_flat_types)}."}), 400
            user.type_val = data['type_val']

        # Flat Number Validation (1 to 12)
        if 'number' in data:
            try:
                flat_number_int = int(data['number'])
                if not (1 <= flat_number_int <= 12):
                    return jsonify({"error": "Flat number must be an integer between 1 and 12."}), 400
                user.number = str(flat_number_int)
            except ValueError:
                return jsonify({"error": "Flat number must be a valid integer."}), 400
        
        # User Role Validation
        if 'user_role' in data:
            if data['user_role'] not in allowed_user_roles:
                return jsonify({"error": f"Invalid user role. Allowed values are: {', '.join(allowed_user_roles)}."}), 400
            user.user_role = data['user_role']

        # Reconstruct flat_details if any relevant fields changed
        new_flat_details = f"{user.tower_number}-{user.wing}-{user.type_val}-{user.number}"
        
        # Check if the new flat_details conflict with another user (excluding self)
        if new_flat_details != user.flat_details:
            existing_flat_user = User.query.filter(
                User.flat_details == new_flat_details,
                User.phone_number != phone_number
            ).first()
            if existing_flat_user:
                return jsonify({"error": f"Flat details '{new_flat_details}' are already registered to another user."}), 409
            user.flat_details = new_flat_details # Update if valid and not conflicting

        db.session.commit()
        return jsonify({"message": "User updated successfully", "user": user.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Database service error during update: {e}")
        return jsonify({"error": "Internal server error during update.", "details": str(e)}), 500

# This ensures tables are created when the Flask app starts
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
