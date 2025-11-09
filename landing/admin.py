from django.contrib import admin
from .models import Phone


@admin.register(Phone)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "created_at", "ip_address")
    search_fields = ("phone", "ip_address", "user_agent")
    list_filter = ("created_at",)



