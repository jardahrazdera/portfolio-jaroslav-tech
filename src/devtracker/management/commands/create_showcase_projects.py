from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import random
from devtracker.models import Project, Task, TimeLog, Tag, Technology, ProjectStatus


class Command(BaseCommand):
    help = 'Creates additional showcase projects to demonstrate DevTracker capabilities'

    def handle(self, *args, **options):
        # Get or create demo user
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
            user.set_password('demo123')
            user.save()

        # Get existing tags and technologies
        tags = {tag.slug: tag for tag in Tag.objects.all()}
        technologies = {tech.name: tech for tech in Technology.objects.all()}

        # Create additional technologies if needed
        additional_tech = [
            'Vue.js', 'Flutter', 'Kotlin', 'Swift', 'Node.js', 'Express.js',
            'MongoDB', 'Firebase', 'Unity', 'TensorFlow', 'PyTorch', 
            'Elasticsearch', 'Kubernetes', 'Jenkins', 'Terraform'
        ]
        
        for tech_name in additional_tech:
            tech, created = Technology.objects.get_or_create(name=tech_name)
            technologies[tech_name] = tech
            if created:
                self.stdout.write(f'Created technology: {tech.name}')

        projects_data = [
            {
                'slug': 'mobile-fitness-tracker',
                'name': 'FitTrack Mobile App',
                'description': """A comprehensive fitness tracking mobile application built with Flutter for cross-platform compatibility. 
                Features include workout planning, nutrition tracking, progress analytics, and social challenges.
                
                Key Features:
                - Real-time workout tracking with GPS integration
                - Barcode scanner for food logging
                - Social features with friend challenges
                - Integration with wearable devices (Apple Watch, Fitbit)
                - Offline mode with data synchronization
                - Custom workout plan generator using AI
                
                The app has gained 50K+ downloads and maintains a 4.8-star rating on app stores.""",
                'status': 'completed',
                'start_date': date.today() - timedelta(days=180),
                'end_date': date.today() - timedelta(days=30),
                'is_public': True,
                'github_url': 'https://github.com/demo/fittrack-mobile',
                'live_url': 'https://play.google.com/store/apps/details?id=com.demo.fittrack',
                'tags': ['web-dev', 'open-source'],
                'technologies': ['Flutter', 'Firebase', 'Node.js', 'MongoDB'],
                'task_count': 15,
                'completed_percentage': 100,
                'time_logs_count': 35
            },
            {
                'slug': 'smart-home-dashboard',
                'name': 'IoT Home Dashboard',
                'description': """A real-time dashboard for monitoring and controlling smart home devices. Built with Vue.js frontend 
                and Python backend with WebSocket support for instant updates.
                
                Features:
                - Real-time device monitoring and control
                - Energy consumption analytics
                - Automated scheduling and rules
                - Mobile-responsive design
                - Voice command integration
                - Security camera integration
                - Weather-based automation
                
                Supports 50+ device types including Philips Hue, Nest, Ring, and custom Arduino sensors.""",
                'status': 'active',
                'start_date': date.today() - timedelta(days=90),
                'is_public': True,
                'github_url': 'https://github.com/demo/iot-dashboard',
                'live_url': 'https://smart-home-demo.herokuapp.com',
                'tags': ['web-dev', 'backend', 'open-source'],
                'technologies': ['Vue.js', 'Python', 'FastAPI', 'WebSockets', 'Redis'],
                'task_count': 12,
                'completed_percentage': 75,
                'time_logs_count': 22
            },
            {
                'slug': 'blockchain-voting-system',
                'name': 'SecureVote Blockchain',
                'description': """A decentralized voting system built on blockchain technology ensuring transparency, 
                security, and immutability of election results.
                
                Technical highlights:
                - Smart contracts written in Solidity
                - Zero-knowledge proofs for voter privacy
                - Multi-signature validation system
                - Real-time result visualization
                - Audit trail with cryptographic verification
                - Mobile and web interfaces
                
                Successfully tested in 3 pilot elections with 10,000+ participants.""",
                'status': 'on-hold',
                'start_date': date.today() - timedelta(days=200),
                'is_public': True,
                'github_url': 'https://github.com/demo/securevote-blockchain',
                'tags': ['backend', 'open-source'],
                'technologies': ['Python', 'JavaScript', 'React', 'PostgreSQL'],
                'task_count': 18,
                'completed_percentage': 60,
                'time_logs_count': 28
            },
            {
                'slug': 'ai-content-generator',
                'name': 'ContentMaster AI',
                'description': """An AI-powered content generation platform that helps marketers and writers create 
                high-quality content at scale using advanced language models.
                
                Capabilities:
                - Blog post and article generation
                - Social media content creation
                - Email marketing campaigns
                - SEO optimization suggestions
                - Multi-language support (12 languages)
                - Brand voice customization
                - Plagiarism detection
                - Content performance analytics
                
                Processes 1M+ content requests monthly with 95% user satisfaction.""",
                'status': 'active',
                'start_date': date.today() - timedelta(days=150),
                'is_public': False,  # Private project
                'tags': ['ai-ml', 'backend'],
                'technologies': ['Python', 'TensorFlow', 'FastAPI', 'PostgreSQL', 'Redis'],
                'task_count': 20,
                'completed_percentage': 80,
                'time_logs_count': 42
            },
            {
                'slug': 'game-dev-portfolio',
                'name': 'Retro Arcade Collection',
                'description': """A collection of retro-style arcade games built with Unity, showcasing game development 
                skills and classic gameplay mechanics.
                
                Games included:
                - Space Invaders remake with modern graphics
                - Pac-Man inspired maze game
                - Tetris with multiplayer support
                - Snake game with power-ups
                - Breakout with physics simulation
                
                Features cross-platform deployment, leaderboards, and achievement system.""",
                'status': 'completed',
                'start_date': date.today() - timedelta(days=120),
                'end_date': date.today() - timedelta(days=15),
                'is_public': True,
                'github_url': 'https://github.com/demo/retro-arcade',
                'live_url': 'https://demo-arcade.itch.io',
                'tags': ['open-source'],
                'technologies': ['Unity', 'C#'],
                'task_count': 10,
                'completed_percentage': 100,
                'time_logs_count': 18
            },
            {
                'slug': 'microservices-architecture',
                'name': 'CloudNative Microservices',
                'description': """A demonstration of cloud-native microservices architecture using Docker, Kubernetes, 
                and modern DevOps practices.
                
                Architecture components:
                - API Gateway with rate limiting
                - User service with JWT authentication
                - Product catalog service
                - Order processing service
                - Payment gateway integration
                - Message queuing with RabbitMQ
                - Centralized logging and monitoring
                - Auto-scaling and load balancing
                
                Deployed on AWS EKS with CI/CD pipeline using GitHub Actions.""",
                'status': 'planning',
                'start_date': date.today() - timedelta(days=30),
                'is_public': True,
                'github_url': 'https://github.com/demo/cloudnative-microservices',
                'tags': ['backend', 'devops', 'open-source'],
                'technologies': ['Docker', 'Kubernetes', 'Python', 'Go', 'AWS'],
                'task_count': 25,
                'completed_percentage': 20,
                'time_logs_count': 8
            },
            {
                'slug': 'data-analytics-platform',
                'name': 'BusinessIntel Analytics',
                'description': """A comprehensive data analytics platform for businesses to visualize key metrics, 
                generate reports, and gain actionable insights from their data.
                
                Features:
                - Real-time dashboard with custom widgets
                - ETL pipeline for data processing
                - Machine learning predictions
                - A/B testing framework
                - Custom report builder
                - Data export in multiple formats
                - Multi-tenant architecture
                - Role-based access control
                
                Processes 10TB+ of data daily for 200+ enterprise clients.""",
                'status': 'active',
                'start_date': date.today() - timedelta(days=240),
                'is_public': False,  # Private/Enterprise
                'tags': ['ai-ml', 'backend', 'database'],
                'technologies': ['Python', 'PostgreSQL', 'React', 'Elasticsearch', 'Docker'],
                'task_count': 35,
                'completed_percentage': 85,
                'time_logs_count': 68
            }
        ]

        created_count = 0
        for project_data in projects_data:
            project, created = Project.objects.get_or_create(
                slug=project_data['slug'],
                defaults={
                    'name': project_data['name'],
                    'description': project_data['description'],
                    'status': project_data['status'],
                    'start_date': project_data['start_date'],
                    'end_date': project_data.get('end_date'),
                    'is_public': project_data['is_public'],
                    'github_url': project_data.get('github_url', ''),
                    'live_url': project_data.get('live_url', ''),
                    'owner': user
                }
            )
            
            if created:
                created_count += 1
                
                # Add tags
                for tag_slug in project_data['tags']:
                    if tag_slug in tags:
                        project.tags.add(tags[tag_slug])
                
                # Add technologies
                for tech_name in project_data['technologies']:
                    if tech_name in technologies:
                        project.technologies.add(technologies[tech_name])
                
                # Create tasks based on completion percentage
                total_tasks = project_data['task_count']
                completed_tasks = int(total_tasks * (project_data['completed_percentage'] / 100))
                
                task_templates = [
                    'Set up project structure and dependencies',
                    'Design system architecture',
                    'Implement core functionality',
                    'Create user interface components',
                    'Set up database and models',
                    'Implement authentication system',
                    'Add API endpoints and validation',
                    'Create comprehensive test suite',
                    'Optimize performance and scalability',
                    'Write technical documentation',
                    'Deploy to staging environment',
                    'Conduct user testing and feedback',
                    'Fix bugs and edge cases',
                    'Implement security measures',
                    'Deploy to production environment',
                    'Set up monitoring and logging',
                    'Create user documentation',
                    'Implement analytics tracking',
                    'Add internationalization support',
                    'Conduct code review and refactoring',
                    'Set up CI/CD pipeline',
                    'Implement backup and recovery',
                    'Add advanced features',
                    'Performance optimization',
                    'Security audit and testing',
                    'Scale infrastructure',
                    'Add third-party integrations',
                    'Implement caching strategy',
                    'Create admin dashboard',
                    'Add reporting functionality',
                    'Implement notification system',
                    'Add mobile responsiveness',
                    'Create API documentation',
                    'Set up error tracking',
                    'Implement data migration tools'
                ]
                
                selected_tasks = random.sample(task_templates, min(total_tasks, len(task_templates)))
                
                for i, task_title in enumerate(selected_tasks):
                    is_completed = i < completed_tasks
                    priority = random.choice([1, 1, 2, 2, 2, 3])  # More medium priority tasks
                    
                    task = Task.objects.create(
                        project=project,
                        title=task_title,
                        description=f"Technical implementation for: {task_title}",
                        is_completed=is_completed,
                        priority=priority
                    )
                    
                    if is_completed:
                        days_ago = random.randint(1, int((date.today() - project.start_date).days))
                        task.completed_at = timezone.now() - timedelta(days=days_ago)
                        task.save()
                
                # Create time logs
                for i in range(project_data['time_logs_count']):
                    days_ago = random.randint(1, int((date.today() - project.start_date).days))
                    TimeLog.objects.create(
                        project=project,
                        date=date.today() - timedelta(days=days_ago),
                        hours=round(random.uniform(1.0, 8.0), 1),
                        description=random.choice([
                            'Feature development and implementation',
                            'Bug fixes and testing',
                            'Code review and refactoring',
                            'Research and technical planning',
                            'Client meetings and requirements gathering',
                            'Documentation and technical writing',
                            'Performance optimization',
                            'Security implementation',
                            'Database design and optimization',
                            'UI/UX development',
                            'API development and testing',
                            'DevOps and deployment',
                            'Monitoring and maintenance',
                            'Team collaboration and code review'
                        ])
                    )
                
                # Create status updates for active/completed projects
                if project.status in ['active', 'completed']:
                    milestones = [
                        ('Project Kickoff', 0, 'Project initiated with requirements gathering and team setup.'),
                        ('Architecture Complete', 15, 'System architecture finalized and development environment set up.'),
                        ('Core Features Implemented', 45, 'Primary functionality developed and initial testing completed.'),
                        ('Beta Release', 70, 'Beta version released for user testing and feedback collection.'),
                        ('Production Launch', 90, 'Successfully launched to production with monitoring in place.')
                    ]
                    
                    for status_name, days_offset, note in milestones:
                        milestone_date = project.start_date + timedelta(days=days_offset)
                        if milestone_date <= date.today():
                            if project.status == 'completed' or days_offset <= (project_data['completed_percentage'] / 100 * 90):
                                ProjectStatus.objects.create(
                                    project=project,
                                    status=status_name,
                                    date=milestone_date,
                                    note=note
                                )
                
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {project.name}'))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n=== Showcase Projects Created ==='))
        self.stdout.write(f'Created {created_count} new projects')
        self.stdout.write(f'Total projects: {Project.objects.filter(owner=user).count()}')
        self.stdout.write(f'Public projects: {Project.objects.filter(owner=user, is_public=True).count()}')
        self.stdout.write(f'Private projects: {Project.objects.filter(owner=user, is_public=False).count()}')
        
        # Status breakdown
        for status in ['planning', 'active', 'completed', 'on-hold']:
            count = Project.objects.filter(owner=user, status=status).count()
            self.stdout.write(f'{status.title()} projects: {count}')
        
        self.stdout.write(f'\nTotal tasks: {Task.objects.filter(project__owner=user).count()}')
        self.stdout.write(f'Total time logs: {TimeLog.objects.filter(project__owner=user).count()}')
        total_hours = sum(tl.hours for tl in TimeLog.objects.filter(project__owner=user))
        self.stdout.write(f'Total hours logged: {total_hours:.1f}h')