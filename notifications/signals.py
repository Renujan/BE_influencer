from django.db.models.signals import post_save, pre_save, post_delete
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from user.models import BusinessProfile, CreatorProfile
from campegin.models import Campaign, AdminComplianceTicket, PaymentInstallment, Pitch, WorkspaceMessage
from portfolio.models import PortfolioItem
from chat_monitor.models import ChatReview
from notifications.models import Notification

@receiver(user_logged_in)
def create_login_notification(sender, request, user, **kwargs):
    role_display = "Administrator"
    t_role = "admin"
    if hasattr(user, 'creator_profile'):
        role_display = "Creator"
        t_role = "creator"
    elif hasattr(user, 'business_profile'):
        role_display = "Business"
        t_role = "business"
    Notification.objects.create(
        user=user,
        target_role=t_role,
        title="User Signed In",
        message="Signed into the system.",
        category="signup",
        icon="fas fa-sign-in-alt"
    )

@receiver(post_save, sender=BusinessProfile)
def create_business_profile_notification(sender, instance, created, **kwargs):
    if created:
        name_display = instance.company_name or instance.user.username
        Notification.objects.create(
            target_role="admin",
            title="New User Registered",
            message=f"{name_display} enrolled as a Business.",
            category="signup",
            icon="fas fa-user-plus",
            target_url=f"/admin/businessprofile/inspect/{instance.id}/"
        )

@receiver(post_save, sender=CreatorProfile)
def create_creator_profile_notification(sender, instance, created, **kwargs):
    if created:
        name_display = instance.user.username
        Notification.objects.create(
            target_role="admin",
            title="New User Registered",
            message=f"{name_display} enrolled as a Creator.",
            category="signup",
            icon="fas fa-user-plus",
            target_url=f"/admin/creatorprofile/inspect/{instance.id}/"
        )

# --- Campaign Signals ---
@receiver(pre_save, sender=Campaign)
def cache_campaign_status(sender, instance, **kwargs):
    if instance.id:
        try:
            instance._old_status = Campaign.objects.get(id=instance.id).status
        except Campaign.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Campaign)
def create_campaign_notification(sender, instance, created, **kwargs):
    if created:
        if instance.brand:
            Notification.objects.create(
                user=instance.brand,
                target_role="business",
                title="New Campaign Workspace",
                message=f"Campaign '{instance.name}' has been created with a budget of ${instance.budget:,.2f}.",
                category="campaign",
                icon="fas fa-bullhorn",
                target_url="/dashboard/campaigns"
            )
        if instance.creator:
            Notification.objects.create(
                user=instance.creator,
                target_role="creator",
                title="New Campaign Invite",
                message=f"You have been invited to campaign '{instance.name}'.",
                category="campaign",
                icon="fas fa-bullhorn",
                target_url="/creator/campaigns"
            )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != instance.status:
            is_declined = instance.status.lower() in ["declined", "cancelled", "rejected"]
            title_txt = "Campaign Declined" if is_declined else f"Campaign {instance.status.capitalize()}"
            msg_txt = f"Campaign '{instance.name}' status changed to {instance.status}."
            icon_txt = "fas fa-times-circle" if is_declined else "fas fa-sync"

            if instance.brand:
                Notification.objects.create(
                    user=instance.brand,
                    target_role="business",
                    title=title_txt,
                    message=msg_txt,
                    category="campaign",
                    icon=icon_txt,
                    target_url="/dashboard/campaigns"
                )
            if instance.creator:
                Notification.objects.create(
                    user=instance.creator,
                    target_role="creator",
                    title=title_txt,
                    message=msg_txt,
                    category="campaign",
                    icon=icon_txt,
                    target_url="/creator/campaigns"
                )

@receiver(post_delete, sender=Campaign)
def create_campaign_delete_notification(sender, instance, **kwargs):
    if instance.brand:
        Notification.objects.create(
            user=instance.brand,
            target_role="business",
            title="Campaign Deleted",
            message=f"Campaign '{instance.name}' was removed.",
            category="campaign",
            icon="fas fa-trash",
            target_url="/dashboard/campaigns"
        )
    if instance.creator:
        Notification.objects.create(
            user=instance.creator,
            target_role="creator",
            title="Campaign Deleted",
            message=f"Campaign '{instance.name}' was removed.",
            category="campaign",
            icon="fas fa-trash",
            target_url="/creator/campaigns"
        )

# --- Pitch Signals ---
@receiver(pre_save, sender=Pitch)
def cache_pitch_status(sender, instance, **kwargs):
    if instance.id:
        try:
            instance._old_status = Pitch.objects.get(id=instance.id).status
        except Pitch.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Pitch)
