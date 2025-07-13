# Payment_Service/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask application
COPY . .

EXPOSE 5009  

# Command to run the application with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5009", "app:app"]