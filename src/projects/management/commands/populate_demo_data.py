from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
import random
from projects.models import Project, Technology, WorkSession, ProjectImage, UserProfile


class Command(BaseCommand):
    help = "Populate the database with realistic demo data for the project dashboard"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing demo data before creating new data",
        )
    
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing demo data...")
            # Keep admin user but clear demo data
            Project.objects.exclude(owner__username="admin").delete()
            WorkSession.objects.exclude(user__username="admin").delete()
            Technology.objects.all().delete()
            User.objects.filter(username__startswith="demo_").delete()
        
        self.create_technologies()
        self.create_demo_users()
        self.create_projects()
        self.create_work_sessions()
        
        self.stdout.write(
            self.style.SUCCESS("Successfully populated dashboard with demo data\!")
        )
        
        # Print summary
        self.stdout.write("\n=== DEMO DATA SUMMARY ===")
        self.stdout.write(f"Technologies: {Technology.objects.count()}")
        self.stdout.write(f"Projects: {Project.objects.count()}")
        self.stdout.write(f"Work Sessions: {WorkSession.objects.count()}")
        self.stdout.write(f"Users: {User.objects.count()}")
    
    def create_technologies(self):
        """Create comprehensive technology stack"""
        self.stdout.write("Creating technologies...")
        
        technologies = [
            # Frontend
            ("React", "frontend", "A JavaScript library for building user interfaces"),
            ("Vue.js", "frontend", "Progressive JavaScript framework"),
            ("Angular", "frontend", "Platform for building mobile and desktop web applications"),
            ("Svelte", "frontend", "Cybernetically enhanced web apps"),
            ("Next.js", "frontend", "The React Framework for Production"),
            ("Nuxt.js", "frontend", "The Vue.js Framework"),
            ("Tailwind CSS", "frontend", "Utility-first CSS framework"),
            ("Bootstrap", "frontend", "CSS framework for responsive design"),
            ("Sass", "frontend", "CSS extension language"),
            ("TypeScript", "frontend", "Typed superset of JavaScript"),
            ("JavaScript", "frontend", "Programming language of the web"),
            ("HTML5", "frontend", "Latest HTML standard"),
            ("CSS3", "frontend", "Latest CSS standard"),
            
            # Backend
            ("Django", "backend", "High-level Python web framework"),
            ("Flask", "backend", "Lightweight Python web framework"),
            ("FastAPI", "backend", "Modern, fast Python API framework"),
            ("Node.js", "backend", "JavaScript runtime built on Chrome V8 engine"),
            ("Express.js", "backend", "Fast, unopinionated web framework for Node.js"),
            ("Ruby on Rails", "backend", "Server-side web application framework"),
            ("Laravel", "backend", "PHP framework for web artisans"),
            ("Spring Boot", "backend", "Java-based framework for building applications"),
            ("ASP.NET Core", "backend", "Cross-platform .NET framework"),
            ("Go", "backend", "Open source programming language"),
            ("Rust", "backend", "Systems programming language"),
            ("Python", "backend", "High-level programming language"),
            ("Java", "backend", "Object-oriented programming language"),
            ("C#", "backend", "Modern object-oriented programming language"),
            
            # Database
            ("PostgreSQL", "database", "Advanced open source relational database"),
            ("MySQL", "database", "Popular open source relational database"),
            ("MongoDB", "database", "Document-oriented NoSQL database"),
            ("Redis", "database", "In-memory data structure store"),
            ("SQLite", "database", "Lightweight embedded database"),
            ("Elasticsearch", "database", "Distributed search and analytics engine"),
            ("CouchDB", "database", "NoSQL document-oriented database"),
            ("Firebase", "database", "Backend-as-a-Service platform"),
            
            # DevOps
            ("Docker", "devops", "Containerization platform"),
            ("Kubernetes", "devops", "Container orchestration system"),
            ("Jenkins", "devops", "Automation server for CI/CD"),
            ("GitHub Actions", "devops", "CI/CD platform integrated with GitHub"),
            ("GitLab CI/CD", "devops", "DevOps platform with CI/CD capabilities"),
            ("Terraform", "devops", "Infrastructure as Code tool"),
            ("Ansible", "devops", "IT automation platform"),
            ("AWS", "devops", "Amazon Web Services cloud platform"),
            ("Azure", "devops", "Microsoft cloud computing platform"),
            ("Google Cloud", "devops", "Google Cloud Platform"),
            ("Nginx", "devops", "Web server and reverse proxy"),
            ("Apache", "devops", "HTTP server"),
            ("Linux", "devops", "Open source operating system"),
            
            # Mobile
            ("React Native", "mobile", "Framework for building native mobile apps"),
            ("Flutter", "mobile", "UI toolkit for building mobile applications"),
            ("Swift", "mobile", "Programming language for iOS development"),
            ("Kotlin", "mobile", "Programming language for Android development"),
            ("Ionic", "mobile", "Cross-platform mobile app development"),
            ("Xamarin", "mobile", "Microsoft mobile app development platform"),
            
            # Other
            ("Git", "other", "Distributed version control system"),
            ("Webpack", "other", "Module bundler for JavaScript"),
            ("Vite", "other", "Next generation frontend tooling"),
            ("GraphQL", "other", "Query language and runtime for APIs"),
            ("REST API", "other", "Architectural style for web services"),
            ("WebSocket", "other", "Communication protocol for real-time apps"),
            ("OAuth", "other", "Authorization framework"),
            ("JWT", "other", "JSON Web Token for secure information transmission"),
        ]
        
        for name, category, description in technologies:
            Technology.objects.get_or_create(
                name=name,
                defaults={
                    "category": category,
                    "description": description
                }
            )
        
        self.stdout.write(f"Created {len(technologies)} technologies")
    
    def create_demo_users(self):
        """Create demo users with profiles"""
        self.stdout.write("Creating demo users...")
        
        demo_users = [
            {
                "username": "demo_sarah",
                "first_name": "Sarah",
                "last_name": "Johnson",
                "email": "sarah@demo.com",
                "bio": "Full-stack developer passionate about React and Django. Love building scalable web applications with modern technologies.",
                "github_url": "https://github.com/sarahjohnson",
                "linkedin_url": "https://linkedin.com/in/sarah-johnson-dev"
            },
            {
                "username": "demo_alex",
                "first_name": "Alex",
                "last_name": "Chen",
                "email": "alex@demo.com",
                "bio": "DevOps engineer and cloud architect. Experienced in Kubernetes, Docker, and AWS. Building reliable infrastructure at scale.",
                "github_url": "https://github.com/alexchen",
                "linkedin_url": "https://linkedin.com/in/alex-chen-devops"
            },
            {
                "username": "demo_maria",
                "first_name": "Maria",
                "last_name": "Rodriguez",
                "email": "maria@demo.com",
                "bio": "Mobile app developer specializing in React Native and Flutter. Creating beautiful cross-platform experiences.",
                "github_url": "https://github.com/mariarodriguez",
                "linkedin_url": "https://linkedin.com/in/maria-rodriguez-mobile"
            }
        ]
        
        for user_data in demo_users:
            bio = user_data.pop("bio")
            github_url = user_data.pop("github_url")
            linkedin_url = user_data.pop("linkedin_url")
            
            user, created = User.objects.get_or_create(
                username=user_data["username"],
                defaults=user_data
            )
            
            if created:
                UserProfile.objects.create(
                    user=user,
                    bio=bio,
                    github_url=github_url,
                    linkedin_url=linkedin_url
                )
        
        self.stdout.write(f"Created {len(demo_users)} demo users")
    
    def create_projects(self):
        """Create realistic projects with proper descriptions"""
        self.stdout.write("Creating demo projects...")
        
        # Get all users
        users = list(User.objects.all())
        all_technologies = list(Technology.objects.all())
        
        projects_data = [
            {
                "title": "E-Commerce Platform",
                "short_description": "Full-stack e-commerce solution with React and Django",
                "description": "Comprehensive e-commerce platform featuring user authentication, product catalog, shopping cart, payment integration with Stripe, order management, and admin dashboard. Built with modern technologies and responsive design.",
                "status": "completed",
                "priority": "high",
                "is_featured": True,
                "is_public": True,
                "github_url": "https://github.com/demo/ecommerce-platform",
                "live_url": "https://demo-ecommerce.herokuapp.com",
                "tech_categories": ["frontend", "backend", "database", "devops"],
                "days_ago": 30
            },
            {
                "title": "Task Management App",
                "short_description": "Collaborative project management tool with real-time updates",
                "description": "Modern task management application with drag-and-drop Kanban boards, real-time collaboration, team management, time tracking, and comprehensive reporting. Features beautiful UI with dark/light themes.",
                "status": "development",
                "priority": "high",
                "is_featured": True,
                "is_public": True,
                "github_url": "https://github.com/demo/task-manager",
                "live_url": "https://demo-tasks.netlify.app",
                "tech_categories": ["frontend", "backend", "database"],
                "days_ago": 5
            },
        ]
        
        for project_data in projects_data:
            tech_categories = project_data.pop("tech_categories")
            days_ago = project_data.pop("days_ago")
            
            # Assign random user
            owner = random.choice(users)
            project_data["owner"] = owner
            
            # Set dates
            created_date = timezone.now() - timedelta(days=days_ago)
            project_data["start_date"] = created_date.date()
            
            if project_data["status"] == "completed":
                project_data["end_date"] = (created_date + timedelta(days=random.randint(10, 40))).date()
            
            # Create project
            project = Project.objects.create(**project_data)
            project.created_at = created_date
            project.save(update_fields=["created_at"])
            
            # Add technologies
            selected_technologies = []
            for category in tech_categories:
                category_techs = [t for t in all_technologies if t.category == category]
                if category_techs:
                    selected_technologies.extend(random.sample(category_techs, min(3, len(category_techs))))
            
            # Remove duplicates and add to project
            unique_technologies = list(set(selected_technologies))
            project.technologies.set(unique_technologies[:8])  # Limit to 8 technologies
        
        self.stdout.write(f"Created {len(projects_data)} demo projects")
    
    def create_work_sessions(self):
        """Create realistic work sessions for projects"""
        self.stdout.write("Creating work sessions...")
        
        projects = Project.objects.all()
        total_sessions = 0
        for project in projects:
            # Create 3-5 sessions per project for demo
            num_sessions = random.randint(3, 5)
            project_start = project.created_at
            
            for i in range(num_sessions):
                # Random session date between project start and now
                days_offset = random.randint(0, (timezone.now() - project_start).days)
                session_date = project_start + timedelta(days=days_offset)
                
                # Random session duration (1 to 6 hours)
                duration = round(random.uniform(1.0, 6.0), 2)
                
                WorkSession.objects.create(
                    project=project,
                    user=project.owner,
                    title=f"Working on {project.title}",
                    description=f"Development session for {project.title.lower()}.",
                    start_time=session_date,
                    end_time=session_date + timedelta(hours=duration),
                    duration_hours=duration,
                    productivity_rating=random.randint(3, 5),
                    notes="Productive development session",
                    is_active=False
                )
                total_sessions += 1
        
        self.stdout.write(f"Created {total_sessions} work sessions")
