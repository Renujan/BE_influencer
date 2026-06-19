from django.db.models.signals import post_save, pre_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from user.models import BusinessProfile, CreatorProfile
from campegin.models import Campaign, AdminComplianceTicket, PaymentInstallment
from notifications.models import Notification

@receiver(user_logged_in)
def create_login_notification(sender, request, user, **kwargs):
    role_display = "Administrator"
    if hasattr(user, 'creator_profile'):
        role_display = "Creator"
    elif hasattr(user, 'business_profile'):
        role_display = "Business"
    Notification.objects.create(
        title="User Signed In",
        message=f"{user.username} ({role_display}) signed into the system.",
        category="signup",
        icon="fas fa-sign-in-alt"
    )

@receiver(post_save, sender=BusinessProfile)
def create_business_profile_notification(sender, instance, created, **kwargs):
    if created:
        name_display = instance.company_name or instance.user.username
        Notification.objects.create(
            title="New User Registered",
            message=f"{name_display} enrolled as a Business.",
            category="signup",
            icon="fas fa-user-plus",
            target_url=f"/admin/snippets/user/businessprofile/inspect/{instance.id}/"
        )

@receiver(post_save, sender=CreatorProfile)
def create_creator_profile_notification(sender, instance, created, **kwargs):
    if created:
        name_display = instance.user.username
        Notification.objects.create(
            title="New User Registered",
            message=f"{name_display} enrolled as a Creator.",
            category="signup",
            icon="fas fa-user-plus",
            target_url=f"/admin/snippets/user/creatorprofile/inspect/{instance.id}/"
        )

@receiver(post_save, sender=Campaign)
def create_campaign_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            title="New Campaign Workspace",
            message=f"Campaign '{instance.name}' has been created with a budget of ${instance.budget:,.2f}.",
            category="campaign",
            icon="fas fa-bullhorn",
            target_url=f"/admin/snippets/campegin/campaign/inspect/{instance.id}/"
        )

@receiver(post_save, sender=AdminComplianceTicket)
def create_compliance_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            title="Compliance Ticket Submitted",
            message=f"Ticket '{instance.category}' submitted for campaign '{instance.campaign.name}'.",
            category="compliance",
            icon="fas fa-exclamation-triangle",
            target_url=f"/admin/snippets/campegin/admincomplianceticket/inspect/{instance.id}/"
        )

@receiver(post_save, sender=PaymentInstallment)
def create_payment_notification(sender, instance, created, **kwargs):
    if created:
        status_text = "funded & secured in escrow" if instance.status == "In Escrow" else "released to creator"
        Notification.objects.create(
            title="Escrow Payment Action",
            message=f"Payment of ${instance.amount:,.2f} for '{instance.campaign.name}' milestone '{instance.milestone_name}' was {status_text}.",
            category="payment",
            icon="fas fa-wallet",
            target_url=f"/admin/snippets/campegin/paymentinstallment/inspect/{instance.id}/"
        )


from business_service.models import BusinessServiceRequest

@receiver(pre_save, sender=BusinessServiceRequest)
def cache_business_service_request_status(sender, instance, **kwargs):
    if instance.id:
        try:
            instance._old_status = BusinessServiceRequest.objects.get(id=instance.id).status
        except BusinessServiceRequest.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=BusinessServiceRequest)
def create_business_service_request_notification(sender, instance, created, **kwargs):
    if created:
        user = instance.user
        if hasattr(user, 'creator_profile'):
            role_display = "Creator"
        elif hasattr(user, 'business_profile'):
            role_display = "Business"
        else:
            role_display = "User"
        Notification.objects.create(
            title="New Service Inquiry",
            message=f"{role_display} '{user.username}' submitted an inquiry for service '{instance.service.title}' (Provider: {instance.service.provider}).",
            category="campaign",
            icon="fas fa-paper-plane",
            target_url=f"/admin/snippets/business_service/businessservicerequest/inspect/{instance.id}/"
        )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != instance.status:
            user = instance.user
            if hasattr(user, 'creator_profile'):
                role_display = "Creator"
            elif hasattr(user, 'business_profile'):
                role_display = "Business"
            else:
                role_display = "User"
            
            if instance.status == "connected":
                Notification.objects.create(
                    title="Service Inquiry Connected",
                    message=f"{role_display} '{user.username}' inquiry for '{instance.service.title}' has been successfully connected.",
                    category="campaign",
                    icon="fas fa-handshake",
                    target_url=f"/admin/snippets/business_service/businessservicerequest/inspect/{instance.id}/"
                )
            elif instance.status == "declined":
                Notification.objects.create(
                    title="Service Inquiry Declined",
                    message=f"{role_display} '{user.username}' inquiry for '{instance.service.title}' has been declined.",
                    category="campaign",
                    icon="fas fa-times-circle",
                    target_url=f"/admin/snippets/business_service/businessservicerequest/inspect/{instance.id}/"
                )



