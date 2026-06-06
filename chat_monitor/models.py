from django.db import models
from django.contrib.auth.models import User
from platform_api.models import Campaign
from wagtail.snippets.models import register_snippet

@register_snippet
class ChatMessage(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="chat_messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_messages_sent")
    text = models.TextField()
    file_attachment = models.CharField(max_length=255, blank=True, default="")
    time = models.CharField(max_length=50) # e.g. "10:24"

    def __str__(self):
        return f"{self.campaign.name} - Msg by {self.sender.username} ({self.time})"

@register_snippet
class ChatReview(models.Model):
    TARGET_CHOICES = (
        ("business", "Business"),
        ("creator", "Creator"),
        ("both", "Both"),
    )
    
    CATEGORY_CHOICES = (
        ("Safety / Guidelines", "Safety / Guidelines"),
        ("Escrow Protection", "Escrow Protection"),
        ("Contract Scope Dispute", "Contract Scope Dispute"),
        ("Deliverable Audit", "Deliverable Audit"),
    )

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="chat_reviews")
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default="Safety / Guidelines")
    review_text = models.TextField()
    target_audience = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        default="both"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.campaign.name} - {self.get_target_audience_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
