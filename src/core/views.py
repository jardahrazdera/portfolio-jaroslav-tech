# src/core/views.py
import os

import markdown2
from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.
def index(request):
    return render(request, "core/index.html")

def cv_view(request):
    # Check if this is a PDF generation request
    pdf_lang = request.GET.get('pdf_lang')
    
    if pdf_lang:
        # Use specified language for PDF generation
        if pdf_lang == 'cs':
            cv_filename = 'cv-cz.md'
        else:
            cv_filename = 'cv-en.md'
        pdf_mode = True
    else:
        # Use current interface language for normal view
        from django.utils import translation
        current_language = translation.get_language()
        
        if current_language == 'cs':
            cv_filename = 'cv-cz.md'
        else:
            cv_filename = 'cv-en.md'
        pdf_mode = False
    
    file_path = os.path.join(os.path.dirname(__file__), 'static', 'cv', cv_filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        cv_content = f.read()
    
    html_content = markdown2.markdown(cv_content, extras=['tables', 'fenced-code-blocks'])
    
    context = {
        'cv_content': html_content,
        'current_language': request.LANGUAGE_CODE,
        'pdf_mode': pdf_mode,
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
