from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from complaint.models import Complaint
from notifications.models import Notification

@receiver(post_save, sender=Complaint)
def handle_complaint_created(sender, instance, created, **kwargs):
    """
    Auto-triggers a Compliance Notification when a new support ticket is raised.
    """
    if created:
        Notification.objects.create(
            title="New Support Ticket",
            message=f"Ticket #{instance.id} '{instance.subject}' was raised by {instance.user.username}.",
            category="compliance",
            icon="fas fa-exclamation-circle"
        )

@receiver(pre_save, sender=Complaint)
def handle_complaint_reply_notification(sender, instance, **kwargs):
    """
    Auto-triggers a Notification when the administrator adds or updates a reply on a ticket.
    """
    if instance.id:
        try:
            old_instance = Complaint.objects.get(id=instance.id)
            # If admin_reply has changed and is now populated
            if old_instance.admin_reply != instance.admin_reply and instance.admin_reply:
                Notification.objects.create(
                    title="Support Ticket Replied",
                    message=f"Admin replied to ticket #{instance.id} '{instance.subject}': \"{instance.admin_reply[:60]}...\"",
                    category="compliance",
                    icon="fas fa-reply"
                )
        except Complaint.DoesNotExist:
            pass
