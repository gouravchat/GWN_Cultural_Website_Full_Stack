
# app-auth/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 5002 for the authentication service
EXPOSE 5002

CMD ["gunicorn", "--bind", "0.0.0.0:5002", "app:app"]