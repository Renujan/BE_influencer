from django.db import models

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Service Category"
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name

class BusinessService(models.Model):
    TARGET_CHOICES = (
        ("business", "Business"),
        ("creator", "Creator"),
        ("both", "Both"),
    )

    service_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Unique Business Service identifier (automatically generated).",
    )
    title = models.CharField(max_length=255)
    provider = models.CharField(max_length=255)
    rate = models.CharField(
        max_length=255,
        help_text="e.g. 'From $1,500 / project' or 'From $250 / hour'"
    )
    speed = models.CharField(
        max_length=255,
        help_text="e.g. '3-5 Days' or 'Ongoing'"
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
    )
    description = models.TextField()
    bullet_points = models.TextField(
        help_text="Highlight points of the service, one point per line."
    )
    target_audience = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        default="both",
        help_text="Determine whether this service shows for businesses, creators, or both.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active services will be shown in the dashboards.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Business Service"
        verbose_name_plural = "Business Services"

    def generate_next_id(self):
        import re
        max_num = 0
        queryset = BusinessService.objects.all()
        if self.id:
            queryset = queryset.exclude(id=self.id)
            
        for s in queryset:
            if s.service_id:
                match = re.match(r"^BS(\d+)", s.service_id)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
        next_num = max_num + 1
        
        suffix_map = {
            "business": "-BU",
            "creator": "-CR",
            "both": "-BO"
        }
        suffix = suffix_map.get(self.target_audience, "-BO")
        return f"BS{next_num:03d}{suffix}"

    def save(self, *args, **kwargs):
        import re
        if not self.service_id:
            self.service_id = self.generate_next_id()
        else:
            # If target_audience changed, update the suffix
            match = re.match(r"^(BS\d+)", self.service_id)
            if match:
                base_part = match.group(1)
                suffix_map = {
                    "business": "-BU",
                    "creator": "-CR",
                    "both": "-BO"
                }
                suffix = suffix_map.get(self.target_audience, "-BO")
                self.service_id = f"{base_part}{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service_id or 'TEMP'} - {self.title} by {self.provider} ({self.get_target_audience_display()})"

from django.contrib.auth.models import User

class BusinessServiceRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("connected", "Connected"),
        ("declined", "Declined"),
    )
    TIMELINE_CHOICES = (
        ("Standard", "Standard Speed"),
        ("Urgent", "Urgent / Rush"),
        ("Flexible", "Flexible / Ongoing"),
    )

    service = models.ForeignKey(
        BusinessService,
        on_delete=models.CASCADE,
        related_name="requests",
        help_text="The service that is being requested."
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="business_service_requests",
        help_text="The user (creator or business) making the request."
    )
    message = models.TextField(
        help_text="Project brief or inquiry details."
    )
    budget = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Proposed budget for the request (e.g. '1500' or 'Flexible')."
    )
    timeline = models.CharField(
        max_length=50,
        choices=TIMELINE_CHOICES,
        default="Standard",
        help_text="Timeline requirement."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Status of the request."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"
        ordering = ["-created_at"]

    def get_user_role(self):
        try:
            return self.user.profile.role.capitalize()
        except AttributeError:
            return "Unknown"
    get_user_role.short_description = "User Role"

    def __str__(self):
        return f"Request by {self.user.username} for {self.service.title} ({self.get_status_display()})"

