from django.urls import path
from . import views

app_name = 'devtracker'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('project/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('project/<slug:slug>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('project/<slug:slug>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    path('project/<slug:slug>/log-time/', views.TimeLogCreateView.as_view(), name='time_log'),
]