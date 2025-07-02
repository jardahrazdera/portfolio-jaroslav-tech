# src/portfolio/views.py
from django.http import HttpResponse

def home(request):
    html = "<html><body><h1>Welcome to jaroslav.tech!</h1><p>This page runs in Docker container behind Traefik proxy and uses Django framework.</p></body></html>"
    return HttpResponse(html)
