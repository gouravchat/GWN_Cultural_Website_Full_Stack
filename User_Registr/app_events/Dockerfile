# app-events/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 5004 for the events service
EXPOSE 5004

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5005", "app:app"]
