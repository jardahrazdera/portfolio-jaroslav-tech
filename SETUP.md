# Development Environment Setup

## Overview

This is a Django-based portfolio and blog application with DevTracker project management system. The project uses Docker for containerization and mise for Python version management.

## Prerequisites

- Docker & Docker Compose
- mise (for Python version management)
- Node.js & npm (for frontend dependencies)
- Git

## Project Structure

```
portfolio-jaroslav-tech/
├── src/                    # Main Django application
│   ├── core/              # Portfolio app
│   ├── blog/              # Blog application
│   ├── devtracker/        # Project management system
│   ├── jaroslav_tech/     # Django project settings
│   ├── manage.py          # Django management script
│   └── requirements.txt   # Python dependencies
├── frontend/              # Frontend dependencies (npm)
├── .venv/                 # Python virtual environment
├── .env                   # Environment variables
├── docker-compose.yml     # Docker services configuration
└── mise.toml             # Python version specification (3.11)
```

## Environment Setup

### 1. Python Environment with mise

The project requires Python 3.11, managed by mise:

```bash
# Navigate to project directory
cd /home/jarek/Documents/Projects/portfolio-jaroslav-tech

# mise automatically detects the Python version from mise.toml
# Verify Python version
mise exec -- python --version  # Should show Python 3.11.13
```

### 2. Virtual Environment

Python virtual environment is located in `.venv/`:

```bash
# Activate virtual environment
source .venv/bin/activate

# Or use mise to run commands
mise exec -- .venv/bin/python src/manage.py [command]
```

### 3. Environment Variables

Configuration is stored in `.env` file. Key variables:
- Database credentials (PostgreSQL)
- Redis configuration
- Django secret key
- Debug settings

## Running the Application

### Option 1: Docker Compose (Recommended)

Runs the full stack (web app, PostgreSQL, Redis):

```bash
docker compose up --build
```

Access points:
- Portfolio: http://localhost:8000
- Blog: http://localhost:8000/blog/
- DevTracker: http://localhost:8000/tracker/
- Admin Panel: http://localhost:8000/admin

### Option 2: Local Development

For development without Docker:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run migrations
python src/manage.py migrate

# Collect static files
python src/manage.py collectstatic --noinput

# Run development server
python src/manage.py runserver
```

**Note:** Local development requires PostgreSQL and Redis running separately.

## Common Tasks

### Database Migrations

```bash
# Create migrations
mise exec -- .venv/bin/python src/manage.py makemigrations

# Apply migrations
mise exec -- .venv/bin/python src/manage.py migrate
```

### Create Superuser

```bash
mise exec -- .venv/bin/python src/manage.py createsuperuser
```

### Update Dependencies

```bash
# Python dependencies
source .venv/bin/activate
pip install -r src/requirements.txt

# Frontend dependencies
cd frontend
npm install
```

### Run Tests

```bash
mise exec -- .venv/bin/python src/manage.py test
```

### Clear Cache

```bash
# Clear blog cache
mise exec -- .venv/bin/python src/manage.py clear_blog_cache

# Warm cache
mise exec -- .venv/bin/python src/manage.py warm_cache
```

## Git Workflow

Currently on `feature_blog` branch:

```bash
# Check status
git status

# Switch branches
git checkout main
git checkout feature_blog

# Push changes
git add .
git commit -m "Your message"
git push origin feature_blog
```

## Useful Django Management Commands

```bash
# Shell with Django context
python src/manage.py shell

# Create demo data for DevTracker
python src/manage.py create_demo_data

# Cache statistics
python src/manage.py cache_stats

# Optimize images
python src/manage.py optimize_images
```

## Technology Stack

- **Backend:** Django 5.2.4, Python 3.11
- **Database:** PostgreSQL
- **Cache:** Redis
- **Frontend:** HTML, CSS (Catppuccin theme), JavaScript (Alpine.js)
- **Fonts:** JetBrains Mono
- **Deployment:** Docker, Docker Compose, GitHub Actions
- **Web Server:** Gunicorn (production)

## Notes

- The project uses Catppuccin color scheme with light/dark mode support
- Internationalization: Czech and English (i18n with gettext)
- Static files managed by WhiteNoise
- Rich text editing with CKEditor 5
- SEO optimized with sitemaps and meta tags
- CI/CD via GitHub Actions

## Troubleshooting

### Python version issues
```bash
# Verify mise is using correct Python
mise which python
mise exec -- python --version
```

### Database connection errors
Check `.env` file for correct PostgreSQL credentials

### Port already in use
```bash
# Check what's using port 8000
sudo lsof -i :8000

# Or use different port
python src/manage.py runserver 8001
```

### Docker issues
```bash
# Clean Docker setup
docker compose down
docker compose up --build

# Remove volumes (WARNING: deletes database)
docker compose down -v
```

## Further Information

See `README.md` for comprehensive project documentation and feature descriptions.