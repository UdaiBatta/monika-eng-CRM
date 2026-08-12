from django.contrib import admin

from .models import Enquiry, EnquiryItem, EnquiryRequirement

admin.site.register(Enquiry)
admin.site.register(EnquiryRequirement)
admin.site.register(EnquiryItem)
