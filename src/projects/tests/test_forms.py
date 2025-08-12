import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
from projects.models import (
    Project, Technology, WorkSession, ProjectImage, UserProfile
)
from projects.forms import (
    ProjectForm, WorkSessionForm, ProjectImageForm, UserProfileForm,
    TechnologyFilterForm, BulkProjectActionForm
)


@pytest.mark.django_db
class TestProjectForm(TestCase):
    """Comprehensive tests for ProjectForm"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.technology = Technology.objects.create(
            name='Django',
            category='backend'
        )
        self.technology2 = Technology.objects.create(
            name='React',
            category='frontend'
        )

    def test_project_form_valid_data(self):
        """Test project form with valid data"""
        form_data = {
            'title': 'Test Project',
            'short_description': 'Short description for testing',
            'description': 'Long enough description for the test project validation',
            'status': 'planning',
            'priority': 'medium',
            'technologies': [self.technology.id, self.technology2.id],
            'start_date': date.today(),
            'github_url': 'https://github.com/user/repo',
            'live_url': 'https://example.com',
            'is_featured': True,
            'is_public': True
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_project_form_title_validation_too_short(self):
        """Test project form title validation for too short title"""
        form_data = {
            'title': 'AB',  # Too short
            'short_description': 'Short description for testing',
            'description': 'Long enough description for the test project validation',
            'status': 'planning',
            'priority': 'medium'
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Please choose a more descriptive project title', str(form.errors['title']))

    def test_project_form_title_inappropriate_content(self):
        """Test project form title validation for inappropriate content"""
        form_data = {
            'title': 'spam test project',  # Contains inappropriate word
            'short_description': 'Short description for testing',
            'description': 'Long enough description for the test project validation',
            'status': 'planning',
            'priority': 'medium'
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Please choose a more descriptive project title', str(form.errors['title']))

    def test_project_form_duplicate_title_validation(self):
        """Test project form prevents duplicate titles for same user"""
        # Create existing project
        Project.objects.create(
            title='Existing Project',
            description='Long enough description for the existing project',
            short_description='Short description',
            owner=self.user
        )
        
        form_data = {
            'title': 'Existing Project',
            'short_description': 'Different short description',
            'description': 'Different long enough description for the test project',
            'status': 'planning',
            'priority': 'medium'
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('You already have a project with this title', str(form.errors['title']))

    def test_project_form_short_description_validation(self):
        """Test project form short description validation"""
        form_data = {
            'title': 'Valid Project Title',
            'short_description': 'Short',  # Too short
            'description': 'Long enough description for the test project validation',
            'status': 'planning',
            'priority': 'medium'
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Short description should be at least 10 characters long', str(form.errors['short_description']))

    def test_project_form_description_validation(self):
        """Test project form description validation"""
        form_data = {
            'title': 'Valid Project Title',
            'short_description': 'Valid short description',
            'description': 'Short desc',  # Too short
            'status': 'planning',
            'priority': 'medium'
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Description should be at least 20 characters long', str(form.errors['description']))

    def test_project_form_github_url_validation(self):
        """Test project form GitHub URL validation"""
        form_data = {
            'title': 'Valid Project Title',
            'short_description': 'Valid short description',
            'description': 'Long enough description for the test project validation',
            'status': 'planning',
            'priority': 'medium',
            'github_url': 'https://invalid-site.com/repo'  # Not GitHub
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Please enter a valid GitHub repository URL', str(form.errors['github_url']))

    def test_project_form_live_url_validation(self):
        """Test project form live URL validation"""
        form_data = {
            'title': 'Valid Project Title',
            'short_description': 'Valid short description',
            'description': 'Long enough description for the test project validation',
            'status': 'planning',
            'priority': 'medium',
            'live_url': 'http://localhost:3000'  # Localhost not allowed
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Live URL cannot be localhost or development server', str(form.errors['live_url']))

    def test_project_form_date_validation(self):
        """Test project form start/end date validation"""
        form_data = {
            'title': 'Valid Project Title',
            'short_description': 'Valid short description',
            'description': 'Long enough description for the test project validation',
            'status': 'planning',
            'priority': 'medium',
            'start_date': date.today(),
            'end_date': date.today() - timedelta(days=1)  # End before start
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Start date cannot be after end date', str(form.errors['__all__']))

    def test_project_form_completed_status_with_future_end_date(self):
        """Test project form prevents completed status with future end date"""
        form_data = {
            'title': 'Valid Project Title',
            'short_description': 'Valid short description',
            'description': 'Long enough description for the test project validation',
            'status': 'completed',
            'priority': 'medium',
            'start_date': date.today() - timedelta(days=10),
            'end_date': date.today() + timedelta(days=1)  # Future date
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Cannot mark project as completed with future end date', str(form.errors['__all__']))

    def test_project_form_auto_set_end_date_for_completed(self):
        """Test project form automatically sets end date for completed projects"""
        form_data = {
            'title': 'Completed Project',
            'short_description': 'Valid short description',
            'description': 'Long enough description for the test project validation',
            'status': 'completed',
            'priority': 'medium',
            'start_date': date.today() - timedelta(days=10)
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['end_date'], date.today())

    def test_project_form_technology_limit_validation(self):
        """Test project form technology selection limit"""
        # Create many technologies
        technologies = []
        for i in range(20):
            tech = Technology.objects.create(name=f'Tech-{i}', category='other')
            technologies.append(tech.id)
        
        form_data = {
            'title': 'Valid Project Title',
            'short_description': 'Valid short description',
            'description': 'Long enough description for the test project validation',
            'status': 'planning',
            'priority': 'medium',
            'technologies': technologies  # Too many technologies
        }
        
        form = ProjectForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Please select no more than 15 technologies', str(form.errors['__all__']))

    def test_project_form_technology_queryset_ordering(self):
        """Test project form technology queryset is properly ordered"""
        form = ProjectForm(user=self.user)
        
        # Verify technologies are ordered by category, then name
        queryset = form.fields['technologies'].queryset
        technologies = list(queryset)
        
        # Should be ordered by category, then name
        self.assertEqual(technologies[0].name, 'Django')  # backend comes before frontend
        self.assertEqual(technologies[1].name, 'React')

    def test_project_form_update_existing_project(self):
        """Test project form for updating existing project"""
        # Create existing project
        project = Project.objects.create(
            title='Existing Project',
            description='Long enough description for the existing project',
            short_description='Short description',
            owner=self.user
        )
        
        # Form should allow same title when updating existing project
        form_data = {
            'title': 'Existing Project',  # Same title should be allowed
            'short_description': 'Updated short description',
            'description': 'Updated long enough description for the project',
            'status': 'development',
            'priority': 'high'
        }
        
        form = ProjectForm(data=form_data, user=self.user, instance=project)
        self.assertTrue(form.is_valid())


@pytest.mark.django_db
class TestWorkSessionForm(TestCase):
    """Comprehensive tests for WorkSessionForm"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )

    def test_work_session_form_valid_data(self):
        """Test work session form with valid data"""
        start_time = timezone.now() - timedelta(hours=2)
        end_time = timezone.now() - timedelta(hours=1)
        
        form_data = {
            'project': self.project.id,
            'title': 'Test Work Session',
            'description': 'Test session description',
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end_time.strftime('%Y-%m-%dT%H:%M'),
            'productivity_rating': 4,
            'notes': 'Test notes'
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_work_session_form_user_project_queryset(self):
        """Test work session form limits projects to user's own projects"""
        # Create another user with their project
        other_user = User.objects.create_user(username='other', password='pass')
        other_project = Project.objects.create(
            title='Other Project',
            description='Long enough description for the other project',
            short_description='Short description',
            owner=other_user
        )
        
        form = WorkSessionForm(user=self.user)
        
        # Should only contain user's projects
        project_ids = [p.id for p in form.fields['project'].queryset]
        self.assertIn(self.project.id, project_ids)
        self.assertNotIn(other_project.id, project_ids)

    def test_work_session_form_title_validation(self):
        """Test work session form title validation"""
        form_data = {
            'project': self.project.id,
            'title': 'AB',  # Too short
            'start_time': (timezone.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Session title should be at least 3 characters long', str(form.errors['title']))

    def test_work_session_form_start_time_validation_past(self):
        """Test work session form start time validation for distant past"""
        old_time = timezone.now() - timedelta(days=400)  # More than 1 year
        
        form_data = {
            'project': self.project.id,
            'title': 'Valid Session Title',
            'start_time': old_time.strftime('%Y-%m-%dT%H:%M')
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Start time cannot be more than 1 year in the past', str(form.errors['start_time']))

    def test_work_session_form_start_time_validation_future(self):
        """Test work session form start time validation for distant future"""
        future_time = timezone.now() + timedelta(hours=2)  # More than 1 hour
        
        form_data = {
            'project': self.project.id,
            'title': 'Valid Session Title',
            'start_time': future_time.strftime('%Y-%m-%dT%H:%M')
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Start time cannot be more than 1 hour in the future', str(form.errors['start_time']))

    def test_work_session_form_end_time_validation_future(self):
        """Test work session form end time validation for future"""
        future_time = timezone.now() + timedelta(minutes=10)  # More than 5 minutes
        
        form_data = {
            'project': self.project.id,
            'title': 'Valid Session Title',
            'start_time': (timezone.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'end_time': future_time.strftime('%Y-%m-%dT%H:%M')
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('End time cannot be in the future', str(form.errors['end_time']))

    def test_work_session_form_productivity_rating_validation(self):
        """Test work session form productivity rating validation"""
        form_data = {
            'project': self.project.id,
            'title': 'Valid Session Title',
            'start_time': (timezone.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'productivity_rating': 6  # Out of range (1-5)
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Productivity rating must be between 1 and 5', str(form.errors['productivity_rating']))

    def test_work_session_form_time_order_validation(self):
        """Test work session form validates end time after start time"""
        start_time = timezone.now() - timedelta(hours=1)
        end_time = timezone.now() - timedelta(hours=2)  # End before start
        
        form_data = {
            'project': self.project.id,
            'title': 'Valid Session Title',
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end_time.strftime('%Y-%m-%dT%H:%M')
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('End time must be after start time', str(form.errors['__all__']))

    def test_work_session_form_duration_too_long_validation(self):
        """Test work session form validates maximum duration"""
        start_time = timezone.now() - timedelta(hours=20)
        end_time = timezone.now()
        
        form_data = {
            'project': self.project.id,
            'title': 'Valid Session Title',
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end_time.strftime('%Y-%m-%dT%H:%M')
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Session duration cannot exceed 16 hours', str(form.errors['__all__']))

    def test_work_session_form_duration_too_short_validation(self):
        """Test work session form validates minimum duration"""
        start_time = timezone.now() - timedelta(seconds=30)
        end_time = timezone.now()
        
        form_data = {
            'project': self.project.id,
            'title': 'Valid Session Title',
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end_time.strftime('%Y-%m-%dT%H:%M')
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Session duration must be at least 1 minute', str(form.errors['__all__']))

    def test_work_session_form_overlapping_sessions_validation(self):
        """Test work session form prevents overlapping sessions"""
        # Create existing session
        existing_start = timezone.now() - timedelta(hours=3)
        existing_end = timezone.now() - timedelta(hours=2)
        
        WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Existing Session',
            start_time=existing_start,
            end_time=existing_end
        )
        
        # Try to create overlapping session
        overlap_start = timezone.now() - timedelta(hours=2, minutes=30)
        overlap_end = timezone.now() - timedelta(hours=1, minutes=30)
        
        form_data = {
            'project': self.project.id,
            'title': 'Overlapping Session',
            'start_time': overlap_start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': overlap_end.strftime('%Y-%m-%dT%H:%M')
        }
        
        form = WorkSessionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('This session overlaps with an existing session', str(form.errors['__all__']))

    def test_work_session_form_update_existing_session(self):
        """Test work session form for updating existing session"""
        # Create existing session
        session = WorkSession.objects.create(
            project=self.project,
            user=self.user,
            title='Existing Session',
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1)
        )
        
        # Update same session (should not conflict with itself)
        form_data = {
            'project': self.project.id,
            'title': 'Updated Session Title',
            'start_time': (timezone.now() - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
            'end_time': (timezone.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        }
        
        form = WorkSessionForm(data=form_data, user=self.user, instance=session)
        self.assertTrue(form.is_valid())


@pytest.mark.django_db
class TestProjectImageForm(TestCase):
    """Comprehensive tests for ProjectImageForm"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.project = Project.objects.create(
            title='Test Project',
            description='Long enough description for the project',
            short_description='Short description',
            owner=self.user
        )

    def test_project_image_form_valid_data(self):
        """Test project image form with valid data"""
        # Create a simple test image file
        test_image = SimpleUploadedFile(
            'test.jpg',
            b'fake image content',
            content_type='image/jpeg'
        )
        
        form_data = {
            'title': 'Test Image Title',
            'description': 'Test image description',
            'order': 1,
            'is_featured': False
        }
        
        form = ProjectImageForm(data=form_data, files={'image': test_image})
        self.assertTrue(form.is_valid(), form.errors)

    def test_project_image_form_title_validation_too_short(self):
        """Test project image form title validation for too short title"""
        test_image = SimpleUploadedFile(
            'test.jpg',
            b'fake image content',
            content_type='image/jpeg'
        )
        
        form_data = {
            'title': 'A',  # Too short
            'description': 'Test description',
            'order': 1
        }
        
        form = ProjectImageForm(data=form_data, files={'image': test_image})
        self.assertFalse(form.is_valid())
        self.assertIn('Image title should be at least 2 characters long', str(form.errors['title']))

    def test_project_image_form_order_validation_negative(self):
        """Test project image form order validation for negative values"""
        test_image = SimpleUploadedFile(
            'test.jpg',
            b'fake image content',
            content_type='image/jpeg'
        )
        
        form_data = {
            'title': 'Valid Title',
            'description': 'Test description',
            'order': -1  # Negative not allowed
        }
        
        form = ProjectImageForm(data=form_data, files={'image': test_image})
        self.assertFalse(form.is_valid())
        self.assertIn('Display order must be 0 or greater', str(form.errors['order']))

    def test_project_image_form_image_size_validation(self):
        """Test project image form image size validation"""
        # Create a large fake image file (over 10MB)
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB
        large_image = SimpleUploadedFile(
            'large.jpg',
            large_content,
            content_type='image/jpeg'
        )
        
        form_data = {
            'title': 'Large Image',
            'description': 'Test description',
            'order': 1
        }
        
        form = ProjectImageForm(data=form_data, files={'image': large_image})
        self.assertFalse(form.is_valid())
        self.assertIn('Image file size cannot exceed 10MB', str(form.errors['image']))

    def test_project_image_form_invalid_file_type(self):
        """Test project image form invalid file type validation"""
        # Create a text file instead of image
        text_file = SimpleUploadedFile(
            'test.txt',
            b'this is not an image',
            content_type='text/plain'
        )
        
        form_data = {
            'title': 'Invalid File',
            'description': 'Test description',
            'order': 1
        }
        
        form = ProjectImageForm(data=form_data, files={'image': text_file})
        self.assertFalse(form.is_valid())
        self.assertIn('Only JPEG, PNG, GIF, and WebP images are allowed', str(form.errors['image']))

    def test_project_image_form_missing_image(self):
        """Test project image form requires image file"""
        form_data = {
            'title': 'Valid Title',
            'description': 'Test description',
            'order': 1
        }
        
        form = ProjectImageForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please select an image file', str(form.errors['image']))

    def test_project_image_form_optional_fields(self):
        """Test project image form with only required fields"""
        test_image = SimpleUploadedFile(
            'test.jpg',
            b'fake image content',
            content_type='image/jpeg'
        )
        
        form_data = {
            'title': 'Minimal Image'
        }
        
        form = ProjectImageForm(data=form_data, files={'image': test_image})
        self.assertTrue(form.is_valid())


@pytest.mark.django_db
class TestUserProfileForm(TestCase):
    """Comprehensive tests for UserProfileForm"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_user_profile_form_valid_data(self):
        """Test user profile form with valid data"""
        form_data = {
            'bio': 'Valid biography for testing purposes and validation checks',
            'github_url': 'https://github.com/testuser',
            'linkedin_url': 'https://linkedin.com/in/testuser',
            'portfolio_url': 'https://testuser.com'
        }
        
        form = UserProfileForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_user_profile_form_bio_validation_too_short(self):
        """Test user profile form bio validation for too short bio"""
        form_data = {
            'bio': 'Short',  # Too short
            'github_url': 'https://github.com/testuser'
        }
        
        form = UserProfileForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Bio should be at least 10 characters long', str(form.errors['bio']))

    def test_user_profile_form_bio_validation_inappropriate_content(self):
        """Test user profile form bio validation for inappropriate content"""
        form_data = {
            'bio': 'This is a fake test user biography for validation',
            'github_url': 'https://github.com/testuser'
        }
        
        form = UserProfileForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please write a genuine bio about yourself', str(form.errors['bio']))

    def test_user_profile_form_github_url_validation(self):
        """Test user profile form GitHub URL validation"""
        form_data = {
            'bio': 'Valid biography for testing purposes and validation checks',
            'github_url': 'https://invalid-site.com/user'  # Not GitHub
        }
        
        form = UserProfileForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please enter a valid GitHub profile URL', str(form.errors['github_url']))

    def test_user_profile_form_linkedin_url_validation(self):
        """Test user profile form LinkedIn URL validation"""
        form_data = {
            'bio': 'Valid biography for testing purposes and validation checks',
            'linkedin_url': 'https://invalid-site.com/in/user'  # Not LinkedIn
        }
        
        form = UserProfileForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please enter a valid LinkedIn profile URL', str(form.errors['linkedin_url']))

    def test_user_profile_form_portfolio_url_validation(self):
        """Test user profile form portfolio URL validation"""
        form_data = {
            'bio': 'Valid biography for testing purposes and validation checks',
            'portfolio_url': 'http://localhost:3000'  # Localhost not allowed
        }
        
        form = UserProfileForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please enter your actual portfolio URL', str(form.errors['portfolio_url']))

    def test_user_profile_form_all_fields_optional(self):
        """Test user profile form with no fields filled (all optional)"""
        form_data = {}
        
        form = UserProfileForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_user_profile_form_valid_linkedin_variations(self):
        """Test user profile form accepts various valid LinkedIn URL formats"""
        valid_urls = [
            'https://linkedin.com/in/testuser',
            'https://www.linkedin.com/in/testuser',
            'https://linkedin.com/in/test-user',
            'https://www.linkedin.com/in/test.user'
        ]
        
        for url in valid_urls:
            form_data = {
                'bio': 'Valid biography for testing purposes and validation checks',
                'linkedin_url': url
            }
            
            form = UserProfileForm(data=form_data)
            self.assertTrue(form.is_valid(), f'URL {url} should be valid')


@pytest.mark.django_db
class TestTechnologyFilterForm(TestCase):
    """Comprehensive tests for TechnologyFilterForm"""

    def setUp(self):
        self.technology = Technology.objects.create(
            name='Django',
            category='backend'
        )

    def test_technology_filter_form_valid_data(self):
        """Test technology filter form with valid data"""
        form_data = {
            'technology': self.technology.id,
            'status': 'development',
            'priority': 'high',
            'date_range': 'month',
            'search': 'test query'
        }
        
        form = TechnologyFilterForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_technology_filter_form_empty_data(self):
        """Test technology filter form with empty data (all optional)"""
        form_data = {}
        
        form = TechnologyFilterForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_technology_filter_form_search_validation_too_short(self):
        """Test technology filter form search validation for too short query"""
        form_data = {
            'search': 'a'  # Too short
        }
        
        form = TechnologyFilterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Search query must be at least 2 characters long', str(form.errors['search']))

    def test_technology_filter_form_search_validation_too_long(self):
        """Test technology filter form search validation for too long query"""
        form_data = {
            'search': 'x' * 101  # Too long
        }
        
        form = TechnologyFilterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Search query cannot exceed 100 characters', str(form.errors['search']))

    def test_technology_filter_form_choice_field_validation(self):
        """Test technology filter form choice field validation"""
        valid_statuses = ['planning', 'development', 'testing', 'completed', 'archived']
        valid_priorities = ['low', 'medium', 'high']
        valid_date_ranges = ['week', 'month', 'quarter', 'year']
        
        # Test valid choices
        for status in valid_statuses:
            form = TechnologyFilterForm(data={'status': status})
            self.assertTrue(form.is_valid(), f'Status {status} should be valid')
        
        for priority in valid_priorities:
            form = TechnologyFilterForm(data={'priority': priority})
            self.assertTrue(form.is_valid(), f'Priority {priority} should be valid')
        
        for date_range in valid_date_ranges:
            form = TechnologyFilterForm(data={'date_range': date_range})
            self.assertTrue(form.is_valid(), f'Date range {date_range} should be valid')


@pytest.mark.django_db
class TestBulkProjectActionForm(TestCase):
    """Comprehensive tests for BulkProjectActionForm"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.project1 = Project.objects.create(
            title='Project 1',
            description='Long enough description for project 1',
            short_description='Short description 1',
            owner=self.user
        )
        self.project2 = Project.objects.create(
            title='Project 2',
            description='Long enough description for project 2',
            short_description='Short description 2',
            owner=self.user
        )

    def test_bulk_action_form_valid_set_status(self):
        """Test bulk action form with valid set status action"""
        form_data = {
            'action': 'set_status',
            'projects': [self.project1.id, self.project2.id],
            'new_status': 'development'
        }
        
        form = BulkProjectActionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_bulk_action_form_valid_set_priority(self):
        """Test bulk action form with valid set priority action"""
        form_data = {
            'action': 'set_priority',
            'projects': [self.project1.id],
            'new_priority': 'high'
        }
        
        form = BulkProjectActionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_bulk_action_form_valid_set_visibility(self):
        """Test bulk action form with valid set visibility action"""
        form_data = {
            'action': 'set_visibility',
            'projects': [self.project1.id],
            'new_visibility': True
        }
        
        form = BulkProjectActionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_bulk_action_form_valid_delete(self):
        """Test bulk action form with valid delete action"""
        form_data = {
            'action': 'delete',
            'projects': [self.project2.id]
        }
        
        form = BulkProjectActionForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_bulk_action_form_missing_action(self):
        """Test bulk action form validation for missing action"""
        form_data = {
            'projects': [self.project1.id]
        }
        
        form = BulkProjectActionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Please select an action', str(form.errors['__all__']))

    def test_bulk_action_form_missing_projects(self):
        """Test bulk action form validation for missing projects"""
        form_data = {
            'action': 'set_status',
            'new_status': 'development'
        }
        
        form = BulkProjectActionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Please select at least one project', str(form.errors['__all__']))

    def test_bulk_action_form_set_status_missing_new_status(self):
        """Test bulk action form validation for set_status without new_status"""
        form_data = {
            'action': 'set_status',
            'projects': [self.project1.id]
        }
        
        form = BulkProjectActionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Please select a new status', str(form.errors['__all__']))

    def test_bulk_action_form_set_priority_missing_new_priority(self):
        """Test bulk action form validation for set_priority without new_priority"""
        form_data = {
            'action': 'set_priority',
            'projects': [self.project1.id]
        }
        
        form = BulkProjectActionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Please select a new priority', str(form.errors['__all__']))

    def test_bulk_action_form_too_many_projects(self):
        """Test bulk action form validation for too many projects"""
        # Create many projects
        projects = []
        for i in range(51):
            project = Project.objects.create(
                title=f'Project {i}',
                description=f'Long enough description for project {i}',
                short_description=f'Short description {i}',
                owner=self.user
            )
            projects.append(project.id)
        
        form_data = {
            'action': 'delete',
            'projects': projects
        }
        
        form = BulkProjectActionForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('Cannot perform bulk actions on more than 50 projects at once', str(form.errors['__all__']))

    def test_bulk_action_form_project_queryset_limited_to_user(self):
        """Test bulk action form limits project choices to user's projects"""
        # Create another user with their project
        other_user = User.objects.create_user(username='other', password='pass')
        other_project = Project.objects.create(
            title='Other Project',
            description='Long enough description for other project',
            short_description='Short description other',
            owner=other_user
        )
        
        form = BulkProjectActionForm(user=self.user)
        
        # Should only contain user's projects
        project_ids = [p.id for p in form.fields['projects'].queryset]
        self.assertIn(self.project1.id, project_ids)
        self.assertIn(self.project2.id, project_ids)
        self.assertNotIn(other_project.id, project_ids)
