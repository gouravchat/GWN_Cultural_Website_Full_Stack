FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 5004 for the admin database service
EXPOSE 5004

CMD ["gunicorn", "--bind", "0.0.0.0:5004", "app:app"]