import os
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, session, url_for
from bcrypt import hashpw, gensalt, checkpw
from flask_cors import CORS
import logging
import time

# Email sending imports
import smtplib
import ssl
from email.mime.text import MIMEText

# Get the script name from environment variable, which Nginx will pass
AUTH_SERVICE_SCRIPT_NAME = os.environ.get('FLASK_SCRIPT_NAME', '')

app = Flask(__name__,
            static_url_path=AUTH_SERVICE_SCRIPT_NAME + '/static',
            static_folder='static')

CORS(app)

# --- Configuration ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_very_secret_key_here_change_me_for_auth_serv')

DB_API_URL = os.environ.get('DB_API_URL', 'http://localhost:5004')

USER_PORTAL_URL_AFTER_LOGIN = os.environ.get('USER_PORTAL_URL', 'https://localhost/user-portal')
ADMIN_PORTAL_URL_AFTER_LOGIN = os.environ.get('ADMIN_PORTAL_URL', 'https://localhost/admin-portal')

# --- Email Sender Configuration ---
# These MUST be set in your .env file and passed to the auth_api service in docker-compose.yml
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
EMAIL_SENDER = os.environ.get('EMAIL_SENDER',"nest.alpine.cultural.team@gmail.com") # The email address that will SEND the welcome emails
EMAIL_PASSWORD = os.environ.get('EMAIL_APP_PASSWORD',"ukdz guel pqyv pnfc") # The App Password for the SENDER email


# print("Email Sender:", EMAIL_SENDER)
# print("SMTP Server:", SMTP_SERVER)
# print("SMTP Port:", SMTP_PORT)
# print("EMAIL_PASSWORD:", EMAIL_PASSWORD)


# --- Crucial: Set APPLICATION_ROOT and SCRIPT_NAME for Nginx proxying ---
app.config['APPLICATION_ROOT'] = AUTH_SERVICE_SCRIPT_NAME

# app logger configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger(__name__)

#Admin password and user details for default admin creation
DEFAULT_ADMIN_USERNAME = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin_nacs')
DEFAULT_ADMIN_PASSWORD = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'nestadmin@1234')
DEFAULT_ADMIN_EMAIL = os.environ.get('DEFAULT_ADMIN_EMAIL', 'Nest.alpine.cultural.team@gmail.com')
DEFAULT_ADMIN_PHONE = os.environ.get('DEFAULT_ADMIN_PHONE', '9933735742')


@app.before_request
def set_script_name_from_proxy():
    if 'X-Forwarded-Prefix' in request.headers:
        request.environ['SCRIPT_NAME'] = request.headers['X-Forwarded-Prefix']
    elif AUTH_SERVICE_SCRIPT_NAME:
        request.environ['SCRIPT_NAME'] = AUTH_SERVICE_SCRIPT_NAME
    else:
        request.environ['SCRIPT_NAME'] = ''

# --- Email Sending Helper Function ---
def send_welcome_email(recipient_email, username, password):
    """
    Sends a welcome email to a new user with their username and password.
    WARNING: Sending passwords in plain text via email is generally INSECURE.
             Consider alternative methods like password reset links.
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        app_logger.error("Email sender credentials not configured. Cannot send welcome email.")
        return False

    subject = "Welcome to Nest Alpine Cultural Society!"
    body = f"""
Dear {username},

Welcome to Nest Alpine Cultural Society! We are thrilled to have you as a new member.

Here are your login credentials:
Username: {username}
Password: {password}

You can log in to your User Portal here: {USER_PORTAL_URL_AFTER_LOGIN}

We look forward to seeing you at our events and cultural gatherings!

Best regards,
The Nest Alpine Cultural Society Team
"""
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = recipient_email

    context = ssl.create_default_context()

    try:
        app_logger.info(f"Attempting to send welcome email to {recipient_email}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipient_email, msg.as_string())
        app_logger.info(f"Welcome email sent successfully to {recipient_email}.")
        return True
    except Exception as e:
        app_logger.error(f"Error sending welcome email to {recipient_email}: {e}")
        return False

# --- Routes for Frontend (Login/Registration Page) ---
@app.route('/')
def login_or_register_page():
    """Serves the login/registration page (index.html for Auth_Serv)."""
    target_portal = request.args.get('target')
    return render_template('index.html', target_portal=target_portal) 

@app.route('/login', methods=['GET'])
def login_page():
    """Serves the login page."""
    target_portal = request.args.get('target')
    return render_template('index.html', target_portal=target_portal) 

@app.route('/static/<path:filename>')
def serve_auth_static(filename):
    """Serves static files (CSS, JS) for the Auth_Serv's login/registration page."""
    return send_from_directory(app.static_folder, filename)

