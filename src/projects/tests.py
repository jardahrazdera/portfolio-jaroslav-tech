from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import json

from .models import Project, Technology, WorkSession, ProjectImage, UserProfile
from .forms import ProjectForm, WorkSessionForm, ProjectImageForm, UserProfileForm, TechnologyFilterForm, BulkProjectActionForm


class UserProfileModelTests(TestCase):
    """
    Comprehensive tests for UserProfile model validation and business logic.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        self.profile = UserProfile.objects.create(user=self.user)
    
    def test_user_profile_creation(self):
        """Test UserProfile model creation with valid data"""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(str(self.profile), "Test User's Profile")
        self.assertFalse(self.profile.is_complete)
        self.assertEqual(self.profile.completion_percentage, 0)
    
    def test_profile_bio_validation(self):
        """Test biography validation rules"""
        # Test minimum length
        self.profile.bio = "short"
        with self.assertRaises(ValidationError):
            self.profile.full_clean()
        
        # Test suspicious content detection
        self.profile.bio = "This is a test biography with test content"
        with self.assertRaises(ValidationError):
            self.profile.full_clean()
        
        # Test valid bio
        self.profile.bio = "This is a genuine professional biography about my experience."
        self.profile.full_clean()  # Should not raise
    
    def test_github_url_validation(self):
        """Test GitHub URL format validation"""
        # Invalid GitHub URL
        self.profile.github_url = "https://example.com/user"
        with self.assertRaises(ValidationError):
            self.profile.full_clean()
        
        # Valid GitHub URL
        self.profile.github_url = "https://github.com/username"
        self.profile.full_clean()  # Should not raise
    
    def test_linkedin_url_validation(self):
        """Test LinkedIn URL format validation"""
        # Invalid LinkedIn URL
        self.profile.linkedin_url = "https://example.com/profile"
        with self.assertRaises(ValidationError):
            self.profile.full_clean()
        
        # Valid LinkedIn URL
        self.profile.linkedin_url = "https://www.linkedin.com/in/username"
        self.profile.full_clean()  # Should not raise
    
    def test_portfolio_url_validation(self):
        """Test portfolio URL validation (no localhost)"""
        # Localhost URL should fail
        self.profile.portfolio_url = "http://localhost:3000"
        with self.assertRaises(ValidationError):
            self.profile.full_clean()
        
        # Valid portfolio URL
        self.profile.portfolio_url = "https://myportfolio.com"
        self.profile.full_clean()  # Should not raise
    
    def test_profile_completion_calculation(self):
        """Test profile completion percentage calculation"""
        # Empty profile
        self.assertEqual(self.profile.completion_percentage, 0)
        
        # Add bio only (25%)
        self.profile.bio = "Professional biography about my experience in software development."
        self.profile.save()
        self.assertEqual(self.profile.completion_percentage, 25)
        
        # Add GitHub URL (50%)
        self.profile.github_url = "https://github.com/testuser"
        self.profile.save()
        self.assertEqual(self.profile.completion_percentage, 50)
        
        # Add all fields (100%)
        self.profile.linkedin_url = "https://www.linkedin.com/in/testuser"
        self.profile.portfolio_url = "https://testuser.com"
        self.profile.save()
        self.assertEqual(self.profile.completion_percentage, 100)
        self.assertTrue(self.profile.is_complete)
    
    def test_social_links_property(self):
        """Test social_links property returns correct format"""
        self.profile.github_url = "https://github.com/testuser"
        self.profile.linkedin_url = "https://www.linkedin.com/in/testuser"
        self.profile.save()
        
        links = self.profile.social_links
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0], ('GitHub', 'https://github.com/testuser'))
        self.assertEqual(links[1], ('LinkedIn', 'https://www.linkedin.com/in/testuser'))
    
    def test_url_normalization(self):
        """Test URL normalization removes trailing slashes"""
        self.profile.github_url = "https://github.com/testuser/"
        self.profile.linkedin_url = "https://www.linkedin.com/in/testuser/"
        self.profile.portfolio_url = "https://testuser.com/"
        self.profile.save()
        
        self.assertEqual(self.profile.github_url, "https://github.com/testuser")
        self.assertEqual(self.profile.linkedin_url, "https://www.linkedin.com/in/testuser")
        self.assertEqual(self.profile.portfolio_url, "https://testuser.com")


class TechnologyModelTests(TestCase):
    """
    Tests for Technology model functionality.
    """
    
    def setUp(self):
        self.tech = Technology.objects.create(
            name="Django",
            category="backend",
            description="Web framework for Python"
        )
    
    def test_technology_creation(self):
        """Test Technology model creation"""
        self.assertEqual(str(self.tech), "Django")
        self.assertEqual(self.tech.category, "backend")
        self.assertTrue(self.tech.created_at)
    
    def test_technology_unique_name(self):
        """Test that technology names must be unique"""
        with self.assertRaises(Exception):  # IntegrityError
            Technology.objects.create(name="Django", category="backend")


class ProjectModelTests(TestCase):
    """
    Comprehensive tests for Project model validation and business logic.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.tech1 = Technology.objects.create(name="Django", category="backend")
        self.tech2 = Technology.objects.create(name="React", category="frontend")
        
        self.project = Project.objects.create(
            title="Test Project",
            description="This is a detailed test project description with sufficient length.",
            short_description="Short test description with enough characters.",
            owner=self.user,
            status="development",
            priority="high",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=30)
        )
        self.project.technologies.add(self.tech1, self.tech2)
    
    def test_project_creation(self):
        """Test Project model creation with valid data"""
        self.assertEqual(str(self.project), "Test Project")
        self.assertEqual(self.project.owner, self.user)
        self.assertTrue(self.project.is_active)
        self.assertFalse(self.project.is_completed)
        self.assertFalse(self.project.is_overdue)
        self.assertEqual(self.project.progress_percentage, 50)
    
    def test_project_title_validation(self):
        """Test project title validation"""
        # Title too short
        self.project.title = "ab"
        with self.assertRaises(ValidationError):
            self.project.full_clean()
        
        # Valid title
        self.project.title = "Valid Project Title"
        self.project.full_clean()  # Should not raise
    
    def test_project_description_validation(self):
        """Test project description validation"""
        # Short description too short
        self.project.short_description = "short"
        with self.assertRaises(ValidationError):
            self.project.full_clean()
        
        # Full description too short
        self.project.short_description = "Valid short description here"
        self.project.description = "short desc"
        with self.assertRaises(ValidationError):
            self.project.full_clean()
        
        # Valid descriptions
        self.project.short_description = "Valid short description here"
        self.project.description = "This is a valid detailed project description with sufficient length."
        self.project.full_clean()  # Should not raise
    
    def test_project_date_validation(self):
        """Test project date validation"""
        # End date before start date
        self.project.start_date = date.today()
        self.project.end_date = date.today() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.project.full_clean()
        
        # Valid dates
        self.project.start_date = date.today() - timedelta(days=30)
        self.project.end_date = date.today() + timedelta(days=30)
        self.project.full_clean()  # Should not raise
    
    def test_project_status_properties(self):
        """Test project status-related properties"""
        # Test active status
        self.project.status = "development"
        self.assertTrue(self.project.is_active)
        self.assertFalse(self.project.is_completed)
        
        # Test completed status
        self.project.status = "completed"
        self.assertFalse(self.project.is_active)
        self.assertTrue(self.project.is_completed)
        self.assertEqual(self.project.progress_percentage, 100)
    
    def test_project_overdue_calculation(self):
        """Test overdue calculation"""
        # Past end date, not completed
        self.project.end_date = date.today() - timedelta(days=1)
        self.project.status = "development"
        self.assertTrue(self.project.is_overdue)
        
        # Past end date, but completed
        self.project.status = "completed"
        self.assertFalse(self.project.is_overdue)
    
    def test_project_duration_calculation(self):
        """Test project duration calculation"""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        self.project.start_date = start_date
        self.project.end_date = end_date
        
        self.assertEqual(self.project.duration_days, 30)
    
    def test_mark_completed_method(self):
        """Test mark_completed method"""
        self.project.status = "development"
        self.project.end_date = None
        self.project.mark_completed()
        
        self.assertEqual(self.project.status, "completed")
        self.assertEqual(self.project.end_date, date.today())
    
    def test_can_be_edited_by(self):
        """Test permission checking"""
        # Owner can edit
        self.assertTrue(self.project.can_be_edited_by(self.user))
        
        # Other user cannot edit
        other_user = User.objects.create_user(username='other', email='other@test.com')
        self.assertFalse(self.project.can_be_edited_by(other_user))
        
        # Superuser can edit
        superuser = User.objects.create_superuser(username='admin', email='admin@test.com', password='pass')
        self.assertTrue(self.project.can_be_edited_by(superuser))


