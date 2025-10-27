# src/Dockerfile

# --- Stage 1: Frontend Builder ---
FROM node:20-slim AS frontend-builder

# Set a build directory
WORKDIR /build

# Copy frontend and src folders to maintain directory structure
COPY frontend ./frontend
COPY src ./src

# Install dependencies and run the build script
# This creates the dist folder inside /build/src/static/
RUN cd frontend && npm ci && npm run build


# --- Stage 2: Final Python Application ---
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory for the final app
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gettext && apt-get clean

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy Python requirements and install them
COPY --from=frontend-builder /build/src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire built 'src' directory from the builder stage
COPY --from=frontend-builder /build/src .

# Copy node_modules so collectstatic can find Alpine.js
# The final path will be /frontend/node_modules, to match STATICFILES_DIRS
RUN mkdir /frontend
COPY --from=frontend-builder /build/frontend/node_modules /frontend/node_modules

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Change ownership to app user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Compile translation messages
RUN python manage.py compilemessages

# Collect static files (will now include the built assets from dist/)
ARG CACHEBUST=1
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=$GIT_COMMIT
RUN python manage.py collectstatic --no-input --clear --verbosity=2

# Run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "jaroslav_tech.wsgi:application"]
