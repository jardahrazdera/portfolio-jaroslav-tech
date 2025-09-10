# src/core/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
import markdown2

# Create your views here.
def index(request):
    return render(request, "core/index.html")

def cv_view(request):
    cv_content = '''# JAROSLAV HRAZDĚRA

**Full-Stack Python Developer**

📧 Email: [jarek@jaroslav.tech](mailto:jarek@jaroslav.tech)  
🌍 Location: Brno, Czech Republic  
🌐 Website: [jaroslav.tech](https://jaroslav.tech)  
💻 GitHub: [github.com/jardahrazdera](https://github.com/jardahrazdera)

---

## PROFESSIONAL SUMMARY

Intermediate full-stack developer with 6+ years of technical experience, transitioning from IT infrastructure to software development. Python Backend certified with active open source contributions to Basecamp's Omarchy Linux distribution. Personally invited by David Heinemeier Hansson to collaborate on system-level projects.

**Core Differentiators:**

- **Open Source Contributor:** 10+ merged PRs to Basecamp's Omarchy project
- **DHH Collaboration:** Direct invitation to join Omarchy-ISO development team  
- **Full-Stack Capabilities:** From system architecture to frontend implementation
- **Hardware Integration:** Custom 3D printer builder, IoT and prototyping experience

---

## TECHNICAL SKILLS

### Languages & Frameworks

- **Backend:** Python, Django, Flask, Django REST Framework, SQL
- **Frontend:** JavaScript, HTML5, CSS3, Responsive Design, Bootstrap
- **Database:** PostgreSQL, MySQL, SQLite
- **Testing:** Unit Testing, Integration Testing

### DevOps & Infrastructure

- **Containerization:** Docker, Docker Compose
- **Virtualisation:** Proxmox
- **Version Control:** Git, GitHub, GitLab
- **CI/CD:** GitHub Actions, Automated Testing
- **Operating Systems:** Linux (Arch/Omarchy daily driver), Ubuntu, Debian
- **Web Servers:** Nginx, Apache

---

## PROFESSIONAL EXPERIENCE

### Full-Stack Developer & Technical Manager

**Gridoff Solar s.r.o.** | Brno, Czech Republic | *January 2019 - Present*

- Developed and deployed Django-based website, increasing organic traffic by 200%
- Built Python automation scripts reducing operational tasks by 40%, saving 15+ hours weekly
- Created REST API integrations for photovoltaic monitoring systems
- Implemented responsive web interfaces improving data collection efficiency by 60%
- Reduced IT operational costs by 75% through strategic self-hosting and containerization
- Deployed Docker-based development environment for team collaboration

**Technologies:** Python, Django, PostgreSQL, Docker, JavaScript, HTML/CSS, REST APIs, Linux

### Freelance Web Developer & IT Consultant

**Self-Employed** | Brno, Czech Republic | *January 2012 - December 2019*

- Built 15+ responsive websites using modern web technologies
- Developed custom web applications for inventory management and booking systems
- Created automated reporting tools using Python, reducing manual work by 80%
- Implemented secure payment gateway integrations

**Technologies:** Python, PHP, JavaScript, MySQL, HTML5, CSS3, WordPress, Linux

### Network Administrator & Junior Developer

**Airanet s.r.o.** | Brno, Czech Republic | *January 2007 - December 2012*

- Created network monitoring dashboard using Python and web technologies
- Developed automated configuration scripts for MikroTik routers
- Built customer portal for service management

**Technologies:** Python, Bash, HTML/CSS, Network Protocols

---

## KEY PROJECTS

### DevTracker - Project Management System

**Technologies:** Django, PostgreSQL, Docker, Alpine.js, GitHub Actions

- Full-featured project management application with authentication and authorization
- Implemented comprehensive test suite with 95% code coverage
- Deployed with Docker Compose and automated CI/CD pipeline

### Omarchy Linux Distribution - Open Source Contributor

**Technologies:** Bash, Linux, Git, System Programming

- Contributing to Basecamp's Arch-based Linux distribution for developers
- Fixed critical boot script issues for Arch Linux compatibility
- Enhanced network configuration and DNS management

### Portfolio Platform

**Technologies:** Django, PostgreSQL, Docker, HTML5, CSS3, JavaScript, Redis  
**Live Demo:** [jaroslav.tech](https://jaroslav.tech)

- Bilingual portfolio with integrated DevTracker application
- SEO optimized achieving top search rankings
- Containerized deployment with automated backups

---

## EDUCATION & CERTIFICATIONS

### Python Backend Developer Certification

**CodersLab IT Academy** | *January 2025 - August 2025* (In Progress)

- 169-hour intensive bootcamp covering Python, Django, and PostgreSQL
- Focus on OOP, REST APIs, and Test-Driven Development

### Electronics Engineering Diploma

**Secondary School of Industrial Electronics** | Prague | *2010*

### Additional Certifications

- Electrical Engineering Professional Qualification
- Photovoltaic Systems Electrician
- Master of Brewing Arts (MBA)

---

## LANGUAGES

- **Czech:** Native
- **English:** B1 (Professional working proficiency)
'''
    
    html_content = markdown2.markdown(cv_content, extras=['tables', 'fenced-code-blocks'])
    
    context = {
        'cv_content': html_content,
        'seo': {
            'title': 'CV - Jaroslav Hrazděra',
            'description': 'Developer CV',
            'noindex': True
        }
    }
    return render(request, 'core/cv.html', context)

class RobotstxtView(TemplateView):
    template_name = "robots.txt"
    content_type = "text/plain"