from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from user.models import CreatorRate
from .models import RateCard


@receiver(post_save, sender=CreatorRate)
def sync_creator_rate_to_rate_card(sender, instance, created, **kwargs):
    try:
        user = instance.creator.user if (instance.creator and instance.creator.user) else None
        c_name = (user.get_full_name() or user.username) if user else "Creator"

        t_lower = (instance.content_type or "").lower()
        default_dur = "60s" if any(k in t_lower for k in ["reel", "story", "shorts", "tiktok"]) else ("3-5 mins" if any(k in t_lower for k in ["video", "youtube"]) else ("1 Post" if any(k in t_lower for k in ["post", "image", "photo"]) else "-"))

        rate_card, _ = RateCard.objects.get_or_create(
            creator=user,
            platform=instance.platforms or "General",
            type=instance.content_type or "Deliverable",
            defaults={
                "creator_name": c_name,
                "duration": default_dur,
                "price": instance.price or 0.00,
                "min_price": instance.min_price or 0.00,
                "max_price": instance.max_price or 0.00,
                "description": instance.notes or "",
                "is_active": True,
            }
        )

        rate_card.creator_name = c_name
        if not rate_card.duration or not rate_card.duration.strip():
            rate_card.duration = default_dur
        rate_card.price = instance.price or 0.00
        rate_card.min_price = instance.min_price or 0.00
        rate_card.max_price = instance.max_price or 0.00
        rate_card.description = instance.notes or ""
        rate_card.is_active = True
        rate_card.save()
    except Exception as e:
        print(f"Error syncing CreatorRate to RateCard: {e}")


@receiver(post_delete, sender=CreatorRate)
def delete_creator_rate_from_rate_card(sender, instance, **kwargs):
    try:
        user = instance.creator.user if (instance.creator and instance.creator.user) else None
        if user:
            RateCard.objects.filter(
                creator=user,
                platform=instance.platforms or "General",
                type=instance.content_type or "Deliverable",
            ).delete()
    except Exception as e:
        print(f"Error deleting CreatorRate from RateCard: {e}")
