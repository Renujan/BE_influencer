from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
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
            icon="fas fa-exclamation-circle",
            target_url=f"/admin/snippets/complaint/complaint/inspect/{instance.id}/"
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
                    icon="fas fa-reply",
                    target_url=f"/admin/snippets/complaint/complaint/inspect/{instance.id}/"
                )
                if instance.user.email:
                    try:
                        subject = f"Ampli Support: Admin Replied to Ticket #{instance.id}"
                        message = (
                            f"Hello {instance.user.first_name or instance.user.username},\n\n"
                            f"An administrator has replied to your support ticket #{instance.id} '{instance.subject}'.\n\n"
                            f"Admin Reply:\n"
                            f"----------------------------------------\n"
                            f"{instance.admin_reply}\n"
                            f"----------------------------------------\n\n"
                            f"You can view this reply in your Support Dashboard.\n\n"
                            f"Best regards,\n"
                            f"The Ampli Team"
                        )
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[instance.user.email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        print(f"Error sending support ticket reply email: {e}")
        except Complaint.DoesNotExist:
            pass

