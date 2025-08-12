import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta, date
from projects.models import (
    Project, Technology, WorkSession, ProjectImage, UserProfile
)
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
class TestUserProfileModel(TestCase):
    """Comprehensive tests for UserProfile model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_profile_creation(self):
        """Test basic profile creation"""
        profile = UserProfile.objects.create(
            user=self.user,
            bio='Software engineer passionate about web development',
            github_url='https://github.com/testuser',
            linkedin_url='https://linkedin.com/in/testuser',
            portfolio_url='https://testuser.com'
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.bio, 'Software engineer passionate about web development')
        self.assertTrue(profile.github_url.startswith('https://github.com/'))
        self.assertTrue(profile.linkedin_url.startswith('https://linkedin.com/'))
        self.assertIsInstance(profile.created_at, datetime)
        self.assertIsInstance(profile.updated_at, datetime)

    def test_profile_str_method_with_full_name(self):
        """Test string representation with full name"""
        profile = UserProfile.objects.create(user=self.user)
        expected = "Test User's Profile"
        self.assertEqual(str(profile), expected)

    def test_profile_str_method_without_full_name(self):
        """Test string representation without full name"""
        user = User.objects.create_user(username='noname', password='pass')
        profile = UserProfile.objects.create(user=user)
        expected = "noname's Profile"
        self.assertEqual(str(profile), expected)

    def test_bio_length_validation(self):
        """Test bio minimum length validation"""
        profile = UserProfile(user=self.user, bio='short')
        with self.assertRaises(ValidationError) as context:
            profile.full_clean()
        self.assertIn('Biography must be at least 10 characters long', str(context.exception))

    def test_bio_suspicious_content_validation(self):
        """Test bio suspicious content validation"""
        profile = UserProfile(user=self.user, bio='This is just a test biography')
        with self.assertRaises(ValidationError) as context:
            profile.full_clean()
        self.assertIn('Please write a genuine biography', str(context.exception))

    def test_github_url_validation_success(self):
        """Test valid GitHub URL validation"""
        profile = UserProfile(
            user=self.user,
            bio='Valid biography for testing purposes',
            github_url='https://github.com/validuser'
        )
        try:
            profile.full_clean()
        except ValidationError:
            self.fail('Valid GitHub URL should not raise ValidationError')

    def test_github_url_validation_failure(self):
        """Test invalid GitHub URL validation"""
        profile = UserProfile(
            user=self.user,
            bio='Valid biography for testing purposes',
            github_url='https://invalid-site.com/user'
        )
        with self.assertRaises(ValidationError) as context:
            profile.full_clean()
        self.assertIn('Please enter a valid GitHub profile URL', str(context.exception))

    def test_linkedin_url_validation_success(self):
        """Test valid LinkedIn URL validation"""
        profile = UserProfile(
            user=self.user,
            bio='Valid biography for testing purposes',
            linkedin_url='https://www.linkedin.com/in/validuser'
        )
        try:
            profile.full_clean()
        except ValidationError:
            self.fail('Valid LinkedIn URL should not raise ValidationError')

    def test_linkedin_url_validation_failure(self):
        """Test invalid LinkedIn URL validation"""
        profile = UserProfile(
            user=self.user,
            bio='Valid biography for testing purposes',
            linkedin_url='https://invalid-site.com/in/user'
        )
        with self.assertRaises(ValidationError) as context:
            profile.full_clean()
        self.assertIn('Please enter a valid LinkedIn profile URL', str(context.exception))

    def test_portfolio_url_localhost_validation(self):
        """Test portfolio URL localhost validation"""
        profile = UserProfile(
            user=self.user,
            bio='Valid biography for testing purposes',
            portfolio_url='http://localhost:3000'
        )
        with self.assertRaises(ValidationError) as context:
            profile.full_clean()
        self.assertIn('Portfolio URL cannot be a local development server', str(context.exception))

    def test_url_normalization_on_save(self):
        """Test URL normalization removes trailing slashes"""
        profile = UserProfile.objects.create(
            user=self.user,
            bio='Valid biography for testing purposes',
            github_url='https://github.com/testuser/',
            linkedin_url='https://linkedin.com/in/testuser/',
            portfolio_url='https://testuser.com/'
        )
        
        self.assertEqual(profile.github_url, 'https://github.com/testuser')
        self.assertEqual(profile.linkedin_url, 'https://linkedin.com/in/testuser')
        self.assertEqual(profile.portfolio_url, 'https://testuser.com')

    def test_is_complete_property_true(self):
        """Test is_complete property returns True when complete"""
        profile = UserProfile.objects.create(
            user=self.user,
            bio='Valid biography for testing purposes',
            github_url='https://github.com/testuser'
        )
        self.assertTrue(profile.is_complete)

    def test_is_complete_property_false(self):
        """Test is_complete property returns False when incomplete"""
        profile = UserProfile.objects.create(user=self.user)
        self.assertFalse(profile.is_complete)

    def test_completion_percentage_property(self):
        """Test completion percentage calculation"""
        profile = UserProfile.objects.create(
            user=self.user,
            bio='Valid biography for testing purposes',
            github_url='https://github.com/testuser'
        )
        # 2 out of 4 fields filled = 50%
        self.assertEqual(profile.completion_percentage, 50)

    def test_social_links_property(self):
        """Test social links property returns correct links"""
        profile = UserProfile.objects.create(
            user=self.user,
            bio='Valid biography for testing purposes',
            github_url='https://github.com/testuser',
            linkedin_url='https://linkedin.com/in/testuser'
        )
        
        links = profile.social_links
        self.assertEqual(len(links), 2)
        self.assertIn(('GitHub', 'https://github.com/testuser'), links)
        self.assertIn(('LinkedIn', 'https://linkedin.com/in/testuser'), links)

    def test_display_name_property_with_full_name(self):
        """Test display name with full name"""
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.display_name, 'Test User')

    def test_display_name_property_without_full_name(self):
        """Test display name without full name"""
        user = User.objects.create_user(username='noname', password='pass')
        profile = UserProfile.objects.create(user=user)
        self.assertEqual(profile.display_name, 'noname')

    def test_get_projects_count(self):
        """Test get projects count method"""
        profile = UserProfile.objects.create(user=self.user)
        
        # Create some projects
        Project.objects.create(
            title='Test Project 1',
            description='Test description for project 1',
            short_description='Short desc 1',
            owner=self.user
        )
        Project.objects.create(
            title='Test Project 2',
            description='Test description for project 2',
            short_description='Short desc 2',
            owner=self.user
        )
        
        self.assertEqual(profile.get_projects_count(), 2)

    def test_get_public_projects_count(self):
        """Test get public projects count method"""
        profile = UserProfile.objects.create(user=self.user)
        
        # Create public and private projects
        Project.objects.create(
            title='Public Project',
            description='Test description for public project',
            short_description='Short desc public',
            owner=self.user,
            is_public=True
        )
        Project.objects.create(
            title='Private Project',
            description='Test description for private project',
            short_description='Short desc private',
            owner=self.user,
            is_public=False
        )
        
        self.assertEqual(profile.get_public_projects_count(), 1)

    def test_get_total_work_hours(self):
        """Test get total work hours method"""
        profile = UserProfile.objects.create(user=self.user)
        project = Project.objects.create(
            title='Test Project',
            description='Test description',
            short_description='Short desc',
            owner=self.user
        )
        
        # Create work sessions
        WorkSession.objects.create(
            project=project,
            user=self.user,
            title='Session 1',
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1),
            duration_hours=Decimal('1.00')
        )
        WorkSession.objects.create(
            project=project,
            user=self.user,
            title='Session 2',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            duration_hours=Decimal('1.50')
        )
        
        self.assertEqual(profile.get_total_work_hours(), Decimal('2.50'))

    def test_get_or_create_for_user(self):
        """Test get or create for user class method"""
        # First call should create
        profile1, created1 = UserProfile.get_or_create_for_user(self.user)
        self.assertTrue(created1)
        self.assertEqual(profile1.user, self.user)
        
        # Second call should retrieve existing
        profile2, created2 = UserProfile.get_or_create_for_user(self.user)
        self.assertFalse(created2)
        self.assertEqual(profile1, profile2)


@pytest.mark.django_db
class TestTechnologyModel(TestCase):
    """Comprehensive tests for Technology model"""

    def test_technology_creation(self):
        """Test basic technology creation"""
        tech = Technology.objects.create(
            name='Django',
            category='backend',
            description='Python web framework',
            icon_url='https://example.com/django-icon.png',
            official_url='https://djangoproject.com'
        )
        
        self.assertEqual(tech.name, 'Django')
        self.assertEqual(tech.category, 'backend')
        self.assertEqual(tech.description, 'Python web framework')
        self.assertTrue(tech.icon_url.startswith('https://'))
        self.assertTrue(tech.official_url.startswith('https://'))
        self.assertIsInstance(tech.created_at, datetime)

    def test_technology_str_method(self):
        """Test technology string representation"""
        tech = Technology.objects.create(name='React')
        self.assertEqual(str(tech), 'React')

    def test_technology_unique_name_constraint(self):
        """Test technology name uniqueness constraint"""
        Technology.objects.create(name='Django')
        
        with self.assertRaises(IntegrityError):
            Technology.objects.create(name='Django')

    def test_technology_category_choices(self):
        """Test technology category choices validation"""
        valid_categories = ['frontend', 'backend', 'database', 'devops', 'mobile', 'other']
        
        for category in valid_categories:
            tech = Technology.objects.create(
                name=f'Tech-{category}',
                category=category
            )
            self.assertEqual(tech.category, category)

    def test_technology_default_category(self):
        """Test technology default category"""
        tech = Technology.objects.create(name='TestTech')
        self.assertEqual(tech.category, 'other')

    def test_technology_ordering(self):
        """Test technology model ordering"""
        tech_a = Technology.objects.create(name='Angular')
        tech_b = Technology.objects.create(name='Bootstrap')
        tech_z = Technology.objects.create(name='Zend')
        
        technologies = list(Technology.objects.all())
        self.assertEqual(technologies[0], tech_a)
        self.assertEqual(technologies[1], tech_b)
        self.assertEqual(technologies[2], tech_z)


@pytest.mark.django_db
class TestProjectModel(TestCase):
    """Comprehensive tests for Project model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.technology = Technology.objects.create(
            name='Django',
            category='backend'
        )

    def test_project_creation(self):
        """Test basic project creation"""
        project = Project.objects.create(
            title='Test Project',
            description='This is a test project description that meets minimum length requirements',
            short_description='Short test description',
            owner=self.user,
            status='planning',
            priority='medium',
            start_date=date.today(),
            github_url='https://github.com/user/repo',
            live_url='https://example.com',
            is_featured=True,
            is_public=True
        )
        
        self.assertEqual(project.title, 'Test Project')
        self.assertEqual(project.owner, self.user)
        self.assertEqual(project.status, 'planning')
        self.assertEqual(project.priority, 'medium')
        self.assertTrue(project.is_featured)
        self.assertTrue(project.is_public)
        self.assertIsInstance(project.created_at, datetime)
        self.assertIsInstance(project.updated_at, datetime)

    def test_project_str_method(self):
        """Test project string representation"""
        project = Project.objects.create(
            title='My Awesome Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        self.assertEqual(str(project), 'My Awesome Project')

    def test_project_default_values(self):
        """Test project default field values"""
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        self.assertEqual(project.status, 'planning')
        self.assertEqual(project.priority, 'medium')
        self.assertFalse(project.is_featured)
        self.assertTrue(project.is_public)

    def test_project_title_validation_min_length(self):
        """Test project title minimum length validation"""
        project = Project(
            title='AB',  # Too short
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            project.full_clean()
        self.assertIn('Project title must be at least 3 characters long', str(context.exception))

    def test_project_short_description_validation(self):
        """Test project short description validation"""
        project = Project(
            title='Valid Title',
            description='Long enough description for the project',
            short_description='Short',  # Too short
            owner=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            project.full_clean()
        self.assertIn('Short description must be at least 10 characters long', str(context.exception))

    def test_project_description_validation(self):
        """Test project description validation"""
        project = Project(
            title='Valid Title',
            description='Short desc',  # Too short
            short_description='Valid short description',
            owner=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            project.full_clean()
        self.assertIn('Description must be at least 20 characters long', str(context.exception))

    def test_project_date_validation(self):
        """Test project start/end date validation"""
        project = Project(
            title='Valid Title',
            description='Long enough description for the project',
            short_description='Valid short description',
            owner=self.user,
            start_date=date.today(),
            end_date=date.today() - timedelta(days=1)  # End before start
        )
        
        with self.assertRaises(ValidationError) as context:
            project.full_clean()
        self.assertIn('End date cannot be before start date', str(context.exception))

    def test_project_technologies_relationship(self):
        """Test project-technology many-to-many relationship"""
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        project.technologies.add(self.technology)
        self.assertIn(self.technology, project.technologies.all())
        self.assertIn(project, self.technology.projects.all())

    def test_total_hours_worked_property(self):
        """Test total hours worked property"""
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        # Create work sessions
        WorkSession.objects.create(
            project=project,
            user=self.user,
            title='Session 1',
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1),
            duration_hours=Decimal('1.00')
        )
        WorkSession.objects.create(
            project=project,
            user=self.user,
            title='Session 2',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            duration_hours=Decimal('2.50')
        )
        
        self.assertEqual(project.total_hours_worked, Decimal('3.50'))

    def test_is_completed_property(self):
        """Test is_completed property"""
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user,
            status='completed'
        )
        
        self.assertTrue(project.is_completed)
        
        project.status = 'development'
        project.save()
        
        self.assertFalse(project.is_completed)

    def test_is_active_property(self):
        """Test is_active property"""
        active_statuses = ['planning', 'development', 'testing']
        inactive_statuses = ['completed', 'archived']
        
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        for status in active_statuses:
            project.status = status
            project.save()
            self.assertTrue(project.is_active, f'Status {status} should be active')
        
        for status in inactive_statuses:
            project.status = status
            project.save()
            self.assertFalse(project.is_active, f'Status {status} should not be active')

    def test_is_overdue_property(self):
        """Test is_overdue property"""
        # Project with past end date and not completed
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user,
            end_date=date.today() - timedelta(days=1),
            status='development'
        )
        self.assertTrue(project.is_overdue)
        
        # Project with past end date but completed
        project.status = 'completed'
        project.save()
        self.assertFalse(project.is_overdue)
        
        # Project with no end date
        project.end_date = None
        project.save()
        self.assertFalse(project.is_overdue)

    def test_duration_days_property(self):
        """Test duration_days property"""
        start_date = date.today() - timedelta(days=10)
        end_date = date.today() - timedelta(days=5)
        
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user,
            start_date=start_date,
            end_date=end_date
        )
        
        self.assertEqual(project.duration_days, 5)
        
        # Test with no start date
        project.start_date = None
        project.save()
        self.assertIsNone(project.duration_days)

    def test_progress_percentage_property(self):
        """Test progress_percentage property"""
        expected_progress = {
            'planning': 10,
            'development': 50,
            'testing': 85,
            'completed': 100,
            'archived': 100,
        }
        
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        for status, expected in expected_progress.items():
            project.status = status
            project.save()
            self.assertEqual(project.progress_percentage, expected)

    def test_can_be_edited_by_method(self):
        """Test can_be_edited_by method"""
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        # Owner can edit
        self.assertTrue(project.can_be_edited_by(self.user))
        
        # Other user cannot edit
        other_user = User.objects.create_user(username='other', password='pass')
        self.assertFalse(project.can_be_edited_by(other_user))
        
        # Superuser can edit
        superuser = User.objects.create_superuser(username='admin', password='pass')
        self.assertTrue(project.can_be_edited_by(superuser))

    def test_get_active_session_method(self):
        """Test get_active_session method"""
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )
        
        # No active session initially
        self.assertIsNone(project.get_active_session())
        
        # Create active session
        active_session = WorkSession.objects.create(
            project=project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now(),
            is_active=True
        )
        
        self.assertEqual(project.get_active_session(), active_session)

    def test_mark_completed_method(self):
        """Test mark_completed method"""
        project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user,
            status='development'
        )
        
        project.mark_completed()
        project.refresh_from_db()
        
        self.assertEqual(project.status, 'completed')
        self.assertEqual(project.end_date, date.today())

    def test_get_user_stats_class_method(self):
        """Test get_user_stats class method"""
        # Create various projects
        Project.objects.create(
            title='Planning Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user,
            status='planning',
            is_featured=True,
            is_public=True
        )
        Project.objects.create(
            title='Completed Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user,
            status='completed',
            is_featured=False,
            is_public=False
        )
        
        stats = Project.get_user_stats(self.user)
        
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['featured'], 1)
        self.assertEqual(stats['public'], 1)
        self.assertIn('Planning', stats['by_status'])
        self.assertIn('Completed', stats['by_status'])


