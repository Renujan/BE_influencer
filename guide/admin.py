from django.contrib import admin
from .models import Guide

@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ("guide_id", "title", "category", "target_audience", "is_active", "created_at")
    list_filter = ("category", "target_audience", "is_active")
    search_fields = ("guide_id", "title", "content")
