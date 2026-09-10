from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Niche, BusinessType, BusinessProfile

@receiver(post_save, sender=Niche)
def sync_niche_to_campaign_niche(sender, instance, created, **kwargs):
    from campegin.models import CampaignNiche
    if created:
        CampaignNiche.objects.get_or_create(name=instance.name, defaults={"is_active": True})

@receiver(post_delete, sender=BusinessType)
def cleanup_business_type_on_delete(sender, instance, **kwargs):
    """
    When a BusinessType is deleted by Super Admin, clean up any references to it
    in BusinessProfile.business_type (CharField) and ensure M2M links are removed.
    """
    deleted_name = (instance.name or "").strip().lower()
    if not deleted_name:
        return

    for profile in BusinessProfile.objects.all():
        changed = False
        if profile.business_type:
            types = [t.strip() for t in profile.business_type.split(",") if t.strip()]
            filtered = [t for t in types if t.lower() != deleted_name]
            if len(filtered) != len(types):
                profile.business_type = ", ".join(filtered) if filtered else None
                changed = True

        if profile.business_types.filter(id=instance.id).exists():
            profile.business_types.remove(instance)
            changed = True

        if changed:
            profile.save(update_fields=["business_type"])

