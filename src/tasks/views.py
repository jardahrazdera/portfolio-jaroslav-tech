from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, IntegrityError
from datetime import datetime, timedelta
import logging

from projects.models import Project
from .models import Task, TaskComment
from .forms import TaskForm, TaskFilterForm, TaskCommentForm

# Set up logging
logger = logging.getLogger(__name__)


class TaskListView(LoginRequiredMixin, ListView):
    """
    List view for tasks with filtering and search capabilities.
    """
    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"
    paginate_by = 20

    def get_queryset(self):
        try:
            # Get tasks for projects owned by the user or assigned to the user
            queryset = Task.objects.select_related("project", "assignee", "creator").prefetch_related("dependencies")
            
            # Filter based on permissions
            queryset = queryset.filter(
                Q(project__owner=self.request.user) | Q(assignee=self.request.user)
            ).distinct()
            
            # Apply filters
            form = TaskFilterForm(self.request.GET, user=self.request.user)
            if form.is_valid():
                # Status filter
                status = form.cleaned_data.get("status")
                if status:
                    queryset = queryset.filter(status=status)
                
                # Priority filter
                priority = form.cleaned_data.get("priority")
                if priority:
                    queryset = queryset.filter(priority=priority)
                
                # Task type filter
                task_type = form.cleaned_data.get("task_type")
                if task_type:
                    queryset = queryset.filter(task_type=task_type)
                
                # Assignee filter
                assignee = form.cleaned_data.get("assignee")
                if assignee:
                    queryset = queryset.filter(assignee=assignee)
                
                # Due date filter
                due_date_filter = form.cleaned_data.get("due_date_filter")
                if due_date_filter:
                    today = timezone.now().date()
                    if due_date_filter == "overdue":
                        queryset = queryset.filter(due_date__lt=today, status__in=["todo", "in_progress"])
                    elif due_date_filter == "today":
                        queryset = queryset.filter(due_date=today)
                    elif due_date_filter == "week":
                        week_end = today + timedelta(days=7)
                        queryset = queryset.filter(due_date__lte=week_end, due_date__gte=today)
                    elif due_date_filter == "month":
                        month_end = today + timedelta(days=30)
                        queryset = queryset.filter(due_date__lte=month_end, due_date__gte=today)
                    elif due_date_filter == "no_date":
                        queryset = queryset.filter(due_date__isnull=True)
                
                # Search filter
                search = form.cleaned_data.get("search")
                if search:
                    queryset = queryset.filter(
                        Q(title__icontains=search) |
                        Q(description__icontains=search) |
                        Q(tags__icontains=search)
                    )
            
            return queryset.order_by("-created_at")
            
        except Exception as e:
            logger.error(f"Error in TaskListView.get_queryset(): {str(e)}")
            messages.error(self.request, "There was an error loading tasks.")
            return Task.objects.none()

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context["filter_form"] = TaskFilterForm(self.request.GET, user=self.request.user)
            
            # Add statistics
            user_tasks = Task.objects.filter(
                Q(project__owner=self.request.user) | Q(assignee=self.request.user)
            ).distinct()
            
            context["stats"] = {
                "total_tasks": user_tasks.count(),
                "todo": user_tasks.filter(status="todo").count(),
                "in_progress": user_tasks.filter(status="in_progress").count(),
                "done": user_tasks.filter(status="done").count(),
                "overdue": user_tasks.filter(
                    due_date__lt=timezone.now().date(),
                    status__in=["todo", "in_progress"]
                ).count(),
            }
            
            return context
        except Exception as e:
            logger.error(f"Error in TaskListView.get_context_data(): {str(e)}")
            return context


