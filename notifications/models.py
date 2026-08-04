from django.db import models
from django.contrib.auth.models import User
from wagtail.snippets.models import register_snippet

@register_snippet
class Notification(models.Model):
    CATEGORY_CHOICES = (
        ("signup", "User Registration"),
        ("campaign", "Campaign Created"),
        ("payment", "Escrow / Payment"),
        ("compliance", "Compliance & Dispute"),
    )
    TARGET_ROLE_CHOICES = (
        ("all", "All Roles"),
        ("admin", "Admin Only"),
        ("business", "Business Only"),
        ("creator", "Creator Only"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    target_role = models.CharField(max_length=20, choices=TARGET_ROLE_CHOICES, default="all")
    title = models.CharField(max_length=255)
    message = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="signup")
    icon = models.CharField(max_length=100, default="fas fa-bell")
    is_read = models.BooleanField(default=False)
    target_url = models.CharField(max_length=512, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()}: {self.title} ({'Read' if self.is_read else 'Unread'})"

