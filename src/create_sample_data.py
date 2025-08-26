#!/usr/bin/env python
import os
import sys
import django
from datetime import date, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jaroslav_tech.settings')
django.setup()

from devtracker.models import Project, Task, TimeLog, Tag, Technology, ProjectStatus

def create_sample_data():
    """Create sample data for DevTracker."""
    
    # Create Tags
    tags_data = [
        ('Web Development', '#89B4FA'),  # Blue
        ('Mobile App', '#A6E3A1'),      # Green  
        ('Open Source', '#F9E2AF'),     # Yellow
        ('Personal', '#CBA6F7'),        # Mauve
        ('Learning', '#FAB387'),        # Peach
    ]
    
    tags = []
    for name, color in tags_data:
        tag, created = Tag.objects.get_or_create(name=name, defaults={'color': color})
        tags.append(tag)
        if created:
            print(f"Created tag: {name}")

    # Create Technologies  
    tech_data = ['Django', 'Python', 'JavaScript', 'React', 'PostgreSQL', 'Docker', 'HTML/CSS', 'Git']
    
    technologies = []
    for name in tech_data:
        tech, created = Technology.objects.get_or_create(name=name)
        technologies.append(tech)
        if created:
            print(f"Created technology: {name}")

    # Create Projects
    projects_data = [
        {
            'name': 'DevTracker - Project Management System',
            'description': 'A Django-based project management system for tracking development projects, tasks, and time logs. Features include project organization, task management, time tracking, and progress visualization.',
            'status': 'active',
            'start_date': date.today() - timedelta(days=7),
            'is_public': True,
            'github_url': 'https://github.com/username/devtracker',
            'tags': [tags[0], tags[2], tags[3]],  # Web Development, Open Source, Personal
            'technologies': [technologies[0], technologies[1], technologies[4], technologies[5]],  # Django, Python, PostgreSQL, Docker
        },
        {
            'name': 'Portfolio Website Redesign',
            'description': 'Complete redesign of personal portfolio website with modern UI/UX, responsive design, and improved performance. Includes project showcase, blog functionality, and contact forms.',
            'status': 'completed',
            'start_date': date.today() - timedelta(days=30),
            'end_date': date.today() - timedelta(days=3),
            'is_public': True,
            'live_url': 'https://jaroslav.tech',
            'tags': [tags[0], tags[3]],  # Web Development, Personal
            'technologies': [technologies[0], technologies[1], technologies[6]],  # Django, Python, HTML/CSS
        },
        {
            'name': 'E-Commerce Mobile App',
            'description': 'React Native mobile application for online shopping with features like product browsing, cart management, user authentication, and payment integration.',
            'status': 'planning', 
            'is_public': False,
            'tags': [tags[1], tags[4]],  # Mobile App, Learning
            'technologies': [technologies[2], technologies[3]],  # JavaScript, React
        },
    ]

    projects = []
    for proj_data in projects_data:
        # Extract relationships
        tags_for_project = proj_data.pop('tags')
        techs_for_project = proj_data.pop('technologies')
        
        project, created = Project.objects.get_or_create(
            name=proj_data['name'],
            defaults=proj_data
        )
        
        if created:
            print(f"Created project: {project.name}")
            # Add many-to-many relationships
            project.tags.set(tags_for_project)
            project.technologies.set(techs_for_project)
            projects.append(project)

    # Create Tasks
    if projects:
        devtracker_project = projects[0]  # DevTracker project
        
        tasks_data = [
            {'title': 'Set up Django project structure', 'description': 'Initialize Django project with apps and basic configuration', 'is_completed': True, 'priority': 2},
            {'title': 'Design database models', 'description': 'Create models for Project, Task, TimeLog, Tag, Technology, and ProjectStatus', 'is_completed': True, 'priority': 3},
            {'title': 'Implement admin interface', 'description': 'Configure Django admin with inline editing and proper field organization', 'is_completed': True, 'priority': 2},
            {'title': 'Create project views and templates', 'description': 'Build list, detail, and form views with responsive templates', 'is_completed': True, 'priority': 3},
            {'title': 'Add authentication and permissions', 'description': 'Implement login/logout and protect authenticated views', 'is_completed': False, 'priority': 2},
            {'title': 'Write comprehensive tests', 'description': 'Create pytest tests for all views and models', 'is_completed': False, 'priority': 2},
            {'title': 'Deploy to production', 'description': 'Set up production environment with Docker and CI/CD', 'is_completed': False, 'priority': 1},
        ]
        
        for task_data in tasks_data:
            task, created = Task.objects.get_or_create(
                project=devtracker_project,
                title=task_data['title'],
                defaults=task_data
            )
            if created:
                print(f"Created task: {task.title}")

        # Create Time Logs
        time_logs_data = [
            {'date': date.today() - timedelta(days=6), 'hours': 4.5, 'description': 'Initial project setup and model design'},
            {'date': date.today() - timedelta(days=5), 'hours': 6.0, 'description': 'Implemented all database models and admin interface'},
            {'date': date.today() - timedelta(days=4), 'hours': 3.5, 'description': 'Created base templates and navigation structure'},
            {'date': date.today() - timedelta(days=3), 'hours': 5.5, 'description': 'Built project views and templates'},
            {'date': date.today() - timedelta(days=2), 'hours': 2.0, 'description': 'Added CSS styling and responsive design'},
            {'date': date.today() - timedelta(days=1), 'hours': 1.5, 'description': 'Bug fixes and template improvements'},
            {'date': date.today(), 'hours': 3.0, 'description': 'Sample data creation and testing'},
        ]
        
        for log_data in time_logs_data:
            time_log, created = TimeLog.objects.get_or_create(
                project=devtracker_project,
                date=log_data['date'],
                defaults=log_data
            )
            if created:
                print(f"Created time log: {log_data['description'][:30]}...")

        # Create Project Status Updates
        status_updates_data = [
            {'status': 'Project kickoff - initial planning complete', 'date': date.today() - timedelta(days=7), 'note': 'Defined requirements and technical approach'},
            {'status': 'Database design completed', 'date': date.today() - timedelta(days=5), 'note': 'All models implemented with proper relationships'},
            {'status': 'Basic functionality working', 'date': date.today() - timedelta(days=3), 'note': 'CRUD operations for projects and time logging functional'},
            {'status': 'UI/UX improvements added', 'date': date.today() - timedelta(days=1), 'note': 'Responsive design and Catppuccin theme integration'},
        ]
        
        for update_data in status_updates_data:
            status, created = ProjectStatus.objects.get_or_create(
                project=devtracker_project,
                status=update_data['status'],
                defaults=update_data
            )
            if created:
                print(f"Created status update: {status.status[:30]}...")

    print("\nSample data creation completed!")
    print(f"Created {Project.objects.count()} projects")
    print(f"Created {Task.objects.count()} tasks")
    print(f"Created {TimeLog.objects.count()} time logs")
    print(f"Created {Tag.objects.count()} tags")
    print(f"Created {Technology.objects.count()} technologies")
    print(f"Created {ProjectStatus.objects.count()} status updates")

if __name__ == '__main__':
    create_sample_data()