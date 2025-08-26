from django.contrib import admin
from .models import Project, Task, TimeLog, Tag, Technology, ProjectStatus

admin.site.register(Project)
admin.site.register(Task)
admin.site.register(TimeLog)
admin.site.register(Tag)
admin.site.register(Technology)
admin.site.register(ProjectStatus)
