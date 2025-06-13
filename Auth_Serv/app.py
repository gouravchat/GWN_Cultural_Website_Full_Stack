import os
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, session, url_for
from bcrypt import hashpw, gensalt, checkpw
from flask_cors import CORS

app = Flask(__name__)

CORS(app)  # Enable CORS for all routes


# --- Configuration ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_very_secret_key_here_change_me_for_auth_serv')

DB_API_URL = os.environ.get('DB_API_URL', 'http://localhost:5004')

# Define redirect URLs. These should ideally come from environment variables.
USER_PORTAL_URL_AFTER_LOGIN = os.environ.get('USER_PORTAL_URL', 'http://localhost:5001/portal') # e.g., http://host:port/portal
ADMIN_PORTAL_URL_AFTER_LOGIN = os.environ.get('ADMIN_PORTAL_URL', 'http://localhost:5001/') # Admin Portal root, as per docker-compose for admin-portal-service

# --- Routes for Frontend (Login/Registration Page) ---
@app.route('/')
def login_or_register_page():
    """Serves the login/registration page (index.html for Auth_Serv)."""
    # Check if 'target' query param is present for admin login attempt from landing page
    target_portal = request.args.get('target')
    return render_template('index.html', target_portal=target_portal) # Pass target to template if needed for UI cues

@app.route('/static/<path:filename>')
def serve_auth_static(filename):
    """Serves static files (CSS, JS) for the Auth_Serv's login/registration page."""
    return send_from_directory('static', filename)
# --- End Routes ---


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier')
    password = data.get('password')

    if not identifier or not password:
        return jsonify({"error": "Identifier (username/email/phone) and password are required."}), 400

    try:
        db_response = requests.get(f"{DB_API_URL}/users", params={'query': identifier})
        db_response.raise_for_status()
        user_data_response = db_response.json()

        user = None
        if isinstance(user_data_response, list):
            for u_data in user_data_response:
                if (u_data.get('username') == identifier or
                    u_data.get('email') == identifier or
                    u_data.get('phone_number') == identifier):
                    user = u_data
                    break
        elif isinstance(user_data_response, dict) and user_data_response.get("id"):
            if (user_data_response.get('username') == identifier or
                user_data_response.get('email') == identifier or
                user_data_response.get('phone_number') == identifier):
                user = user_data_response
        elif isinstance(user_data_response, dict) and user_data_response.get("message") == "User not found.":
            return jsonify({"error": "Invalid credentials."}), 401


        if not user or 'hashed_password' not in user:
            return jsonify({"error": "Invalid credentials or user data issue."}), 401

        if checkpw(password.encode('utf-8'), user['hashed_password'].encode('utf-8')):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user.get('role', 'user')
            session.permanent = True

            redirect_url = ""
            if user.get('role') == 'admin':
                # Admin Portal URL does not need user ID typically for its root page
                redirect_url = ADMIN_PORTAL_URL_AFTER_LOGIN
            else:
                # User Portal URL needs user ID as path parameter: http://localhost:5001/portal/123
                base_user_portal_url = USER_PORTAL_URL_AFTER_LOGIN.rstrip('/')
                redirect_url = f"{base_user_portal_url}/{user['id']}"
            
            app.logger.info(f"Login successful for {user['username']}. Role: {user.get('role')}. Redirecting to: {redirect_url}")

            return jsonify({
                "message": "Login successful",
                "user_id": user['id'],
                "username": user['username'],
                "role": user.get('role', 'user'),
                "redirect_url": redirect_url
            }), 200
        else:
            return jsonify({"error": "Invalid credentials."}), 401

    except requests.exceptions.ConnectionError:
        app.logger.error("Failed to connect to DB API during login.")
        return jsonify({"error": "Login service is temporarily unavailable (DB API connection error)."}), 503
    except requests.exceptions.Timeout:
        app.logger.error("DB API connection timed out during login.")
        return jsonify({"error": "Login service is temporarily unavailable (DB API timeout)."}), 504
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response is not None else 500
        app.logger.error(f"Error communicating with DB API during login: {e} (Status: {status_code})")
        error_details = "Error during DB API communication"
        if e.response is not None:
            try:
                error_details_from_db = e.response.json().get('error', str(e))
                error_details = f"DB API Error: {error_details_from_db}"
            except ValueError:
                error_details = f"DB API Error: {e.response.text}"
        return jsonify({"error": error_details}), status_code
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during login: {e}")
        return jsonify({"error": "An internal server error occurred during login."}), 500


@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    phone_number = data.get('phone_number')
    password = data.get('password')

    if not all([username, email, phone_number, password]):
        return jsonify({"error": "All fields are required."}), 400
    
    if not "@" in email:
        return jsonify({"error": "Invalid email format."}), 400
    
    hashed_password = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')
    new_user_data = {
        "username": username,
        "email": email,
        "phone_number": phone_number,
        "hashed_password": hashed_password,
        "role": "user"
    }

    try:
        db_response = requests.post(f"{DB_API_URL}/users", json=new_user_data)
        db_response.raise_for_status()
        created_user = db_response.json()
        
        session['user_id'] = created_user['id']
        session['username'] = created_user['username']
        session['role'] = created_user.get('role', 'user')
        session.permanent = True

        # Redirect new users to their portal page
        base_user_portal_url = USER_PORTAL_URL_AFTER_LOGIN.rstrip('/')
        registration_redirect_url = f"{base_user_portal_url}/{created_user['id']}"

        return jsonify({
            "message": "User registered successfully. You are now logged in.",
            "user": created_user,
            "redirect_url": registration_redirect_url
        }), 201

    except requests.exceptions.ConnectionError:
        app.logger.error("Failed to connect to DB API during registration.")
        return jsonify({"error": "Registration service is temporarily unavailable (DB API connection error)."}), 503
    except requests.exceptions.Timeout:
        app.logger.error("DB API connection timed out during registration.")
        return jsonify({"error": "Registration service is temporarily unavailable (DB API timeout)."}), 504
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response is not None else 500
        app.logger.error(f"Error communicating with DB API during registration: {e} (Status: {status_code})")
        error_details = "Error during DB API communication for registration"
        if e.response is not None:
            try:
                error_details_from_db = e.response.json().get('error', str(e))
                if status_code == 409:
                     return jsonify({"error": error_details_from_db or "User with these details already exists."}), 409
                error_details = f"DB API Error: {error_details_from_db}"
            except ValueError:
                error_details = f"DB API Error: {e.response.text}"
        return jsonify({"error": error_details}), status_code
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during registration: {e}")
        return jsonify({"error": "An internal server error occurred during registration."}), 500

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    # Redirect to the Auth Service's own login page after logout
    return jsonify({"message": "Logout successful", "redirect_url": url_for('login_or_register_page', _external=False)}), 200


@app.route('/hash_password', methods=['POST'])
def hash_password_endpoint():
    data = request.get_json()
    password = data.get('password')
    if not password:
        return jsonify({"error": "Password is required."}), 400
    hashed = hashpw(password.encode('utf-8'), gensalt())
    return jsonify({"hashed_password": hashed.decode('utf-8')}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
