# src/core/views.py
import os
import time

import markdown2
import psutil
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.core.cache import cache
from django.views.decorators.cache import cache_page


# Create your views here.
def index(request):
    return render(request, "core/index.html")


def cv_view(request):
    # Check if this is a PDF generation request
    pdf_lang = request.GET.get("pdf_lang")

    if pdf_lang:
        # Use specified language for PDF generation
        if pdf_lang == "cs":
            cv_filename = "cv-cz.md"
        else:
            cv_filename = "cv-en.md"
        pdf_mode = True
    else:
        # Use current interface language for normal view
        from django.utils import translation

        current_language = translation.get_language()

        if current_language == "cs":
            cv_filename = "cv-cz.md"
        else:
            cv_filename = "cv-en.md"
        pdf_mode = False

    file_path = os.path.join(os.path.dirname(__file__), "static", "cv", cv_filename)
    with open(file_path, "r", encoding="utf-8") as f:
        cv_content = f.read()

    html_content = markdown2.markdown(
        cv_content, extras=["tables", "fenced-code-blocks"]
    )

    context = {
        "cv_content": html_content,
        "current_language": request.LANGUAGE_CODE,
        "pdf_mode": pdf_mode,
        "seo": {
            "title": "CV - Jaroslav Hrazdera",
            "description": "Full-Stack Python Developer CV - Django, PostgreSQL, DevOps expertise. Open source contributor to Basecamp's Omarchy Linux with 6+ years technical experience in software development and IT infrastructure.",
            "noindex": True,
        },
    }
    return render(request, "core/cv.html", context)


def privacy_policy(request):
    """Privacy policy page for the website and newsletter."""
    context = {
        "seo": {
            "title": "Privacy Policy - Jaroslav.tech",
            "description": "Privacy policy for jaroslav.tech website and newsletter subscription.",
            "noindex": False,
        }
    }
    return render(request, "core/privacy_policy.html", context)


@cache_page(5)  # Cache for 5 seconds
def server_stats(request):
    """
    API endpoint that returns server metrics: CPU, RAM, and System Load.
    Returns JSON with percentages and load average.
    Cached for 5 seconds to reduce load.
    """
    try:
        # Get CPU usage percentage (averaged over 1 second)
        cpu_percent = round(psutil.cpu_percent(interval=1), 1)

        # Get RAM usage percentage
        memory = psutil.virtual_memory()
        ram_percent = round(memory.percent, 1)

        # Get system load average (1-minute average)
        load_avg = psutil.getloadavg()[0]  # 1-minute load average

        # Get CPU count to calculate load percentage
        cpu_count = psutil.cpu_count()

        # Calculate load as percentage (load / cpu_count * 100)
        # Capped at 100% for display purposes
        load_percent = min(100, round((load_avg / cpu_count) * 100, 1))

        return JsonResponse(
            {
                "cpu": cpu_percent,
                "ram": ram_percent,
                "load": load_percent,
                "load_raw": round(load_avg, 2),  # Include raw load for reference
            }
        )

    except Exception as e:
        # Return error response if something goes wrong
        return JsonResponse(
            {"error": str(e), "cpu": 0, "ram": 0, "load": 0, "load_raw": 0}, status=500
        )


class RobotstxtView(TemplateView):
    template_name = "robots.txt"
    content_type = "text/plain"
