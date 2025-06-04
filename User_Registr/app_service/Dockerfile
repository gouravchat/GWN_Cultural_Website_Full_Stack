# app-service/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and the static HTML files
COPY . .

# Expose port 5000 for the frontend service
EXPOSE 5000

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]