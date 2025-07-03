# src/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to prevent temporary files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Run Gunicorn, pointing to the correct WSGI application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "jaroslav_tech.wsgi:application"]