class TaskDetailView(LoginRequiredMixin, DetailView):
    """
    Detailed view of a single task with comments.
    """
    model = Task
    template_name = "tasks/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.select_related("project", "assignee", "creator", "parent_task").prefetch_related(
            "dependencies", "subtasks", "comments__author"
        ).filter(
            Q(project__owner=self.request.user) | Q(assignee=self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        
        # Check if user can edit this task
        context["can_edit"] = task.can_be_edited_by(self.request.user)
        
        # Add comment form
        context["comment_form"] = TaskCommentForm()
        
        # Add related tasks
        context["subtasks"] = task.subtasks.all().order_by("created_at")
        context["dependencies"] = task.dependencies.all()
        
        return context


class TaskCreateView(LoginRequiredMixin, CreateView):
    """
    Create new task view.
    """
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        
        # If project_id is provided in URL, set project context
        project_id = self.kwargs.get("project_id")
        if project_id:
            try:
                project = get_object_or_404(Project, id=project_id, owner=self.request.user)
                kwargs["project"] = project
            except Http404:
                messages.error(self.request, "Project not found or access denied.")
        
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                form.instance.creator = self.request.user
                
                # Set assignee to creator if not specified
                if not form.instance.assignee:
                    form.instance.assignee = self.request.user
                
                response = super().form_valid(form)
                
                logger.info(f"Task '{self.object.title}' created by user {self.request.user.id}")
                messages.success(
                    self.request, 
                    f"Task '{self.object.title}' created successfully\!"
                )
                
                return response
                
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            messages.error(self.request, "There was an error creating the task.")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("tasks:task_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create New Task"
        context["submit_text"] = "Create Task"
        return context


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update existing task view.
    """
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"

    def get_queryset(self):
        return Task.objects.filter(
            Q(project__owner=self.request.user) | 
            Q(assignee=self.request.user) | 
            Q(creator=self.request.user)
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Check if user can edit this task
        if not self.object.can_be_edited_by(self.request.user):
            messages.error(self.request, "You don't have permission to edit this task.")
            return redirect(self.object.get_absolute_url())
        
        messages.success(self.request, "Task updated successfully\!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("tasks:task_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit Task: {self.object.title}"
        context["submit_text"] = "Update Task"
        return context


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete task view.
    """
    model = Task
    template_name = "tasks/task_confirm_delete.html"

    def get_queryset(self):
        return Task.objects.filter(
            Q(project__owner=self.request.user) | 
            Q(creator=self.request.user)
        )

    def delete(self, request, *args, **kwargs):
        task = self.get_object()
        
        # Check if user can delete this task
        if not (task.creator == request.user or task.project.owner == request.user):
            messages.error(request, "You don't have permission to delete this task.")
            return redirect(task.get_absolute_url())
        
        messages.success(request, f"Task '{task.title}' deleted successfully\!")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("tasks:task_list")


@login_required
def add_task_comment(request, task_id):
    """
    Add a comment to a task.
    """
    try:
        task = get_object_or_404(
            Task.objects.select_related("project"),
            id=task_id
        )
        
        # Check permissions
        if not (task.project.owner == request.user or 
                task.assignee == request.user or 
                task.creator == request.user):
            messages.error(request, "You don't have permission to comment on this task.")
            return redirect(task.get_absolute_url())
        
        if request.method == "POST":
            form = TaskCommentForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        comment = form.save(commit=False)
                        comment.task = task
                        comment.author = request.user
                        comment.save()
                        
                        messages.success(request, "Comment added successfully\!")
                        logger.info(f"Comment added to task {task.id} by user {request.user.id}")
                        
                except Exception as e:
                    logger.error(f"Error adding comment: {str(e)}")
                    messages.error(request, "There was an error adding your comment.")
            else:
                messages.error(request, "Invalid comment data.")
        
        return redirect(task.get_absolute_url())
        
    except Exception as e:
        logger.error(f"Error in add_task_comment: {str(e)}")
        messages.error(request, "There was an error processing your request.")
        return redirect("tasks:task_list")


@login_required
def mark_task_complete(request, task_id):
    """
    Mark a task as completed.
    """
    try:
        task = get_object_or_404(
            Task.objects.select_related("project"),
            id=task_id
        )
        
        # Check permissions
        if not task.can_be_edited_by(request.user):
            messages.error(request, "You don't have permission to modify this task.")
            return redirect(task.get_absolute_url())
        
        if request.method == "POST":
            try:
                with transaction.atomic():
                    task.mark_completed()
                    messages.success(request, f"Task '{task.title}' marked as completed\!")
                    logger.info(f"Task {task.id} marked complete by user {request.user.id}")
                    
            except Exception as e:
                logger.error(f"Error marking task complete: {str(e)}")
                messages.error(request, "There was an error updating the task.")
        
        return redirect(task.get_absolute_url())
        
    except Exception as e:
        logger.error(f"Error in mark_task_complete: {str(e)}")
        messages.error(request, "There was an error processing your request.")
        return redirect("tasks:task_list")


@login_required
def project_tasks_view(request, project_id):
    """
    View all tasks for a specific project.
    """
    try:
        project = get_object_or_404(Project, id=project_id, owner=request.user)
        
        tasks = Task.objects.filter(project=project).select_related(
            "assignee", "creator"
        ).prefetch_related("dependencies")
        
        # Apply filters
        form = TaskFilterForm(request.GET, project=project)
        if form.is_valid():
            # Apply same filtering logic as TaskListView
            status = form.cleaned_data.get("status")
            if status:
                tasks = tasks.filter(status=status)
            
            priority = form.cleaned_data.get("priority")
            if priority:
                tasks = tasks.filter(priority=priority)
            
            task_type = form.cleaned_data.get("task_type")
            if task_type:
                tasks = tasks.filter(task_type=task_type)
            
            assignee = form.cleaned_data.get("assignee")
            if assignee:
                tasks = tasks.filter(assignee=assignee)
            
            search = form.cleaned_data.get("search")
            if search:
                tasks = tasks.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(tags__icontains=search)
                )
        
        # Get project task statistics
        project_stats = Task.get_project_stats(project)
        
        context = {
            "project": project,
            "tasks": tasks.order_by("-created_at"),
            "filter_form": form,
            "stats": project_stats,
        }
        
        return render(request, "tasks/project_tasks.html", context)
        
    except Exception as e:
        logger.error(f"Error in project_tasks_view: {str(e)}")
        messages.error(request, "There was an error loading project tasks.")
        return redirect("projects:project_list")


@login_required 
def task_api_list(request):
    """
    JSON API endpoint for tasks with filtering.
    """
    try:
        # Get user's tasks
        tasks = Task.objects.filter(
            Q(project__owner=request.user) | Q(assignee=request.user)
        ).select_related("project", "assignee").distinct()
        
        # Apply filters
        status = request.GET.get("status")
        if status:
            tasks = tasks.filter(status=status)
        
        project_id = request.GET.get("project")
        if project_id:
            try:
                tasks = tasks.filter(project_id=int(project_id))
            except (ValueError, TypeError):
                return JsonResponse({"error": "Invalid project ID"}, status=400)
        
        assignee_id = request.GET.get("assignee")
        if assignee_id:
            try:
                tasks = tasks.filter(assignee_id=int(assignee_id))
            except (ValueError, TypeError):
                return JsonResponse({"error": "Invalid assignee ID"}, status=400)
        
        # Pagination
        try:
            page = max(1, int(request.GET.get("page", 1)))
            limit = min(50, max(1, int(request.GET.get("limit", 20))))
            offset = (page - 1) * limit
            
            total_count = tasks.count()
            tasks = tasks[offset:offset + limit]
            
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid pagination parameters"}, status=400)
        
        # Serialize data
        task_data = []
        for task in tasks:
            task_dict = {
                "id": str(task.id),
                "title": task.title,
                "description": task.description or "",
                "status": task.status,
                "status_display": task.get_status_display(),
                "priority": task.priority,
                "priority_display": task.get_priority_display(),
                "task_type": task.task_type,
                "progress_percentage": task.progress_percentage,
                "is_overdue": task.is_overdue,
                "can_start": task.can_start,
                "project": {
                    "id": task.project.id,
                    "title": task.project.title
                },
                "assignee": {
                    "id": task.assignee.id,
                    "username": task.assignee.username
                } if task.assignee else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "created_at": task.created_at.isoformat(),
                "url": request.build_absolute_uri(task.get_absolute_url()),
            }
            task_data.append(task_dict)
        
        response_data = {
            "tasks": task_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in task_api_list: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)
