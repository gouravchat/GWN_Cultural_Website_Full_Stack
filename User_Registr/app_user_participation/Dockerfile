# app-participation/Dockerfile
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 5006 for the participation service
EXPOSE 5006

CMD ["gunicorn", "--bind", "0.0.0.0:5006", "app:app"]