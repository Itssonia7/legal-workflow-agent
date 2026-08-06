from django.contrib import admin

from .models import CaseFile, Client, HearingSchedule

admin.site.register(Client)
admin.site.register(CaseFile)
admin.site.register(HearingSchedule)
