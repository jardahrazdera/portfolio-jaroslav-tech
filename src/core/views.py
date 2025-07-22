# src/core/views.py
from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.
def index(request):
    return render(request, "core/index.html")

class RobotstxtView(TemplateView):
    template_name = "robots.txt"
    content_type = "text/plain"