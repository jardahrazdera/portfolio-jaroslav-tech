from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from .models import Project, Task, TimeLog, Tag, Technology, ProjectStatus


class ProjectListViewTests(TestCase):
    """Test the public project list view."""
    
    def setUp(self):
        self.client = Client()
        self.tag = Tag.objects.create(name='Web Dev', slug='web-dev')
        self.tech = Technology.objects.create(name='Django')
        
    def test_public_project_list_shows_only_public_projects(self):
        """Public project list should only show is_public=True projects."""
        # Create public and private projects
        public_project = Project.objects.create(
            name='Public Project',
            slug='public-project',
            description='A public project',
            is_public=True
        )
        private_project = Project.objects.create(
            name='Private Project', 
            slug='private-project',
            description='A private project',
            is_public=False
        )
        
        response = self.client.get(reverse('devtracker:project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Project')
        self.assertNotContains(response, 'Private Project')

    def test_authenticated_user_sees_all_projects(self):
        """Authenticated users should see both public and private projects."""
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.client.login(username='testuser', password='password')
        
        public_project = Project.objects.create(
            name='Public Project',
            slug='public-project', 
            description='A public project',
            is_public=True
        )
        private_project = Project.objects.create(
            name='Private Project',
            slug='private-project',
            description='A private project', 
            is_public=False
        )
        
        response = self.client.get(reverse('devtracker:project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Project')
        self.assertContains(response, 'Private Project')


class ProjectDetailViewTests(TestCase):
    """Test the project detail view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        
    def test_public_project_accessible_to_anonymous_users(self):
        """Public projects should be accessible to anonymous users."""
        project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            description='Test description',
            is_public=True
        )
        
        response = self.client.get(reverse('devtracker:project_detail', kwargs={'slug': 'test-project'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')

    def test_private_project_not_accessible_to_anonymous_users(self):
        """Private projects should return 404 for anonymous users."""
        project = Project.objects.create(
            name='Private Project',
            slug='private-project',
            description='Private description',
            is_public=False
        )
        
        response = self.client.get(reverse('devtracker:project_detail', kwargs={'slug': 'private-project'}))
        self.assertEqual(response.status_code, 404)

    def test_authenticated_user_can_access_private_project(self):
        """Authenticated users should access private projects."""
        self.client.login(username='testuser', password='password')
        project = Project.objects.create(
            name='Private Project',
            slug='private-project',
            description='Private description',
            is_public=False
        )
        
        response = self.client.get(reverse('devtracker:project_detail', kwargs={'slug': 'private-project'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Private Project')


class DashboardViewTests(TestCase):
    """Test the authenticated dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        
    def test_dashboard_requires_authentication(self):
        """Dashboard should redirect to login for anonymous users."""
        response = self.client.get(reverse('devtracker:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_dashboard_accessible_to_authenticated_users(self):
        """Dashboard should be accessible to authenticated users."""
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('devtracker:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_dashboard_shows_project_statistics(self):
        """Dashboard should display project statistics."""
        self.client.login(username='testuser', password='password')
        
        # Create test projects
        Project.objects.create(name='Active Project', slug='active', description='Test', status='active')
        Project.objects.create(name='Completed Project', slug='completed', description='Test', status='completed')
        
        response = self.client.get(reverse('devtracker:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total Projects')
        self.assertContains(response, 'Active')
        self.assertContains(response, 'Completed')


class ProjectCreateViewTests(TestCase):
    """Test project creation view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        
    def test_create_view_requires_authentication(self):
        """Project create view should require authentication."""
        response = self.client.get(reverse('devtracker:project_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_authenticated_user_can_access_create_form(self):
        """Authenticated users should access the create form."""
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('devtracker:project_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Project')

    def test_create_project_with_valid_data(self):
        """Should create project with valid POST data."""
        self.client.login(username='testuser', password='password')
        data = {
            'name': 'New Test Project',
            'description': 'A new test project',
            'status': 'planning',
            'is_public': True,
        }
        
        response = self.client.post(reverse('devtracker:project_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        self.assertTrue(Project.objects.filter(name='New Test Project').exists())


class ProjectUpdateViewTests(TestCase):
    """Test project update view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            description='Original description',
            status='planning'
        )
        
    def test_update_view_requires_authentication(self):
        """Project update view should require authentication."""
        response = self.client.get(reverse('devtracker:project_edit', kwargs={'slug': 'test-project'}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_authenticated_user_can_update_project(self):
        """Authenticated users should be able to update projects."""
        self.client.login(username='testuser', password='password')
        data = {
            'name': 'Updated Test Project',
            'description': 'Updated description', 
            'status': 'active',
            'is_public': False,
        }
        
        response = self.client.post(reverse('devtracker:project_edit', kwargs={'slug': 'test-project'}), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful update
        
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Updated Test Project')
        self.assertEqual(self.project.description, 'Updated description')


class TimeLogCreateViewTests(TestCase):
    """Test time log creation view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            description='Test description'
        )
        
    def test_timelog_view_requires_authentication(self):
        """Time log view should require authentication."""
        response = self.client.get(reverse('devtracker:time_log', kwargs={'slug': 'test-project'}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_authenticated_user_can_log_time(self):
        """Authenticated users should be able to log time."""
        self.client.login(username='testuser', password='password')
        data = {
            'date': date.today(),
            'hours': 2.5,
            'description': 'Working on feature X'
        }
        
        response = self.client.post(reverse('devtracker:time_log', kwargs={'slug': 'test-project'}), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        time_log = TimeLog.objects.filter(project=self.project).first()
        self.assertIsNotNone(time_log)
        self.assertEqual(time_log.hours, 2.5)
        self.assertEqual(time_log.description, 'Working on feature X')


class ProjectModelTests(TestCase):
    """Test Project model methods."""
    
    def setUp(self):
        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            description='Test description'
        )
        
    def test_project_progress_calculation_no_tasks(self):
        """Project with no tasks should have 0% progress."""
        self.assertEqual(self.project.get_progress_percentage(), 0)
        
    def test_project_progress_calculation_with_tasks(self):
        """Project progress should be calculated correctly."""
        Task.objects.create(project=self.project, title='Task 1', is_completed=True)
        Task.objects.create(project=self.project, title='Task 2', is_completed=False)
        Task.objects.create(project=self.project, title='Task 3', is_completed=True)
        
        # 2 out of 3 tasks completed = 67%
        self.assertEqual(self.project.get_progress_percentage(), 67)

    def test_project_total_hours_calculation(self):
        """Project should calculate total hours correctly."""
        TimeLog.objects.create(project=self.project, date=date.today(), hours=2.5, description='Work 1')
        TimeLog.objects.create(project=self.project, date=date.today(), hours=3.0, description='Work 2')
        
        self.assertEqual(self.project.get_total_hours(), 5.5)


class TaskModelTests(TestCase):
    """Test Task model behavior."""
    
    def setUp(self):
        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            description='Test description'
        )
        
    def test_task_completion_sets_completed_at(self):
        """Marking task as completed should set completed_at timestamp."""
        task = Task.objects.create(
            project=self.project,
            title='Test Task',
            is_completed=False
        )
        
        self.assertIsNone(task.completed_at)
        
        task.is_completed = True
        task.save()
        
        self.assertIsNotNone(task.completed_at)
        
    def test_task_uncomplete_clears_completed_at(self):
        """Unmarking task as completed should clear completed_at timestamp.""" 
        task = Task.objects.create(
            project=self.project,
            title='Test Task',
            is_completed=True
        )
        
        # Should have completed_at set initially
        self.assertIsNotNone(task.completed_at)
        
        task.is_completed = False
        task.save()
        
        self.assertIsNone(task.completed_at)
