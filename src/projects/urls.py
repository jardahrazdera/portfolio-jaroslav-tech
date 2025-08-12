from django.urls import path
from . import views

app_name = "projects"

urlpatterns = [
    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    
    # Project CRUD views
    path("projects/", views.ProjectListView.as_view(), name="project_list"),
    path("projects/create/", views.ProjectCreateView.as_view(), name="project_create"),
    path("projects/<int:pk>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("projects/<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_update"),
    path("projects/<int:pk>/delete/", views.ProjectDeleteView.as_view(), name="project_delete"),
    
    # Work session actions
    path("projects/<int:project_id>/start-session/", views.start_work_session, name="start_session"),
    path("sessions/<int:session_id>/stop/", views.stop_work_session, name="stop_session"),
    path("sessions/<int:pk>/edit/", views.WorkSessionUpdateView.as_view(), name="session_update"),
    path("sessions/<int:pk>/delete/", views.WorkSessionDeleteView.as_view(), name="session_delete"),
    
    # Image management
    path("projects/<int:project_id>/upload-image/", views.upload_project_image, name="upload_image"),
    path("projects/<int:project_id>/images/<int:image_id>/delete/", views.delete_project_image, name="delete_image"),
    
    # Profile management
    
    # Bulk actions
    path("bulk-actions/", views.bulk_project_action, name="bulk_actions"),
    
    # API endpoints
    path("api/projects/", views.project_api_list, name="api_project_list"),
    path("profile/edit/", views.UserProfileUpdateView.as_view(), name="profile_update"),
]
