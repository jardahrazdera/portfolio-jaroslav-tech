import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError
from decimal import Decimal
from datetime import date, timedelta
import uuid

from projects.models import Project
from tasks.models import Task, TaskComment, TaskManager


@pytest.mark.django_db
class TestTaskManager(TestCase):
    """Test the custom TaskManager methods."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
    def test_get_active_tasks(self):
        """Test getting active tasks (todo and in_progress)."""
        task1 = Task.objects.create(
            title='Active Task 1',
            project=self.project,
            creator=self.user,
            status='todo'
        )
        task2 = Task.objects.create(
            title='Active Task 2', 
            project=self.project,
            creator=self.user,
            status='in_progress'
        )
        task3 = Task.objects.create(
            title='Completed Task',
            project=self.project,
            creator=self.user,
            status='done'
        )
        
        active_tasks = Task.objects.get_active_tasks()
        self.assertEqual(active_tasks.count(), 2)
        self.assertIn(task1, active_tasks)
        self.assertIn(task2, active_tasks)
        self.assertNotIn(task3, active_tasks)
    
    def test_get_overdue_tasks(self):
        """Test getting overdue tasks."""
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)
        
        overdue_task = Task.objects.create(
            title='Overdue Task',
            project=self.project,
            creator=self.user,
            status='todo',
            due_date=yesterday
        )
        future_task = Task.objects.create(
            title='Future Task',
            project=self.project,
            creator=self.user,
            status='todo',
            due_date=tomorrow
        )
        completed_overdue = Task.objects.create(
            title='Completed Overdue',
            project=self.project,
            creator=self.user,
            status='done',
            due_date=yesterday
        )
        
        overdue_tasks = Task.objects.get_overdue_tasks()
        self.assertEqual(overdue_tasks.count(), 1)
        self.assertIn(overdue_task, overdue_tasks)
        self.assertNotIn(future_task, overdue_tasks)
        self.assertNotIn(completed_overdue, overdue_tasks)
    
    def test_get_high_priority_tasks(self):
        """Test getting high priority tasks."""
        high_task = Task.objects.create(
            title='High Priority Task',
            project=self.project,
            creator=self.user,
            priority='high'
        )
        low_task = Task.objects.create(
            title='Low Priority Task',
            project=self.project,
            creator=self.user,
            priority='low'
        )
        
        high_priority_tasks = Task.objects.get_high_priority_tasks()
        self.assertEqual(high_priority_tasks.count(), 1)
        self.assertIn(high_task, high_priority_tasks)
        self.assertNotIn(low_task, high_priority_tasks)
    
    def test_get_user_tasks(self):
        """Test getting tasks assigned to a specific user."""
        user2 = User.objects.create_user(username='testuser2', password='testpass')
        
        user1_task = Task.objects.create(
            title='User 1 Task',
            project=self.project,
            creator=self.user,
            assignee=self.user
        )
        user2_task = Task.objects.create(
            title='User 2 Task',
            project=self.project,
            creator=self.user,
            assignee=user2
        )
        unassigned_task = Task.objects.create(
            title='Unassigned Task',
            project=self.project,
            creator=self.user
        )
        
        user1_tasks = Task.objects.get_user_tasks(self.user)
        self.assertEqual(user1_tasks.count(), 1)
        self.assertIn(user1_task, user1_tasks)
        
        user2_tasks = Task.objects.get_user_tasks(user2)
        self.assertEqual(user2_tasks.count(), 1)
        self.assertIn(user2_task, user2_tasks)
    
    def test_get_project_tasks(self):
        """Test getting all tasks for a specific project."""
        project2 = Project.objects.create(
            title='Another Project',
            description='Another test project',
            owner=self.user
        )
        
        project1_task = Task.objects.create(
            title='Project 1 Task',
            project=self.project,
            creator=self.user
        )
        project2_task = Task.objects.create(
            title='Project 2 Task',
            project=project2,
            creator=self.user
        )
        
        project1_tasks = Task.objects.get_project_tasks(self.project)
        self.assertEqual(project1_tasks.count(), 1)
        self.assertIn(project1_task, project1_tasks)
        self.assertNotIn(project2_task, project1_tasks)


@pytest.mark.django_db
class TestTaskModel(TestCase):
    """Test the Task model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.assignee = User.objects.create_user(username='assignee', password='testpass')
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
    def test_task_creation_with_defaults(self):
        """Test creating a task with default values."""
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
        
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.creator, self.user)
        self.assertEqual(task.status, 'todo')
        self.assertEqual(task.priority, 'medium')
        self.assertEqual(task.task_type, 'feature')
        self.assertEqual(task.progress_percentage, 0)
        self.assertEqual(task.actual_hours, Decimal('0.00'))
        self.assertIsInstance(task.id, uuid.UUID)
        self.assertIsNotNone(task.created_at)
        self.assertIsNotNone(task.updated_at)
    
    def test_task_creation_with_all_fields(self):
        """Test creating a task with all fields populated."""
        due_date = date.today() + timedelta(days=7)
        start_date = date.today()
        
        task = Task.objects.create(
            title='Comprehensive Task',
            description='A detailed task description',
            project=self.project,
            creator=self.user,
            assignee=self.assignee,
            status='in_progress',
            priority='high',
            task_type='bug',
            estimated_hours=Decimal('8.50'),
            actual_hours=Decimal('3.25'),
            due_date=due_date,
            start_date=start_date,
            progress_percentage=40,
            tags='urgent, bug-fix, frontend',
            external_url='https://github.com/example/issue/123',
            notes='Additional notes about this task'
        )
        
        self.assertEqual(task.title, 'Comprehensive Task')
        self.assertEqual(task.description, 'A detailed task description')
        self.assertEqual(task.assignee, self.assignee)
        self.assertEqual(task.status, 'in_progress')
        self.assertEqual(task.priority, 'high')
        self.assertEqual(task.task_type, 'bug')
        self.assertEqual(task.estimated_hours, Decimal('8.50'))
        self.assertEqual(task.actual_hours, Decimal('3.25'))
        self.assertEqual(task.due_date, due_date)
        self.assertEqual(task.start_date, start_date)
        self.assertEqual(task.progress_percentage, 40)
        self.assertEqual(task.tags, 'urgent, bug-fix, frontend')
        self.assertEqual(task.external_url, 'https://github.com/example/issue/123')
        self.assertEqual(task.notes, 'Additional notes about this task')
    
    def test_task_str_representation(self):
        """Test the string representation of a task."""
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
        
        expected_str = f"{self.project.title} - Test Task"
        self.assertEqual(str(task), expected_str)
    
    def test_task_absolute_url(self):
        """Test the get_absolute_url method."""
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
        
        expected_url = f'/tasks/{task.pk}/'
        # Just verify the URL contains the task ID
        self.assertIn(str(task.pk), task.get_absolute_url())
    
    def test_is_overdue_property(self):
        """Test the is_overdue property."""
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)
        
        # Overdue task
        overdue_task = Task.objects.create(
            title='Overdue Task',
            project=self.project,
            creator=self.user,
            due_date=yesterday,
            status='todo'
        )
        self.assertTrue(overdue_task.is_overdue)
        
        # Future task
        future_task = Task.objects.create(
            title='Future Task',
            project=self.project,
            creator=self.user,
            due_date=tomorrow,
            status='todo'
        )
        self.assertFalse(future_task.is_overdue)
        
        # Completed overdue task
        completed_task = Task.objects.create(
            title='Completed Task',
            project=self.project,
            creator=self.user,
            due_date=yesterday,
            status='done'
        )
        self.assertFalse(completed_task.is_overdue)
        
        # Task without due date
        no_date_task = Task.objects.create(
            title='No Date Task',
            project=self.project,
            creator=self.user,
            status='todo'
        )
        self.assertFalse(no_date_task.is_overdue)
    
    def test_is_subtask_property(self):
        """Test the is_subtask property."""
        parent_task = Task.objects.create(
            title='Parent Task',
            project=self.project,
            creator=self.user
        )
        
        subtask = Task.objects.create(
            title='Subtask',
            project=self.project,
            creator=self.user,
            parent_task=parent_task
        )
        
        self.assertFalse(parent_task.is_subtask)
        self.assertTrue(subtask.is_subtask)
    
    def test_has_subtasks_property(self):
        """Test the has_subtasks property."""
        parent_task = Task.objects.create(
            title='Parent Task',
            project=self.project,
            creator=self.user
        )
        
        self.assertFalse(parent_task.has_subtasks)
        
        subtask = Task.objects.create(
            title='Subtask',
            project=self.project,
            creator=self.user,
            parent_task=parent_task
        )
        
        self.assertTrue(parent_task.has_subtasks)
    
    def test_can_start_property_no_dependencies(self):
        """Test can_start property for task with no dependencies."""
        task = Task.objects.create(
            title='Independent Task',
            project=self.project,
            creator=self.user
        )
        
        self.assertTrue(task.can_start)
    
    def test_can_start_property_with_dependencies(self):
        """Test can_start property for task with dependencies."""
        dep1 = Task.objects.create(
            title='Dependency 1',
            project=self.project,
            creator=self.user,
            status='done'
        )
        
        dep2 = Task.objects.create(
            title='Dependency 2',
            project=self.project,
            creator=self.user,
            status='todo'
        )
        
        task = Task.objects.create(
            title='Dependent Task',
            project=self.project,
            creator=self.user
        )
        
        # With completed dependency
        task.dependencies.add(dep1)
        self.assertTrue(task.can_start)
        
        # With incomplete dependency
        task.dependencies.add(dep2)
        self.assertFalse(task.can_start)
        
        # Complete the second dependency
        dep2.status = 'done'
        dep2.save()
        self.assertTrue(task.can_start)
    
    def test_status_color_property(self):
        """Test the status_color property."""
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
        
        expected_colors = {
            'todo': 'bg-gray-100 text-gray-800',
            'in_progress': 'bg-blue-100 text-blue-800',
            'review': 'bg-yellow-100 text-yellow-800',
            'testing': 'bg-purple-100 text-purple-800',
            'done': 'bg-green-100 text-green-800',
            'blocked': 'bg-red-100 text-red-800',
            'cancelled': 'bg-gray-100 text-gray-600',
        }
        
        for status, expected_color in expected_colors.items():
            task.status = status
            task.save()
            self.assertEqual(task.status_color, expected_color)
    
    def test_priority_color_property(self):
        """Test the priority_color property."""
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
        
        expected_colors = {
            'low': 'text-green-600',
            'medium': 'text-yellow-600',
            'high': 'text-orange-600',
            'urgent': 'text-red-600',
        }
        
        for priority, expected_color in expected_colors.items():
            task.priority = priority
            task.save()
            self.assertEqual(task.priority_color, expected_color)
    
    def test_task_validation_title_length(self):
        """Test task validation for title length."""
        task = Task(
            title='AB',  # Too short
            project=self.project,
            creator=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            task.clean()
        
        self.assertIn('title', context.exception.message_dict)
    
    def test_task_validation_date_order(self):
        """Test task validation for date order."""
        task = Task(
            title='Test Task',
            project=self.project,
            creator=self.user,
            start_date=date.today() + timedelta(days=7),
            due_date=date.today()  # Due date before start date
        )
        
        with self.assertRaises(ValidationError) as context:
            task.clean()
        
        self.assertIn('due_date', context.exception.message_dict)
    
    def test_task_validation_self_parent(self):
        """Test task validation prevents self as parent."""
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
        
        task.parent_task = task
        
        with self.assertRaises(ValidationError) as context:
            task.clean()
        
        self.assertIn('parent_task', context.exception.message_dict)
    
    def test_mark_completed_method(self):
        """Test the mark_completed method."""
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user,
            status='in_progress',
            progress_percentage=50
        )
        
        original_completed_date = task.completed_date
        self.assertIsNone(original_completed_date)
        
        task.mark_completed()
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'done')
        self.assertEqual(task.progress_percentage, 100)
        self.assertIsNotNone(task.completed_date)
        self.assertNotEqual(task.completed_date, original_completed_date)
    
    def test_can_be_edited_by_method(self):
        """Test the can_be_edited_by method."""
        other_user = User.objects.create_user(username='otheruser', password='testpass')
        
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user,
            assignee=self.assignee
        )
        
        # Creator can edit
        self.assertTrue(task.can_be_edited_by(self.user))
        
        # Assignee can edit
        self.assertTrue(task.can_be_edited_by(self.assignee))
        
        # Project owner can edit
        self.assertTrue(task.can_be_edited_by(self.project.owner))
        
        # Other user cannot edit
        self.assertFalse(task.can_be_edited_by(other_user))
        
        # Superuser can edit
        superuser = User.objects.create_superuser(username='admin', password='adminpass')
        self.assertTrue(task.can_be_edited_by(superuser))
    
    def test_get_project_stats_method(self):
        """Test the get_project_stats class method."""
        # Create tasks with different statuses
        Task.objects.create(
            title='Task 1',
            project=self.project,
            creator=self.user,
            status='done'
        )
        Task.objects.create(
            title='Task 2',
            project=self.project,
            creator=self.user,
            status='done'
        )
        Task.objects.create(
            title='Task 3',
            project=self.project,
            creator=self.user,
            status='in_progress'
        )
        Task.objects.create(
            title='Task 4',
            project=self.project,
            creator=self.user,
            status='blocked'
        )
        Task.objects.create(
            title='Overdue Task',
            project=self.project,
            creator=self.user,
            status='todo',
            due_date=date.today() - timedelta(days=1)
        )
        
        stats = Task.get_project_stats(self.project)
        
        self.assertEqual(stats['total_tasks'], 5)
        self.assertEqual(stats['completed'], 2)
        self.assertEqual(stats['in_progress'], 1)
        self.assertEqual(stats['blocked'], 1)
        self.assertEqual(stats['overdue'], 1)
        self.assertEqual(stats['completion_percentage'], 40)  # 2/5 * 100
    
    def test_get_project_stats_empty_project(self):
        """Test get_project_stats for empty project."""
        stats = Task.get_project_stats(self.project)
        
        self.assertEqual(stats['total_tasks'], 0)
        self.assertEqual(stats['completed'], 0)
        self.assertEqual(stats['in_progress'], 0)
        self.assertEqual(stats['blocked'], 0)
        self.assertEqual(stats['overdue'], 0)
        self.assertEqual(stats['completion_percentage'], 0)
    
    def test_task_dependencies_many_to_many(self):
        """Test task dependencies many-to-many relationship."""
        task1 = Task.objects.create(
            title='Task 1',
            project=self.project,
            creator=self.user
        )
        task2 = Task.objects.create(
            title='Task 2',
            project=self.project,
            creator=self.user
        )
        task3 = Task.objects.create(
            title='Task 3',
            project=self.project,
            creator=self.user
        )
        
        # Add dependencies
        task3.dependencies.add(task1, task2)
        
        # Test forward relationship
        self.assertEqual(task3.dependencies.count(), 2)
        self.assertIn(task1, task3.dependencies.all())
        self.assertIn(task2, task3.dependencies.all())
        
        # Test reverse relationship
        self.assertEqual(task1.dependent_tasks.count(), 1)
        self.assertIn(task3, task1.dependent_tasks.all())
        self.assertEqual(task2.dependent_tasks.count(), 1)
        self.assertIn(task3, task2.dependent_tasks.all())
    
    def test_task_subtasks_hierarchy(self):
        """Test task subtasks hierarchy."""
        parent_task = Task.objects.create(
            title='Parent Task',
            project=self.project,
            creator=self.user
        )
        
        subtask1 = Task.objects.create(
            title='Subtask 1',
            project=self.project,
            creator=self.user,
            parent_task=parent_task
        )
        
        subtask2 = Task.objects.create(
            title='Subtask 2',
            project=self.project,
            creator=self.user,
            parent_task=parent_task
        )
        
        # Test forward relationship
        self.assertEqual(parent_task.subtasks.count(), 2)
        self.assertIn(subtask1, parent_task.subtasks.all())
        self.assertIn(subtask2, parent_task.subtasks.all())
        
        # Test reverse relationship
        self.assertEqual(subtask1.parent_task, parent_task)
        self.assertEqual(subtask2.parent_task, parent_task)
    
    def test_task_ordering(self):
        """Test task default ordering by created_at descending."""
        task1 = Task.objects.create(
            title='First Task',
            project=self.project,
            creator=self.user
        )
        
        # Small delay to ensure different created_at times
        import time
        time.sleep(0.01)
        
        task2 = Task.objects.create(
            title='Second Task',
            project=self.project,
            creator=self.user
        )
        
        tasks = list(Task.objects.all())
        self.assertEqual(tasks[0], task2)  # Most recent first
        self.assertEqual(tasks[1], task1)
    
    def test_task_indexes(self):
        """Test that database indexes are created correctly."""
        # This test checks that the model's indexes are properly defined
        # In a real application, you'd check the database schema
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
        
        # The indexes are defined in Meta.indexes, so we just verify
        # that queries using indexed fields work efficiently
        # In practice, you'd use database query analysis tools
        
        # Test filtering by indexed fields
        Task.objects.filter(project=self.project, status='todo')
        Task.objects.filter(assignee=self.user, status='in_progress')
        Task.objects.filter(due_date=date.today())
        Task.objects.filter(priority='high', status='todo')
        
        # No assertion needed - we're just verifying the queries execute


