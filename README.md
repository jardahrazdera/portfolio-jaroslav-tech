# Portfolio - jaroslav.tech

**Live Project:** [**https://jaroslav.tech**](https://jaroslav.tech)

This repository contains the source code for my personal portfolio website. The project is a demonstration of modern web development practices, including a containerized Django application, a robust CI/CD pipeline, and a clean, scalable project structure.

## Project Overview

The goal of this project is to serve as a professional portfolio and a showcase of my technical skills. It follows a **monolithic architecture**, where a single Django application is responsible for both backend logic and serving server-rendered frontend templates. This approach is chosen for its simplicity and rapid development capabilities.

The project is built with a focus on best practices in security, deployment, and code organization.

### Key Features

*   **Containerized Environment:** The entire application stack (web app and database) is managed with Docker and Docker Compose, ensuring consistency across development and production environments.
*   **Automated Deployments:** A CI/CD pipeline using GitHub Actions automatically builds the Docker image, pushes it to a container registry, and deploys the new version to the production server on every push to the `main` branch.
*   **Secure by Design:** The application is configured to use environment variables for all sensitive data, following the principles of a twelve-factor app. It also includes a production-ready setup with Gunicorn, Whitenoise for static file serving, and Traefik as a reverse proxy with automated SSL certificate generation from Let's Encrypt.
*   **Scalable Architecture:** The project follows a standard `src` layout for clean separation of code and includes a dedicated Django app (`core`) for the main portfolio functionality.

## Tech Stack

*   **Backend:** Django
*   **Database:** PostgreSQL
*   **Web Server:** Gunicorn
*   **Static Files:** Whitenoise
*   **Containerization:** Docker, Docker Compose
*   **Reverse Proxy:** Traefik
*   **CI/CD:** GitHub Actions

## Project Structure

Below is a simplified tree representing the high-level architecture of the project. It highlights the key files and directories that define the structure.

```
.
├── .github/              # CI/CD workflows (GitHub Actions)
├── .gitignore            # Files and directories ignored by Git
├── docker-compose.yml    # Docker configuration for services
├── LICENSE               # MIT License
├── README.md             # You are here!
└── src/                  # Main source code directory
    ├── core/             # The primary Django application
    │   ├── models.py     # Database models
    │   ├── views.py      # View logic
    │   ├── urls.py       # App-specific URL routing
    │   └── templates/    # HTML templates
    ├── jaroslav_tech/    # Django project-level configuration
    │   ├── settings.py   # Project settings
    │   └── urls.py       # Root URL configuration
    ├── manage.py         # Django's command-line utility
    └── requirements.txt  # Python dependencies
```

## Local Development

To run this project locally, follow these steps:

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/jardahrazdera/portfolio-jaroslav-tech.git
    cd portfolio-jaroslav-tech
    ```

2.  **Set up the environment:**

    *   Create a virtual environment:

        ```bash
        python -m venv .venv
        source .venv/bin/activate
        ```

    *   Install the dependencies:

        ```bash
        pip install -r src/requirements.txt
        ```

3.  **Configure the environment variables:**

    *   Copy the example environment file:

        ```bash
        cp .env.example .env
        ```

    *   Open the `.env` file and fill in the required values for your local database and a new Django secret key.

4.  **Run the database migrations:**

    ```bash
    python src/manage.py migrate
    ```

5.  **Start the development server:**

    ```bash
    python src/manage.py runserver
    ```

The application will be available at `http://127.0.0.1:8000`.

## Docker Deployment

This project is configured for Docker deployment. To build and run the Docker containers, use the following commands:

```bash
docker-compose build
docker-compose up
```
