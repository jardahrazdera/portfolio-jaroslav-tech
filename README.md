# Portfolio Jaroslav Tech

[![Portfolio CI/CD](https://github.com/jardahrazdera/portfolio-jaroslav-tech/actions/workflows/deploy.yml/badge.svg)](https://github.com/jardahrazdera/portfolio-jaroslav-tech/actions/workflows/deploy.yml)
[![Django CI](https://github.com/jardahrazdera/portfolio-jaroslav-tech/actions/workflows/django-ci.yml/badge.svg)](https://github.com/jardahrazdera/portfolio-jaroslav-tech/actions/workflows/django-ci.yml)

Professional portfolio demonstrating Infrastructure & DevOps engineering expertise combined with full-stack development skills. Built with Django, containerized with Docker, and self-hosted on Proxmox with fully automated CI/CD deployment.

**Live at:** **[https://jaroslav.tech](https://jaroslav.tech)**

---

## 🎯 DevTracker - Project Management System

Portfolio includes **DevTracker**, a comprehensive project management system demonstrating advanced Django development:

- **Complex Data Models** with relationships for projects, tasks, time tracking, and categorization
- **Authentication & Authorization** with separate user and admin interfaces
- **Time Tracking System** with full CRUD operations
- **Project Organization** with public/private visibility controls
- **Progress Tracking** with visual metrics and completion indicators
- **Responsive Design** using Catppuccin theme with light/dark mode

**Access DevTracker:** Available at `/tracker/` with demo projects.

[![DevTracker Demo](https://img.shields.io/badge/Demo-DevTracker-blue?style=for-the-badge)](https://jaroslav.tech/tracker/)

---

## ✨ Key Features

**Infrastructure & DevOps**
* Fully automated CI/CD pipeline with GitHub Actions
* Docker containerization with PostgreSQL and Redis
* Zero-downtime deployments to production server
* Self-hosted on Proxmox infrastructure
* Redis caching for performance optimization
* Real-time server metrics monitoring (CPU, RAM, disk, uptime)

**Full-Stack Development**
* Django backend with PostgreSQL database
* Responsive frontend with mobile-first approach
* Internationalization (i18n) supporting Czech and English
* Dynamic content management through Django admin
* Blog system with CKEditor rich text editor
* Live GitHub API integration for repository stats

**SEO & Performance**
* Comprehensive SEO optimization (meta tags, Open Graph, structured data)
* XML sitemap with multilingual support (hreflang)
* Schema.org markup for rich search results
* Redis caching with user-specific keys
* Optimized database queries

---

## 🛠️ Tech Stack

<p align="left">
  <a href="https://www.python.org" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" alt="python" width="40" height="40"/></a>
  <a href="https://www.djangoproject.com/" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/django/django-plain.svg" alt="django" width="40" height="40"/></a>
  <a href="https://www.postgresql.org" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/postgresql/postgresql-original-wordmark.svg" alt="postgresql" width="40" height="40"/></a>
  <a href="https://redis.io" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/redis/redis-original-wordmark.svg" alt="redis" width="40" height="40"/></a>
  <a href="https://www.docker.com/" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/docker/docker-original-wordmark.svg" alt="docker" width="40" height="40"/></a>
  <a href="https://docs.github.com/en/actions" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/github/github-original-wordmark.svg" alt="githubactions" width="40" height="40"/></a>
  <a href="https://developer.mozilla.org/en-US/docs/Web/HTML" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/html5/html5-original-wordmark.svg" alt="html5" width="40" height="40"/></a>
  <a href="https://developer.mozilla.org/en-US/docs/Web/CSS" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/css3/css3-original-wordmark.svg" alt="css3" width="40" height="40"/></a>
  <a href="https://developer.mozilla.org/en-US/docs/Web/JavaScript" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/javascript/javascript-original.svg" alt="javascript" width="40" height="40"/></a>
</p>

---

## 📂 Project Structure

```
.
├── .github/              # CI/CD workflows (GitHub Actions)
├── docker-compose.yml    # Multi-service orchestration
└── src/
    ├── core/             # Portfolio app with SEO, i18n, server metrics
    ├── devtracker/       # Project management system
    ├── blog/             # Blog with CKEditor integration
    └── jaroslav_tech/    # Django project configuration
```

---

## ⚙️ Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/jardahrazdera/portfolio-jaroslav-tech.git
   cd portfolio-jaroslav-tech
   cp .env.example .env
   ```

2. **Run with Docker Compose:**
   ```bash
   docker compose up --build
   ```

3. **Access:**
   - Portfolio: `http://localhost:8000`
   - DevTracker: `http://localhost:8000/tracker/`
   - Admin Panel: `http://localhost:8000/admin`

---

## 🔄 CI/CD Deployment

Automated deployment pipeline on every push to `main`:

1. Build Docker image with application code and dependencies
2. Push to GitHub Container Registry (GHCR)
3. SSH to production server
4. Pull latest image and gracefully restart services
5. Run database migrations, collect static files, compile translations

Zero-downtime deployment ensures continuous availability.

---

## 🧪 Testing & Quality

Comprehensive test suite using Django's TestCase framework:
* View and template integrity tests
* Context data validation
* Business logic verification (Singleton pattern for settings)
* Redis caching functionality tests

Automated CI runs on every push, pull request, and nightly schedule via GitHub Actions.

---

## 📫 Contact

* **GitHub:** [jardahrazdera](https://github.com/jardahrazdera)
* **LinkedIn:** [jaroslav-hrazdera](https://www.linkedin.com/in/jaroslav-hrazdera-326295382/)
* **Email:** [jarek@jaroslav.tech](mailto:jarek@jaroslav.tech)
