from django.db import models
from wagtail.snippets.models import register_snippet
import re

@register_snippet
class Inquiry(models.Model):
    ROLE_CHOICES = (
        ("brand", "Brand / Brand Representative"),
        ("creator", "Creator / Influencer"),
        ("agency", "Agency Partner"),
        ("other", "Other Inquiry"),
    )
    
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("contacted", "Contacted"),
        ("resolved", "Resolved"),
    )

    inquiry_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Unique Inquiry identifier (automatically generated).",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="brand")
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"
        ordering = ["-created_at"]

    def generate_next_id(self):
        max_num = 0
        queryset = Inquiry.objects.all()
        if self.id:
            queryset = queryset.exclude(id=self.id)
            
        for q in queryset:
            if q.inquiry_id:
                match = re.match(r"^INQ(\d+)", q.inquiry_id)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
        next_num = max_num + 1
        
        suffix_map = {
            "brand": "-BR",
            "creator": "-CR",
            "agency": "-AG",
            "other": "-OT"
        }
        suffix = suffix_map.get(self.role, "-OT")
        return f"INQ{next_num:03d}{suffix}"

    def save(self, *args, **kwargs):
        if not self.inquiry_id:
            self.inquiry_id = self.generate_next_id()
        else:
            match = re.match(r"^(INQ\d+)", self.inquiry_id)
            if match:
                base_part = match.group(1)
                suffix_map = {
                    "brand": "-BR",
                    "creator": "-CR",
                    "agency": "-AG",
                    "other": "-OT"
                }
                suffix = suffix_map.get(self.role, "-OT")
                self.inquiry_id = f"{base_part}{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.inquiry_id or 'TEMP'} - {self.name} ({self.get_role_display()})"