class WorkSessionModelTests(TestCase):
    """
    Comprehensive tests for WorkSession model validation and business logic.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.project = Project.objects.create(
            title="Test Project",
            description="Test project description with sufficient length.",
            short_description="Short test description here.",
            owner=self.user
        )
        
        self.start_time = timezone.now() - timedelta(hours=2)
        self.end_time = timezone.now() - timedelta(hours=1)
        
        self.session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title="Test work session",
            start_time=self.start_time,
            end_time=self.end_time,
            productivity_rating=4
        )
    
    def test_work_session_creation(self):
        """Test WorkSession model creation"""
        self.assertEqual(str(self.session), f"{self.project.title} - Test work session ({self.session.duration_hours}h)")
        self.assertTrue(self.session.is_completed)
        self.assertFalse(self.session.is_active)
        self.assertAlmostEqual(float(self.session.duration_hours), 1.0, places=1)
    
    def test_duration_calculation(self):
        """Test automatic duration calculation"""
        # Create session with start and end time
        start = timezone.now() - timedelta(hours=3)
        end = timezone.now() - timedelta(hours=1)
        
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title="Duration test",
            start_time=start,
            end_time=end
        )
        
        expected_hours = 2.0
        self.assertAlmostEqual(float(session.duration_hours), expected_hours, places=1)
        self.assertFalse(session.is_active)
    
    def test_active_session_handling(self):
        """Test active session without end time"""
        active_session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title="Active session",
            start_time=timezone.now() - timedelta(minutes=30),
            is_active=True
        )
        
        self.assertTrue(active_session.is_active)
        self.assertFalse(active_session.is_completed)
        self.assertIsNone(active_session.end_time)


class ProjectFormTests(TestCase):
    """
    Tests for ProjectForm validation and behavior.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.tech1 = Technology.objects.create(name="Django", category="backend")
        self.tech2 = Technology.objects.create(name="React", category="frontend")
    
    def test_valid_project_form(self):
        """Test ProjectForm with valid data"""
        form_data = {
            'title': 'Test Project',
            'short_description': 'This is a valid short description for testing.',
            'description': 'This is a detailed project description with sufficient length for validation.',
            'status': 'planning',
            'priority': 'medium',
            'start_date': '2024-01-01',
            'technologies': [self.tech1.id, self.tech2.id],
            'is_public': True,
            'is_featured': False
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_project_form_title_validation(self):
        """Test ProjectForm title validation"""
        form_data = {
            'title': '',  # Empty title
            'short_description': 'Valid short description here.',
            'description': 'Valid detailed description with sufficient length.',
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
    
    def test_project_form_duplicate_title_validation(self):
        """Test duplicate title validation for same user"""
        # Create existing project
        Project.objects.create(
            title='Existing Project',
            description='Description with sufficient length.',
            short_description='Valid short description.',
            owner=self.user
        )
        
        # Try to create another with same title
        form_data = {
            'title': 'Existing Project',
            'short_description': 'Valid short description here.',
            'description': 'Valid detailed description with sufficient length.',
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)


class ProjectViewTests(TestCase):
    """
    Tests for project-related views.
    """
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.project = Project.objects.create(
            title="Test Project",
            description="Test project description with sufficient length.",
            short_description="Short test description here.",
            owner=self.user,
            is_public=True
        )
    
    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        self.assertContains(response, 'testuser')
        self.assertIn('total_projects', response.context)
        self.assertIn('active_projects', response.context)
        self.assertIn('recent_projects', response.context)
    
    def test_dashboard_view_unauthenticated(self):
        """Test dashboard redirects unauthenticated users"""
        response = self.client.get(reverse('projects:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_project_list_view(self):
        """Test project list view"""
        response = self.client.get(reverse('projects:project_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.title)
        self.assertIn('projects', response.context)
    
    def test_project_detail_view(self):
        """Test project detail view"""
        response = self.client.get(reverse('projects:project_detail', kwargs={'pk': self.project.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.title)
        self.assertContains(response, self.project.description)
        self.assertEqual(response.context['project'], self.project)
    
    def test_project_create_view_authenticated(self):
        """Test project creation view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        
        # GET request
        response = self.client.get(reverse('projects:project_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Project')
        
        # POST request with valid data
        post_data = {
            'title': 'New Test Project',
            'short_description': 'This is a valid short description for testing.',
            'description': 'This is a detailed project description with sufficient length.',
            'status': 'planning',
            'priority': 'medium',
            'is_public': True
        }
        
        response = self.client.post(reverse('projects:project_create'), data=post_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        self.assertTrue(Project.objects.filter(title='New Test Project').exists())
    
    def test_project_create_view_unauthenticated(self):
        """Test project creation requires authentication"""
        response = self.client.get(reverse('projects:project_create'))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class IntegrationTests(TestCase):
    """
    End-to-end integration tests for complete workflows.
    """
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.tech = Technology.objects.create(name="Django", category="backend")
    
    def test_complete_project_workflow(self):
        """Test complete project creation and management workflow"""
        self.client.login(username='testuser', password='testpass123')
        
        # 1. Create project
        project_data = {
            'title': 'Integration Test Project',
            'short_description': 'This is an integration test project description.',
            'description': 'This is a detailed integration test project description with sufficient length.',
            'status': 'planning',
            'priority': 'high',
            'technologies': [self.tech.id],
            'is_public': True
        }
        
        response = self.client.post(reverse('projects:project_create'), data=project_data)
        self.assertEqual(response.status_code, 302)
        
        project = Project.objects.get(title='Integration Test Project')
        self.assertEqual(project.owner, self.user)
        
        # 2. Start work session
        response = self.client.post(reverse('projects:start_session', kwargs={'project_id': project.pk}))
        self.assertEqual(response.status_code, 302)
        
        session = WorkSession.objects.filter(project=project, is_active=True).first()
        self.assertIsNotNone(session)
        
        # 3. Stop work session
        response = self.client.post(reverse('projects:stop_session', kwargs={'session_id': session.pk}))
        self.assertEqual(response.status_code, 302)
        
        session.refresh_from_db()
                # Manually set some duration for testing
        session.duration_hours = 0.1
        session.save()
        self.assertFalse(session.is_active)
        
        # 4. Check dashboard reflects changes
        response = self.client.get(reverse('projects:dashboard'))
        self.assertEqual(response.status_code, 200)
        # Check that dashboard loaded successfully and project exists
        self.assertEqual(response.context["total_projects"], 1)
