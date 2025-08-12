from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, IntegrityError
from datetime import datetime, timedelta
import logging

from .models import Project, Technology, WorkSession, ProjectImage, UserProfile
from .forms import ProjectForm, WorkSessionForm, ProjectImageForm, UserProfileForm, TechnologyFilterForm, BulkProjectActionForm

# Set up logging
logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """
    Main dashboard view showing project overview and statistics.
    Enhanced with comprehensive error handling and user feedback.
    """
    try:
        user_projects = Project.objects.filter(owner=request.user)
        
        # Project statistics with error handling
        try:
            total_projects = user_projects.count()
            active_projects = user_projects.filter(status__in=["planning", "development", "testing"]).count()
            completed_projects = user_projects.filter(status="completed").count()
        except Exception as e:
            logger.error(f"Error calculating project statistics for user {request.user.id}: {str(e)}")
            messages.error(request, "There was an issue loading your project statistics.")
            total_projects = active_projects = completed_projects = 0
        
        # Time tracking statistics with error handling
        try:
            total_hours_result = WorkSession.objects.filter(user=request.user).aggregate(
                total=Sum("duration_hours")
            )
            total_hours = total_hours_result["total"] or 0
            
            # Validate total hours is reasonable (not negative or extremely large)
            if total_hours < 0:
                logger.warning(f"Negative total hours detected for user {request.user.id}: {total_hours}")
                total_hours = 0
            elif total_hours > 10000:  # More than 10k hours seems unrealistic
                logger.warning(f"Unusually high total hours for user {request.user.id}: {total_hours}")
                
        except Exception as e:
            logger.error(f"Error calculating time statistics for user {request.user.id}: {str(e)}")
            messages.warning(request, "Could not load time tracking statistics.")
            total_hours = 0
        
        # Recent work sessions with error handling
        try:
            recent_sessions = WorkSession.objects.filter(user=request.user).select_related("project").order_by("-start_time")[:5]
        except Exception as e:
            logger.error(f"Error loading recent sessions for user {request.user.id}: {str(e)}")
            recent_sessions = []
        
        # Recent projects with error handling
        try:
            recent_projects = user_projects.prefetch_related("technologies").order_by("-created_at")[:6]
        except Exception as e:
            logger.error(f"Error loading recent projects for user {request.user.id}: {str(e)}")
            recent_projects = []
        
        # Task statistics with error handling
        try:
            from tasks.models import Task
            user_tasks = Task.objects.filter(project__owner=request.user)
            
            total_tasks = user_tasks.count()
            active_tasks = user_tasks.filter(status__in=["todo", "in_progress", "review"]).count()
            completed_tasks = user_tasks.filter(status="done").count()
            overdue_tasks = user_tasks.filter(
                due_date__lt=timezone.now().date(),
                status__in=["todo", "in_progress", "review"]
            ).count() if user_tasks.exists() else 0
        except Exception as e:
            logger.error(f"Error calculating task statistics for user {request.user.id}: {str(e)}")
            total_tasks = active_tasks = completed_tasks = overdue_tasks = 0
        
        # Active session (if any) with error handling
        try:
            active_session = WorkSession.objects.filter(user=request.user, is_active=True).select_related("project").first()
            
            # Validate active session data
            if active_session and active_session.start_time > timezone.now():
                logger.warning(f"Active session has future start time for user {request.user.id}")
                messages.warning(request, "There appears to be an issue with your active work session timing.")
                
        except Exception as e:
            logger.error(f"Error loading active session for user {request.user.id}: {str(e)}")
            active_session = None
        
        context = {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "total_hours": total_hours,
            "recent_sessions": recent_sessions,
            "recent_projects": recent_projects,
            "active_session": active_session,
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "completed_tasks_count": completed_tasks,
            "overdue_tasks": overdue_tasks,
        }
        
        # Log successful dashboard load for analytics
        logger.info(f"Dashboard loaded successfully for user {request.user.id}")
        
        return render(request, "projects/dashboard.html", context)
        
    except Exception as e:
        logger.critical(f"Critical error in dashboard view for user {request.user.id}: {str(e)}")
        messages.error(request, "There was a serious error loading the dashboard. Please try again or contact support.")
        
        # Return minimal context to prevent complete failure
        context = {
            "total_projects": 0,
            "active_projects": 0,
            "completed_projects": 0,
            "total_hours": 0,
            "recent_sessions": [],
            "recent_projects": [],
            "active_session": None,
            "total_tasks": 0,
            "active_tasks": 0,
            "completed_tasks_count": 0,
            "overdue_tasks": 0,
        }
        return render(request, "projects/dashboard.html", context)


