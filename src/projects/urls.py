from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Project views
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    
    # Work session actions
    path('projects/<int:project_id>/start-session/', views.start_work_session, name='start_session'),
    path('sessions/<int:session_id>/stop/', views.stop_work_session, name='stop_session'),
]
