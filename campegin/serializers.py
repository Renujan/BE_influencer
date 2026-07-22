from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Campaign, CampaignTask, CampaignMilestone, Deliverable,
    PaymentInstallment, WorkspaceFile, WorkspaceMessage, AdminComplianceTicket,
    CampaignCategory, CampaignLanguage, CampaignDeliverable, CampaignPlatform, Pitch
)

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
        fields = ["id", "name", "type", "status", "deadline", "brief", "link", "screenshot_name", "assetDriveLink", "assetFileName", "views", "reach", "er"]

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
    class Meta:
        model = AdminComplianceTicket
        fields = ["id", "category", "message", "status", "reply", "date"]

class CampaignSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.username", read_only=True)
    creator_name = serializers.CharField(source="creator.username", read_only=True, default="Open Request")
    tasks = CampaignTaskSerializer(many=True, read_only=True)
    milestones = CampaignMilestoneSerializer(many=True, read_only=True)
    deliverables = DeliverableSerializer(many=True, read_only=True)
    payments = PaymentInstallmentSerializer(many=True, read_only=True)
    files = WorkspaceFileSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    tickets = AdminComplianceTicketSerializer(many=True, read_only=True)

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

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "brand", "brand_name", "creator", "creator_name",
            "status", "budget", "start_date", "end_date", "progress", "brief", "admin_review",
            "category", "delivery_language", "country", "province", "district", "medium", "voice_brief", "screenshare_brief", "video_brief",
            "counter_price", "counter_note", "counter_round", "decline_reason", "created_via",
            "tasks", "milestones", "deliverables", "payments", "files", "messages", "tickets"
        ]
        read_only_fields = ["brand"]

class CampaignCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignCategory
        fields = ["id", "name"]

class CampaignLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignLanguage
        fields = ["id", "name"]

class CampaignDeliverableSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignDeliverable
        fields = ["id", "name"]

class CampaignPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignPlatform
        fields = ["id", "platform_id", "name", "color", "logo"]

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
