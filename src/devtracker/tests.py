from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from .models import Project, Task, TimeLog, Tag, Technology, ProjectStatus


class BaseTestCase(TestCase):
    """Base test case with common setup."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.admin_user = User.objects.create_user(username='admin', password='adminpass', is_staff=True)
        self.tag = Tag.objects.create(name='Web Dev', slug='web-dev')
        self.tech = Technology.objects.create(name='Django')


class ProjectWorkflowTests(BaseTestCase):
    """Test complete project workflow from creation to deletion."""
    
    def test_complete_project_lifecycle(self):
        """Test creating, managing, and deleting a project with all features."""
        self.client.login(username='testuser', password='testpass')
        
        # 1. Create project
        response = self.client.post(reverse('devtracker:project_create'), {
            'name': 'Test Project',
            'description': 'Test description',
            'status': 'active',
            'is_public': True
        })
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(name='Test Project')
        
        # 2. Add tasks to project
        response = self.client.post(
            reverse('devtracker:task_create', kwargs={'slug': project.slug}),
            {'title': 'Task 1', 'priority': 2, 'is_completed': False}
        )
        self.assertEqual(response.status_code, 302)
        
        response = self.client.post(
            reverse('devtracker:task_create', kwargs={'slug': project.slug}),
            {'title': 'Task 2', 'priority': 1, 'is_completed': True}
        )
        self.assertEqual(response.status_code, 302)
        
        # 3. Log time
        response = self.client.post(
            reverse('devtracker:time_log', kwargs={'slug': project.slug}),
            {'date': date.today().isoformat(), 'hours': 4.5, 'description': 'Development work'}
        )
        self.assertEqual(response.status_code, 302)
        
        # 4. Add status update
        response = self.client.post(
            reverse('devtracker:status_create', kwargs={'slug': project.slug}),
            {'status': 'Milestone 1', 'date': date.today().isoformat(), 'note': 'First milestone'}
        )
        self.assertEqual(response.status_code, 302)
        
        # 5. Verify project has all data
        project.refresh_from_db()
        self.assertEqual(project.tasks.count(), 2)
        self.assertEqual(project.time_logs.count(), 1)
        self.assertEqual(project.status_updates.count(), 1)
        self.assertEqual(project.get_progress_percentage(), 50)  # 1/2 tasks done
        self.assertEqual(project.get_total_hours(), 4.5)
        
        # 6. Update a task
        task = project.tasks.first()
        response = self.client.post(
            reverse('devtracker:task_edit', kwargs={'pk': task.pk}),
            {'title': 'Updated Task', 'priority': 3, 'is_completed': True}
        )
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.title, 'Updated Task')
        self.assertTrue(task.is_completed)
        
        # 7. Delete a task
        task_count_before = project.tasks.count()
        response = self.client.post(reverse('devtracker:task_delete', kwargs={'pk': task.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(project.tasks.count(), task_count_before - 1)
        
        # 8. Delete entire project
        response = self.client.post(reverse('devtracker:project_delete', kwargs={'slug': project.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Project.objects.filter(slug=project.slug).exists())


class SecurityTests(BaseTestCase):
    """Test security aspects - authentication, authorization."""
    
    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(
            name='Owner Project',
            slug='owner-project', 
            description='Test',
            owner=self.user
        )
        self.other_user = User.objects.create_user('other', 'other@test.com', 'pass')
    
    def test_authentication_required_for_protected_views(self):
        """Test that protected views require login."""
        protected_urls = [
            reverse('devtracker:dashboard'),
            reverse('devtracker:project_create'),
            reverse('devtracker:task_create', kwargs={'slug': self.project.slug}),
            reverse('devtracker:project_delete', kwargs={'slug': self.project.slug}),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/tracker/login/', response.url)
    
    def test_ownership_protection(self):
        """Test that users can only modify their own projects."""
        self.client.login(username='other', password='pass')
        
        # Other user cannot access owner's project management
        ownership_urls = [
            reverse('devtracker:project_edit', kwargs={'slug': self.project.slug}),
            reverse('devtracker:project_delete', kwargs={'slug': self.project.slug}),
            reverse('devtracker:task_create', kwargs={'slug': self.project.slug}),
        ]
        
        for url in ownership_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)
    
    def test_admin_user_separation(self):
        """Test that admin users are redirected to admin interface."""
        # Admin login attempt redirects to admin
        response = self.client.post(reverse('devtracker:login'), {
            'username': 'admin',
            'password': 'adminpass'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)
        
        # Admin accessing user views redirects to admin
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('devtracker:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/', response.url)


class PublicAccessTests(BaseTestCase):
    """Test public vs private project access."""
    
    def setUp(self):
        super().setUp()
        self.public_project = Project.objects.create(
            name='Public Project',
            slug='public-project',
            description='Public test',
            owner=self.user,
            is_public=True
        )
        self.private_project = Project.objects.create(
            name='Private Project', 
            slug='private-project',
            description='Private test',
            owner=self.user,
            is_public=False
        )
    
    def test_project_visibility(self):
        """Test public/private project access for anonymous users."""
        # Anonymous can see public project
        response = self.client.get(reverse('devtracker:project_detail', kwargs={'slug': self.public_project.slug}))
        self.assertEqual(response.status_code, 200)
        
        # Anonymous cannot see private project
        response = self.client.get(reverse('devtracker:project_detail', kwargs={'slug': self.private_project.slug}))
        self.assertEqual(response.status_code, 404)
        
        # Project list shows only public projects to anonymous users
        response = self.client.get(reverse('devtracker:project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Project')
        self.assertNotContains(response, 'Private Project')


class AuthenticationFlowTests(TestCase):
    """Test login/logout functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'testpass')
        self.admin = User.objects.create_user('admin', 'admin@test.com', 'adminpass', is_staff=True)
    
    def test_user_login_logout_flow(self):
        """Test complete login/logout flow for regular users."""
        # Login
        response = self.client.post(reverse('devtracker:login'), {
            'username': 'testuser',
            'password': 'testpass'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/', response.url)
        
        # Logout shows goodbye page
        response = self.client.get(reverse('devtracker:logout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Goodbye!')
        
        # After logout, protected views redirect to login
        response = self.client.get(reverse('devtracker:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/tracker/login/', response.url)


class ModelLogicTests(TestCase):
    """Test model methods and business logic."""
    
    def test_project_progress_calculation(self):
        """Test project progress percentage calculation."""
        user = User.objects.create_user('test', 'test@test.com', 'pass')
        project = Project.objects.create(name='Test', slug='test', owner=user)
        
        # No tasks = 0% progress
        self.assertEqual(project.get_progress_percentage(), 0)
        
        # Mixed completed/incomplete tasks
        Task.objects.create(project=project, title='Task 1', is_completed=True)
        Task.objects.create(project=project, title='Task 2', is_completed=False)
        Task.objects.create(project=project, title='Task 3', is_completed=True)
        
        # 2/3 = 67%
        self.assertEqual(project.get_progress_percentage(), 67)
    
    def test_project_total_hours_calculation(self):
        """Test project total hours calculation."""
        user = User.objects.create_user('test', 'test@test.com', 'pass')
        project = Project.objects.create(name='Test', slug='test', owner=user)
        
        TimeLog.objects.create(project=project, date=date.today(), hours=2.5, description='Work 1')
        TimeLog.objects.create(project=project, date=date.today(), hours=3.0, description='Work 2')
        
        self.assertEqual(project.get_total_hours(), 5.5)
    
    def test_task_completion_timestamp(self):
        """Test task completion timestamp behavior."""
        user = User.objects.create_user('test', 'test@test.com', 'pass')
        project = Project.objects.create(name='Test', slug='test', owner=user)
        task = Task.objects.create(project=project, title='Test Task', is_completed=False)
        
        self.assertIsNone(task.completed_at)
        
        # Mark completed
        task.is_completed = True
        task.save()
        self.assertIsNotNone(task.completed_at)
        
        # Mark incomplete
        task.is_completed = False
        task.save()
        self.assertIsNone(task.completed_at)