def create_pitch_notification(sender, instance, created, **kwargs):
    camp_name = getattr(instance, 'campaign_name', '') or "Campaign"
    brand_user = getattr(instance, 'brand', None)
    creator_user = getattr(instance, 'creator', None)

    if created:
        if creator_user:
            Notification.objects.create(
                user=creator_user,
                target_role="creator",
                title="Pitch Submitted",
                message=f"Your pitch for '{camp_name}' has been submitted.",
                category="campaign",
                icon="fas fa-paper-plane",
                target_url="/creator/pitches"
            )
        if brand_user:
            Notification.objects.create(
                user=brand_user,
                target_role="business",
                title="New Pitch Received",
                message=f"Creator '{creator_user.username if creator_user else 'Creator'}' submitted a pitch for '{camp_name}'.",
                category="campaign",
                icon="fas fa-paper-plane",
                target_url="/dashboard/requests"
            )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != instance.status:
            st = str(instance.status).lower()
            if "accept" in st:
                if creator_user:
                    Notification.objects.create(
                        user=creator_user,
                        target_role="creator",
                        title="Pitch Accepted!",
                        message=f"Your pitch for '{camp_name}' was accepted!",
                        category="campaign",
                        icon="fas fa-check-circle",
                        target_url="/creator/campaigns"
                    )
                if brand_user:
                    Notification.objects.create(
                        user=brand_user,
                        target_role="business",
                        title="Pitch Accepted",
                        message=f"Pitch for '{camp_name}' has been accepted.",
                        category="campaign",
                        icon="fas fa-check-circle",
                        target_url="/dashboard/campaigns"
                    )
            elif "decline" in st or "reject" in st:
                if creator_user:
                    Notification.objects.create(
                        user=creator_user,
                        target_role="creator",
                        title="Pitch Declined",
                        message=f"Your pitch for '{camp_name}' was declined.",
                        category="campaign",
                        icon="fas fa-times-circle",
                        target_url="/creator/pitches"
                    )
                if brand_user:
                    Notification.objects.create(
                        user=brand_user,
                        target_role="business",
                        title="Pitch Declined",
                        message=f"Pitch for '{camp_name}' was declined.",
                        category="campaign",
                        icon="fas fa-times-circle",
                        target_url="/dashboard/requests"
                    )

@receiver(post_delete, sender=Pitch)
def create_pitch_delete_notification(sender, instance, **kwargs):
    camp_name = getattr(instance, 'campaign_name', '') or "Campaign"
    creator_user = getattr(instance, 'creator', None)
    if creator_user:
        Notification.objects.create(
            user=creator_user,
            target_role="creator",
            title="Pitch Withdrawn",
            message=f"Pitch for '{camp_name}' was removed.",
            category="campaign",
            icon="fas fa-trash",
            target_url="/creator/pitches"
        )

# --- Workspace Chat Signals ---
@receiver(post_save, sender=WorkspaceMessage)
def create_workspace_message_notification(sender, instance, created, **kwargs):
    if created and instance.campaign:
        camp = instance.campaign
        sender_user = instance.sender
        snippet = (instance.text[:50] + "...") if len(instance.text) > 50 else instance.text

        if camp.brand and sender_user == camp.brand and camp.creator:
            Notification.objects.create(
                user=camp.creator,
                target_role="creator",
                title="New Workspace Message",
                message=f"Message from '{camp.brand_name}': {snippet}",
                category="compliance",
                icon="fas fa-comment-dots",
                target_url=f"/workspace/{camp.id}"
            )
        elif camp.creator and sender_user == camp.creator and camp.brand:
            Notification.objects.create(
                user=camp.brand,
                target_role="business",
                title="New Workspace Message",
                message=f"Message from '{camp.creator_name}': {snippet}",
                category="compliance",
                icon="fas fa-comment-dots",
                target_url=f"/workspace/{camp.id}"
            )

# --- Support & Chat Review Directives Signals ---
@receiver(post_save, sender=AdminComplianceTicket)
def create_compliance_notification(sender, instance, created, **kwargs):
    if created:
        t_role = "business" if instance.sender_role == "business" else ("creator" if instance.sender_role == "creator" else "admin")
        Notification.objects.create(
            user=instance.sender,
            target_role=t_role,
            title="Compliance Ticket Submitted",
            message=f"Ticket '{instance.category}' submitted for campaign '{instance.campaign.name}'.",
            category="compliance",
            icon="fas fa-exclamation-triangle",
            target_url="/dashboard/support" if t_role == "business" else "/creator/support"
        )

