from django.contrib import admin
from .models import Inquiry

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("inquiry_id", "name", "email", "phone", "role", "subject", "status", "created_at")
    list_filter = ("role", "status")
    search_fields = ("inquiry_id", "name", "email", "phone", "subject", "message")
    readonly_fields = ("inquiry_id", "created_at", "updated_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

