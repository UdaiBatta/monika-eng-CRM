from django.contrib import admin

from .models import PanelJob, PanelJobMaterialLine, PanelJobStageEvent

for model in (PanelJob, PanelJobMaterialLine, PanelJobStageEvent):
    admin.site.register(model)