class ProjectListView(ListView):
    """
    List view for all public projects (portfolio) or user projects if authenticated.
    Enhanced with comprehensive error handling and input validation.
    """
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 12
    
    def get_queryset(self):
        try:
            queryset = Project.objects.select_related("owner").prefetch_related("technologies", "images")
            
            # Filter based on user authentication with error handling
            try:
                if self.request.user.is_authenticated:
                    # Show users own projects plus public featured projects from others
                    queryset = queryset.filter(
                        Q(owner=self.request.user) | Q(is_public=True, is_featured=True)
                    )
                else:
                    # Show only public projects
                    queryset = queryset.filter(is_public=True)
            except Exception as e:
                logger.error(f"Error applying authentication filters: {str(e)}")
                # Fallback to public projects only
                queryset = queryset.filter(is_public=True)
            
            # Filter by technology if specified with validation
            tech_filter = self.request.GET.get("technology")
            if tech_filter:
                # Validate technology filter
                if len(tech_filter.strip()) > 100:
                    messages.warning(self.request, "Technology filter too long, ignoring.")
                else:
                    try:
                        queryset = queryset.filter(technologies__name__icontains=tech_filter.strip())
                    except Exception as e:
                        logger.error(f"Error applying technology filter '{tech_filter}': {str(e)}")
                        messages.error(self.request, "Invalid technology filter.")
            
            # Filter by status if specified with validation
            status_filter = self.request.GET.get("status")
            if status_filter:
                # Validate status filter against valid choices
                valid_statuses = [choice[0] for choice in Project.STATUS_CHOICES]
                if status_filter not in valid_statuses:
                    messages.warning(self.request, "Invalid status filter, ignoring.")
                    logger.warning(f"Invalid status filter attempted: {status_filter}")
                else:
                    try:
                        queryset = queryset.filter(status=status_filter)
                    except Exception as e:
                        logger.error(f"Error applying status filter '{status_filter}': {str(e)}")
                        messages.error(self.request, "Error applying status filter.")
            
            # Search functionality with validation
            search_query = self.request.GET.get("search")
            if search_query:
                # Validate search query
                search_query = search_query.strip()
                if len(search_query) < 2:
                    messages.info(self.request, "Search query too short, ignoring.")
                elif len(search_query) > 100:
                    messages.warning(self.request, "Search query too long, truncating.")
                    search_query = search_query[:100]
                
                if len(search_query) >= 2:
                    try:
                        queryset = queryset.filter(
                            Q(title__icontains=search_query) | 
                            Q(description__icontains=search_query) |
                            Q(short_description__icontains=search_query)
                        )
                    except Exception as e:
                        logger.error(f"Error applying search query '{search_query}': {str(e)}")
                        messages.error(self.request, "Error processing search query.")
            
            try:
                return queryset.distinct().order_by("-created_at")
            except Exception as e:
                logger.error(f"Error ordering queryset: {str(e)}")
                return queryset.distinct()
                
        except Exception as e:
            logger.critical(f"Critical error in ProjectListView.get_queryset(): {str(e)}")
            messages.error(self.request, "There was an error loading projects. Please try again.")
            # Return empty queryset as fallback
            return Project.objects.none()
    
    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            
            # Load technologies with error handling
            try:
                context["technologies"] = Technology.objects.all().order_by("category", "name")
            except Exception as e:
                logger.error(f"Error loading technologies: {str(e)}")
                context["technologies"] = []
            
            # Get filter values with validation
            try:
                context["current_tech"] = self.request.GET.get("technology", "")[:100]  # Limit length
                context["current_status"] = self.request.GET.get("status", "")[:20]  # Limit length
                context["search_query"] = self.request.GET.get("search", "")[:100]  # Limit length
            except Exception as e:
                logger.error(f"Error getting filter values: {str(e)}")
                context["current_tech"] = ""
                context["current_status"] = ""
                context["search_query"] = ""
            
            # Add filter form for future use
            try:
                context["filter_form"] = TechnologyFilterForm(self.request.GET)
            except Exception as e:
                logger.error(f"Error creating filter form: {str(e)}")
                context["filter_form"] = None
            
            return context
            
        except Exception as e:
            logger.critical(f"Critical error in ProjectListView.get_context_data(): {str(e)}")
            messages.error(self.request, "There was an error loading the page context.")
            # Return minimal context
            return {
                "object_list": [],
                "technologies": [],
                "current_tech": "",
                "current_status": "",
                "search_query": "",
                "filter_form": None
            }
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add request-level error handling"""
        try:
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            messages.error(request, "You don't have permission to view this page.")
            return redirect("projects:project_list")
        except Exception as e:
            logger.critical(f"Critical error in ProjectListView dispatch: {str(e)}")
            messages.error(request, "There was an unexpected error. Please try again.")
            return redirect("projects:dashboard")


class ProjectDetailView(DetailView):
    """
    Detailed view of a single project with gallery and work sessions.
    """
    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"
    
    def get_queryset(self):
        queryset = Project.objects.select_related("owner").prefetch_related(
            "technologies", "images", "work_sessions__user"
        )
        
        # Filter based on authentication and ownership
        if self.request.user.is_authenticated:
            return queryset.filter(
                Q(owner=self.request.user) | Q(is_public=True)
            )
        else:
            return queryset.filter(is_public=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        
        # Get work sessions for the project
        context["work_sessions"] = project.work_sessions.order_by("-start_time")[:10]
        
        # Get project images
        context["images"] = project.images.order_by("order", "-created_at")
        
        # Check if user can edit this project
        context["can_edit"] = (
            self.request.user.is_authenticated and 
            project.owner == self.request.user
        )
        
        # Get active work session for this project (if user is owner)
        if context["can_edit"]:
            context["active_session"] = project.work_sessions.filter(
                user=self.request.user, is_active=True
            ).first()
        
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    """
    Create new project view with comprehensive error handling and validation.
    """
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"
    
    def get_form_kwargs(self):
        """Add user to form kwargs for validation"""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                form.instance.owner = self.request.user
                
                # Additional validation
                if not form.instance.title.strip():
                    messages.error(self.request, "Project title cannot be empty.")
                    return self.form_invalid(form)
                
                # Save the project
                response = super().form_valid(form)
                
                # Log successful creation
                logger.info(f"Project '{self.object.title}' created successfully by user {self.request.user.id}")
                
                messages.success(
                    self.request, 
                    f"Project '{self.object.title}' created successfully\! You can now add images and start tracking work sessions."
                )
                
                return response
                
        except IntegrityError as e:
            logger.error(f"Database integrity error creating project: {str(e)}")
            messages.error(
                self.request, 
                "A project with this information already exists or there was a database constraint violation."
            )
            return self.form_invalid(form)
            
        except ValidationError as e:
            logger.error(f"Validation error creating project: {str(e)}")
            messages.error(self.request, f"Validation error: {str(e)}")
            return self.form_invalid(form)
            
        except Exception as e:
            logger.critical(f"Unexpected error creating project: {str(e)}")
            messages.error(
                self.request, 
                "There was an unexpected error creating the project. Please try again or contact support."
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Handle form validation errors with detailed feedback"""
        logger.warning(f"Project creation form invalid for user {self.request.user.id}: {form.errors}")
        
        # Add specific error messages for common issues
        if "title" in form.errors:
            messages.error(self.request, "Please check the project title for issues.")
        if "technologies" in form.errors:
            messages.error(self.request, "Please check your technology selections.")
        if "__all__" in form.errors:
            messages.error(self.request, "Please check your form data for conflicts or issues.")
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        try:
            return reverse_lazy("projects:project_detail", kwargs={"pk": self.object.pk})
        except Exception as e:
            logger.error(f"Error generating success URL: {str(e)}")
            return reverse_lazy("projects:project_list")
    
    def get_context_data(self, **kwargs):
        """Add additional context with error handling"""
        try:
            context = super().get_context_data(**kwargs)
            context["title"] = "Create New Project"
            context["submit_text"] = "Create Project"
            
            # Add technologies count for UX
            try:
                context["technology_count"] = Technology.objects.count()
            except Exception as e:
                logger.error(f"Error getting technology count: {str(e)}")
                context["technology_count"] = 0
            
            return context
        except Exception as e:
            logger.error(f"Error in ProjectCreateView context: {str(e)}")
            return {"form": self.get_form()}


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update existing project view.
    """
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, "Project updated successfully\!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy("projects:project_detail", kwargs={"pk": self.object.pk})


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete project view.
    """
    model = Project
    template_name = "projects/project_confirm_delete.html"
    success_url = reverse_lazy("projects:project_list")
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Project deleted successfully\!")
        return super().delete(request, *args, **kwargs)


