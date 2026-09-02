from django.contrib import admin
from .models import PrivacyPolicy

@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ("policy_id", "title", "target_audience", "is_active", "created_at")
    list_filter = ("target_audience", "is_active")
    search_fields = ("policy_id", "title", "content")
