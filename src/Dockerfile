# src/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to prevent temporary files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies, including gettext for translations
RUN apt-get update && apt-get install -y gettext && apt-get clean

# Create a non-root user for running the app
RUN useradd --create-home --shell /bin/bash app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Change ownership to app user before compiling messages
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Compile translation messages with correct permissions
RUN python manage.py compilemessages

# Run Gunicorn as non-root user, pointing to the correct WSGI application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "jaroslav_tech.wsgi:application"]
