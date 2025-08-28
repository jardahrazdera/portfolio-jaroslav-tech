from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import random
from devtracker.models import Project, Task, TimeLog, ProjectStatus


class Command(BaseCommand):
    help = 'Enriches existing demo projects with more data'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='demo_user')
            self.stdout.write(self.style.SUCCESS(f'Found demo user: {user.username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Demo user not found! Run create_demo_data first.'))
            return

        # Enrich Quantum Commerce Platform
        try:
            project1 = Project.objects.get(slug='quantum-commerce', owner=user)
            
            if project1.tasks.count() == 0:
                self.stdout.write('Adding tasks to Quantum Commerce Platform...')
                
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
                
                self.stdout.write(f'  Added {len(tasks_p1)} tasks')
            
            if project1.time_logs.count() == 0:
                self.stdout.write('Adding time logs to Quantum Commerce Platform...')
                
                # Create time logs
                logs_created = 0
                for i in range(25):
                    days_ago = random.randint(1, 90)
                    TimeLog.objects.create(
                        project=project1,
                        date=date.today() - timedelta(days=days_ago),
                        hours=round(random.uniform(1.5, 6.5), 1),
                        description=random.choice([
                            'Frontend development with React components',
                            'Backend API implementation and testing',
                            'Database optimization and indexing',
                            'Bug fixes and unit testing',
                            'Code review and refactoring',
                            'Documentation and API specs',
                            'DevOps and CI/CD pipeline setup',
                            'Meeting with stakeholders and planning'
                        ])
                    )
                    logs_created += 1
                
                self.stdout.write(f'  Added {logs_created} time logs')
            
            if project1.status_updates.count() == 0:
                self.stdout.write('Adding status updates to Quantum Commerce Platform...')
                
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
                    note='Minimum viable product deployed to staging environment for testing.'
                )
                ProjectStatus.objects.create(
                    project=project1,
                    status='Production Launch',
                    date=project1.start_date + timedelta(days=75),
                    note='Successfully launched to production with initial user base of 500+ users.'
                )
                
                self.stdout.write('  Added 3 status updates')
                
            self.stdout.write(self.style.SUCCESS(f'✓ Enriched: {project1.name}'))
            
        except Project.DoesNotExist:
            self.stdout.write(self.style.WARNING('Quantum Commerce Platform not found'))

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Demo Data Summary ==='))
        self.stdout.write(f'User: {user.username}')
        
        for p in Project.objects.filter(owner=user):
            total_hours = sum(tl.hours for tl in p.time_logs.all())
            completed_tasks = p.tasks.filter(is_completed=True).count()
            total_tasks = p.tasks.count()
            
            self.stdout.write(f'\n{p.name}:')
            self.stdout.write(f'  - Public: {"Yes" if p.is_public else "No (Private)"}')
            self.stdout.write(f'  - Status: {p.get_status_display()}')
            self.stdout.write(f'  - Tasks: {completed_tasks}/{total_tasks} completed')
            self.stdout.write(f'  - Time Logged: {total_hours:.1f} hours across {p.time_logs.count()} entries')
            self.stdout.write(f'  - Technologies: {", ".join([t.name for t in p.technologies.all()[:5]])}')