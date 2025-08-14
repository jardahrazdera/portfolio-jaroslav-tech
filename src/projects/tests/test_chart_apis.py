import pytest
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from projects.models import Project


@pytest.mark.django_db
class TestChartAPIs(TestCase):
    """Comprehensive tests for Chart.js API endpoints"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='chartuser',
            email='chart@example.com',
            password='testpass123'
        )
        
        # Create test projects with different statuses
        self.project1 = Project.objects.create(
            title='Planning Project',
            description='A project in planning phase',
            short_description='Planning project',
            owner=self.user,
            status='planning'
        )

    def test_chart_project_progress_api_requires_login(self):
        """Test that chart API requires authentication"""
        response = self.client.get(reverse('projects:chart_project_progress_api'))
        # Should redirect to login or return 302/403
        self.assertIn(response.status_code, [302, 403])

    def test_chart_project_progress_api_success(self):
        """Test successful project progress API response"""
        self.client.login(username='chartuser', password='testpass123')
        response = self.client.get(reverse('projects:chart_project_progress_api'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertIn('status_distribution', data)
        self.assertIn('completion_data', data)
        
        # Should have our test project data
        self.assertIsInstance(data['completion_data'], list)
        if data['completion_data']:
            self.assertIn('name', data['completion_data'][0])
            self.assertIn('completion', data['completion_data'][0])

    def test_chart_time_tracking_api_success(self):
        """Test time tracking API basic functionality"""
        self.client.login(username='chartuser', password='testpass123')
        response = self.client.get(reverse('projects:chart_time_tracking_api'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, dict)

    def test_chart_productivity_metrics_api_success(self):
        """Test productivity metrics API basic functionality"""
        self.client.login(username='chartuser', password='testpass123')
        response = self.client.get(reverse('projects:chart_productivity_metrics_api'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsInstance(data, dict)
