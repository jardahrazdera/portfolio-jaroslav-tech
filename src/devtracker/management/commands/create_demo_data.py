from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import random
from devtracker.models import Project, Task, TimeLog, Tag, Technology, ProjectStatus


class Command(BaseCommand):
    help = 'Creates rich demo data for demo user'

    def handle(self, *args, **options):
        # Create or get demo user
        user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@jaroslav.tech',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_active': False,
            }
        )
        if created:
            user.set_password('demo123')  # Simple password for demo
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created demo user: {user.username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Found demo user: {user.username}'))

        # Create Tags
        tags_data = [
            {'name': 'Web Development', 'slug': 'web-dev', 'color': '#F5C2E7'},  # Pink
            {'name': 'AI/ML', 'slug': 'ai-ml', 'color': '#CBA6F7'},  # Mauve
            {'name': 'Open Source', 'slug': 'open-source', 'color': '#94E2D5'},  # Teal
            {'name': 'Backend', 'slug': 'backend', 'color': '#FAB387'},  # Peach
            {'name': 'DevOps', 'slug': 'devops', 'color': '#F38BA8'},  # Red
            {'name': 'Database', 'slug': 'database', 'color': '#A6E3A1'},  # Green
        ]
        
        tags = {}
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(
                slug=tag_data['slug'],
                defaults={'name': tag_data['name'], 'color': tag_data['color']}
            )
            tags[tag_data['slug']] = tag
            if created:
                self.stdout.write(f'Created tag: {tag.name}')

        # Create Technologies
        tech_data = [
            'Python', 'Django', 'PostgreSQL', 'Docker', 'Redis', 'Celery',
            'JavaScript', 'React', 'TypeScript', 'FastAPI', 'GraphQL',
            'AWS', 'GitHub Actions', 'Nginx', 'Git', 'REST API', 'WebSockets'
        ]
        
        technologies = {}
        for tech_name in tech_data:
            tech, created = Technology.objects.get_or_create(name=tech_name)
            technologies[tech_name] = tech
            if created:
                self.stdout.write(f'Created technology: {tech.name}')

        # PROJECT 1: E-Commerce Platform (PUBLIC)
        project1, created = Project.objects.get_or_create(
            slug='quantum-commerce',
            defaults={
                'name': 'Quantum Commerce Platform',
                'description': """A modern, scalable e-commerce platform built with Django and React. This project showcases 
                full-stack development skills with features including real-time inventory management, payment processing, 
                multi-vendor support, and advanced analytics dashboard. 
                
                Key achievements:
                - Handled 10,000+ concurrent users during Black Friday sale
                - Integrated with Stripe, PayPal, and cryptocurrency payments
                - Implemented ML-based recommendation engine
                - 99.9% uptime over 6 months
                
                The platform uses microservices architecture with Docker orchestration, Redis caching, 
                and Celery for async task processing. Frontend built with React + TypeScript.""",
                'status': 'active',
                'start_date': date.today() - timedelta(days=120),
                'is_public': True,
                'github_url': 'https://github.com/jarek/quantum-commerce',
                'live_url': 'https://quantum-commerce-demo.herokuapp.com',
                'owner': user
            }
        )
        
        if created:
            # Add tags and technologies
            project1.tags.add(tags['web-dev'], tags['backend'], tags['open-source'])
            project1.technologies.add(
                technologies['Django'], technologies['React'], technologies['PostgreSQL'],
                technologies['Docker'], technologies['Redis'], technologies['Celery'],
                technologies['TypeScript'], technologies['REST API'],
                technologies['AWS']
            )
            
            # Create tasks
            tasks_p1 = [
                {'title': 'Set up Django project structure', 'is_completed': True, 'priority': 3},
                {'title': 'Design database schema', 'is_completed': True, 'priority': 3},
                {'title': 'Implement user authentication', 'is_completed': True, 'priority': 3},
                {'title': 'Create product catalog system', 'is_completed': True, 'priority': 2},
                {'title': 'Build shopping cart functionality', 'is_completed': True, 'priority': 2},
                {'title': 'Integrate Stripe payments', 'is_completed': True, 'priority': 3},
                {'title': 'Develop admin dashboard', 'is_completed': True, 'priority': 2},
                {'title': 'Implement search with ElasticSearch', 'is_completed': False, 'priority': 2},
                {'title': 'Add recommendation engine', 'is_completed': False, 'priority': 1},
                {'title': 'Performance optimization', 'is_completed': False, 'priority': 3},
                {'title': 'Write comprehensive tests', 'is_completed': True, 'priority': 3},
                {'title': 'Deploy to production', 'is_completed': True, 'priority': 3},
            ]
            
            for task_data in tasks_p1:
                task = Task.objects.create(
                    project=project1,
                    title=task_data['title'],
                    description=f"Implementation details for: {task_data['title']}",
                    is_completed=task_data['is_completed'],
                    priority=task_data['priority']
                )
                if task_data['is_completed']:
                    task.completed_at = timezone.now() - timedelta(days=random.randint(1, 30))
                    task.save()
            
            # Create time logs
            for i in range(25):
                days_ago = random.randint(1, 90)
                TimeLog.objects.create(
                    project=project1,
                    date=date.today() - timedelta(days=days_ago),
                    hours=round(random.uniform(1.5, 6.5), 1),
                    description=random.choice([
                        'Frontend development',
                        'Backend API implementation',
                        'Database optimization',
                        'Bug fixes and testing',
                        'Code review and refactoring',
                        'Documentation writing',
                        'DevOps and deployment',
                        'Meeting with stakeholders'
                    ])
                )
            
            # Create status updates
            ProjectStatus.objects.create(
                project=project1,
                status='Project Kickoff',
                date=project1.start_date,
                note='Initial project setup and requirements gathering completed.'
            )
            ProjectStatus.objects.create(
                project=project1,
                status='MVP Released',
                date=project1.start_date + timedelta(days=45),
                note='Minimum viable product deployed to staging environment.'
            )
            ProjectStatus.objects.create(
                project=project1,
                status='Production Launch',
                date=project1.start_date + timedelta(days=75),
                note='Successfully launched to production with initial user base.'
            )
            
            self.stdout.write(self.style.SUCCESS(f'Created project: {project1.name}'))

        # PROJECT 2: AI Research Tool (PRIVATE)
        project2, created = Project.objects.get_or_create(
            slug='neural-insights-pro',
            defaults={
                'name': 'Neural Insights Pro',
                'description': """A proprietary AI-powered research assistant that helps analyze scientific papers, 
                extract key insights, and generate comprehensive literature reviews. This cutting-edge tool uses 
                advanced NLP models and custom-trained transformers.
                
                Features:
                - PDF parsing and intelligent text extraction
                - Citation network analysis and visualization
                - Automatic summarization with GPT-4 integration
                - Knowledge graph construction
                - Collaborative research workspace
                - Real-time collaboration with WebSockets
                
                This private project is being developed for a research institution and contains 
                proprietary algorithms for academic paper analysis and synthesis.""",
                'status': 'active',
                'start_date': date.today() - timedelta(days=60),
                'is_public': False,  # PRIVATE PROJECT
                'github_url': '',  # Private repo
                'live_url': '',  # Internal deployment only
                'owner': user
            }
        )
        
        if created:
            # Add tags and technologies
            project2.tags.add(tags['ai-ml'], tags['backend'], tags['database'])
            project2.technologies.add(
                technologies['Python'], technologies['FastAPI'], technologies['PostgreSQL'],
                technologies['Docker'], technologies['Redis'],
                technologies['JavaScript'], technologies['WebSockets'],
                technologies['GraphQL']
            )
            
            # Create tasks
            tasks_p2 = [
                {'title': 'Research NLP models for paper analysis', 'is_completed': True, 'priority': 3},
                {'title': 'Set up FastAPI project architecture', 'is_completed': True, 'priority': 3},
                {'title': 'Implement PDF parsing pipeline', 'is_completed': True, 'priority': 3},
                {'title': 'Build citation extraction system', 'is_completed': True, 'priority': 2},
                {'title': 'Create knowledge graph database', 'is_completed': True, 'priority': 2},
                {'title': 'Integrate GPT-4 API', 'is_completed': False, 'priority': 3},
                {'title': 'Develop collaborative workspace', 'is_completed': False, 'priority': 2},
                {'title': 'Implement real-time sync with WebSockets', 'is_completed': False, 'priority': 2},
                {'title': 'Build visualization components', 'is_completed': False, 'priority': 1},
                {'title': 'Add export functionality', 'is_completed': False, 'priority': 1},
            ]
            
            for task_data in tasks_p2:
                task = Task.objects.create(
                    project=project2,
                    title=task_data['title'],
                    description=f"Technical implementation: {task_data['title']}",
                    is_completed=task_data['is_completed'],
                    priority=task_data['priority']
                )
                if task_data['is_completed']:
                    task.completed_at = timezone.now() - timedelta(days=random.randint(1, 20))
                    task.save()
            
            # Create time logs
            for i in range(15):
                days_ago = random.randint(1, 45)
                TimeLog.objects.create(
                    project=project2,
                    date=date.today() - timedelta(days=days_ago),
                    hours=round(random.uniform(2.0, 5.0), 1),
                    description=random.choice([
                        'ML model training and evaluation',
                        'API endpoint development',
                        'Database schema design',
                        'Algorithm optimization',
                        'Research and experimentation',
                        'Client meetings and demos',
                        'Security implementation'
                    ])
                )
            
            # Create status updates
            ProjectStatus.objects.create(
                project=project2,
                status='Research Phase Complete',
                date=project2.start_date + timedelta(days=15),
                note='Completed evaluation of NLP models and selected optimal approach.'
            )
            ProjectStatus.objects.create(
                project=project2,
                status='Alpha Version Ready',
                date=project2.start_date + timedelta(days=35),
                note='Core functionality implemented and ready for internal testing.'
            )
            
            self.stdout.write(self.style.SUCCESS(f'Created project: {project2.name}'))

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Demo Data Created Successfully ==='))
        self.stdout.write(f'User: {user.username}')
        self.stdout.write(f'Projects: 2 (1 public, 1 private)')
        self.stdout.write(f'Total Tasks: {Task.objects.filter(project__owner=user).count()}')
        self.stdout.write(f'Total Time Logs: {TimeLog.objects.filter(project__owner=user).count()}')
        self.stdout.write(f'Total Hours Logged: {sum(tl.hours for tl in TimeLog.objects.filter(project__owner=user))}')