import pytest
from django.contrib.auth.models import User
from faker import Faker
from projects.models import Project, Technology, WorkSession, UserProfile
from tasks.models import Task

fake = Faker()


@pytest.fixture
def db_access(db):
    """Fixture to ensure database access for tests."""
    pass


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(
        username=fake.user_name(),
        email=fake.email(),
        password="testpass123",
        first_name=fake.first_name(),
        last_name=fake.last_name(),
    )
    return user


@pytest.fixture
def authenticated_user(test_user):
    """Return an authenticated test user."""
    test_user.is_authenticated = True
    return test_user


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    admin = User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="adminpass123"
    )
    return admin


@pytest.fixture
def user_profile(test_user):
    """Create a user profile for the test user."""
    profile, created = UserProfile.objects.get_or_create(
        user=test_user,
        defaults={
            'bio': fake.text(max_nb_chars=200),
            'github_url': f'https://github.com/{fake.user_name()}',
            'linkedin_url': f'https://linkedin.com/in/{fake.user_name()}',
            'twitter_url': f'https://twitter.com/{fake.user_name()}',
            'website_url': fake.url(),
            'location': fake.city(),
            'timezone': 'UTC',
            'preferred_language': 'en',
        }
    )
    return profile


@pytest.fixture
def technologies(db):
    """Create sample technologies."""
    tech_names = ['Python', 'Django', 'JavaScript', 'React', 'PostgreSQL', 'Docker', 'AWS']
    technologies = []
    for name in tech_names:
        tech, created = Technology.objects.get_or_create(
            name=name,
            defaults={
                'slug': name.lower(),
                'description': f'{name} technology description',
                'icon_class': f'devicon-{name.lower()}-plain',
            }
        )
        technologies.append(tech)
    return technologies


@pytest.fixture
def sample_project(test_user, technologies):
    """Create a sample project."""
    project = Project.objects.create(
        owner=test_user,
        title=fake.catch_phrase(),
        slug=fake.slug(),
        short_description=fake.text(max_nb_chars=100),
        full_description=fake.text(max_nb_chars=500),
        status='development',
        priority='high',
        start_date=fake.date_this_year(),
        github_url=fake.url(),
        live_url=fake.url(),
        estimated_hours=fake.random_int(min=10, max=200),
        actual_hours=fake.random_int(min=5, max=150),
        completion_percentage=fake.random_int(min=0, max=100),
        visibility='public',
    )
    project.technologies.set(technologies[:3])
    return project


@pytest.fixture
def multiple_projects(test_user, technologies):
    """Create multiple projects for testing."""
    projects = []
    statuses = ['planning', 'development', 'testing', 'completed', 'on_hold']
    priorities = ['low', 'medium', 'high', 'critical']
    
    for i in range(10):
        project = Project.objects.create(
            owner=test_user,
            title=f"{fake.catch_phrase()} {i}",
            slug=f"{fake.slug()}-{i}",
            short_description=fake.text(max_nb_chars=100),
            full_description=fake.text(max_nb_chars=500),
            status=statuses[i % len(statuses)],
            priority=priorities[i % len(priorities)],
            start_date=fake.date_this_year(),
            estimated_hours=fake.random_int(min=10, max=200),
            actual_hours=fake.random_int(min=5, max=150),
            completion_percentage=fake.random_int(min=0, max=100),
            visibility='public' if i % 2 == 0 else 'private',
        )
        # Add random technologies
        tech_count = fake.random_int(min=1, max=len(technologies))
        project.technologies.set(fake.random_choices(technologies, length=tech_count))
        projects.append(project)
    
    return projects


@pytest.fixture
def work_session(sample_project):
    """Create a work session for the sample project."""
    session = WorkSession.objects.create(
        project=sample_project,
        title=fake.sentence(nb_words=4),
        description=fake.text(max_nb_chars=200),
        start_time=fake.date_time_this_month(),
        productivity_rating=fake.random_int(min=1, max=5),
    )
    # Set end time to make it a completed session
    import datetime
    session.end_time = session.start_time + datetime.timedelta(hours=fake.random_int(min=1, max=8))
    session.save()
    return session


@pytest.fixture
def active_session(sample_project):
    """Create an active (ongoing) work session."""
    session = WorkSession.objects.create(
        project=sample_project,
        title=fake.sentence(nb_words=4),
        description=fake.text(max_nb_chars=200),
        start_time=fake.date_time_this_month(),
    )
    return session


@pytest.fixture
def sample_task(sample_project, test_user):
    """Create a sample task."""
    task = Task.objects.create(
        title=fake.sentence(nb_words=6),
        description=fake.text(max_nb_chars=300),
        project=sample_project,
        assignee=test_user,
        status='todo',
        priority='medium',
        task_type='feature',
        estimated_hours=fake.random_int(min=1, max=20),
        progress=fake.random_int(min=0, max=100),
        due_date=fake.date_this_month(),
    )
    task.tags = fake.words(nb=3)
    task.save()
    return task


@pytest.fixture
def client(db):
    """Override the default Django test client."""
    from django.test import Client
    return Client()


@pytest.fixture
def authenticated_client(client, test_user):
    """Return a client with an authenticated user."""
    client.force_login(test_user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Return a client with an authenticated admin user."""
    client.force_login(admin_user)
    return client