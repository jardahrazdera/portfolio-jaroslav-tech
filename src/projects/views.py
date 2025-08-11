from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Project, Technology, WorkSession, ProjectImage, UserProfile


@login_required
def dashboard(request):
    """
    Main dashboard view showing project overview and statistics.
    """
    user_projects = Project.objects.filter(owner=request.user)
    
    # Project statistics
    total_projects = user_projects.count()
    active_projects = user_projects.filter(status__in=['planning', 'development', 'testing']).count()
    completed_projects = user_projects.filter(status='completed').count()
    
    # Time tracking statistics
    total_hours = WorkSession.objects.filter(user=request.user).aggregate(
        total=Sum('duration_hours')
    )['total'] or 0
    
    # Recent work sessions
    recent_sessions = WorkSession.objects.filter(user=request.user).order_by('-start_time')[:5]
    
    # Recent projects
    recent_projects = user_projects.order_by('-created_at')[:6]
    
    # Active session (if any)
    active_session = WorkSession.objects.filter(user=request.user, is_active=True).first()
    
    context = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'total_hours': total_hours,
        'recent_sessions': recent_sessions,
        'recent_projects': recent_projects,
        'active_session': active_session,
    }
    
    return render(request, 'projects/dashboard.html', context)


class ProjectListView(ListView):
    """
    List view for all public projects (portfolio) or user's projects if authenticated.
    """
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Project.objects.select_related('owner').prefetch_related('technologies')
        
        # Filter based on user authentication
        if self.request.user.is_authenticated:
            # Show user's own projects plus public featured projects from others
            queryset = queryset.filter(
                Q(owner=self.request.user) | Q(is_public=True, is_featured=True)
            )
        else:
            # Show only public projects
            queryset = queryset.filter(is_public=True)
        
        # Filter by technology if specified
        tech_filter = self.request.GET.get('technology')
        if tech_filter:
            queryset = queryset.filter(technologies__name__icontains=tech_filter)
        
        # Filter by status if specified
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['technologies'] = Technology.objects.all()
        context['current_tech'] = self.request.GET.get('technology', "")
        context['current_status'] = self.request.GET.get('status', "")
        context['search_query'] = self.request.GET.get('search', "")
        return context


class ProjectDetailView(DetailView):
    """
    Detailed view of a single project with gallery and work sessions.
    """
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    
    def get_queryset(self):
        queryset = Project.objects.select_related('owner').prefetch_related(
            'technologies', 'images', 'work_sessions__user'
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
        context['work_sessions'] = project.work_sessions.order_by('-start_time')[:10]
        
        # Get project images
        context['images'] = project.images.order_by('order', '-created_at')
        
        # Check if user can edit this project
        context['can_edit'] = (
            self.request.user.is_authenticated and 
            project.owner == self.request.user
        )
        
        # Get active work session for this project (if user is owner)
        if context['can_edit']:
            context['active_session'] = project.work_sessions.filter(
                user=self.request.user, is_active=True
            ).first()
        
        return context


@login_required
def start_work_session(request, project_id):
    """
    Start a new work session for a project.
    """
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    
    # Check if there's already an active session
    active_session = WorkSession.objects.filter(user=request.user, is_active=True).first()
    if active_session:
        messages.warning(request, 'You already have an active work session. Please stop it first.')
        return redirect('projects:project_detail', pk=project.id)
    
    # Create new work session
    session = WorkSession.objects.create(
        project=project,
        user=request.user,
        title=f"Work session - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
        start_time=timezone.now(),
        is_active=True
    )
    
    messages.success(request, f'Started work session for {project.title}')
    return redirect('projects:project_detail', pk=project.id)


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
        f'Stopped work session. Duration: {session.duration_hours:.2f} hours'
    )
    return redirect('projects:project_detail', pk=session.project.id)
