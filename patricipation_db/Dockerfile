# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir reduces the image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
# This should include the Python script (e.g., app_renamed.py)
COPY . .

# Make port 5005 available to the world outside this container
EXPOSE 5005

# Define environment variable for the port, which can be overwritten at runtime
ENV PORT 5005

# Run the app when the container launches. 
# IMPORTANT: Make sure your Python file is named 'app_renamed.py' or change the command below.
CMD ["python", "app.py"]
