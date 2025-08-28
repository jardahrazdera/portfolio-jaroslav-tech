from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Project, Task, TimeLog, ProjectStatus, TrackerSettings
from .forms import ProjectForm, TimeLogForm, TaskForm, ProjectStatusForm, RegistrationForm


class UserOnlyMixin:
    """Mixin to prevent admin users from accessing user interface views."""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            messages.warning(request, 'Admin users should use the admin interface.')
            return redirect('/admin/')
        return super().dispatch(request, *args, **kwargs)


class ProjectListView(ListView):
    """Public list view showing only public projects."""
    model = Project
    template_name = 'devtracker/project_list.html'
    context_object_name = 'projects'
    paginate_by = 12
    
    def get_queryset(self):
        """For pagination, return all projects user should see."""
        base_queryset = Project.objects.select_related('owner').prefetch_related('tags', 'technologies')
        
        if self.request.user.is_authenticated:
            # Show user's own projects (public and private) + other users' public projects
            return base_queryset.filter(
                Q(owner=self.request.user) | Q(is_public=True)
            ).order_by('-updated_at')
        return base_queryset.filter(is_public=True).order_by('-updated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            # Separate user's projects from other public projects
            base_queryset = Project.objects.select_related('owner').prefetch_related('tags', 'technologies')
            
            # User's own projects (both public and private)
            user_projects = base_queryset.filter(owner=self.request.user).order_by('-updated_at')
            
            # Other users' public projects
            public_projects = base_queryset.filter(
                is_public=True
            ).exclude(owner=self.request.user).order_by('-updated_at')
            
            context['user_projects'] = user_projects
            context['public_projects'] = public_projects
            context['total_projects'] = user_projects.count() + public_projects.count()
        else:
            # Anonymous users see only public projects
            context['user_projects'] = Project.objects.none()
            context['public_projects'] = context['projects']
            context['total_projects'] = context['projects'].count()
            
        return context


class ProjectDetailView(DetailView):
    """Detail view for individual projects."""
    model = Project
    template_name = 'devtracker/project_detail.html'
    context_object_name = 'project'
    
    def get_queryset(self):
        """Filter queryset based on authentication status."""
        base_queryset = Project.objects.select_related('owner').prefetch_related(
            'tags', 'technologies', 'tasks', 'time_logs', 'status_updates'
        )
        
        if self.request.user.is_authenticated:
            return base_queryset.all()
        return base_queryset.filter(is_public=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        context['tasks'] = project.tasks.all()
        context['time_logs'] = project.time_logs.all()[:5]  # Latest 5 time logs
        context['recent_updates'] = project.status_updates.all()[:3]  # Latest 3 updates
        return context


class DashboardView(LoginRequiredMixin, UserOnlyMixin, ListView):
    """Dashboard view for authenticated users showing only their projects."""
    model = Project
    template_name = 'devtracker/dashboard.html'
    context_object_name = 'projects'
    login_url = reverse_lazy('devtracker:login')
    paginate_by = 8
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user).prefetch_related('tags', 'technologies', 'tasks', 'time_logs')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = self.get_queryset()
        
        # Dashboard statistics - only for user's projects
        context['total_projects'] = projects.count()
        context['active_projects'] = projects.filter(status='active').count()
        context['completed_projects'] = projects.filter(status='completed').count()
        context['total_tasks'] = Task.objects.filter(project__owner=self.request.user).count()
        context['completed_tasks'] = Task.objects.filter(project__owner=self.request.user, is_completed=True).count()
        context['recent_tasks'] = Task.objects.filter(project__owner=self.request.user, is_completed=False).select_related('project').order_by('-created_at')[:5]
        context['recent_logs'] = TimeLog.objects.filter(project__owner=self.request.user).select_related('project').order_by('-created_at')[:5]
        
        return context


class ProjectCreateView(LoginRequiredMixin, UserOnlyMixin, CreateView):
    """Create view for new projects."""
    model = Project
    form_class = ProjectForm
    template_name = 'devtracker/project_form.html'
    success_url = reverse_lazy('devtracker:dashboard')
    login_url = reverse_lazy('devtracker:login')
    
    def form_valid(self, form):
        """Set the project owner to the current user."""
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, UserOnlyMixin, UpdateView):
    """Update view for existing projects - users can only edit their own projects."""
    model = Project
    form_class = ProjectForm
    template_name = 'devtracker/project_form.html'
    success_url = reverse_lazy('devtracker:dashboard')
    login_url = reverse_lazy('devtracker:login')
    
    def get_queryset(self):
        """Filter to only allow editing user's own projects."""
        return Project.objects.filter(owner=self.request.user).prefetch_related('tags', 'technologies')


