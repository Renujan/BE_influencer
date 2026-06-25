from django.db import models
from django.contrib.auth.models import User
from campegin.models import Campaign
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

    PRIORITY_CHOICES = (
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaints")
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="other")
    subject = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Medium")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    admin_reply = models.TextField(blank=True, default="")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.id} - {self.subject} ({self.get_status_display()})"

@register_snippet
class SupportMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("admin", "Admin"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_messages")
    sender_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")
    message = models.TextField(blank=True, default="")
    attachment = models.FileField(upload_to="support_attachments/", null=True, blank=True)
    is_voice = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_thread_sender_role(self):
        first_msg = SupportMessage.objects.filter(user=self.user).order_by("created_at").first()
        if first_msg and first_msg.sender_role == "admin":
            return "Admin"
        if hasattr(self.user, "creator_profile") and self.user.creator_profile:
            return "Creator"
        elif hasattr(self.user, "business_profile") and self.user.business_profile:
            return "Business"
        return "User"
    get_thread_sender_role.short_description = "Sender role"

    def __str__(self):
        msg_snippet = self.message[:30] if self.message else (f"[Attachment: {self.attachment.name}]" if self.attachment else "")
        return f"{self.user.username} ({self.get_sender_role_display()}): {msg_snippet}"
