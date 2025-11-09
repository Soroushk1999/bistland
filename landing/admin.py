from django.contrib import admin
from .models import Phone


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "created_at")
    search_fields = ("phone",)
    list_filter = ("created_at",)



