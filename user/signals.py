from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Niche

@receiver(post_save, sender=Niche)
def sync_niche_to_campaign_niche(sender, instance, created, **kwargs):
    from campegin.models import CampaignNiche
    if created:
        CampaignNiche.objects.get_or_create(name=instance.name, defaults={"is_active": True})