@pytest.mark.django_db
class TestWorkSessionModel(TestCase):
    """Comprehensive tests for WorkSession model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )

    def test_work_session_creation(self):
        """Test basic work session creation"""
        start_time = timezone.now() - timedelta(hours=2)
        end_time = timezone.now() - timedelta(hours=1)
        
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Test Session',
            description='Test session description',
            start_time=start_time,
            end_time=end_time,
            productivity_rating=4,
            notes='Test notes'
        )
        
        self.assertEqual(session.project, self.project)
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.title, 'Test Session')
        self.assertEqual(session.productivity_rating, 4)
        self.assertEqual(session.duration_hours, 1.0)
        self.assertFalse(session.is_active)

    def test_work_session_str_method(self):
        """Test work session string representation"""
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Test Session',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            duration_hours=Decimal('1.50')
        )
        
        expected = f'{self.project.title} - Test Session (1.50h)'
        self.assertEqual(str(session), expected)

    def test_duration_calculation_on_save(self):
        """Test duration calculation when both start and end times are set"""
        start_time = timezone.now() - timedelta(hours=2, minutes=30)
        end_time = timezone.now() - timedelta(hours=1)
        
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Test Session',
            start_time=start_time,
            end_time=end_time
        )
        
        # Duration should be 1.5 hours
        self.assertEqual(session.duration_hours, 1.5)
        self.assertFalse(session.is_active)

    def test_is_completed_property(self):
        """Test is_completed property"""
        # Session without end time (not completed)
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now(),
            is_active=True
        )
        self.assertFalse(session.is_completed)
        
        # Session with end time (completed)
        session.end_time = timezone.now()
        session.save()
        self.assertTrue(session.is_completed)

    def test_duration_formatted_property(self):
        """Test duration_formatted property"""
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Test Session',
            start_time=timezone.now() - timedelta(hours=2, minutes=30),
            end_time=timezone.now(),
            duration_hours=Decimal('2.50')
        )
        
        self.assertEqual(session.duration_formatted, '2h 30m')
        
        # Test zero duration
        session.duration_hours = Decimal('0.00')
        session.save()
        self.assertEqual(session.duration_formatted, '0h 0m')
        
        # Test minutes only
        session.duration_hours = Decimal('0.50')
        session.save()
        self.assertEqual(session.duration_formatted, '30m')

    def test_is_today_property(self):
        """Test is_today property"""
        # Today's session
        session_today = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Today Session',
            start_time=timezone.now()
        )
        self.assertTrue(session_today.is_today)
        
        # Yesterday's session
        session_yesterday = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Yesterday Session',
            start_time=timezone.now() - timedelta(days=1)
        )
        self.assertFalse(session_yesterday.is_today)

    def test_is_this_week_property(self):
        """Test is_this_week property"""
        # This week's session
        session_this_week = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='This Week Session',
            start_time=timezone.now() - timedelta(days=2)
        )
        self.assertTrue(session_this_week.is_this_week)
        
        # Last week's session
        session_last_week = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Last Week Session',
            start_time=timezone.now() - timedelta(days=10)
        )
        self.assertFalse(session_last_week.is_this_week)

    def test_productivity_stars_property(self):
        """Test productivity_stars property"""
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Test Session',
            start_time=timezone.now(),
            productivity_rating=3
        )
        
        self.assertEqual(session.productivity_stars, '★★★☆☆')
        
        # Test with no rating
        session.productivity_rating = None
        session.save()
        self.assertEqual(session.productivity_stars, '')

    def test_can_be_edited_by_method(self):
        """Test can_be_edited_by method"""
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Test Session',
            start_time=timezone.now()
        )
        
        # Owner can edit
        self.assertTrue(session.can_be_edited_by(self.user))
        
        # Other user cannot edit
        other_user = User.objects.create_user(username='other', password='pass')
        self.assertFalse(session.can_be_edited_by(other_user))
        
        # Superuser can edit
        superuser = User.objects.create_superuser(username='admin', password='pass')
        self.assertTrue(session.can_be_edited_by(superuser))

    def test_can_be_stopped_by_method(self):
        """Test can_be_stopped_by method"""
        # Active session
        active_session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now(),
            is_active=True
        )
        self.assertTrue(active_session.can_be_stopped_by(self.user))
        
        # Inactive session
        inactive_session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Inactive Session',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            is_active=False
        )
        self.assertFalse(inactive_session.can_be_stopped_by(self.user))

    def test_stop_session_method(self):
        """Test stop_session method"""
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now() - timedelta(hours=1),
            is_active=True
        )
        
        duration = session.stop_session()
        session.refresh_from_db()
        
        self.assertFalse(session.is_active)
        self.assertIsNotNone(session.end_time)
        self.assertGreater(duration, 0)
        
        # Test stopping non-active session
        with self.assertRaises(ValueError):
            session.stop_session()

    def test_get_break_duration_method(self):
        """Test get_break_duration method"""
        session1 = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Session 1',
            start_time=timezone.now() - timedelta(hours=3),
            end_time=timezone.now() - timedelta(hours=2)
        )
        
        session2 = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Session 2',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now()
        )
        
        break_duration = session1.get_break_duration(session2)
        expected_duration = timedelta(hours=1)
        self.assertEqual(break_duration, expected_duration)

    def test_get_user_stats_class_method(self):
        """Test get_user_stats class method"""
        # Create various sessions
        WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Session 1',
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() - timedelta(days=1) + timedelta(hours=2),
            duration_hours=Decimal('2.00'),
            productivity_rating=4
        )
        WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Session 2',
            start_time=timezone.now() - timedelta(hours=3),
            end_time=timezone.now() - timedelta(hours=1),
            duration_hours=Decimal('2.00'),
            productivity_rating=5
        )
        
        stats = WorkSession.get_user_stats(self.user, days=30)
        
        self.assertEqual(stats['total_sessions'], 2)
        self.assertEqual(stats['total_hours'], Decimal('4.00'))
        self.assertEqual(stats['avg_session_length'], Decimal('2.00'))
        self.assertIsNotNone(stats['productivity_distribution'])
        self.assertGreater(stats['avg_hours_per_day'], 0)

    def test_get_active_sessions_class_method(self):
        """Test get_active_sessions class method"""
        # Create active and inactive sessions
        active_session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Active Session',
            start_time=timezone.now(),
            is_active=True
        )
        
        WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Inactive Session',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            is_active=False
        )
        
        # Test all active sessions
        active_sessions = WorkSession.get_active_sessions()
        self.assertEqual(active_sessions.count(), 1)
        self.assertEqual(active_sessions.first(), active_session)
        
        # Test user-specific active sessions
        user_active_sessions = WorkSession.get_active_sessions(user=self.user)
        self.assertEqual(user_active_sessions.count(), 1)
        self.assertEqual(user_active_sessions.first(), active_session)

    def test_get_recent_sessions_class_method(self):
        """Test get_recent_sessions class method"""
        # Create multiple sessions
        for i in range(15):
            WorkSession.objects.create(
                project=self.project,
                user=self.user,
                title=f'Session {i}',
                start_time=timezone.now() - timedelta(hours=i),
                end_time=timezone.now() - timedelta(hours=i-1) if i > 0 else None,
                is_active=i == 0
            )
        
        recent_sessions = WorkSession.get_recent_sessions(self.user, limit=5)
        self.assertEqual(len(recent_sessions), 5)
        
        # Should be ordered by start_time descending
        self.assertEqual(recent_sessions[0].title, 'Session 1')  # Most recent completed