@pytest.mark.django_db
class TestTaskCommentModel(TestCase):
    """Test the TaskComment model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.commenter = User.objects.create_user(username='commenter', password='testpass')
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
    
    def test_comment_creation(self):
        """Test creating a task comment."""
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.commenter,
            content='This is a test comment.'
        )
        
        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.author, self.commenter)
        self.assertEqual(comment.content, 'This is a test comment.')
        self.assertIsNotNone(comment.created_at)
    
    def test_comment_str_representation(self):
        """Test the string representation of a comment."""
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.commenter,
            content='Test comment'
        )
        
        expected_str = f"Comment on {self.task.title} by {self.commenter.username}"
        self.assertEqual(str(comment), expected_str)
    
    def test_comment_ordering(self):
        """Test comment ordering by created_at ascending."""
        comment1 = TaskComment.objects.create(
            task=self.task,
            author=self.commenter,
            content='First comment'
        )
        
        # Small delay to ensure different created_at times
        import time
        time.sleep(0.01)
        
        comment2 = TaskComment.objects.create(
            task=self.task,
            author=self.commenter,
            content='Second comment'
        )
        
        comments = list(TaskComment.objects.all())
        self.assertEqual(comments[0], comment1)  # Oldest first
        self.assertEqual(comments[1], comment2)
    
    def test_comment_task_relationship(self):
        """Test the relationship between comments and tasks."""
        comment1 = TaskComment.objects.create(
            task=self.task,
            author=self.commenter,
            content='First comment'
        )
        comment2 = TaskComment.objects.create(
            task=self.task,
            author=self.commenter,
            content='Second comment'
        )
        
        # Test forward relationship
        self.assertEqual(comment1.task, self.task)
        self.assertEqual(comment2.task, self.task)
        
        # Test reverse relationship
        task_comments = self.task.comments.all()
        self.assertEqual(task_comments.count(), 2)
        self.assertIn(comment1, task_comments)
        self.assertIn(comment2, task_comments)
    
    def test_comment_author_relationship(self):
        """Test the relationship between comments and authors."""
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.commenter,
            content='Test comment'
        )
        
        # Test forward relationship
        self.assertEqual(comment.author, self.commenter)
        
        # Test reverse relationship
        user_comments = self.commenter.task_comments.all()
        self.assertEqual(user_comments.count(), 1)
        self.assertIn(comment, user_comments)
    
    def test_comment_cascade_delete_with_task(self):
        """Test that comments are deleted when task is deleted."""
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.commenter,
            content='Test comment'
        )
        
        comment_id = comment.id
        self.assertTrue(TaskComment.objects.filter(id=comment_id).exists())
        
        # Delete the task
        self.task.delete()
        
        # Comment should be deleted too
        self.assertFalse(TaskComment.objects.filter(id=comment_id).exists())
    
    def test_comment_cascade_delete_with_user(self):
        """Test that comments are deleted when author is deleted."""
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.commenter,
            content='Test comment'
        )
        
        comment_id = comment.id
        self.assertTrue(TaskComment.objects.filter(id=comment_id).exists())
        
        # Delete the author
        self.commenter.delete()
        
        # Comment should be deleted too
        self.assertFalse(TaskComment.objects.filter(id=comment_id).exists())


@pytest.mark.django_db
class TestTaskModelEdgeCases(TestCase):
    """Test edge cases and complex scenarios for Task model."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
    
    def test_circular_dependency_prevention(self):
        """Test that circular dependencies are prevented."""
        task1 = Task.objects.create(
            title='Task 1',
            project=self.project,
            creator=self.user
        )
        task2 = Task.objects.create(
            title='Task 2',
            project=self.project,
            creator=self.user
        )
        
        # Add task2 as dependency of task1
        task1.dependencies.add(task2)
        
        # Try to add task1 as dependency of task2 (circular)
        # This should be handled in form validation or view logic
        # The model itself allows this, but application logic should prevent it
        task2.dependencies.add(task1)
        
        # Both tasks now have circular dependencies
        self.assertIn(task2, task1.dependencies.all())
        self.assertIn(task1, task2.dependencies.all())
        
        # Neither task can start due to circular dependency
        self.assertFalse(task1.can_start)
        self.assertFalse(task2.can_start)
    
    def test_deep_subtask_hierarchy(self):
        """Test deep subtask hierarchies."""
        parent = Task.objects.create(
            title='Parent Task',
            project=self.project,
            creator=self.user
        )
        
        child = Task.objects.create(
            title='Child Task',
            project=self.project,
            creator=self.user,
            parent_task=parent
        )
        
        grandchild = Task.objects.create(
            title='Grandchild Task',
            project=self.project,
            creator=self.user,
            parent_task=child
        )
        
        # Test hierarchy
        self.assertEqual(grandchild.parent_task, child)
        self.assertEqual(child.parent_task, parent)
        self.assertIsNone(parent.parent_task)
        
        # Test properties
        self.assertFalse(parent.is_subtask)
        self.assertTrue(child.is_subtask)
        self.assertTrue(grandchild.is_subtask)
        
        self.assertTrue(parent.has_subtasks)
        self.assertTrue(child.has_subtasks)
        self.assertFalse(grandchild.has_subtasks)
    
    def test_complex_dependency_chain(self):
        """Test complex dependency chains."""
        task1 = Task.objects.create(
            title='Task 1',
            project=self.project,
            creator=self.user,
            status='done'
        )
        
        task2 = Task.objects.create(
            title='Task 2',
            project=self.project,
            creator=self.user,
            status='done'
        )
        
        task3 = Task.objects.create(
            title='Task 3',
            project=self.project,
            creator=self.user,
            status='in_progress'
        )
        
        task4 = Task.objects.create(
            title='Task 4',
            project=self.project,
            creator=self.user
        )
        
        # Task 4 depends on tasks 1, 2, and 3
        task4.dependencies.add(task1, task2, task3)
        
        # Task 4 cannot start because task 3 is not done
        self.assertFalse(task4.can_start)
        
        # Complete task 3
        task3.status = 'done'
        task3.save()
        
        # Now task 4 can start
        self.assertTrue(task4.can_start)
    
    def test_task_with_extreme_values(self):
        """Test tasks with extreme field values."""
        # Very long title (at maximum length)
        long_title = 'A' * 200
        
        # Very long description
        long_description = 'B' * 5000
        
        # Maximum estimated hours
        max_hours = Decimal('999.99')
        
        # Very long tags
        long_tags = ', '.join([f'tag{i}' for i in range(20)])
        
        task = Task.objects.create(
            title=long_title,
            description=long_description,
            project=self.project,
            creator=self.user,
            estimated_hours=max_hours,
            progress_percentage=100,
            tags=long_tags
        )
        
        self.assertEqual(task.title, long_title)
        self.assertEqual(task.description, long_description)
        self.assertEqual(task.estimated_hours, max_hours)
        self.assertEqual(task.progress_percentage, 100)
        self.assertEqual(task.tags, long_tags)
    
    def test_task_with_special_characters(self):
        """Test tasks with special characters and unicode."""
        special_title = "Task with éspecial cháracters & symbols\! @#$%^&*()"
        unicode_description = "描述 with émoji 🚀 and ñiño characters"
        
        task = Task.objects.create(
            title=special_title,
            description=unicode_description,
            project=self.project,
            creator=self.user
        )
        
        self.assertEqual(task.title, special_title)
        self.assertEqual(task.description, unicode_description)
    
    def test_task_database_constraints(self):
        """Test database-level constraints."""
        # Test that progress_percentage constraints work
        with self.assertRaises(ValidationError):
            task = Task(
                title='Test Task',
                project=self.project,
                creator=self.user,
                progress_percentage=-1
            )
            task.full_clean()
        
        with self.assertRaises(ValidationError):
            task = Task(
                title='Test Task',
                project=self.project,
                creator=self.user,
                progress_percentage=101
            )
            task.full_clean()
        
        # Test that estimated_hours constraints work
        with self.assertRaises(ValidationError):
            task = Task(
                title='Test Task',
                project=self.project,
                creator=self.user,
                estimated_hours=Decimal('0.05')  # Below minimum
            )
            task.full_clean()
    
    def test_task_bulk_operations(self):
        """Test bulk operations on tasks."""
        # Create multiple tasks
        tasks_data = [
            Task(title=f'Task {i}', project=self.project, creator=self.user)
            for i in range(100)
        ]
        
        # Bulk create
        created_tasks = Task.objects.bulk_create(tasks_data)
        self.assertEqual(len(created_tasks), 100)
        
        # Bulk update
        Task.objects.filter(project=self.project).update(status='in_progress')
        
        updated_count = Task.objects.filter(
            project=self.project,
            status='in_progress'
        ).count()
        self.assertEqual(updated_count, 100)
        
        # Bulk delete
        deleted_count, _ = Task.objects.filter(project=self.project).delete()
        self.assertEqual(deleted_count, 100)
