from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Project, Task, TimeLog, Tag, Technology
from .forms import ProjectForm, TimeLogForm


class ProjectListView(ListView):
    """Public list view showing only public projects."""
    model = Project
    template_name = 'devtracker/project_list.html'
    context_object_name = 'projects'
    paginate_by = 12
    
    def get_queryset(self):
        """Filter to show only public projects for non-authenticated users."""
        if self.request.user.is_authenticated:
            return Project.objects.all().prefetch_related('tags', 'technologies')
        return Project.objects.filter(is_public=True).prefetch_related('tags', 'technologies')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_projects'] = self.get_queryset().count()
        return context


class ProjectDetailView(DetailView):
    """Detail view for individual projects."""
    model = Project
    template_name = 'devtracker/project_detail.html'
    context_object_name = 'project'
    
    def get_queryset(self):
        """Filter queryset based on authentication status."""
        if self.request.user.is_authenticated:
            return Project.objects.all()
        return Project.objects.filter(is_public=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        context['tasks'] = project.tasks.all()
        context['time_logs'] = project.time_logs.all()[:5]  # Latest 5 time logs
        context['recent_updates'] = project.status_updates.all()[:3]  # Latest 3 updates
        return context


class DashboardView(LoginRequiredMixin, ListView):
    """Dashboard view for authenticated users showing all projects."""
    model = Project
    template_name = 'devtracker/dashboard.html'
    context_object_name = 'projects'
    login_url = '/admin/login/'
    
    def get_queryset(self):
        return Project.objects.all().prefetch_related('tags', 'technologies', 'tasks', 'time_logs')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = self.get_queryset()
        
        # Dashboard statistics
        context['total_projects'] = projects.count()
        context['active_projects'] = projects.filter(status='active').count()
        context['completed_projects'] = projects.filter(status='completed').count()
        context['total_tasks'] = Task.objects.count()
        context['completed_tasks'] = Task.objects.filter(is_completed=True).count()
        context['recent_tasks'] = Task.objects.filter(is_completed=False).order_by('-created_at')[:5]
        context['recent_logs'] = TimeLog.objects.all().order_by('-created_at')[:5]
        
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    """Create view for new projects."""
    model = Project
    form_class = ProjectForm
    template_name = 'devtracker/project_form.html'
    success_url = reverse_lazy('devtracker:dashboard')
    login_url = '/admin/login/'


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for existing projects."""
    model = Project
    form_class = ProjectForm
    template_name = 'devtracker/project_form.html'
    success_url = reverse_lazy('devtracker:dashboard')
    login_url = '/admin/login/'


class TimeLogCreateView(LoginRequiredMixin, CreateView):
    """Create view for logging time to a project."""
    model = TimeLog
    form_class = TimeLogForm
    template_name = 'devtracker/timelog_form.html'
    login_url = '/admin/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, slug=self.kwargs['slug'])
        return context
    
    def form_valid(self, form):
        form.instance.project = get_object_or_404(Project, slug=self.kwargs['slug'])
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('devtracker:project_detail', kwargs={'slug': self.kwargs['slug']})
