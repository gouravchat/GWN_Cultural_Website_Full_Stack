import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import logging # Import logging

app = Flask(__name__)

CORS(app)  # Enable CORS for all routes

# Configure SQLite database for this service
# The database file 'users.db' will be created inside the container's /app/db_data directory
# Make sure this path matches the volume mount in docker-compose.yml: db_data:/app/db_data
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/data/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configure logger for db service
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
db_logger = logging.getLogger(__name__)

# Database Model for User
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False) # NEW: Phone number field
    hashed_password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone_number': self.phone_number, # Include phone number
            'role': self.role,
            'hashed_password': self.hashed_password # Still include hashed password for completeness if needed by other services
        }

# --- API Endpoints ---

@app.route('/users', methods=['POST'])
def create_user():
    """
    Creates a new user in the database.
    Expected JSON: {"username": "...", "email": "...", "phone_number": "...", "hashed_password": "...", "role": "..."}
    """
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    phone_number = data.get('phone_number')
    hashed_password = data.get('hashed_password')
    role = data.get('role', 'user')

    if not username or not email or not phone_number or not hashed_password:
        return jsonify({"error": "Username, email, phone number, and hashed_password are required."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists."}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 409
    if User.query.filter_by(phone_number=phone_number).first():
        return jsonify({"error": "Phone number already exists."}), 409

    new_user = User(username=username, email=email, phone_number=phone_number, hashed_password=hashed_password, role=role)
    try:
        db.session.add(new_user)
        db.session.commit()
        db_logger.info(f"User '{username}' created successfully.")
        return jsonify(new_user.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        db_logger.error(f"Error creating user: {e}")
        return jsonify({"error": "Could not create user.", "details": str(e)}), 500

@app.route('/users', methods=['GET'])
def get_users():
    """
    Retrieves users. Can filter by 'query' (username, email, or phone number) for auth_api,
    or return all users.
    """
    query_param = request.args.get('query')

    if query_param:
        # For authentication, find a user by username, email, or phone number
        user = User.query.filter(
            (User.username == query_param) |
            (User.email == query_param) |
            (User.phone_number == query_param)
        ).first()
        if user:
            return jsonify(user.to_dict()), 200
        else:
            return jsonify({"message": "User not found."}), 404
    else:
        users = User.query.all()
        return jsonify([user.to_dict() for user in users]), 200

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """Retrieves a user by their ID."""
    user = User.query.get(user_id)
    if user:
        return jsonify(user.to_dict()), 200
    return jsonify({"message": "User not found."}), 404

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Updates an existing user's information.
    Specifically used for updating hashed_password during password reset.
    Expected JSON: {"hashed_password": "..."} (or other fields)
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found."}), 404

    data = request.get_json()

    # Allow updating of specific fields. Here, we focus on hashed_password.
    # You can extend this to allow updating other fields as needed.
    if 'hashed_password' in data:
        user.hashed_password = data['hashed_password']
        db_logger.info(f"User {user_id}: hashed_password updated.")
    
    if 'username' in data:
        if User.query.filter(User.username == data['username'], User.id != user_id).first():
            return jsonify({"error": "Username already taken."}), 409
        user.username = data['username']
        db_logger.info(f"User {user_id}: username updated to {data['username']}.")
    
    if 'email' in data:
        if User.query.filter(User.email == data['email'], User.id != user_id).first():
            return jsonify({"error": "Email already registered."}), 409
        user.email = data['email']
        db_logger.info(f"User {user_id}: email updated to {data['email']}.")

    if 'phone_number' in data:
        if User.query.filter(User.phone_number == data['phone_number'], User.id != user_id).first():
            return jsonify({"error": "Phone number already registered."}), 409
        user.phone_number = data['phone_number']
        db_logger.info(f"User {user_id}: phone_number updated to {data['phone_number']}.")

    if 'role' in data:
        user.role = data['role']
        db_logger.info(f"User {user_id}: role updated to {data['role']}.")


    try:
        db.session.commit()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        db_logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({"error": "Could not update user.", "details": str(e)}), 500


# --- Database Initialization ---
with app.app_context():
    # This creates tables if they don't exist. If you made schema changes (like adding phone_number),
    # you MUST delete the old `db_data` Docker volume and let it recreate to apply the new schema.
    db.create_all()
    print("Database tables for users created/checked.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)