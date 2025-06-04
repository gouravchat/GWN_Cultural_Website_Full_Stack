# app-admin/admin_service.py
import requests
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# The URL for the new app-admin-db service.
# In Docker Compose, 'admin_db_api' is the service name, and 5004 is its internal port.
ADMIN_DB_API_BASE_URL = os.environ.get('ADMIN_DB_API_URL', 'http://admin_db_api:5004')

# Endpoint to handle admin registration requests
@app.route('/admin/register', methods=['POST'])
def register_admin():
    """
    Proxies admin registration requests to the admin_db_api service.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    admin_data = request.get_json()
    app.logger.info(f"Admin Service: Received admin registration data: {admin_data.get('username')}")

    try:
        db_response = requests.post(f"{ADMIN_DB_API_BASE_URL}/admins", json=admin_data)
        db_response.raise_for_status() 
        return jsonify(db_response.json()), db_response.status_code
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"Admin Service: Could not connect to Admin DB API for admin registration: {e}")
        return jsonify({"error": "Backend admin database service is unavailable."}), 503
    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Admin Service: Admin DB API returned an error for admin registration: {e.response.status_code} - {e.response.text}")
        return jsonify(e.response.json()), e.response.status_code
    except Exception as e:
        app.logger.error(f"Admin Service: An unexpected error occurred during admin registration: {e}")
        return jsonify({"error": "An unexpected error occurred during admin registration."}), 500

# Endpoint to handle admin login requests
@app.route('/admin/login', methods=['POST'])
def admin_login():
    """
    Proxies admin login requests to the admin_db_api service for authentication.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    credentials = request.get_json()
    username = credentials.get('username')
    password = credentials.get('password')

    if not all([username, password]):
        return jsonify({"error": "Username and password are required for login."}), 400

    app.logger.info(f"Admin Service: Attempting admin login for username: {username}")

    try:
        db_response = requests.post(f"{ADMIN_DB_API_BASE_URL}/admins/login", json={'username': username, 'password': password})
        db_response.raise_for_status()
        return jsonify(db_response.json()), db_response.status_code
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"Admin Service: Could not connect to Admin DB API for admin login: {e}")
        return jsonify({"error": "Backend admin database service is unavailable for authentication."}), 503
    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Admin Service: Admin DB API returned an error for admin login: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401: # Unauthorized from DB API
            return jsonify({"error": "Invalid username or password."}), 401
        return jsonify({"error": "Authentication service error.", "details": e.response.text}), 500
    except Exception as e:
        app.logger.error(f"Admin Service: An unexpected error occurred during admin login: {e}")
        return jsonify({"error": "An unexpected error occurred during admin login."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True) # Running on port 5003
