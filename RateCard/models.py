from django.db import models
from django.contrib.auth.models import User
from django import forms
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel
from wagtail.admin.forms import WagtailAdminModelForm


class RateCardForm(WagtailAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from campegin.models import CampaignPlatform
        platform_choices = [(p.name, p.name) for p in CampaignPlatform.objects.all()]
        self.fields["platform"].widget = forms.Select(
            choices=[("", "Select Platform")] + platform_choices,
            attrs={"class": "w-full"}
        )


class RateCard(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rate_cards", null=True, blank=True)
    creator_name = models.CharField(max_length=150, blank=True, default="")
    platform = models.CharField(max_length=100, blank=True, default="")
    type = models.CharField(max_length=100, blank=True, default="")
    duration = models.CharField(max_length=100, blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, null=True, blank=True)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, null=True, blank=True)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, null=True, blank=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    base_form_class = RateCardForm

    panels = [
        FieldPanel("creator"),
        FieldPanel("creator_name"),
        FieldPanel("platform"),
        FieldPanel("type"),
        FieldPanel("duration"),
        FieldPanel("price"),
        FieldPanel("min_price"),
        FieldPanel("max_price"),
        FieldPanel("description"),
        FieldPanel("is_active"),
    ]

    class Meta:
        verbose_name = "Rate Card"
        verbose_name_plural = "Rate Cards"
        ordering = ["-id"]

    def get_niches(self):
        user = self.creator
        if not user and self.creator_name:
            from django.contrib.auth.models import User
            user = User.objects.filter(
                models.Q(username__iexact=self.creator_name) |
                models.Q(first_name__iexact=self.creator_name)
            ).first()
        if user and hasattr(user, "creator_profile") and user.creator_profile:
            niches = [n.name for n in user.creator_profile.niches.all()]
            if niches:
                return ", ".join(niches)
        return "-"
    get_niches.short_description = "Selected Niches"

    @property
    def display_duration(self):
        if self.duration and str(self.duration).strip():
            return self.duration
        t_lower = (self.type or "").lower()
        if any(k in t_lower for k in ["reel", "story", "shorts", "tiktok"]):
            return "60s"
        if any(k in t_lower for k in ["video", "youtube"]):
            return "3-5 mins"
        if any(k in t_lower for k in ["post", "image", "photo"]):
            return "1 Post"
        return "-"

    def __str__(self):
        c_str = self.creator.username if self.creator else (self.creator_name or "General Creator")
        return f"{c_str} - {self.platform} {self.type} (${self.price})"