# --- Standard Login/Registration/Logout Routes ---

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
                redirect_url = ADMIN_PORTAL_URL_AFTER_LOGIN
            else:
                base_user_portal_url = USER_PORTAL_URL_AFTER_LOGIN.rstrip('/')
                redirect_url = f"{base_user_portal_url}/portal/{user['id']}"

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
    password = data.get('password') # The unhashed password, needed for email

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

        # Send Welcome Email
        send_email_success = send_welcome_email(email, username, password)
        if not send_email_success:
            app_logger.warning(f"Failed to send welcome email to {email} during registration.")

        base_user_portal_url = USER_PORTAL_URL_AFTER_LOGIN.rstrip('/')
        registration_redirect_url = f"{base_user_portal_url}/portal/{created_user['id']}"

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
    return jsonify({"message": "Logout successful", "redirect_url": url_for('login_or_register_page', _external=False)}), 200

@app.route('/hash_password', methods=['POST'])
def hash_password_endpoint():
    data = request.get_json()
    password = data.get('password')
    if not password:
        return jsonify({"error": "Password is required."}), 400
    hashed = hashpw(password.encode('utf-8'), gensalt())
    return jsonify({"hashed_password": hashed.decode('utf-8')}), 200

# --- Admin User Creation Logic ---
def provision_admin_user_on_startup(app_instance):
    """
    Attempts to create a default admin user in the DB API if one doesn't exist.
    This function includes retries for DB_API connectivity, as it's meant to run
    at service startup where DB_API might not be immediately available.
    """
    app_logger.info("Auth Service startup: Starting admin provisioning logic with retries.")
    
    admin_username = DEFAULT_ADMIN_USERNAME
    admin_password = DEFAULT_ADMIN_PASSWORD
    admin_email = DEFAULT_ADMIN_EMAIL
    admin_phone = DEFAULT_ADMIN_PHONE

    if not all([admin_username, admin_password, admin_email, admin_phone]):
        app_logger.error("Missing environment variables for DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, etc. Cannot provision default admin.")
        return

    max_retries = 15
    retry_delay_seconds = 5

    for attempt in range(max_retries):
        try:
            app_logger.info(f"Attempt {attempt + 1}/{max_retries}: Checking for admin user '{admin_username}' in DB API...")
            check_response = requests.get(f"{DB_API_URL}/users", params={'query': admin_username}, timeout=5)
            
            user_found_in_db = False
            if check_response.status_code == 200:
                user_data_response = check_response.json()
                if isinstance(user_data_response, list) and any(u.get('username') == admin_username for u in user_data_response):
                    user_found_in_db = True
                elif isinstance(user_data_response, dict) and user_data_response.get('username') == admin_username:
                    user_found_in_db = True
                else:
                    app_logger.debug(f"DB API returned data for query '{admin_username}' but no matching user found in content (status 200).")
            elif check_response.status_code == 404:
                app_logger.info(f"Default admin user '{admin_username}' not found (DB API returned 404). Proceeding to create.")
            else:
                app_logger.error(f"Failed to check for admin user existence (Status: {check_response.status_code}): {check_response.text}")
                raise requests.exceptions.RequestException(f"Failed initial check (status {check_response.status_code})")

            if user_found_in_db:
                app_logger.info(f"Default admin user '{admin_username}' already exists in DB API. Skipping creation.")
                return
            
            hashed_password = hashpw(admin_password.encode('utf-8'), gensalt()).decode('utf-8')
            admin_user_data = {
                "username": admin_username,
                "email": admin_email,
                "phone_number": admin_phone,
                "hashed_password": hashed_password,
                "role": "admin"
            }

            app_logger.info(f"Attempting to create default admin user '{admin_username}' in DB API.")
            create_response = requests.post(f"{DB_API_URL}/users", json=admin_user_data, timeout=5)
            create_response.raise_for_status()
            
            app_logger.info(f"Default admin user '{admin_username}' created successfully in DB API.")
            return
        
        except requests.exceptions.ConnectionError:
            app_logger.warning(f"Could not connect to DB API at '{DB_API_URL}' (attempt {attempt + 1}). Retrying in {retry_delay_seconds}s...")
        except requests.exceptions.Timeout:
            app_logger.warning(f"DB API connection timed out at '{DB_API_URL}' (attempt {attempt + 1}). Retrying in {retry_delay_seconds}s...")
        except requests.exceptions.RequestException as e:
            response_text = e.response.text if e.response else 'N/A'
            status_code = e.response.status_code if e.response is not None else 500
            app_logger.warning(f"Error during admin user creation (attempt {attempt + 1}): {e} (Status: {status_code}). Response: {response_text}. Retrying in {retry_delay_seconds}s...")
            if status_code == 409:
                app_logger.info(f"Admin creation failed due to conflict (user might have been created by another process or concurrent startup). Skipping further retries for creation.")
                return
        except Exception as e:
            app_logger.critical(f"An unexpected error occurred during default admin provisioning on startup (attempt {attempt + 1}): {e}", exc_info=True)
            
        if attempt < max_retries - 1:
            time.sleep(retry_delay_seconds)
        else:
            app_logger.critical(f"Max retries ({max_retries}) reached. Failed to provision default admin user '{admin_username}'. This service might not function correctly if admin is required.")


if __name__ == '__main__':
    provision_admin_user_on_startup(app)   
    app.run(host='0.0.0.0', port=5002, debug=True)