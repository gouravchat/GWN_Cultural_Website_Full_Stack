# app-auth/auth_service.py
import requests
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# The URL for the app-db service.
# In Docker Compose, 'db_api' is the service name, and 5001 is its internal port.
DB_API_BASE_URL = os.environ.get('DB_API_URL', 'http://db_api:5001')

# NEW: Endpoint to handle login requests
@app.route('/login', methods=['POST'])
def login_user():
    """
    Authenticates a user based on phone number and password by querying the db_api.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    credentials = request.get_json()
    phone_number = credentials.get('phone_number')
    password = credentials.get('password')

    if not all([phone_number, password]):
        return jsonify({"error": "Phone number and password are required."}), 400

    app.logger.info(f"Auth Service: Attempting login for phone: {phone_number}")

    try:
        # Step 1: Fetch user details from db_api
        # WARNING: In a real app, db_api should have an endpoint to get user's HASHED password
        # based on phone_number, NOT the full user object with plaintext password.
        # For this example, we're fetching the full user object for simplicity of demonstration.
        db_response = requests.get(f"{DB_API_BASE_URL}/users/{phone_number}")
        db_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        user_data = db_response.json()

        # Step 2: Verify password
        # WARNING: Plaintext password comparison! HASH THIS IN A REAL APP!
        if user_data and user_data.get('password') == password:
            # In a real app, you'd generate a JWT or session token here
            return jsonify({"message": "Login successful", "user_id": phone_number}), 200
        else:
            return jsonify({"error": "Invalid phone number or password."}), 401 # Unauthorized

    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"Auth Service: Could not connect to DB API: {e}")
        return jsonify({"error": "Backend database service is unavailable for authentication."}), 503
    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Auth Service: DB API returned an error: {e.response.status_code} - {e.response.text}")
        # If user not found (404 from db_api), return invalid credentials
        if e.response.status_code == 404:
            return jsonify({"error": "Invalid phone number or password."}), 401
        return jsonify({"error": "Authentication service error.", "details": e.response.text}), 500
    except Exception as e:
        app.logger.error(f"Auth Service: An unexpected error occurred during login: {e}")
        return jsonify({"error": "An unexpected error occurred during login."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True) # Running on port 5002
