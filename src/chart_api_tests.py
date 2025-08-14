"""
Comprehensive test coverage for chart API endpoints.
This file should be moved to projects/tests/test_chart_apis.py
"""
import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta, date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from projects.models import Project, Technology, WorkSession, UserProfile


@pytest.mark.django_db
@pytest.mark.api
class TestChartAPIs(TestCase):
    """Test suite for chart API endpoints."""
    
    def setUp(self):
        """Set up test data for chart API tests."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create test technologies
        self.tech_django = Technology.objects.create(
            name='Django',
            category='backend'
        )
        self.tech_react = Technology.objects.create(
            name='React',
            category='frontend'
        )
        
        # Create test projects with different statuses and priorities
        self.project_active = Project.objects.create(
            title='Active Project',
            description='A project currently in development',
            short_description='Active development project',
            owner=self.user,
            status='development',
            priority='high',
            start_date=date.today() - timedelta(days=30),
            estimated_hours=Decimal('100.00'),
            actual_hours=Decimal('45.50')
        )
        
        self.project_completed = Project.objects.create(
            title='Completed Project',
            description='A completed project for testing',
            short_description='Completed project',
            owner=self.user,
            status='completed',
            priority='medium',
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=10),
            estimated_hours=Decimal('80.00'),
            actual_hours=Decimal('85.25')
        )
        
        # Create work sessions for testing
        self.create_test_work_sessions()
    
    def create_test_work_sessions(self):
        """Create test work sessions for time tracking tests."""
        base_time = timezone.now() - timedelta(days=7)
        
        # Sessions for the past week
        for i in range(7):
            day_start = base_time + timedelta(days=i)
            
            # Active project sessions
            WorkSession.objects.create(
                project=self.project_active,
                user=self.user,
                title=f'Active Session Day {i+1}',
                start_time=day_start.replace(hour=9, minute=0),
                end_time=day_start.replace(hour=12, minute=30),
                duration_hours=Decimal('3.50'),
                productivity_rating=4 if i % 2 == 0 else 5
            )
    
    @pytest.mark.unit
    def test_chart_project_progress_api_success(self):
        """Test successful project progress chart API response."""
        url = reverse('chart_project_progress_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        
        # Verify response structure
        self.assertIn('project_status', data)
        self.assertIn('completion_progress', data)
        self.assertIn('hours_comparison', data)
        
        # Verify project status data
        status_data = data['project_status']
        self.assertIsInstance(status_data, dict)
    
    @pytest.mark.unit
    def test_chart_time_tracking_api_success(self):
        """Test successful time tracking chart API response."""
        url = reverse('chart_time_tracking_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Verify response structure
        self.assertIn('daily_hours', data)
        self.assertIn('project_hours', data)
        self.assertIn('weekly_productivity', data)
    
    @pytest.mark.unit
    def test_chart_productivity_metrics_api_success(self):
        """Test successful productivity metrics chart API response."""
        url = reverse('chart_productivity_metrics_api')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Verify response structure
        self.assertIn('task_data', data)
        self.assertIn('priority_distribution', data)
        self.assertIn('monthly_projects', data)
        self.assertIn('productivity_trend', data)
    
    @pytest.mark.unit
    def test_chart_apis_require_authentication(self):
        """Test that chart APIs require authentication."""
        self.client.logout()
        
        urls = [
            reverse('chart_project_progress_api'),
            reverse('chart_time_tracking_api'),
            reverse('chart_productivity_metrics_api'),
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)  # Redirect to login