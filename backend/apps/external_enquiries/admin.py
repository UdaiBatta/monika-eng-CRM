from django.contrib import admin

from .models import ExternalEnquiryAttachment, ExternalEnquirySubmission, IntegrationCredential

admin.site.register(IntegrationCredential)
admin.site.register(ExternalEnquirySubmission)
admin.site.register(ExternalEnquiryAttachment)
