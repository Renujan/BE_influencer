from django.db import models
from django.contrib.auth.models import User
from platform_api.models import Campaign
from wagtail.snippets.models import register_snippet

@register_snippet
class Complaint(models.Model):
    CATEGORY_CHOICES = (
        ("payment", "Payment & Escrow Dispute"),
        ("deliverable", "Deliverable Dispute"),
        ("conduct", "Professional Conduct"),
        ("technical", "Technical / System Issue"),
        ("other", "Other Inquiry"),
    )
    
    STATUS_CHOICES = (
        ("pending", "Pending Review"),
        ("investigating", "Under Investigation"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaints")
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="other")
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    admin_reply = models.TextField(blank=True, default="")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.id} - {self.subject} ({self.get_status_display()})"
