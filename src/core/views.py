# src/core/views.py
import os

import markdown2
from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.
def index(request):
    return render(request, "core/index.html")

def cv_view(request):
    file_path = os.path.join(os.path.dirname(__file__), 'static', 'cv', 'cv.md')
    with open(file_path, 'r', encoding='utf-8') as f:
        cv_content = f.read()
    
    html_content = markdown2.markdown(cv_content, extras=['tables', 'fenced-code-blocks'])
    
    context = {
        'cv_content': html_content,
        'seo': {
            'title': 'CV - Jaroslav Hrazdera',
            'description': 'Full-Stack Python Developer CV - Django, PostgreSQL, DevOps expertise. Open source contributor to Basecamp\'s Omarchy Linux with 6+ years technical experience in software development and IT infrastructure.',
            'noindex': True
        }
    }
    return render(request, 'core/cv.html', context)

class RobotstxtView(TemplateView):
    template_name = "robots.txt"
    content_type = "text/plain"
