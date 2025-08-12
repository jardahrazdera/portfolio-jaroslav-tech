import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import datetime, timedelta, date
from decimal import Decimal
from projects.models import (
    Project, Technology, WorkSession, ProjectImage, UserProfile
)


@pytest.mark.django_db
class TestDashboardView(TestCase):
    """Comprehensive tests for dashboard view"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user,
            status='development'
        )

    def test_dashboard_requires_login(self):
        """Test dashboard requires authentication"""
        response = self.client.get(reverse('projects:dashboard'))
        self.assertRedirects(response, f"/accounts/login/?next={reverse('projects:dashboard')}")

    def test_dashboard_authenticated_user(self):
        """Test dashboard view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'Test Project')

    def test_dashboard_context_data(self):
        """Test dashboard context contains required data"""
        # Create additional test data
        WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Test Session',
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1),
            duration_hours=Decimal('1.00')
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:dashboard'))
        
        context = response.context
        self.assertEqual(context['total_projects'], 1)
        self.assertEqual(context['active_projects'], 1)
        self.assertEqual(context['completed_projects'], 0)
        self.assertEqual(context['total_hours'], Decimal('1.00'))
        self.assertIsNotNone(context['recent_sessions'])
        self.assertIsNotNone(context['recent_projects'])

    def test_dashboard_with_active_session(self):
        """Test dashboard displays active work session"""
        active_session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now(),
            is_active=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:dashboard'))
        
        self.assertEqual(response.context['active_session'], active_session)
        self.assertContains(response, 'Active Session')

    def test_dashboard_error_handling(self):
        """Test dashboard handles database errors gracefully"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test with user that has no projects
        empty_user = User.objects.create_user(username='empty', password='pass')
        self.client.login(username='empty', password='pass')
        response = self.client.get(reverse('projects:dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_projects'], 0)


@pytest.mark.django_db
class TestProjectListView(TestCase):
    """Comprehensive tests for project list view"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.technology = Technology.objects.create(
            name='Django',
            category='backend'
        )
        
        # Create public and private projects
        self.public_project = Project.objects.create(
            title='Public Project',
            description='Long enough description for the public project',
            short_description='Public short description',
            owner=self.user,
            is_public=True,
            is_featured=True
        )
        self.private_project = Project.objects.create(
            title='Private Project',
            description='Long enough description for the private project',
            short_description='Private short description',
            owner=self.user,
            is_public=False
        )
        
        self.public_project.technologies.add(self.technology)

    def test_project_list_anonymous_user(self):
        """Test project list for anonymous users shows only public projects"""
        response = self.client.get(reverse('projects:project_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Project')
        self.assertNotContains(response, 'Private Project')

    def test_project_list_authenticated_user(self):
        """Test project list for authenticated users shows own projects plus public featured"""
        # Create another user with public featured project
        other_user = User.objects.create_user(username='other', password='pass')
        other_public_project = Project.objects.create(
            title='Other Public Project',
            description='Long enough description for other public project',
            short_description='Other public short description',
            owner=other_user,
            is_public=True,
            is_featured=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:project_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Project')
        self.assertContains(response, 'Private Project')  # Own project
        self.assertContains(response, 'Other Public Project')  # Featured public

    def test_project_list_technology_filter(self):
        """Test project list technology filter"""
        response = self.client.get(reverse('projects:project_list'), {'technology': 'Django'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Project')
        # Private project doesn't have Django technology, so shouldn't appear

    def test_project_list_status_filter(self):
        """Test project list status filter"""
        self.public_project.status = 'completed'
        self.public_project.save()
        
        response = self.client.get(reverse('projects:project_list'), {'status': 'completed'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Project')

    def test_project_list_search_functionality(self):
        """Test project list search functionality"""
        response = self.client.get(reverse('projects:project_list'), {'search': 'Public'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Project')
        # Should not contain projects that don't match search

    def test_project_list_invalid_filter_handling(self):
        """Test project list handles invalid filters gracefully"""
        # Test invalid status
        response = self.client.get(reverse('projects:project_list'), {'status': 'invalid_status'})
        self.assertEqual(response.status_code, 200)
        
        # Test overly long search query
        long_query = 'x' * 200
        response = self.client.get(reverse('projects:project_list'), {'search': long_query})
        self.assertEqual(response.status_code, 200)

    def test_project_list_pagination(self):
        """Test project list pagination"""
        # Create many projects to test pagination
        for i in range(15):
            Project.objects.create(
                title=f'Test Project {i}',
                description=f'Long enough description for test project {i}',
                short_description=f'Short description {i}',
                owner=self.user,
                is_public=True
            )
        
        response = self.client.get(reverse('projects:project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])


@pytest.mark.django_db
class TestProjectDetailView(TestCase):
    """Comprehensive tests for project detail view"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        self.public_project = Project.objects.create(
            title='Public Project',
            description='Long enough description for the public project',
            short_description='Public short description',
            owner=self.user,
            is_public=True
        )
        self.private_project = Project.objects.create(
            title='Private Project',
            description='Long enough description for the private project',
            short_description='Private short description',
            owner=self.user,
            is_public=False
        )

    def test_public_project_detail_anonymous(self):
        """Test anonymous user can view public project detail"""
        response = self.client.get(
            reverse('projects:project_detail', kwargs={'pk': self.public_project.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Project')
        self.assertFalse(response.context['can_edit'])

    def test_private_project_detail_anonymous_403(self):
        """Test anonymous user cannot view private project"""
        response = self.client.get(
            reverse('projects:project_detail', kwargs={'pk': self.private_project.pk})
        )
        
        self.assertEqual(response.status_code, 404)

    def test_project_detail_owner_can_edit(self):
        """Test project owner can edit project"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('projects:project_detail', kwargs={'pk': self.public_project.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_edit'])

    def test_project_detail_other_user_cannot_edit_private(self):
        """Test other user cannot view private project"""
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.get(
            reverse('projects:project_detail', kwargs={'pk': self.private_project.pk})
        )
        
        self.assertEqual(response.status_code, 404)

    def test_project_detail_other_user_can_view_public(self):
        """Test other user can view public project but not edit"""
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.get(
            reverse('projects:project_detail', kwargs={'pk': self.public_project.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['can_edit'])

    def test_project_detail_context_data(self):
        """Test project detail context contains required data"""
        # Create work sessions and images
        WorkSession.objects.create(
            project=self.public_project,
            user=self.user,
            title='Test Session',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            duration_hours=Decimal('1.00')
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('projects:project_detail', kwargs={'pk': self.public_project.pk})
        )
        
        self.assertIsNotNone(response.context['work_sessions'])
        self.assertIsNotNone(response.context['images'])

    def test_project_detail_active_session_context(self):
        """Test project detail shows active session for owner"""
        active_session = WorkSession.objects.create(
            project=self.public_project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now(),
            is_active=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('projects:project_detail', kwargs={'pk': self.public_project.pk})
        )
        
        self.assertEqual(response.context['active_session'], active_session)


@pytest.mark.django_db
class TestProjectCreateView(TestCase):
    """Comprehensive tests for project create view"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.technology = Technology.objects.create(
            name='Django',
            category='backend'
        )

    def test_project_create_requires_login(self):
        """Test project create requires authentication"""
        response = self.client.get(reverse('projects:project_create'))
        self.assertRedirects(response, f"/accounts/login/?next={reverse('projects:project_create')}")

    def test_project_create_get_authenticated(self):
        """Test project create GET request for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:project_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Project')
        self.assertContains(response, 'Create Project')

    def test_project_create_post_valid_data(self):
        """Test project create with valid POST data"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'New Test Project',
            'short_description': 'Short description for new project',
            'description': 'Long enough description for the new test project',
            'status': 'planning',
            'priority': 'medium',
            'technologies': [self.technology.id],
            'is_public': True,
            'is_featured': False
        }
        
        response = self.client.post(reverse('projects:project_create'), data)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify project was created
        project = Project.objects.get(title='New Test Project')
        self.assertEqual(project.owner, self.user)
        self.assertIn(self.technology, project.technologies.all())

    def test_project_create_post_invalid_data(self):
        """Test project create with invalid POST data"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'AB',  # Too short
            'short_description': 'Short',  # Too short
            'description': 'Short desc',  # Too short
            'status': 'planning',
            'priority': 'medium'
        }
        
        response = self.client.post(reverse('projects:project_create'), data)
        
        self.assertEqual(response.status_code, 200)  # Form invalid, stay on page
        self.assertFormError(response, 'form', 'title', 'Project title must be at least 3 characters long.')

    def test_project_create_duplicate_title_validation(self):
        """Test project create prevents duplicate titles for same user"""
        # Create existing project
        Project.objects.create(
            title='Duplicate Title',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Duplicate Title',
            'short_description': 'Different short description',
            'description': 'Different long enough description for the project',
            'status': 'planning',
            'priority': 'medium'
        }
        
        response = self.client.post(reverse('projects:project_create'), data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'title', 'You already have a project with this title.')

    def test_project_create_success_message(self):
        """Test project create shows success message"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Success Project',
            'short_description': 'Short description for success project',
            'description': 'Long enough description for the success project',
            'status': 'planning',
            'priority': 'medium'
        }
        
        response = self.client.post(reverse('projects:project_create'), data, follow=True)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('created successfully' in str(m) for m in messages))


@pytest.mark.django_db
class TestProjectUpdateView(TestCase):
    """Comprehensive tests for project update view"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        self.project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )

    def test_project_update_requires_login(self):
        """Test project update requires authentication"""
        url = reverse('projects:project_update', kwargs={'pk': self.project.pk})
        response = self.client.get(url)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_project_update_requires_ownership(self):
        """Test project update requires ownership"""
        self.client.login(username='otheruser', password='otherpass123')
        
        url = reverse('projects:project_update', kwargs={'pk': self.project.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_project_update_get_owner(self):
        """Test project update GET request for owner"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('projects:project_update', kwargs={'pk': self.project.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.title)

    def test_project_update_post_valid_data(self):
        """Test project update with valid POST data"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Updated Project Title',
            'short_description': 'Updated short description',
            'description': 'Updated long enough description for the project',
            'status': 'development',
            'priority': 'high'
        }
        
        url = reverse('projects:project_update', kwargs={'pk': self.project.pk})
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify project was updated
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, 'Updated Project Title')
        self.assertEqual(self.project.status, 'development')

    def test_project_update_success_message(self):
        """Test project update shows success message"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'title': 'Updated Project',
            'short_description': 'Updated short description',
            'description': 'Updated long enough description for the project',
            'status': 'development',
            'priority': 'medium'
        }
        
        url = reverse('projects:project_update', kwargs={'pk': self.project.pk})
        response = self.client.post(url, data, follow=True)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('updated successfully' in str(m) for m in messages))


@pytest.mark.django_db
class TestProjectDeleteView(TestCase):
    """Comprehensive tests for project delete view"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        self.project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )

    def test_project_delete_requires_login(self):
        """Test project delete requires authentication"""
        url = reverse('projects:project_delete', kwargs={'pk': self.project.pk})
        response = self.client.get(url)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_project_delete_requires_ownership(self):
        """Test project delete requires ownership"""
        self.client.login(username='otheruser', password='otherpass123')
        
        url = reverse('projects:project_delete', kwargs={'pk': self.project.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_project_delete_get_confirmation(self):
        """Test project delete GET shows confirmation page"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('projects:project_delete', kwargs={'pk': self.project.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Are you sure')
        self.assertContains(response, self.project.title)

    def test_project_delete_post_confirmation(self):
        """Test project delete POST actually deletes project"""
        self.client.login(username='testuser', password='testpass123')
        project_id = self.project.pk
        
        url = reverse('projects:project_delete', kwargs={'pk': self.project.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify project was deleted
        self.assertFalse(Project.objects.filter(pk=project_id).exists())

    def test_project_delete_success_message(self):
        """Test project delete shows success message"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('projects:project_delete', kwargs={'pk': self.project.pk})
        response = self.client.post(url, follow=True)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('deleted successfully' in str(m) for m in messages))


@pytest.mark.django_db
class TestUserProfileUpdateView(TestCase):
    """Comprehensive tests for user profile update view"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_profile_update_requires_login(self):
        """Test profile update requires authentication"""
        url = reverse('projects:profile_update')
        response = self.client.get(url)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_profile_update_creates_profile_if_not_exists(self):
        """Test profile update creates profile if it doesn't exist"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('projects:profile_update'))
        
        self.assertEqual(response.status_code, 200)
        # Profile should be created automatically
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_profile_update_get_existing_profile(self):
        """Test profile update GET with existing profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            bio='Existing bio for testing purposes',
            github_url='https://github.com/testuser'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('projects:profile_update'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Existing bio for testing purposes')

    def test_profile_update_post_valid_data(self):
        """Test profile update with valid POST data"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'bio': 'Updated biography for testing purposes and validation',
            'github_url': 'https://github.com/updateduser',
            'linkedin_url': 'https://linkedin.com/in/updateduser',
            'portfolio_url': 'https://updatedportfolio.com'
        }
        
        response = self.client.post(reverse('projects:profile_update'), data)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify profile was updated
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.bio, 'Updated biography for testing purposes and validation')
        self.assertEqual(profile.github_url, 'https://github.com/updateduser')

    def test_profile_update_success_message(self):
        """Test profile update shows success message"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'bio': 'Success biography for testing purposes and validation',
            'github_url': 'https://github.com/successuser'
        }
        
        response = self.client.post(reverse('projects:profile_update'), data, follow=True)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('updated successfully' in str(m) for m in messages))


@pytest.mark.django_db
class TestWorkSessionViews(TestCase):
    """Comprehensive tests for work session views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        self.project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        self.session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Test Session',
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1),
            duration_hours=Decimal('1.00')
        )

    def test_start_work_session_requires_login(self):
        """Test start work session requires authentication"""
        url = reverse('projects:start_session', kwargs={'project_id': self.project.pk})
        response = self.client.get(url)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_start_work_session_requires_ownership(self):
        """Test start work session requires project ownership"""
        self.client.login(username='otheruser', password='otherpass123')
        
        url = reverse('projects:start_session', kwargs={'project_id': self.project.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_start_work_session_success(self):
        """Test successful work session start"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('projects:start_session', kwargs={'project_id': self.project.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify active session was created
        active_session = WorkSession.objects.filter(
            user=self.user, 
            project=self.project, 
            is_active=True
        ).first()
        self.assertIsNotNone(active_session)

    def test_start_work_session_prevents_multiple_active(self):
        """Test start work session prevents multiple active sessions"""
        # Create existing active session
        existing_active = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Existing Active',
            start_time=timezone.now(),
            is_active=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('projects:start_session', kwargs={'project_id': self.project.pk})
        response = self.client.get(url, follow=True)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('already have an active work session' in str(m) for m in messages))

    def test_stop_work_session_requires_login(self):
        """Test stop work session requires authentication"""
        active_session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now(),
            is_active=True
        )
        
        url = reverse('projects:stop_session', kwargs={'session_id': active_session.pk})
        response = self.client.get(url)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_stop_work_session_success(self):
        """Test successful work session stop"""
        active_session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now() - timedelta(hours=1),
            is_active=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('projects:stop_session', kwargs={'session_id': active_session.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify session was stopped
        active_session.refresh_from_db()
        self.assertFalse(active_session.is_active)
        self.assertIsNotNone(active_session.end_time)

    def test_stop_work_session_requires_ownership(self):
        """Test stop work session requires session ownership"""
        active_session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now(),
            is_active=True
        )
        
        self.client.login(username='otheruser', password='otherpass123')
        
        url = reverse('projects:stop_session', kwargs={'session_id': active_session.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_work_session_update_requires_ownership(self):
        """Test work session update requires ownership"""
        self.client.login(username='otheruser', password='otherpass123')
        
        url = reverse('projects:session_update', kwargs={'pk': self.session.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_work_session_update_success(self):
        """Test successful work session update"""
        self.client.login(username='testuser', password='testpass123')
        
        data = {
            'project': self.project.pk,
            'title': 'Updated Session Title',
            'description': 'Updated session description',
            'start_time': (timezone.now() - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'end_time': (timezone.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'productivity_rating': 4,
            'notes': 'Updated notes'
        }
        
        url = reverse('projects:session_update', kwargs={'pk': self.session.pk})
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify session was updated
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, 'Updated Session Title')

    def test_work_session_delete_requires_ownership(self):
        """Test work session delete requires ownership"""
        self.client.login(username='otheruser', password='otherpass123')
        
        url = reverse('projects:session_delete', kwargs={'pk': self.session.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_work_session_delete_success(self):
        """Test successful work session delete"""
        self.client.login(username='testuser', password='testpass123')
        session_id = self.session.pk
        
        url = reverse('projects:session_delete', kwargs={'pk': self.session.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify session was deleted
        self.assertFalse(WorkSession.objects.filter(pk=session_id).exists())


@pytest.mark.django_db
class TestProjectImageViews(TestCase):
    """Comprehensive tests for project image views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        
        self.project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )

    def test_upload_project_image_requires_login(self):
        """Test upload project image requires authentication"""
        url = reverse('projects:upload_image', kwargs={'project_id': self.project.pk})
        response = self.client.get(url)
        self.assertRedirects(response, f"/accounts/login/?next={url}")

    def test_upload_project_image_requires_ownership(self):
        """Test upload project image requires project ownership"""
        self.client.login(username='otheruser', password='otherpass123')
        
        url = reverse('projects:upload_image', kwargs={'project_id': self.project.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_upload_project_image_get_form(self):
        """Test upload project image GET shows form"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('projects:upload_image', kwargs={'project_id': self.project.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Upload Image for {self.project.title}')

    def test_upload_project_image_post_valid(self):
        """Test successful project image upload"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create a simple test image
        test_image = SimpleUploadedFile(
            "test.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        
        data = {
            'title': 'Test Image',
            'description': 'Test image description',
            'image': test_image,
            'order': 1,
            'is_featured': False
        }
        
        url = reverse('projects:upload_image', kwargs={'project_id': self.project.pk})
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify image was created
        image = ProjectImage.objects.filter(project=self.project, title='Test Image').first()
        self.assertIsNotNone(image)

    def test_delete_project_image_requires_ownership(self):
        """Test delete project image requires project ownership"""
        image = ProjectImage.objects.create(
            project=self.project,
            title='Test Image',
            order=1
        )
        
        self.client.login(username='otheruser', password='otherpass123')
        
        url = reverse('projects:delete_image', kwargs={
            'project_id': self.project.pk,
            'image_id': image.pk
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_delete_project_image_success(self):
        """Test successful project image delete"""
        image = ProjectImage.objects.create(
            project=self.project,
            title='Test Image',
            order=1
        )
        image_id = image.pk
        
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('projects:delete_image', kwargs={
            'project_id': self.project.pk,
            'image_id': image.pk
        })
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect on success
        
        # Verify image was deleted
        self.assertFalse(ProjectImage.objects.filter(pk=image_id).exists())


@pytest.mark.django_db
class TestErrorHandling(TestCase):
    """Comprehensive tests for error handling in views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_invalid_project_id_handling(self):
        """Test handling of invalid project IDs"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test with non-existent project ID
        response = self.client.get(reverse('projects:project_detail', kwargs={'pk': 99999}))
        self.assertEqual(response.status_code, 404)
        
        # Test with invalid format project ID in start session
        url = reverse('projects:start_session', kwargs={'project_id': 'invalid'})
        response = self.client.get(url, follow=True)
        
        # Should redirect with error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid project identifier' in str(m) for m in messages))

    def test_permission_denied_handling(self):
        """Test permission denied handling"""
        other_user = User.objects.create_user(username='other', password='pass')
        project = Project.objects.create(
            title='Other Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=other_user
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Try to update other user's project
        url = reverse('projects:project_update', kwargs={'pk': project.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_database_error_graceful_handling(self):
        """Test graceful handling of database errors"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test dashboard with potential database issues
        response = self.client.get(reverse('projects:dashboard'))
        
        # Should still render page even if some queries fail
        self.assertEqual(response.status_code, 200)
