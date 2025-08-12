import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from datetime import date, timedelta
import json

from projects.models import Project
from tasks.models import Task, TaskComment
from tasks.forms import TaskForm, TaskFilterForm, TaskCommentForm


@pytest.mark.django_db
class TestTaskListView(TestCase):
    """Test the TaskListView functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
        self.other_project = Project.objects.create(
            title='Other Project',
            description='Another project',
            owner=self.other_user
        )
        
        # Create test tasks
        self.user_task = Task.objects.create(
            title='User Task',
            project=self.project,
            creator=self.user,
            assignee=self.user,
            status='todo'
        )
        
        self.assigned_task = Task.objects.create(
            title='Assigned Task',
            project=self.other_project,
            creator=self.other_user,
            assignee=self.user,
            status='in_progress'
        )
        
        self.other_task = Task.objects.create(
            title='Other Task',
            project=self.other_project,
            creator=self.other_user,
            assignee=self.other_user,
            status='done'
        )
    
    def test_task_list_requires_login(self):
        """Test that task list requires authentication."""
        response = self.client.get(reverse('tasks:task_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_task_list_authenticated_user(self):
        """Test task list for authenticated user."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:task_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Task')
        self.assertContains(response, 'Assigned Task')
        self.assertNotContains(response, 'Other Task')  # User doesn't have access
    
    def test_task_list_filtering_by_status(self):
        """Test filtering tasks by status."""
        self.client.login(username='testuser', password='testpass')
        
        # Filter by 'todo' status
        response = self.client.get(reverse('tasks:task_list'), {'status': 'todo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Task')
        self.assertNotContains(response, 'Assigned Task')
    
    def test_task_list_filtering_by_priority(self):
        """Test filtering tasks by priority."""
        # Update task priority
        self.user_task.priority = 'high'
        self.user_task.save()
        
        self.client.login(username='testuser', password='testpass')
        
        # Filter by 'high' priority
        response = self.client.get(reverse('tasks:task_list'), {'priority': 'high'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Task')
        self.assertNotContains(response, 'Assigned Task')
    
    def test_task_list_search_functionality(self):
        """Test search functionality in task list."""
        self.client.login(username='testuser', password='testpass')
        
        # Search for specific task
        response = self.client.get(reverse('tasks:task_list'), {'search': 'User'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Task')
        self.assertNotContains(response, 'Assigned Task')
    
    def test_task_list_due_date_filtering(self):
        """Test filtering by due date."""
        # Set overdue task
        self.user_task.due_date = date.today() - timedelta(days=1)
        self.user_task.save()
        
        self.client.login(username='testuser', password='testpass')
        
        # Filter overdue tasks
        response = self.client.get(reverse('tasks:task_list'), {'due_date_filter': 'overdue'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Task')
    
    def test_task_list_statistics(self):
        """Test that task statistics are included in context."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:task_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('stats', response.context)
        
        stats = response.context['stats']
        self.assertEqual(stats['total_tasks'], 2)  # user_task and assigned_task
        self.assertEqual(stats['todo'], 1)  # user_task
        self.assertEqual(stats['in_progress'], 1)  # assigned_task
        self.assertEqual(stats['done'], 0)
    
    def test_task_list_pagination(self):
        """Test pagination functionality."""
        # Create many tasks for pagination
        for i in range(25):
            Task.objects.create(
                title=f'Task {i}',
                project=self.project,
                creator=self.user,
                assignee=self.user
            )
        
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:task_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['tasks']), 20)  # paginate_by = 20


@pytest.mark.django_db
class TestTaskDetailView(TestCase):
    """Test the TaskDetailView functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            description='A test task description',
            project=self.project,
            creator=self.user,
            assignee=self.user
        )
        
        # Create dependencies and subtasks
        self.dependency = Task.objects.create(
            title='Dependency Task',
            project=self.project,
            creator=self.user,
            status='done'
        )
        self.task.dependencies.add(self.dependency)
        
        self.subtask = Task.objects.create(
            title='Subtask',
            project=self.project,
            creator=self.user,
            parent_task=self.task
        )
        
        # Create comments
        self.comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            content='Test comment'
        )
    
    def test_task_detail_requires_login(self):
        """Test that task detail requires authentication."""
        response = self.client.get(reverse('tasks:task_detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_task_detail_authenticated_access(self):
        """Test task detail access for authorized user."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:task_detail', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Task')
        self.assertContains(response, 'A test task description')
        self.assertEqual(response.context['task'], self.task)
    
    def test_task_detail_unauthorized_access(self):
        """Test task detail access denied for unauthorized user."""
        self.client.login(username='otheruser', password='testpass')
        response = self.client.get(reverse('tasks:task_detail', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 404)
    
    def test_task_detail_can_edit_permission(self):
        """Test can_edit permission in context."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:task_detail', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_edit'])
    
    def test_task_detail_includes_related_data(self):
        """Test that task detail includes dependencies, subtasks, and comments."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:task_detail', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 200)
        
        # Check subtasks
        self.assertIn('subtasks', response.context)
        subtasks = response.context['subtasks']
        self.assertEqual(subtasks.count(), 1)
        self.assertIn(self.subtask, subtasks)
        
        # Check dependencies
        self.assertIn('dependencies', response.context)
        dependencies = response.context['dependencies']
        self.assertEqual(dependencies.count(), 1)
        self.assertIn(self.dependency, dependencies)
        
        # Check comment form
        self.assertIn('comment_form', response.context)
        self.assertIsInstance(response.context['comment_form'], TaskCommentForm)
    
    def test_task_detail_nonexistent_task(self):
        """Test access to nonexistent task returns 404."""
        self.client.login(username='testuser', password='testpass')
        
        import uuid
        fake_id = uuid.uuid4()
        response = self.client.get(reverse('tasks:task_detail', kwargs={'pk': fake_id}))
        
        self.assertEqual(response.status_code, 404)


@pytest.mark.django_db
class TestTaskCreateView(TestCase):
    """Test the TaskCreateView functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
    
    def test_task_create_requires_login(self):
        """Test that task creation requires authentication."""
        response = self.client.get(reverse('tasks:task_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_task_create_get_form(self):
        """Test GET request to task creation form."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:task_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Task')
        self.assertIsInstance(response.context['form'], TaskForm)
    
    def test_task_create_with_project_context(self):
        """Test task creation with project context."""
        self.client.login(username='testuser', password='testpass')
        url = reverse('tasks:task_create_for_project', kwargs={'project_id': self.project.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.initial.get('project'), self.project)
    
    def test_task_create_post_valid_data(self):
        """Test creating task with valid data."""
        self.client.login(username='testuser', password='testpass')
        
        task_data = {
            'title': 'New Test Task',
            'description': 'Description of the new task',
            'project': self.project.id,
            'status': 'todo',
            'priority': 'medium',
            'task_type': 'feature',
            'progress_percentage': 0
        }
        
        response = self.client.post(reverse('tasks:task_create'), task_data)
        
        # Should redirect to task detail
        self.assertEqual(response.status_code, 302)
        
        # Check task was created
        task = Task.objects.get(title='New Test Task')
        self.assertEqual(task.creator, self.user)
        self.assertEqual(task.assignee, self.user)  # Auto-assigned to creator
        self.assertEqual(task.project, self.project)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('created successfully' in str(m) for m in messages))
    
    def test_task_create_post_invalid_data(self):
        """Test creating task with invalid data."""
        self.client.login(username='testuser', password='testpass')
        
        # Missing required title
        task_data = {
            'description': 'Description without title',
            'project': self.project.id
        }
        
        response = self.client.post(reverse('tasks:task_create'), task_data)
        
        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'title', 'This field is required.')
    
    def test_task_create_unauthorized_project(self):
        """Test creating task for unauthorized project."""
        other_user = User.objects.create_user(username='otheruser', password='testpass')
        other_project = Project.objects.create(
            title='Other Project',
            description='Another project',
            owner=other_user
        )
        
        self.client.login(username='testuser', password='testpass')
        
        task_data = {
            'title': 'Unauthorized Task',
            'project': other_project.id,
            'status': 'todo'
        }
        
        response = self.client.post(reverse('tasks:task_create'), task_data)
        
        # Should return form with validation error
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)


@pytest.mark.django_db
class TestTaskUpdateView(TestCase):
    """Test the TaskUpdateView functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            description='Original description',
            project=self.project,
            creator=self.user,
            assignee=self.user,
            status='todo'
        )
    
    def test_task_update_requires_login(self):
        """Test that task update requires authentication."""
        response = self.client.get(reverse('tasks:task_update', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_task_update_get_form(self):
        """Test GET request to task update form."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:task_update', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Task: Test Task')
        self.assertEqual(response.context['form'].instance, self.task)
    
    def test_task_update_post_valid_data(self):
        """Test updating task with valid data."""
        self.client.login(username='testuser', password='testpass')
        
        update_data = {
            'title': 'Updated Task Title',
            'description': 'Updated description',
            'project': self.project.id,
            'status': 'in_progress',
            'priority': 'high',
            'task_type': 'bug',
            'progress_percentage': 50
        }
        
        response = self.client.post(
            reverse('tasks:task_update', kwargs={'pk': self.task.pk}),
            update_data
        )
        
        # Should redirect to task detail
        self.assertEqual(response.status_code, 302)
        
        # Check task was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated Task Title')
        self.assertEqual(self.task.status, 'in_progress')
        self.assertEqual(self.task.priority, 'high')
        self.assertEqual(self.task.progress_percentage, 50)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('updated successfully' in str(m) for m in messages))
    
    def test_task_update_unauthorized_user(self):
        """Test task update by unauthorized user."""
        self.client.login(username='otheruser', password='testpass')
        response = self.client.get(reverse('tasks:task_update', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 404)
    
    def test_task_update_assignee_can_edit(self):
        """Test that assignee can edit task."""
        # Make other_user the assignee
        self.task.assignee = self.other_user
        self.task.save()
        
        self.client.login(username='otheruser', password='testpass')
        response = self.client.get(reverse('tasks:task_update', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 200)


@pytest.mark.django_db
class TestTaskDeleteView(TestCase):
    """Test the TaskDeleteView functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
    
    def test_task_delete_requires_login(self):
        """Test that task deletion requires authentication."""
        response = self.client.get(reverse('tasks:task_delete', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_task_delete_get_confirmation(self):
        """Test GET request to task deletion confirmation."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:task_delete', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Task')
        self.assertEqual(response.context['object'], self.task)
    
    def test_task_delete_post_confirmation(self):
        """Test POST request to delete task."""
        self.client.login(username='testuser', password='testpass')
        task_id = self.task.id
        
        response = self.client.post(reverse('tasks:task_delete', kwargs={'pk': self.task.pk}))
        
        # Should redirect to task list
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('tasks:task_list'))
        
        # Check task was deleted
        self.assertFalse(Task.objects.filter(id=task_id).exists())
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('deleted successfully' in str(m) for m in messages))
    
    def test_task_delete_unauthorized_user(self):
        """Test task deletion by unauthorized user."""
        self.client.login(username='otheruser', password='testpass')
        response = self.client.get(reverse('tasks:task_delete', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 404)
    
    def test_task_delete_assignee_cannot_delete(self):
        """Test that assignee cannot delete task (only creator/owner can)."""
        # Make other_user the assignee
        self.task.assignee = self.other_user
        self.task.save()
        
        self.client.login(username='otheruser', password='testpass')
        response = self.client.get(reverse('tasks:task_delete', kwargs={'pk': self.task.pk}))
        
        self.assertEqual(response.status_code, 404)


@pytest.mark.django_db
class TestTaskCommentView(TestCase):
    """Test the add_task_comment view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user,
            assignee=self.user
        )
    
    def test_add_comment_requires_login(self):
        """Test that adding comment requires authentication."""
        response = self.client.post(
            reverse('tasks:add_comment', kwargs={'task_id': self.task.id}),
            {'content': 'Test comment'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_add_comment_valid_data(self):
        """Test adding comment with valid data."""
        self.client.login(username='testuser', password='testpass')
        
        response = self.client.post(
            reverse('tasks:add_comment', kwargs={'task_id': self.task.id}),
            {'content': 'This is a test comment'}
        )
        
        # Should redirect to task detail
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.task.get_absolute_url())
        
        # Check comment was created
        comment = TaskComment.objects.get(task=self.task)
        self.assertEqual(comment.content, 'This is a test comment')
        self.assertEqual(comment.author, self.user)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Comment added successfully' in str(m) for m in messages))
    
    def test_add_comment_invalid_data(self):
        """Test adding comment with invalid data."""
        self.client.login(username='testuser', password='testpass')
        
        # Empty content
        response = self.client.post(
            reverse('tasks:add_comment', kwargs={'task_id': self.task.id}),
            {'content': ''}
        )
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
        
        # Check no comment was created
        self.assertEqual(TaskComment.objects.filter(task=self.task).count(), 0)
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid comment data' in str(m) for m in messages))
    
    def test_add_comment_unauthorized_user(self):
        """Test adding comment by unauthorized user."""
        self.client.login(username='otheruser', password='testpass')
        
        response = self.client.post(
            reverse('tasks:add_comment', kwargs={'task_id': self.task.id}),
            {'content': 'Unauthorized comment'}
        )
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
        
        # Check no comment was created
        self.assertEqual(TaskComment.objects.filter(task=self.task).count(), 0)
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('permission' in str(m).lower() for m in messages))
    
    def test_add_comment_assignee_can_comment(self):
        """Test that assignee can add comments."""
        # Make other_user the assignee
        self.task.assignee = self.other_user
        self.task.save()
        
        self.client.login(username='otheruser', password='testpass')
        
        response = self.client.post(
            reverse('tasks:add_comment', kwargs={'task_id': self.task.id}),
            {'content': 'Assignee comment'}
        )
        
        # Should succeed
        self.assertEqual(response.status_code, 302)
        
        # Check comment was created
        comment = TaskComment.objects.get(task=self.task)
        self.assertEqual(comment.content, 'Assignee comment')
        self.assertEqual(comment.author, self.other_user)


@pytest.mark.django_db
class TestMarkTaskCompleteView(TestCase):
    """Test the mark_task_complete view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user,
            assignee=self.user,
            status='in_progress',
            progress_percentage=50
        )
    
    def test_mark_complete_requires_login(self):
        """Test that marking complete requires authentication."""
        response = self.client.post(
            reverse('tasks:mark_complete', kwargs={'task_id': self.task.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_mark_complete_authorized_user(self):
        """Test marking task complete by authorized user."""
        self.client.login(username='testuser', password='testpass')
        
        response = self.client.post(
            reverse('tasks:mark_complete', kwargs={'task_id': self.task.id})
        )
        
        # Should redirect to task detail
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.task.get_absolute_url())
        
        # Check task was marked complete
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'done')
        self.assertEqual(self.task.progress_percentage, 100)
        self.assertIsNotNone(self.task.completed_date)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('marked as completed' in str(m) for m in messages))
    
    def test_mark_complete_unauthorized_user(self):
        """Test marking complete by unauthorized user."""
        self.client.login(username='otheruser', password='testpass')
        
        response = self.client.post(
            reverse('tasks:mark_complete', kwargs={'task_id': self.task.id})
        )
        
        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        
        # Check task was not changed
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'in_progress')
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('permission' in str(m).lower() for m in messages))
    
    def test_mark_complete_get_request(self):
        """Test that GET request doesn't mark task complete."""
        self.client.login(username='testuser', password='testpass')
        
        response = self.client.get(
            reverse('tasks:mark_complete', kwargs={'task_id': self.task.id})
        )
        
        # Should redirect without changing task
        self.assertEqual(response.status_code, 302)
        
        # Check task was not changed
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'in_progress')


@pytest.mark.django_db
class TestProjectTasksView(TestCase):
    """Test the project_tasks_view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
        self.other_project = Project.objects.create(
            title='Other Project',
            description='Another project',
            owner=self.other_user
        )
        
        # Create tasks for the project
        self.task1 = Task.objects.create(
            title='Project Task 1',
            project=self.project,
            creator=self.user,
            status='todo'
        )
        
        self.task2 = Task.objects.create(
            title='Project Task 2',
            project=self.project,
            creator=self.user,
            status='done'
        )
    
    def test_project_tasks_requires_login(self):
        """Test that project tasks view requires authentication."""
        response = self.client.get(
            reverse('tasks:project_tasks', kwargs={'project_id': self.project.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_project_tasks_authorized_access(self):
        """Test project tasks view for project owner."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(
            reverse('tasks:project_tasks', kwargs={'project_id': self.project.id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Project Task 1')
        self.assertContains(response, 'Project Task 2')
        self.assertEqual(response.context['project'], self.project)
    
    def test_project_tasks_unauthorized_access(self):
        """Test project tasks view access denied for non-owner."""
        self.client.login(username='otheruser', password='testpass')
        response = self.client.get(
            reverse('tasks:project_tasks', kwargs={'project_id': self.project.id})
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_project_tasks_filtering(self):
        """Test filtering functionality in project tasks view."""
        self.client.login(username='testuser', password='testpass')
        
        # Filter by status
        response = self.client.get(
            reverse('tasks:project_tasks', kwargs={'project_id': self.project.id}),
            {'status': 'todo'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Project Task 1')
        self.assertNotContains(response, 'Project Task 2')
    
    def test_project_tasks_statistics(self):
        """Test that project statistics are included."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(
            reverse('tasks:project_tasks', kwargs={'project_id': self.project.id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('stats', response.context)
        
        stats = response.context['stats']
        self.assertEqual(stats['total_tasks'], 2)
        self.assertEqual(stats['completed'], 1)


@pytest.mark.django_db
class TestTaskAPIView(TestCase):
    """Test the task_api_list JSON API functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
        self.task = Task.objects.create(
            title='API Test Task',
            description='A task for API testing',
            project=self.project,
            creator=self.user,
            assignee=self.user,
            status='todo',
            priority='high',
            due_date=date.today() + timedelta(days=7)
        )
    
    def test_api_requires_login(self):
        """Test that API requires authentication."""
        response = self.client.get(reverse('tasks:api_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_api_returns_json(self):
        """Test that API returns valid JSON response."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:api_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertIn('tasks', data)
        self.assertIn('pagination', data)
    
    def test_api_task_data_structure(self):
        """Test the structure of task data in API response."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:api_list'))
        
        data = json.loads(response.content)
        tasks = data['tasks']
        
        self.assertEqual(len(tasks), 1)
        task_data = tasks[0]
        
        # Check required fields
        required_fields = [
            'id', 'title', 'description', 'status', 'priority',
            'progress_percentage', 'is_overdue', 'can_start',
            'project', 'due_date', 'created_at', 'url'
        ]
        
        for field in required_fields:
            self.assertIn(field, task_data)
        
        # Check data types and values
        self.assertEqual(task_data['title'], 'API Test Task')
        self.assertEqual(task_data['status'], 'todo')
        self.assertEqual(task_data['priority'], 'high')
        self.assertIsInstance(task_data['is_overdue'], bool)
        self.assertIsInstance(task_data['can_start'], bool)
        
        # Check project data
        self.assertIn('project', task_data)
        project_data = task_data['project']
        self.assertEqual(project_data['title'], 'Test Project')
        
        # Check assignee data
        self.assertIn('assignee', task_data)
        assignee_data = task_data['assignee']
        self.assertEqual(assignee_data['username'], 'testuser')
    
    def test_api_filtering(self):
        """Test API filtering functionality."""
        # Create additional task with different status
        Task.objects.create(
            title='Another Task',
            project=self.project,
            creator=self.user,
            status='done'
        )
        
        self.client.login(username='testuser', password='testpass')
        
        # Filter by status
        response = self.client.get(reverse('tasks:api_list'), {'status': 'todo'})
        data = json.loads(response.content)
        
        self.assertEqual(len(data['tasks']), 1)
        self.assertEqual(data['tasks'][0]['status'], 'todo')
    
    def test_api_pagination(self):
        """Test API pagination functionality."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('tasks:api_list'), {'page': 1, 'limit': 10})
        
        data = json.loads(response.content)
        pagination = data['pagination']
        
        self.assertEqual(pagination['page'], 1)
        self.assertEqual(pagination['limit'], 10)
        self.assertIn('total', pagination)
        self.assertIn('pages', pagination)
    
    def test_api_invalid_parameters(self):
        """Test API with invalid parameters."""
        self.client.login(username='testuser', password='testpass')
        
        # Invalid project ID
        response = self.client.get(reverse('tasks:api_list'), {'project': 'invalid'})
        self.assertEqual(response.status_code, 400)
        
        # Invalid assignee ID
        response = self.client.get(reverse('tasks:api_list'), {'assignee': 'invalid'})
        self.assertEqual(response.status_code, 400)
        
        # Invalid pagination
        response = self.client.get(reverse('tasks:api_list'), {'page': 'invalid'})
        self.assertEqual(response.status_code, 400)


@pytest.mark.django_db
class TestTaskViewsErrorHandling(TestCase):
    """Test error handling in task views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
    
    def test_nonexistent_task_handling(self):
        """Test handling of requests for nonexistent tasks."""
        self.client.login(username='testuser', password='testpass')
        
        import uuid
        fake_id = uuid.uuid4()
        
        # Test detail view
        response = self.client.get(reverse('tasks:task_detail', kwargs={'pk': fake_id}))
        self.assertEqual(response.status_code, 404)
        
        # Test update view
        response = self.client.get(reverse('tasks:task_update', kwargs={'pk': fake_id}))
        self.assertEqual(response.status_code, 404)
        
        # Test delete view
        response = self.client.get(reverse('tasks:task_delete', kwargs={'pk': fake_id}))
        self.assertEqual(response.status_code, 404)
    
    def test_database_error_handling(self):
        """Test handling of potential database errors."""
        self.client.login(username='testuser', password='testpass')
        
        # This test would require mocking database errors
        # In practice, you'd use unittest.mock to simulate exceptions
        pass
    
    def test_permission_denied_scenarios(self):
        """Test various permission denied scenarios."""
        other_user = User.objects.create_user(username='otheruser', password='testpass')
        other_project = Project.objects.create(
            title='Other Project',
            description='Another project',
            owner=other_user
        )
        
        task = Task.objects.create(
            title='Other User Task',
            project=other_project,
            creator=other_user
        )
        
        self.client.login(username='testuser', password='testpass')
        
        # Test access to other user's task
        response = self.client.get(reverse('tasks:task_detail', kwargs={'pk': task.pk}))
        self.assertEqual(response.status_code, 404)
        
        # Test editing other user's task
        response = self.client.get(reverse('tasks:task_update', kwargs={'pk': task.pk}))
        self.assertEqual(response.status_code, 404)
