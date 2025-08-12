import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, ModelMultipleChoiceField
from datetime import date, timedelta
from decimal import Decimal

from projects.models import Project
from tasks.models import Task, TaskComment
from tasks.forms import TaskForm, TaskFilterForm, TaskCommentForm


@pytest.mark.django_db
class TestTaskForm(TestCase):
    """Test the TaskForm functionality."""
    
    def setUp(self):
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
        
        # Create existing task for dependencies
        self.existing_task = Task.objects.create(
            title='Existing Task',
            project=self.project,
            creator=self.user
        )
    
    def test_form_init_with_user(self):
        """Test form initialization with user parameter."""
        form = TaskForm(user=self.user)
        
        # Should limit projects to user's projects
        project_choices = list(form.fields['project'].queryset)
        self.assertIn(self.project, project_choices)
        self.assertNotIn(self.other_project, project_choices)
        
        # Should include user in assignee choices
        assignee_choices = list(form.fields['assignee'].queryset)
        self.assertIn(self.user, assignee_choices)
    
    def test_form_init_with_project(self):
        """Test form initialization with project parameter."""
        form = TaskForm(user=self.user, project=self.project)
        
        # Should set project as initial value
        self.assertEqual(form.fields['project'].initial, self.project)
        
        # Should make project field readonly
        self.assertTrue(form.fields['project'].widget.attrs.get('readonly'))
    
    def test_form_init_with_existing_instance(self):
        """Test form initialization with existing task instance."""
        parent_task = Task.objects.create(
            title='Parent Task',
            project=self.project,
            creator=self.user
        )
        
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
        
        form = TaskForm(instance=task, user=self.user)
        
        # Should configure dependencies and parent_task based on existing project
        self.assertEqual(form.fields['dependencies'].queryset.count(), 2)  # existing_task and parent_task
        self.assertIn(self.existing_task, form.fields['dependencies'].queryset)
        self.assertIn(parent_task, form.fields['dependencies'].queryset)
        self.assertNotIn(task, form.fields['dependencies'].queryset)  # Exclude self
    
    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            'title': 'New Task',
            'description': 'A test task description',
            'project': self.project.id,
            'status': 'todo',
            'priority': 'medium',
            'task_type': 'feature',
            'estimated_hours': Decimal('8.0'),
            'due_date': date.today() + timedelta(days=7),
            'start_date': date.today(),
            'progress_percentage': 0,
            'tags': 'test, feature, backend',
            'external_url': 'https://github.com/test/repo',
            'notes': 'Some additional notes'
        }
        
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        task = form.save(commit=False)
        task.creator = self.user
        task.save()
        
        self.assertEqual(task.title, 'New Task')
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.estimated_hours, Decimal('8.0'))
    
    def test_form_minimal_valid_data(self):
        """Test form with minimal required data."""
        form_data = {
            'title': 'Minimal Task',
            'project': self.project.id
        }
        
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_title_validation(self):
        """Test title field validation."""
        # Test empty title
        form_data = {
            'project': self.project.id
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        
        # Test title too short
        form_data = {
            'title': 'AB',  # Only 2 characters
            'project': self.project.id
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        
        # Test title too long
        form_data = {
            'title': 'A' * 201,  # Exceeds 200 character limit
            'project': self.project.id
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        
        # Test valid title
        form_data = {
            'title': 'Valid Task Title',
            'project': self.project.id
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_description_validation(self):
        """Test description field validation."""
        # Test very short description
        form_data = {
            'title': 'Test Task',
            'description': 'ABC',  # Too short
            'project': self.project.id
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)
        
        # Test valid description
        form_data = {
            'title': 'Test Task',
            'description': 'A proper task description',
            'project': self.project.id
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_estimated_hours_validation(self):
        """Test estimated hours field validation."""
        # Test negative hours
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'estimated_hours': Decimal('-1.0')
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_hours', form.errors)
        
        # Test zero hours
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'estimated_hours': Decimal('0.0')
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_hours', form.errors)
        
        # Test too many hours
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'estimated_hours': Decimal('1000.0')
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_hours', form.errors)
        
        # Test valid hours
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'estimated_hours': Decimal('8.5')
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_progress_percentage_validation(self):
        """Test progress percentage field validation."""
        # Test negative percentage
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'progress_percentage': -1
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('progress_percentage', form.errors)
        
        # Test percentage over 100
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'progress_percentage': 101
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('progress_percentage', form.errors)
        
        # Test valid percentage
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'progress_percentage': 50
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_tags_validation_and_normalization(self):
        """Test tags field validation and normalization."""
        # Test valid tags
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'tags': 'frontend, Backend, UI-UX, test_tag'
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        # Tags should be normalized (lowercase, deduplicated)
        cleaned_tags = form.cleaned_data['tags']
        expected_tags = 'frontend, backend, ui-ux, test_tag'
        self.assertEqual(cleaned_tags, expected_tags)
        
        # Test duplicate tags removal
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'tags': 'frontend, Frontend, FRONTEND, backend'
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        cleaned_tags = form.cleaned_data['tags']
        self.assertEqual(cleaned_tags, 'frontend, backend')
        
        # Test too many tags
        many_tags = ', '.join([f'tag{i}' for i in range(25)])  # 25 tags
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'tags': many_tags
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('tags', form.errors)
        
        # Test invalid tag characters
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'tags': 'valid-tag, invalid@tag, another#tag'
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('tags', form.errors)
        
        # Test tag too long
        long_tag = 'a' * 51  # 51 characters
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'tags': f'valid-tag, {long_tag}'
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('tags', form.errors)
    
    def test_date_validation(self):
        """Test date field validation."""
        # Test start date after due date
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'start_date': date.today() + timedelta(days=7),
            'due_date': date.today()
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        
        # Test valid dates
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'start_date': date.today(),
            'due_date': date.today() + timedelta(days=7)
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_parent_task_validation(self):
        """Test parent task validation."""
        # Create task and try to set itself as parent (should be prevented in form logic)
        task = Task.objects.create(
            title='Self Parent Task',
            project=self.project,
            creator=self.user
        )
        
        form_data = {
            'title': 'Updated Task',
            'project': self.project.id,
            'parent_task': task.id
        }
        form = TaskForm(data=form_data, instance=task, user=self.user)
        
        # Form should be invalid due to self-parent validation
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        
        # Test parent task in different project
        other_task = Task.objects.create(
            title='Other Project Task',
            project=self.other_project,
            creator=self.other_user
        )
        
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'parent_task': other_task.id
        }
        form = TaskForm(data=form_data, user=self.user)
        
        # Should be invalid due to different project
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
    
    def test_dependencies_validation(self):
        """Test dependencies validation."""
        task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user
        )
        
        # Test dependency in different project
        other_task = Task.objects.create(
            title='Other Project Task',
            project=self.other_project,
            creator=self.other_user
        )
        
        form_data = {
            'title': 'Updated Task',
            'project': self.project.id,
            'dependencies': [other_task.id]
        }
        form = TaskForm(data=form_data, instance=task, user=self.user)
        
        # Should be invalid due to different project
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        
        # Test valid dependency
        form_data = {
            'title': 'Updated Task',
            'project': self.project.id,
            'dependencies': [self.existing_task.id]
        }
        form = TaskForm(data=form_data, instance=task, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_status_progress_sync(self):
        """Test automatic progress percentage sync with status."""
        # Test done status with low progress
        form_data = {
            'title': 'Test Task',
            'project': self.project.id,
            'status': 'done',
            'progress_percentage': 50
        }
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        # Progress should be automatically set to 100 for done status
        self.assertEqual(form.cleaned_data['progress_percentage'], 100)
    
    def test_form_save_with_dependencies(self):
        """Test saving form with dependencies."""
        dependency1 = Task.objects.create(
            title='Dependency 1',
            project=self.project,
            creator=self.user
        )
        dependency2 = Task.objects.create(
            title='Dependency 2',
            project=self.project,
            creator=self.user
        )
        
        form_data = {
            'title': 'Task with Dependencies',
            'project': self.project.id,
            'dependencies': [dependency1.id, dependency2.id]
        }
        
        form = TaskForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        task = form.save(commit=False)
        task.creator = self.user
        task.save()
        form.save_m2m()  # Save many-to-many relationships
        
        # Check dependencies were saved
        self.assertEqual(task.dependencies.count(), 2)
        self.assertIn(dependency1, task.dependencies.all())
        self.assertIn(dependency2, task.dependencies.all())


@pytest.mark.django_db
class TestTaskFilterForm(TestCase):
    """Test the TaskFilterForm functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.other_user = User.objects.create_user(username='otheruser', password='testpass')
        
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
        
        # Create task for assignee filtering
        self.task = Task.objects.create(
            title='Test Task',
            project=self.project,
            creator=self.user,
            assignee=self.other_user
        )
    
    def test_form_init_with_user(self):
        """Test form initialization with user parameter."""
        form = TaskFilterForm(user=self.user)
        
        # Should include users from user's projects
        assignee_choices = list(form.fields['assignee'].queryset)
        self.assertIn(self.user, assignee_choices)
        self.assertIn(self.other_user, assignee_choices)  # Has tasks in user's project
    
    def test_form_init_with_project(self):
        """Test form initialization with project parameter."""
        form = TaskFilterForm(project=self.project)
        
        # Should include project owner and users with tasks in project
        assignee_choices = list(form.fields['assignee'].queryset)
        self.assertIn(self.user, assignee_choices)  # Project owner
        self.assertIn(self.other_user, assignee_choices)  # Has tasks in project
    
    def test_form_all_fields_optional(self):
        """Test that all form fields are optional."""
        form = TaskFilterForm(data={}, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_form_valid_filter_data(self):
        """Test form with valid filter data."""
        form_data = {
            'status': 'todo',
            'priority': 'high',
            'task_type': 'feature',
            'assignee': self.user.id,
            'due_date_filter': 'week',
            'search': 'test query'
        }
        
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        self.assertEqual(form.cleaned_data['status'], 'todo')
        self.assertEqual(form.cleaned_data['priority'], 'high')
        self.assertEqual(form.cleaned_data['task_type'], 'feature')
        self.assertEqual(form.cleaned_data['assignee'], self.user)
        self.assertEqual(form.cleaned_data['due_date_filter'], 'week')
        self.assertEqual(form.cleaned_data['search'], 'test query')
    
    def test_search_validation(self):
        """Test search field validation."""
        # Test search too short
        form_data = {
            'search': 'a'  # Only 1 character
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('search', form.errors)
        
        # Test search too long
        form_data = {
            'search': 'a' * 101  # 101 characters
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('search', form.errors)
        
        # Test valid search
        form_data = {
            'search': 'valid search query'
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        # Test search with whitespace (should be stripped)
        form_data = {
            'search': '  spaced search  '
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['search'], 'spaced search')
    
    def test_choice_field_validation(self):
        """Test choice field validation."""
        # Test invalid status
        form_data = {
            'status': 'invalid_status'
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)
        
        # Test invalid priority
        form_data = {
            'priority': 'invalid_priority'
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('priority', form.errors)
        
        # Test invalid task_type
        form_data = {
            'task_type': 'invalid_type'
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('task_type', form.errors)
        
        # Test invalid due_date_filter
        form_data = {
            'due_date_filter': 'invalid_filter'
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('due_date_filter', form.errors)
    
    def test_assignee_field_validation(self):
        """Test assignee field validation."""
        # Test invalid assignee ID
        form_data = {
            'assignee': 99999  # Non-existent user ID
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('assignee', form.errors)
        
        # Test valid assignee
        form_data = {
            'assignee': self.user.id
        }
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
    
    def test_form_choice_labels(self):
        """Test that form choice fields have proper labels."""
        form = TaskFilterForm(user=self.user)
        
        # Check that 'All' options are available
        status_choices = form.fields['status'].choices
        self.assertEqual(status_choices[0][0], '')  # Empty choice for 'All'
        self.assertIn('All Status', status_choices[0][1])
        
        priority_choices = form.fields['priority'].choices
        self.assertEqual(priority_choices[0][0], '')
        self.assertIn('All Priorities', priority_choices[0][1])
        
        assignee_choices = form.fields['assignee'].choices
        self.assertEqual(list(assignee_choices)[0][0], '')  # Empty choice
        self.assertIn('All Assignees', list(assignee_choices)[0][1])


@pytest.mark.django_db
class TestTaskCommentForm(TestCase):
    """Test the TaskCommentForm functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
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
    
    def test_form_valid_data(self):
        """Test form with valid comment data."""
        form_data = {
            'content': 'This is a valid comment with enough content.'
        }
        
        form = TaskCommentForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        comment = form.save(commit=False)
        comment.task = self.task
        comment.author = self.user
        comment.save()
        
        self.assertEqual(comment.content, 'This is a valid comment with enough content.')
        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.author, self.user)
    
    def test_form_empty_content(self):
        """Test form with empty content."""
        form_data = {
            'content': ''
        }
        
        form = TaskCommentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
    
    def test_form_content_too_short(self):
        """Test form with content too short."""
        form_data = {
            'content': 'AB'  # Only 2 characters
        }
        
        form = TaskCommentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
    
    def test_form_content_too_long(self):
        """Test form with content too long."""
        form_data = {
            'content': 'A' * 2001  # Exceeds 2000 character limit
        }
        
        form = TaskCommentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
    
    def test_form_content_validation_and_cleaning(self):
        """Test content validation and cleaning."""
        # Test content with leading/trailing whitespace
        form_data = {
            'content': '   This comment has whitespace   '
        }
        
        form = TaskCommentForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Content should be stripped
        cleaned_content = form.cleaned_data['content']
        self.assertEqual(cleaned_content, 'This comment has whitespace')
    
    def test_form_content_with_special_characters(self):
        """Test form with special characters and unicode."""
        form_data = {
            'content': 'Comment with éspecial characters & émojis 🚀 and symbols @#$%'
        }
        
        form = TaskCommentForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        cleaned_content = form.cleaned_data['content']
        self.assertEqual(cleaned_content, 'Comment with éspecial characters & émojis 🚀 and symbols @#$%')
    
    def test_form_content_with_newlines(self):
        """Test form with multiline content."""
        multiline_content = """This is a comment
with multiple lines
and proper formatting."""
        
        form_data = {
            'content': multiline_content
        }
        
        form = TaskCommentForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        cleaned_content = form.cleaned_data['content']
        self.assertEqual(cleaned_content, multiline_content)
    
    def test_form_widget_attributes(self):
        """Test that form widget has correct attributes."""
        form = TaskCommentForm()
        
        content_widget = form.fields['content'].widget
        self.assertEqual(content_widget.attrs.get('rows'), 3)
        self.assertIn('placeholder', content_widget.attrs)
        self.assertIn('class', content_widget.attrs)
    
    def test_form_field_help_text(self):
        """Test form field help text and labels."""
        form = TaskCommentForm()
        
        # The field should have appropriate verbose names from the model
        content_field = form.fields['content']
        self.assertIsNotNone(content_field.label)


@pytest.mark.django_db
class TestFormIntegration(TestCase):
    """Test integration between different forms."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
    
    def test_task_form_to_comment_form_workflow(self):
        """Test workflow from creating task to adding comments."""
        # Create task using TaskForm
        task_form_data = {
            'title': 'Integration Test Task',
            'description': 'A task for integration testing',
            'project': self.project.id,
            'status': 'todo',
            'priority': 'medium'
        }
        
        task_form = TaskForm(data=task_form_data, user=self.user)
        self.assertTrue(task_form.is_valid())
        
        task = task_form.save(commit=False)
        task.creator = self.user
        task.save()
        
        # Add comment using TaskCommentForm
        comment_form_data = {
            'content': 'This is a comment on the newly created task.'
        }
        
        comment_form = TaskCommentForm(data=comment_form_data)
        self.assertTrue(comment_form.is_valid())
        
        comment = comment_form.save(commit=False)
        comment.task = task
        comment.author = self.user
        comment.save()
        
        # Verify the integration
        self.assertEqual(task.comments.count(), 1)
        self.assertEqual(task.comments.first(), comment)
        self.assertEqual(comment.task, task)
    
    def test_filter_form_with_created_tasks(self):
        """Test filter form with tasks created via TaskForm."""
        # Create multiple tasks with different attributes
        tasks_data = [
            {
                'title': 'High Priority Task',
                'project': self.project.id,
                'priority': 'high',
                'status': 'todo',
                'task_type': 'feature'
            },
            {
                'title': 'Bug Fix Task',
                'project': self.project.id,
                'priority': 'medium',
                'status': 'in_progress',
                'task_type': 'bug'
            },
            {
                'title': 'Completed Task',
                'project': self.project.id,
                'priority': 'low',
                'status': 'done',
                'task_type': 'improvement'
            }
        ]
        
        created_tasks = []
        for task_data in tasks_data:
            form = TaskForm(data=task_data, user=self.user)
            self.assertTrue(form.is_valid())
            
            task = form.save(commit=False)
            task.creator = self.user
            task.assignee = self.user
            task.save()
            created_tasks.append(task)
        
        # Test filtering
        filter_form_data = {
            'status': 'todo',
            'priority': 'high'
        }
        
        filter_form = TaskFilterForm(data=filter_form_data, user=self.user)
        self.assertTrue(filter_form.is_valid())
        
        # Verify filter form choices include the created tasks' assignee
        assignee_choices = list(filter_form.fields['assignee'].queryset)
        self.assertIn(self.user, assignee_choices)


@pytest.mark.django_db
class TestFormErrorHandling(TestCase):
    """Test error handling in forms."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user
        )
    
    def test_task_form_multiple_validation_errors(self):
        """Test TaskForm with multiple validation errors."""
        form_data = {
            'title': 'AB',  # Too short
            'description': 'XYZ',  # Too short
            'project': self.project.id,
            'estimated_hours': Decimal('-1.0'),  # Negative
            'progress_percentage': 150,  # Over 100
            'start_date': date.today() + timedelta(days=7),
            'due_date': date.today(),  # Before start date
            'tags': 'a' * 51  # Too long
        }
        
        form = TaskForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        
        # Should have multiple errors
        self.assertIn('title', form.errors)
        self.assertIn('description', form.errors)
        self.assertIn('estimated_hours', form.errors)
        self.assertIn('progress_percentage', form.errors)
        self.assertIn('tags', form.errors)
        self.assertIn('__all__', form.errors)  # Cross-field validation error
    
    def test_form_with_missing_required_dependencies(self):
        """Test form behavior when required objects are missing."""
        # Try to create TaskForm without providing user
        with self.assertRaises(AttributeError):
            form = TaskForm()
            # This should fail when trying to filter querysets
            list(form.fields['project'].queryset)
    
    def test_comment_form_edge_cases(self):
        """Test TaskCommentForm edge cases."""
        # Test with only whitespace
        form_data = {
            'content': '   \n\t   '
        }
        form = TaskCommentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
        
        # Test with minimum valid length after stripping
        form_data = {
            'content': '  ABC  '  # Will be stripped to 'ABC' (3 chars - minimum)
        }
        form = TaskCommentForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['content'], 'ABC')
    
    def test_filter_form_with_invalid_user_context(self):
        """Test TaskFilterForm with invalid user context."""
        # Create form with non-existent user ID in assignee field
        form_data = {
            'assignee': 99999  # Non-existent user
        }
        
        form = TaskFilterForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('assignee', form.errors)
