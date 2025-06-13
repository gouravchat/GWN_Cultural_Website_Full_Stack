import os
from flask import Flask, render_template

# This is the main frontend service application for the ERS.
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

@app.route('/')
def index():
    """
    Serves the main landing page, which shows the event selection list
    by default.
    """
    return render_template('index.html')

@app.route('/register')
def register():
    """
    NEW: This route handles the redirection from the User Portal.
    It serves the exact same index.html page. The client-side JavaScript
    will detect the '/register' path and URL parameters to pre-fill the form
    for a specific user and event.
    """
    return render_template('index.html')

if __name__ == '__main__':
    # The ERS service runs on port 5006 by default.
    port = int(os.environ.get('PORT', 5006))
    app.run(host='0.0.0.0', port=port, debug=True)
