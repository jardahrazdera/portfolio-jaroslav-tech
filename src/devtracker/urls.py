from django.urls import path
from . import views

app_name = 'devtracker'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('project/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('project/<slug:slug>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('project/<slug:slug>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    path('project/<slug:slug>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('project/<slug:slug>/log-time/', views.TimeLogCreateView.as_view(), name='time_log'),
    path('timelog/<int:pk>/edit/', views.TimeLogUpdateView.as_view(), name='timelog_edit'),
    
    # Task management
    path('project/<slug:slug>/task/create/', views.TaskCreateView.as_view(), name='task_create'),
    path('task/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_edit'),
    path('task/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    
    # Status updates
    path('project/<slug:slug>/status/create/', views.ProjectStatusCreateView.as_view(), name='status_create'),
    
    # Uncomment to test 404 page in DEBUG mode:
    # path('test-404/', views.Test404View.as_view(), name='test_404'),
]