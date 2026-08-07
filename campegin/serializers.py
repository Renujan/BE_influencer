from django.db import models
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Campaign, CampaignTask, CampaignMilestone, Deliverable,
    PaymentInstallment, WorkspaceFile, WorkspaceMessage, AdminComplianceTicket,
    CampaignCategory, CampaignLanguage, CampaignDeliverable, CampaignPlatform, Pitch, CampaignNiche
)

class CampaignNicheSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignNiche
        fields = ["id", "name", "is_active"]

class CampaignTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignTask
        fields = ["id", "title", "is_done", "due_date"]

class CampaignMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignMilestone
        fields = ["id", "title", "is_done"]

class DeliverableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deliverable
        fields = [
            "id", "name", "type", "status", "deadline", "brief", "link", "screenshot_name", 
            "assetDriveLink", "assetFileName", "views", "reach", "er",
            "revision_notes", "revision_reference_link", "revision_reference_file"
        ]

class PaymentInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentInstallment
        fields = ["id", "milestone_name", "amount", "status", "payment_date"]

class WorkspaceFileSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = WorkspaceFile
        fields = ["id", "name", "size", "sender", "sender_name", "date", "time"]

class WorkspaceMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = WorkspaceMessage
        fields = ["id", "sender", "sender_name", "text", "file_attachment", "time", "message_type"]

class AdminComplianceTicketSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = AdminComplianceTicket
        fields = ["id", "category", "message", "status", "reply", "date", "sender_role", "sender_name", "target_audience"]

from chat_monitor.serializers import ChatReviewSerializer

class CampaignSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.username", read_only=True)
    creator_name = serializers.SerializerMethodField()

    def get_creator_name(self, obj):
        if not obj.creator:
            return "Open Request"
        full_name = f"{obj.creator.first_name or ''} {obj.creator.last_name or ''}".strip()
        return full_name if full_name else obj.creator.username
    tasks = CampaignTaskSerializer(many=True, read_only=True)
    milestones = CampaignMilestoneSerializer(many=True, read_only=True)
    deliverables = DeliverableSerializer(many=True, read_only=True)
    payments = PaymentInstallmentSerializer(many=True, read_only=True)
    files = WorkspaceFileSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    tickets = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    def get_tickets(self, obj):
        request = self.context.get('request')
        if not request or not request.user:
            return AdminComplianceTicketSerializer(obj.tickets.all(), many=True).data

        user = request.user
        if user.is_staff or user.is_superuser:
            return AdminComplianceTicketSerializer(obj.tickets.all(), many=True).data

        profile = getattr(user, "profile", None)
        is_creator = (user == obj.creator or (obj.creator and user.id == obj.creator.id) or hasattr(user, "creator_profile") or getattr(profile, "role", "") in ["influencer", "creator"])

        if is_creator:
            qs = obj.tickets.filter(
                models.Q(sender_role__in=["creator", "influencer"]) |
                models.Q(sender=user) |
                (models.Q(sender_role__in=["admin", "system", ""]) & (
                    models.Q(target_audience__iexact="creator") |
                    models.Q(target_audience__iexact="influencer") |
                    models.Q(target_audience__iexact="both") |
                    models.Q(target_audience="") |
                    models.Q(target_audience__isnull=True)
                ))
            ).distinct().order_by("-id")
        else:
            qs = obj.tickets.filter(
                models.Q(sender_role="business") |
                models.Q(sender=user) |
                (models.Q(sender_role__in=["admin", "system", ""]) & (
                    models.Q(target_audience__iexact="business") |
                    models.Q(target_audience__iexact="both") |
                    models.Q(target_audience="") |
                    models.Q(target_audience__isnull=True)
                ))
            ).distinct().order_by("-id")

        return AdminComplianceTicketSerializer(qs, many=True).data

    def get_messages(self, obj):
        request = self.context.get('request')
        if not request or not request.user:
            # Fallback if no request context is provided
            return WorkspaceMessageSerializer(obj.messages.all(), many=True).data

        user = request.user
        if user.is_staff or user.is_superuser:
            # Admin sees all messages
            msgs = obj.messages.all()
        else:
            if hasattr(user, "business_profile"):
                msgs = obj.messages.filter(message_type__in=['main', 'admin_business'])
            elif hasattr(user, "creator_profile"):
                msgs = obj.messages.filter(message_type__in=['main', 'admin_creator'])
            else:
                msgs = obj.messages.filter(message_type='main')
        return WorkspaceMessageSerializer(msgs, many=True).data

    def get_reviews(self, obj):
        request = self.context.get('request')
        if not request or not request.user:
            return ChatReviewSerializer(obj.chat_reviews.all(), many=True).data

        user = request.user
        profile = getattr(user, "profile", None)
        is_creator = (user == obj.creator or (obj.creator and user.id == obj.creator.id) or hasattr(user, "creator_profile") or getattr(profile, "role", "") in ["influencer", "creator"])

        if is_creator:
            qs = obj.chat_reviews.filter(
                models.Q(target_audience__iexact="creator") |
                models.Q(target_audience__iexact="influencer") |
                models.Q(target_audience__iexact="both") |
                models.Q(target_audience="") |
                models.Q(target_audience__isnull=True)
            ).order_by("-id")
        else:
            qs = obj.chat_reviews.filter(
                models.Q(target_audience__iexact="business") |
                models.Q(target_audience__iexact="both") |
                models.Q(target_audience="") |
                models.Q(target_audience__isnull=True)
            ).order_by("-id")
        return ChatReviewSerializer(qs, many=True).data

    creator_rating = serializers.SerializerMethodField()

    def get_creator_rating(self, obj):
        if hasattr(obj, "rating") and obj.rating:
            return {
                "id": obj.rating.id,
                "rating": obj.rating.rating,
                "review": obj.rating.review,
                "created_at": obj.rating.created_at,
            }
        return None

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "brand", "brand_name", "creator", "creator_name",
            "status", "budget", "min_budget", "max_budget", "per_creator_budget", "min_price", "max_price", "rate_card_id", "start_date", "end_date", "progress", "brief", "admin_review",
            "category", "delivery_language", "country", "province", "district", "medium", "voice_brief", "screenshare_brief", "video_brief",
            "counter_price", "counter_note", "counter_round", "decline_reason", "created_via", "created_time", "created_at",
            "tasks", "milestones", "deliverables", "payments", "files", "messages", "tickets", "reviews", "creator_rating"
        ]
        read_only_fields = ["brand"]

class CampaignCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignCategory
        fields = ["id", "name", "platform", "type", "duration", "min_price", "max_price"]

class CampaignLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignLanguage
        fields = ["id", "name"]

class CampaignDeliverableSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignDeliverable
        fields = ["id", "name", "platform"]

class CampaignPlatformSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = CampaignPlatform
        fields = ["id", "platform_id", "name", "color", "logo"]

    def get_logo(self, obj):
        if obj.logo:
            try:
                return obj.logo.url
            except Exception:
                return str(obj.logo)
        return ""

class PitchSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.username", read_only=True)
    creator_name = serializers.CharField(source="creator.username", read_only=True)

    class Meta:
        model = Pitch
        fields = [
            "id", "creator", "creator_name", "brand", "brand_name",
            "campaign_name", "budget", "sent_date", "tags", "status",
            "description", "deliverables", "counter_offer", "counter_note", "counter_count", "attachment", "decline_reason"
        ]
        read_only_fields = ["creator"]
