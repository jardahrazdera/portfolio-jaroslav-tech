from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

# Create your views here.
def home(request):
    """
    This view renders the home page.
    """
    return render(request, "core/home.html")