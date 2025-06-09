# app-admin/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 5003 for the admin service
EXPOSE 5003

CMD ["gunicorn", "--bind", "0.0.0.0:5003", "app:app"]