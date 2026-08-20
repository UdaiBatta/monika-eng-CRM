from django.contrib import admin

from .models import Project, ProjectEngineeringHandoff, ProjectHandoffClarification

for model in (Project, ProjectEngineeringHandoff, ProjectHandoffClarification):
    admin.site.register(model)