class TimeLogCreateView(LoginRequiredMixin, UserOnlyMixin, CreateView):
    """Create view for logging time to a project."""
    model = TimeLog
    form_class = TimeLogForm
    template_name = 'devtracker/timelog_form.html'
    login_url = reverse_lazy('devtracker:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, slug=self.kwargs['slug'], owner=self.request.user)
        return context
    
    def form_valid(self, form):
        form.instance.project = get_object_or_404(Project, slug=self.kwargs['slug'], owner=self.request.user)
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('devtracker:project_detail', kwargs={'slug': self.kwargs['slug']})


class TimeLogUpdateView(LoginRequiredMixin, UserOnlyMixin, UpdateView):
    """Update view for editing existing time logs."""
    model = TimeLog
    form_class = TimeLogForm
    template_name = 'devtracker/timelog_form.html'
    login_url = reverse_lazy('devtracker:login')
    
    def get_queryset(self):
        """Ensure users can only edit time logs for their own projects."""
        return TimeLog.objects.filter(project__owner=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['editing'] = True  # Flag to indicate edit mode
        return context
    
    def get_success_url(self):
        return reverse_lazy('devtracker:project_detail', kwargs={'slug': self.object.project.slug})


class UserRegistrationView(CreateView):
    """User registration view with admin approval required and reCAPTCHA protection."""
    form_class = RegistrationForm
    template_name = 'devtracker/register.html'
    success_url = reverse_lazy('devtracker:login')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if registration is enabled before allowing access."""
        settings = TrackerSettings.get_settings()
        if not settings.registration_enabled:
            messages.error(request, 'Registration is currently disabled. Please contact the administrator.')
            return redirect('devtracker:login')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Create user based on admin approval settings."""
        response = super().form_valid(form)
        
        # Check if admin approval is required
        settings = TrackerSettings.get_settings()
        
        if settings.require_admin_approval:
            # Set user as inactive - requires admin approval
            self.object.is_active = False
            self.object.save()
            
            # Use custom message if set, otherwise default
            if settings.welcome_message:
                messages.info(self.request, settings.welcome_message)
            else:
                messages.info(
                    self.request, 
                    'Registration successful! Your account is pending admin approval. '
                    'You will be able to log in once approved.'
                )
        else:
            # User is automatically active - no admin approval needed
            self.object.is_active = True
            self.object.save()
            
            # Use custom message if set, otherwise default
            if settings.welcome_message:
                messages.success(self.request, settings.welcome_message)
            else:
                messages.success(
                    self.request,
                    'Registration successful! You can now log in with your credentials.'
                )
        
        return response


class UserLoginView(LoginView):
    """Custom login view that prevents admin users from using user interface."""
    template_name = 'devtracker/login.html'
    
    def get_success_url(self):
        """Always redirect to dashboard after login."""
        return reverse_lazy('devtracker:dashboard')
    
    def form_valid(self, form):
        """Check if user is admin and redirect them to admin interface."""
        user = form.get_user()
        
        # Prevent admin/staff users from using the user interface
        if user.is_staff or user.is_superuser:
            messages.error(self.request, 'Admin users should use the admin interface at /admin/')
            return redirect('/admin/login/')
        
        # For regular users, proceed with normal login
        login(self.request, user)
        return redirect(self.get_success_url())
    
    def dispatch(self, request, *args, **kwargs):
        """Redirect already authenticated users to dashboard."""
        if request.user.is_authenticated:
            # If authenticated user is admin, redirect to admin
            if request.user.is_staff or request.user.is_superuser:
                return redirect('/admin/')
            # Regular users go to dashboard
            return redirect('devtracker:dashboard')
        return super().dispatch(request, *args, **kwargs)


class UserLogoutView(TemplateView):
    """Custom logout view that shows a goodbye page."""
    template_name = 'devtracker/logged_out.html'  # Changed path
    
    def get(self, request, *args, **kwargs):
        """Log the user out and show the goodbye page."""
        # Check if user is admin before logging out
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                # Admin users should use admin logout
                return redirect('/admin/logout/')
            # Log out regular users
            logout(request)
        # Show the goodbye page
        return super().get(request, *args, **kwargs)


# Task Management Views
class TaskCreateView(LoginRequiredMixin, UserOnlyMixin, CreateView):
    """Create a new task for a project."""
    model = Task
    form_class = TaskForm
    template_name = 'devtracker/task_form.html'
    login_url = reverse_lazy('devtracker:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, slug=self.kwargs['slug'], owner=self.request.user)
        context['is_create'] = True
        return context
    
    def form_valid(self, form):
        form.instance.project = get_object_or_404(Project, slug=self.kwargs['slug'], owner=self.request.user)
        messages.success(self.request, 'Task created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('devtracker:project_detail', kwargs={'slug': self.kwargs['slug']})


class TaskUpdateView(LoginRequiredMixin, UserOnlyMixin, UpdateView):
    """Update an existing task."""
    model = Task
    form_class = TaskForm
    template_name = 'devtracker/task_form.html'
    login_url = reverse_lazy('devtracker:login')
    
    def get_queryset(self):
        """Only allow editing tasks from user's own projects."""
        return Task.objects.filter(project__owner=self.request.user).select_related('project')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['is_create'] = False
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Task updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('devtracker:project_detail', kwargs={'slug': self.object.project.slug})


class TaskDeleteView(LoginRequiredMixin, UserOnlyMixin, DeleteView):
    """Delete a task."""
    model = Task
    template_name = 'devtracker/task_confirm_delete.html'
    login_url = reverse_lazy('devtracker:login')
    
    def get_queryset(self):
        """Only allow deleting tasks from user's own projects."""
        return Task.objects.filter(project__owner=self.request.user).select_related('project')
    
    def get_success_url(self):
        messages.success(self.request, 'Task deleted successfully!')
        return reverse_lazy('devtracker:project_detail', kwargs={'slug': self.object.project.slug})


# Project Status Management Views
class ProjectStatusCreateView(LoginRequiredMixin, UserOnlyMixin, CreateView):
    """Add a status update to a project."""
    model = ProjectStatus
    form_class = ProjectStatusForm
    template_name = 'devtracker/status_form.html'
    login_url = reverse_lazy('devtracker:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, slug=self.kwargs['slug'], owner=self.request.user)
        return context
    
    def form_valid(self, form):
        form.instance.project = get_object_or_404(Project, slug=self.kwargs['slug'], owner=self.request.user)
        messages.success(self.request, 'Status update added successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('devtracker:project_detail', kwargs={'slug': self.kwargs['slug']})


# Project Delete View
class ProjectDeleteView(LoginRequiredMixin, UserOnlyMixin, DeleteView):
    """Delete a project and all its related data."""
    model = Project
    template_name = 'devtracker/project_confirm_delete.html'
    success_url = reverse_lazy('devtracker:dashboard')
    login_url = reverse_lazy('devtracker:login')
    
    def get_queryset(self):
        """Only allow deleting user's own projects."""
        return Project.objects.filter(owner=self.request.user).select_related('owner')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Project deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Uncomment to test 404 page in DEBUG mode:
# class Test404View(TemplateView):
#     """Temporary view to test 404 template in DEBUG mode."""
#     template_name = '404.html'
