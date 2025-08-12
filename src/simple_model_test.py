import os
import django
from django.test import TestCase
from django.contrib.auth.models import User
from projects.models import Project, Technology, UserProfile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jaroslav_tech.settings')
django.setup()

class SimpleProjectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_project_creation(self):
        project = Project.objects.create(
            owner=self.user,
            title='Test Project',
            slug='test-project'
        )
        self.assertEqual(project.title, 'Test Project')
        self.assertEqual(project.owner, self.user)
    
    def test_technology_creation(self):
        tech = Technology.objects.create(
            name='Django',
            slug='django'
        )
        self.assertEqual(tech.name, 'Django')
        self.assertEqual(str(tech), 'Django')
    
    def test_user_profile_creation(self):
        profile = UserProfile.objects.create(
            user=self.user,
            bio='This is a test bio with enough content to pass validation.'
        )
        self.assertEqual(profile.user, self.user)

if __name__ == '__main__':
    import unittest
    unittest.main()
