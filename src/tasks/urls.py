from django.urls import path
from . import views

app_name = "tasks"

urlpatterns = [
    # Task CRUD views
    path("", views.TaskListView.as_view(), name="task_list"),
    path("create/", views.TaskCreateView.as_view(), name="task_create"),
    path("create/<int:project_id>/", views.TaskCreateView.as_view(), name="task_create_for_project"),
    path("<uuid:pk>/", views.TaskDetailView.as_view(), name="task_detail"),
    path("<uuid:pk>/edit/", views.TaskUpdateView.as_view(), name="task_update"),
    path("<uuid:pk>/delete/", views.TaskDeleteView.as_view(), name="task_delete"),
    
    # Task actions
    path("<uuid:task_id>/complete/", views.mark_task_complete, name="mark_complete"),
    path("<uuid:task_id>/comment/", views.add_task_comment, name="add_comment"),
    
    # Project-specific task views
    path("project/<int:project_id>/", views.project_tasks_view, name="project_tasks"),
    
    # API endpoints
    path("api/list/", views.task_api_list, name="api_task_list"),
]
