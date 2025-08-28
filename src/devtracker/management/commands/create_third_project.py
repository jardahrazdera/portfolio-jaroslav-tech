from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import random
from devtracker.models import Project, Task, TimeLog, Tag, Technology, ProjectStatus


class Command(BaseCommand):
    help = 'Creates DevTracker project for user_jarek'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='user_jarek')
            self.stdout.write(self.style.SUCCESS(f'Found user: {user.username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('User "user_jarek" not found! Please create this user first.'))
            return

        # Get existing tags and technologies
        tags = {
            'web-dev': Tag.objects.get(slug='web-dev'),
            'backend': Tag.objects.get(slug='backend'), 
            'devops': Tag.objects.get(slug='devops'),
            'database': Tag.objects.get(slug='database'),
        }
        
        technologies = {
            'Django': Technology.objects.get(name='Django'),
            'PostgreSQL': Technology.objects.get(name='PostgreSQL'),
            'Docker': Technology.objects.get(name='Docker'),
            'Redis': Technology.objects.get(name='Redis'),
            'REST API': Technology.objects.get(name='REST API'),
            'GitHub Actions': Technology.objects.get(name='GitHub Actions'),
            'Nginx': Technology.objects.get(name='Nginx'),
        }

        # PROJECT 3: DevTracker System (PUBLIC - ACTIVE)
        project3, created = Project.objects.get_or_create(
            slug='devtracker-system',
            defaults={
                'name': 'DevTracker - Project Management System',
                'description': """A comprehensive project management system built with Django as the final project 
                for Fullstack Developer Course. Currently 98% complete and production-ready, deployed to jaroslav.tech.
                
                Completed features:
                - 7 Django models with full relationships (Project, Task, TimeLog, Tag, Technology, ProjectStatus, TrackerSettings)
                - Complete CRUD operations for all entities
                - User authentication with reCAPTCHA protection
                - Admin-configurable settings (registration, approval, reCAPTCHA toggles)
                - Catppuccin theme with responsive design
                - 9 comprehensive tests with full workflow coverage
                - Docker containerization with PostgreSQL
                
                Still in development:
                - UI/UX improvements and theme switcher persistence
                - Project search functionality and image uploads
                - Email verification for registration
                - Performance optimizations and Redis caching
                
                This project demonstrates advanced Django development, database design, modern UI/UX, 
                and professional software engineering practices.""",
                'status': 'active',
                'start_date': date.today() - timedelta(days=14),
                'is_public': True,
                'github_url': 'https://github.com/jardahrazdera/portfolio-jaroslav-tech',
                'live_url': 'https://jaroslav.tech/tracker/',
                'owner': user
            }
        )
        
        if created:
            # Add tags and technologies
            project3.tags.add(tags['web-dev'], tags['backend'], tags['devops'])
            project3.technologies.add(
                technologies['Django'], technologies['PostgreSQL'], technologies['Docker'],
                technologies['Redis'], technologies['REST API'], technologies['GitHub Actions'],
                technologies['Nginx']
            )
            
            # Create tasks (mix of completed and pending from TODO.md)
            tasks_p3 = [
                # Completed tasks
                {'title': 'Create 7 Django models with relationships', 'is_completed': True, 'priority': 3},
                {'title': 'Implement user authentication system', 'is_completed': True, 'priority': 3},
                {'title': 'Build CRUD operations for all entities', 'is_completed': True, 'priority': 3},
                {'title': 'Integrate reCAPTCHA v3 protection', 'is_completed': True, 'priority': 2},
                {'title': 'Create TrackerSettings admin configuration', 'is_completed': True, 'priority': 2},
                {'title': 'Implement Catppuccin theme design', 'is_completed': True, 'priority': 2},
                {'title': 'Write comprehensive test suite', 'is_completed': True, 'priority': 3},
                {'title': 'Configure Docker containerization', 'is_completed': True, 'priority': 3},
                {'title': 'Deploy to production', 'is_completed': True, 'priority': 3},
                # Pending tasks from TODO.md
                {'title': 'Add project image/screenshot uploads', 'is_completed': False, 'priority': 2},
                {'title': 'Implement project search functionality', 'is_completed': False, 'priority': 2},
                {'title': 'Fix theme switcher localStorage persistence', 'is_completed': False, 'priority': 1},
                {'title': 'Add email verification for registration', 'is_completed': False, 'priority': 1},
                {'title': 'Configure Redis caching for performance', 'is_completed': False, 'priority': 1},
                {'title': 'Optimize mobile hamburger menu animation', 'is_completed': False, 'priority': 1},
            ]
            
            for task_data in tasks_p3:
                task = Task.objects.create(
                    project=project3,
                    title=task_data['title'],
                    description=f"Completed: {task_data['title']}",
                    is_completed=task_data['is_completed'],
                    priority=task_data['priority']
                )
                # Only set completion date for completed tasks
                if task_data['is_completed']:
                    days_before_completion = random.randint(1, 12)
                    task.completed_at = timezone.now() - timedelta(days=days_before_completion)
                    task.save()
            
            # Create time logs (spread across 2 weeks of development)
            for _ in range(20):
                days_ago = random.randint(1, 14)  # Throughout project duration
                TimeLog.objects.create(
                    project=project3,
                    date=date.today() - timedelta(days=days_ago),
                    hours=round(random.uniform(3.0, 6.5), 1),
                    description=random.choice([
                        'Django models and relationships implementation',
                        'User authentication and registration system',
                        'reCAPTCHA v3 integration and testing',
                        'TrackerSettings admin configuration',
                        'Catppuccin theme CSS implementation',
                        'Test suite development and debugging',
                        'Docker configuration and deployment',
                        'UI/UX improvements and responsive design',
                        'Production deployment and troubleshooting',
                        'Code review and documentation',
                        'Bug fixes and optimization',
                        'Feature planning and TODO organization'
                    ])
                )
            
            # Create status updates
            ProjectStatus.objects.create(
                project=project3,
                status='Course Project Started',
                date=project3.start_date,
                note='DevTracker development began as final project for Fullstack Developer Course.'
            )
            ProjectStatus.objects.create(
                project=project3,
                status='Core Features Implemented',
                date=project3.start_date + timedelta(days=7),
                note='All 7 models, authentication, CRUD operations, and admin interface completed.'
            )
            ProjectStatus.objects.create(
                project=project3,
                status='Production Deployed - 98% Complete',
                date=project3.start_date + timedelta(days=12),
                note='Successfully deployed to jaroslav.tech with reCAPTCHA protection and comprehensive testing. Still working on UI improvements and additional features.'
            )
            
            self.stdout.write(self.style.SUCCESS(f'✓ Created project: {project3.name}'))
        else:
            self.stdout.write(self.style.WARNING('DevTracker system project already exists'))

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Third Project Created ==='))
        self.stdout.write(f'Project: {project3.name}')
        self.stdout.write(f'Status: {project3.get_status_display()}')
        self.stdout.write(f'Tasks: {project3.tasks.filter(is_completed=True).count()}/{project3.tasks.count()} completed')
        self.stdout.write(f'Time Logged: {project3.get_total_hours()}h across {project3.time_logs.count()} entries')
        self.stdout.write(f'Started: {project3.start_date} (Active development)')