class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update user profile view.
    """
    model = UserProfile
    form_class = UserProfileForm
    template_name = "projects/profile_form.html"
    success_url = reverse_lazy("projects:dashboard")
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully\!")
        return super().form_valid(form)


@login_required
def start_work_session(request, project_id):
    """
    Start a new work session for a project with comprehensive error handling.
    """
    try:
        # Validate project_id
        try:
            project_id = int(project_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid project_id provided: {project_id}")
            messages.error(request, "Invalid project identifier.")
            return redirect("projects:project_list")
        
        # Get project with permission check
        try:
            project = get_object_or_404(Project, id=project_id, owner=request.user)
        except Http404:
            logger.warning(f"User {request.user.id} attempted to access non-existent or unauthorized project {project_id}")
            messages.error(request, "Project not found or you don't have permission to access it.")
            return redirect("projects:project_list")
        
        # Check if theres already an active session
        try:
            active_session = WorkSession.objects.filter(user=request.user, is_active=True).first()
            if active_session:
                messages.warning(
                    request, 
                    f"You already have an active work session for '{active_session.project.title}'. Please stop it first."
                )
                return redirect("projects:project_detail", pk=project.id)
        except Exception as e:
            logger.error(f"Error checking for active session: {str(e)}")
            messages.warning(request, "Could not verify active sessions. Please check your current work sessions.")
        
        # Create new work session with transaction safety
        try:
            with transaction.atomic():
                current_time = timezone.now()
                session_title = f"Work session - {current_time.strftime('%Y-%m-%d %H:%M')}"
                
                session = WorkSession.objects.create(
                    project=project,
                    user=request.user,
                    title=session_title,
                    start_time=current_time,
                    is_active=True
                )
                
                # Log successful session start
                logger.info(f"Work session {session.id} started for project '{project.title}' by user {request.user.id}")
                
                messages.success(
                    request, 
                    f"Started work session for '{project.title}'. Don't forget to stop it when you're done\!"
                )
                
                return redirect("projects:project_detail", pk=project.id)
                
        except IntegrityError as e:
            logger.error(f"Database integrity error creating work session: {str(e)}")
            messages.error(request, "Could not create work session due to a database constraint.")
            return redirect("projects:project_detail", pk=project.id)
            
        except Exception as e:
            logger.critical(f"Unexpected error creating work session: {str(e)}")
            messages.error(request, "An unexpected error occurred while starting the work session.")
            return redirect("projects:project_detail", pk=project.id)
            
    except Exception as e:
        logger.critical(f"Critical error in start_work_session: {str(e)}")
        messages.error(request, "A critical error occurred. Please try again or contact support.")
        return redirect("projects:project_list")


@login_required
def stop_work_session(request, session_id):
    """
    Stop an active work session.
    """
    session = get_object_or_404(
        WorkSession, 
        id=session_id, 
        user=request.user, 
        is_active=True
    )
    
    session.end_time = timezone.now()
    session.is_active = False
    session.save()  # This will trigger the duration calculation
    
    messages.success(
        request, 
        f"Stopped work session. Duration: {session.duration_hours:.2f} hours"
    )
    return redirect("projects:project_detail", pk=session.project.id)


@login_required
def upload_project_image(request, project_id):
    """
    Upload image for a project.
    """
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    
    if request.method == "POST":
        form = ProjectImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.project = project
            image.save()
            messages.success(request, "Image uploaded successfully\!")
            return redirect("projects:project_detail", pk=project.id)
    else:
        form = ProjectImageForm()
    
    context = {
        "form": form,
        "project": project,
        "title": f"Upload Image for {project.title}"
    }
    return render(request, "projects/image_upload.html", context)


@login_required
def delete_project_image(request, project_id, image_id):
    """
    Delete a project image.
    """
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    image = get_object_or_404(ProjectImage, id=image_id, project=project)
    
    if request.method == "POST":
        image.delete()
        messages.success(request, "Image deleted successfully\!")
        return redirect("projects:project_detail", pk=project.id)
    
    context = {
        "project": project,
        "image": image,
    }
    return render(request, "projects/image_confirm_delete.html", context)


class WorkSessionUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update work session view.
    """
    model = WorkSession
    form_class = WorkSessionForm
    template_name = "projects/session_form.html"
    
    def get_queryset(self):
        return WorkSession.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, "Work session updated successfully\!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy("projects:project_detail", kwargs={"pk": self.object.project.pk})


class WorkSessionDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete work session view.
    """
    model = WorkSession
    template_name = "projects/session_confirm_delete.html"
    
    def get_queryset(self):
        return WorkSession.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy("projects:project_detail", kwargs={"pk": self.object.project.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Work session deleted successfully\!")
        return super().delete(request, *args, **kwargs)


@login_required
def bulk_project_action(request):
    """
    Handle bulk actions on multiple projects with comprehensive error handling and validation.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect("projects:project_list")
    
    try:
        form = BulkProjectActionForm(request.POST, user=request.user)
        
        if not form.is_valid():
            logger.warning(f"Invalid bulk action form for user {request.user.id}: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
            return redirect("projects:project_list")
        
        action = form.cleaned_data['action']
        projects = form.cleaned_data['projects']
        
        if not projects.exists():
            messages.warning(request, "No projects selected.")
            return redirect("projects:project_list")
        
        try:
            with transaction.atomic():
                projects_count = projects.count()
                
                if action == 'set_status':
                    new_status = form.cleaned_data.get('new_status')
                    if not new_status:
                        messages.error(request, "No status selected.")
                        return redirect("projects:project_list")
                    
                    updated_count = projects.update(status=new_status)
                    messages.success(
                        request, 
                        f"Successfully updated status to '{dict(Project.STATUS_CHOICES)[new_status]}' for {updated_count} project(s)."
                    )
                    logger.info(f"Bulk status update: {updated_count} projects to '{new_status}' by user {request.user.id}")
                
                elif action == 'set_priority':
                    new_priority = form.cleaned_data.get('new_priority')
                    if not new_priority:
                        messages.error(request, "No priority selected.")
                        return redirect("projects:project_list")
                    
                    updated_count = projects.update(priority=new_priority)
                    messages.success(
                        request, 
                        f"Successfully updated priority to '{dict(Project.PRIORITY_CHOICES)[new_priority]}' for {updated_count} project(s)."
                    )
                    logger.info(f"Bulk priority update: {updated_count} projects to '{new_priority}' by user {request.user.id}")
                
                elif action == 'set_visibility':
                    new_visibility = form.cleaned_data.get('new_visibility', False)
                    updated_count = projects.update(is_public=new_visibility)
                    visibility_text = "public" if new_visibility else "private"
                    messages.success(
                        request, 
                        f"Successfully made {updated_count} project(s) {visibility_text}."
                    )
                    logger.info(f"Bulk visibility update: {updated_count} projects to '{visibility_text}' by user {request.user.id}")
                
                elif action == 'delete':
                    # Additional confirmation needed for delete
                    if not request.POST.get('confirm_delete'):
                        messages.error(request, "Delete confirmation required.")
                        return redirect("projects:project_list")
                    
                    project_titles = list(projects.values_list('title', flat=True))
                    deleted_count = projects.count()
                    projects.delete()
                    
                    messages.success(
                        request, 
                        f"Successfully deleted {deleted_count} project(s): {', '.join(project_titles[:5])}{' and more...' if len(project_titles) > 5 else ''}"
                    )
                    logger.info(f"Bulk delete: {deleted_count} projects by user {request.user.id}")
                
                else:
                    messages.error(request, "Invalid action selected.")
                    return redirect("projects:project_list")
                
        except IntegrityError as e:
            logger.error(f"Database integrity error in bulk action: {str(e)}")
            messages.error(request, "Could not complete bulk action due to database constraints.")
            
        except Exception as e:
            logger.critical(f"Unexpected error in bulk action: {str(e)}")
            messages.error(request, "An unexpected error occurred during bulk operation.")
        
    except Exception as e:
        logger.critical(f"Critical error in bulk_project_action: {str(e)}")
        messages.error(request, "A critical error occurred. Please try again.")
    
    return redirect("projects:project_list")


# API endpoint for future expansion
@login_required 
def project_api_list(request):
    """
    JSON API endpoint for projects list with filtering and search.
    Enhanced with comprehensive error handling and rate limiting considerations.
    """
    try:
        # Basic rate limiting check (could be enhanced with Django-ratelimit)
        if hasattr(request, 'session'):
            api_calls = request.session.get('api_calls', 0)
            if api_calls > 100:  # Limit to 100 API calls per session
                logger.warning(f"API rate limit exceeded for user {request.user.id}")
                return JsonResponse({
                    "error": "Rate limit exceeded",
                    "message": "Too many API calls. Please try again later."
                }, status=429)
            request.session['api_calls'] = api_calls + 1
        
        # Get user's projects with error handling
        try:
            projects = Project.objects.filter(owner=request.user).select_related('owner').prefetch_related('technologies')
        except Exception as e:
            logger.error(f"Error fetching projects for API: {str(e)}")
            return JsonResponse({"error": "Database error"}, status=500)
        
        # Apply filters with validation
        try:
            # Technology filter
            tech_filter = request.GET.get('technology')
            if tech_filter:
                if len(tech_filter.strip()) > 100:
                    return JsonResponse({"error": "Technology filter too long"}, status=400)
                projects = projects.filter(technologies__name__icontains=tech_filter.strip())
            
            # Status filter
            status_filter = request.GET.get('status')
            if status_filter:
                valid_statuses = [choice[0] for choice in Project.STATUS_CHOICES]
                if status_filter not in valid_statuses:
                    return JsonResponse({"error": "Invalid status filter"}, status=400)
                projects = projects.filter(status=status_filter)
            
            # Search filter
            search_query = request.GET.get('search')
            if search_query:
                search_query = search_query.strip()
                if len(search_query) < 2:
                    return JsonResponse({"error": "Search query too short"}, status=400)
                if len(search_query) > 100:
                    return JsonResponse({"error": "Search query too long"}, status=400)
                
                projects = projects.filter(
                    Q(title__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(short_description__icontains=search_query)
                )
            
        except Exception as e:
            logger.error(f"Error applying API filters: {str(e)}")
            return JsonResponse({"error": "Filter error"}, status=500)
        
        # Pagination with limits
        try:
            page = max(1, int(request.GET.get('page', 1)))
            limit = min(50, max(1, int(request.GET.get('limit', 20))))  # Max 50 items per page
            offset = (page - 1) * limit
            
            total_count = projects.count()
            projects = projects[offset:offset + limit]
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid pagination parameters: {str(e)}")
            return JsonResponse({"error": "Invalid pagination parameters"}, status=400)
        
        # Serialize data with error handling
        try:
            project_data = []
            for project in projects:
                project_dict = {
                    "id": project.id,
                    "title": project.title,
                    "short_description": project.short_description or "",
                    "status": project.status,
                    "status_display": project.get_status_display(),
                    "priority": project.priority,
                    "priority_display": project.get_priority_display(),
                    "is_public": project.is_public,
                    "is_featured": project.is_featured,
                    "created_at": project.created_at.isoformat(),
                    "updated_at": project.updated_at.isoformat(),
                    "technologies": [tech.name for tech in project.technologies.all()],
                    "url": request.build_absolute_uri(project.get_absolute_url()),
                }
                
                # Add total hours if available
                try:
                    project_dict["total_hours"] = project.total_hours_worked
                except Exception as e:
                    logger.warning(f"Could not get total hours for project {project.id}: {str(e)}")
                    project_dict["total_hours"] = 0
                
                project_data.append(project_dict)
            
            response_data = {
                "projects": project_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit
                }
            }
            
            logger.info(f"API request successful for user {request.user.id}: {len(project_data)} projects returned")
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error serializing project data: {str(e)}")
            return JsonResponse({"error": "Serialization error"}, status=500)
    
    except Exception as e:
        logger.critical(f"Critical error in project_api_list: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
def chart_project_progress_api(request):
    """API endpoint for project progress chart data."""
    try:
        user_projects = Project.objects.filter(owner=request.user)
        
        # Get project status distribution
        status_data = {}
        status_choices = dict(Project.STATUS_CHOICES)
        
        for status, label in status_choices.items():
            count = user_projects.filter(status=status).count()
            if count > 0:
                status_data[label] = count
        
        # Get project completion percentages
        completion_data = []
        for project in user_projects.select_related().order_by('-updated_at')[:10]:
            completion_data.append({
                'name': project.title[:20] + ('...' if len(project.title) > 20 else ''),
                'completion': project.completion_percentage
            })
        
        return JsonResponse({
            'status_distribution': status_data,
            'completion_data': completion_data
        })
        
    except Exception as e:
        logger.error(f"Error in chart_project_progress_api: {str(e)}")
        return JsonResponse({"error": "Failed to load project progress data"}, status=500)


@login_required  
def chart_time_tracking_api(request):
    """API endpoint for time tracking analytics chart data."""
    try:
        # Get time tracking data for the last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        sessions = WorkSession.objects.filter(
            user=request.user,
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
            end_time__isnull=False
        ).select_related('project')
        
        # Daily hours data
        daily_hours = {}
        current_date = start_date
        while current_date <= end_date:
            daily_hours[current_date.isoformat()] = 0
            current_date += timedelta(days=1)
        
        for session in sessions:
            date_key = session.start_time.date().isoformat()
            if date_key in daily_hours:
                daily_hours[date_key] += float(session.duration_hours)
        
        # Project hours distribution
        project_hours = {}
        for session in sessions:
            project_name = session.project.title
            if project_name not in project_hours:
                project_hours[project_name] = 0
            project_hours[project_name] += float(session.duration_hours)
        
        # Sort by hours and take top 10
        project_hours = dict(sorted(project_hours.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # Weekly productivity averages
        weekly_productivity = []
        current_week_start = start_date
        while current_week_start <= end_date:
            week_end = min(current_week_start + timedelta(days=6), end_date)
            week_sessions = sessions.filter(
                start_time__date__gte=current_week_start,
                start_time__date__lte=week_end,
                productivity_rating__isnull=False
            )
            
            if week_sessions.exists():
                avg_productivity = sum(s.productivity_rating for s in week_sessions) / len(week_sessions)
                weekly_productivity.append({
                    'week': f"{current_week_start.strftime('%m/%d')}-{week_end.strftime('%m/%d')}",
                    'productivity': round(avg_productivity, 1)
                })
            
            current_week_start += timedelta(days=7)
        
        return JsonResponse({
            'daily_hours': daily_hours,
            'project_hours': project_hours,
            'weekly_productivity': weekly_productivity
        })
        
    except Exception as e:
        logger.error(f"Error in chart_time_tracking_api: {str(e)}")
        return JsonResponse({"error": "Failed to load time tracking data"}, status=500)


@login_required
def chart_productivity_metrics_api(request):
    """API endpoint for productivity metrics chart data."""
    try:
        user_projects = Project.objects.filter(owner=request.user)
        
        # Task completion rate (if tasks app is available)
        task_data = {}
        try:
            from tasks.models import Task
            user_tasks = Task.objects.filter(project__owner=request.user)
            
            total_tasks = user_tasks.count()
            if total_tasks > 0:
                completed_tasks = user_tasks.filter(status='done').count()
                in_progress_tasks = user_tasks.filter(status__in=['todo', 'in_progress', 'review']).count()
                overdue_tasks = user_tasks.filter(
                    due_date__lt=timezone.now().date(),
                    status__in=['todo', 'in_progress', 'review']
                ).count()
                
                task_data = {
                    'completed': completed_tasks,
                    'in_progress': in_progress_tasks,
                    'overdue': overdue_tasks,
                    'total': total_tasks,
                    'completion_rate': round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0
                }
        except ImportError:
            # Tasks app not available
            pass
        
        # Project priority distribution
        priority_data = {}
        priority_choices = dict(Project.PRIORITY_CHOICES)
        
        for priority, label in priority_choices.items():
            count = user_projects.filter(priority=priority).count()
            if count > 0:
                priority_data[label] = count
        
        # Monthly project creation trend (last 6 months)
        monthly_projects = []
        current_month = timezone.now().replace(day=1)
        for i in range(6):
            month_start = current_month - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            count = user_projects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            
            monthly_projects.append({
                'month': month_start.strftime('%b %Y'),
                'count': count
            })
        
        monthly_projects.reverse()
        
        # Session productivity trend
        productivity_trend = []
        sessions = WorkSession.objects.filter(
            user=request.user,
            productivity_rating__isnull=False
        ).order_by('-start_time')[:20]
        
        for session in sessions:
            productivity_trend.append({
                'date': session.start_time.strftime('%m/%d'),
                'rating': session.productivity_rating,
                'project': session.project.title[:15] + ('...' if len(session.project.title) > 15 else '')
            })
        
        productivity_trend.reverse()
        
        return JsonResponse({
            'task_data': task_data,
            'priority_distribution': priority_data,
            'monthly_projects': monthly_projects,
            'productivity_trend': productivity_trend
        })
        
    except Exception as e:
        logger.error(f"Error in chart_productivity_metrics_api: {str(e)}")
        return JsonResponse({"error": "Failed to load productivity metrics"}, status=500)
