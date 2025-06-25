# Auth_Service/Dockerfile
# Using a Python base image with a recent version is always recommended.
# Flask 2.x requires Python 3.7+
FROM python:3.9-slim-buster 

WORKDIR /app

# Install system dependencies if needed (e.g., for netcat for wait-for-it.sh if you use it)
# RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install Flask, requests, bcrypt, Flask-Cors, and Gunicorn
RUN pip install --no-cache-dir -r requirements.txt gunicorn 

COPY . . 

# Copy your application code (app.py, templates, static)

# This is the new Docker ENTRYPOINT.
# It's a single shell command that first runs your Python provisioning logic
# and then starts Gunicorn.
ENTRYPOINT [ "/bin/bash", "-c", "\
    echo 'Auth Service Entrypoint: Running admin provisioning...' && \
    python -c 'from app import app, provision_admin_user_on_startup; \
               provision_admin_user_on_startup(app);' \
    && \
    echo 'Auth Service Entrypoint: Admin provisioning complete. Starting Gunicorn...' && \
    exec gunicorn -b 0.0.0.0:5002 app:app \
" ]