@receiver(post_save, sender=ChatReview)
def create_chat_review_notification(sender, instance, created, **kwargs):
    if created and instance.campaign:
        camp = instance.campaign
        snippet = (instance.review_text[:60] + "...") if len(instance.review_text) > 60 else instance.review_text
        
        if instance.target_audience in ["creator", "both"] and camp.creator:
            Notification.objects.create(
                user=camp.creator,
                target_role="creator",
                title="Admin Review Directive",
                message=f"Admin directive issued for campaign '{camp.name}': {snippet}",
                category="compliance",
                icon="fas fa-shield-alt",
                target_url=f"/workspace/{camp.id}"
            )
        if instance.target_audience in ["business", "both"] and camp.brand:
            Notification.objects.create(
                user=camp.brand,
                target_role="business",
                title="Admin Review Directive",
                message=f"Admin directive issued for campaign '{camp.name}': {snippet}",
                category="compliance",
                icon="fas fa-shield-alt",
                target_url=f"/workspace/{camp.id}"
            )

# --- Escrow Payment Signals ---
@receiver(post_save, sender=PaymentInstallment)
def create_payment_notification(sender, instance, created, **kwargs):
    if created:
        status_text = "funded & secured in escrow" if instance.status == "In Escrow" else "released to creator"
        if instance.campaign.brand:
            Notification.objects.create(
                user=instance.campaign.brand,
                target_role="business",
                title="Escrow Payment Action",
                message=f"Payment of ${instance.amount:,.2f} for '{instance.campaign.name}' milestone '{instance.milestone_name}' was {status_text}.",
                category="payment",
                icon="fas fa-wallet",
                target_url="/dashboard/payments"
            )
        if instance.campaign.creator:
            Notification.objects.create(
                user=instance.campaign.creator,
                target_role="creator",
                title="Escrow Payment Action",
                message=f"Payment of ${instance.amount:,.2f} for '{instance.campaign.name}' milestone '{instance.milestone_name}' was {status_text}.",
                category="payment",
                icon="fas fa-wallet",
                target_url="/creator/earnings"
            )

# --- Portfolio Item Signals ---
@receiver(post_save, sender=PortfolioItem)
def create_portfolio_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.creator,
            target_role="creator",
            title="Portfolio Item Added",
            message=f"Portfolio item '{instance.title}' ({instance.platform}) was added successfully.",
            category="signup",
            icon="fas fa-briefcase",
            target_url="/creator/portfolio"
        )
    else:
        Notification.objects.create(
            user=instance.creator,
            target_role="creator",
            title="Portfolio Item Updated",
            message=f"Portfolio item '{instance.title}' was updated.",
            category="signup",
            icon="fas fa-edit",
            target_url="/creator/portfolio"
        )

@receiver(post_delete, sender=PortfolioItem)
def create_portfolio_delete_notification(sender, instance, **kwargs):
    Notification.objects.create(
        user=instance.creator,
        target_role="creator",
        title="Portfolio Item Deleted",
        message=f"Portfolio item '{instance.title}' was deleted.",
        category="signup",
        icon="fas fa-trash",
        target_url="/creator/portfolio"
    )

# --- Business Service Request Signals ---
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
        role_display = "Creator" if hasattr(user, 'creator_profile') else ("Business" if hasattr(user, 'business_profile') else "User")
        t_role = "creator" if hasattr(user, 'creator_profile') else ("business" if hasattr(user, 'business_profile') else "all")
        Notification.objects.create(
            user=user,
            target_role=t_role,
            title="New Service Inquiry",
            message=f"Inquiry submitted for service '{instance.service.title}' (Provider: {instance.service.provider}).",
            category="campaign",
            icon="fas fa-paper-plane",
            target_url="/dashboard/business-services" if t_role == "business" else "/creator/business-services"
        )
    else:
        old_status = getattr(instance, "_old_status", None)
        if old_status and old_status != instance.status:
            user = instance.user
            t_role = "creator" if hasattr(user, 'creator_profile') else ("business" if hasattr(user, 'business_profile') else "all")
            
            if instance.status == "connected":
                Notification.objects.create(
                    user=user,
                    target_role=t_role,
                    title="Service Inquiry Connected",
                    message=f"Inquiry for '{instance.service.title}' has been successfully connected.",
                    category="campaign",
                    icon="fas fa-handshake",
                    target_url="/dashboard/business-services" if t_role == "business" else "/creator/business-services"
                )
            elif instance.status == "declined":
                Notification.objects.create(
                    user=user,
                    target_role=t_role,
                    title="Service Inquiry Declined",
                    message=f"Inquiry for '{instance.service.title}' has been declined.",
                    category="campaign",
                    icon="fas fa-times-circle",
                    target_url="/dashboard/business-services" if t_role == "business" else "/creator/business-services"
                )



