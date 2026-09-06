from django.contrib import admin

from .models import Equipment, ServiceJobLine, ServiceTicket, ServiceTicketStageEvent

for model in (Equipment, ServiceTicket, ServiceJobLine, ServiceTicketStageEvent):
    admin.site.register(model)
