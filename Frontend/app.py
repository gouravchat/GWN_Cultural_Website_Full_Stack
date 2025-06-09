import os
from flask import Flask, render_template, jsonify, send_from_directory

app = Flask(__name__, template_folder='templates', static_folder='static')

# Get URLs from environment variables set in docker-compose.yml
# These are the URLs that the client's browser will use.
# They should point to the externally accessible URLs of your services (e.g., localhost:port on your host machine).
AUTH_SERVICE_LOGIN_URL_FOR_CLIENT = os.environ.get('AUTH_SERVICE_LOGIN_URL', 'http://localhost:5002/')
EVENT_SERVICE_URL_FOR_CLIENT = os.environ.get('EVENT_SERVICE_URL', 'http://localhost:5000')

@app.route('/')
def landing_page():
    """Serves the main landing page and injects configuration for client-side use."""
    print(f"Auth URL for client: {AUTH_SERVICE_LOGIN_URL_FOR_CLIENT}") # For debugging
    print(f"Event URL for client: {EVENT_SERVICE_URL_FOR_CLIENT}") # For debugging
    return render_template(
        'index.html',
        auth_service_login_url=AUTH_SERVICE_LOGIN_URL_FOR_CLIENT,
        event_service_url=EVENT_SERVICE_URL_FOR_CLIENT
    )

@app.route('/config')
def get_landing_page_config_for_client():
    """
    (Optional) Provides configuration to client-side JavaScript if it prefers to fetch it.
    The landing_page.html currently uses template injection.
    """
    return jsonify({
        "authServiceLoginUrl": AUTH_SERVICE_LOGIN_URL_FOR_CLIENT,
        "eventServiceUrl": EVENT_SERVICE_URL_FOR_CLIENT
    })

# Serve static files (CSS, JS specific to landing page, if any)
# Flask automatically serves from 'static_folder' if url_for('static', ...) is used in templates.
# This explicit route is generally not needed if Flask's default static handling is sufficient.
# However, if you directly link like <link rel="stylesheet" href="/static/style.css">,
# and your static files are indeed in a 'static' folder within Landing_Page_Service, this helps.
@app.route('/static/<path:filename>')
def serve_static_files(filename):
    # This will serve files from the 'static' folder located at the same level as this app.py
    # e.g., Landing_Page_Service/static/your_file.css
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    # Port 8080 is used inside the container (as specified in docker-compose.yml)
    # Debug should be False in a production environment.
    app.run(host='0.0.0.0', port=8080, debug=True)
