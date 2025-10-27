# src/core/urls.py
from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path("cv/", views.cv_view, name="cv"),
    path("privacy/", views.privacy_policy, name="privacy_policy"),
]

