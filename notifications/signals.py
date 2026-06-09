from django.db.models.signals import post_save
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
            icon="fas fa-user-plus"
        )

@receiver(post_save, sender=CreatorProfile)
def create_creator_profile_notification(sender, instance, created, **kwargs):
    if created:
        name_display = instance.user.username
        Notification.objects.create(
            title="New User Registered",
            message=f"{name_display} enrolled as a Creator.",
            category="signup",
            icon="fas fa-user-plus"
        )

@receiver(post_save, sender=Campaign)
def create_campaign_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            title="New Campaign Workspace",
            message=f"Campaign '{instance.name}' has been created with a budget of ${instance.budget:,.2f}.",
            category="campaign",
            icon="fas fa-bullhorn"
        )

@receiver(post_save, sender=AdminComplianceTicket)
def create_compliance_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            title="Compliance Ticket Submitted",
            message=f"Ticket '{instance.category}' submitted for campaign '{instance.campaign.name}'.",
            category="compliance",
            icon="fas fa-exclamation-triangle"
        )

@receiver(post_save, sender=PaymentInstallment)
def create_payment_notification(sender, instance, created, **kwargs):
    if created:
        status_text = "funded & secured in escrow" if instance.status == "In Escrow" else "released to creator"
        Notification.objects.create(
            title="Escrow Payment Action",
            message=f"Payment of ${instance.amount:,.2f} for '{instance.campaign.name}' milestone '{instance.milestone_name}' was {status_text}.",
            category="payment",
            icon="fas fa-wallet"
        )
