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
    title = models.CharField(max_length=255)
    message = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="signup")
    icon = models.CharField(max_length=100, default="fas fa-bell")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()}: {self.title} ({'Read' if self.is_read else 'Unread'})"
