from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Niche, UserProfile, CreatorSocialAccount, Campaign, CampaignTask,
    CampaignMilestone, Deliverable, PaymentInstallment, WorkspaceFile,
    WorkspaceMessage, AdminComplianceTicket
)

class NicheSerializer(serializers.ModelSerializer):
    class Meta:
        model = Niche
        fields = ["id", "name"]

class CreatorSocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorSocialAccount
        fields = ["id", "platform", "username", "followers_count", "engagement_rate", "is_connected"]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    niches = NicheSerializer(many=True, read_only=True)
    social_accounts = CreatorSocialAccountSerializer(source="user.social_accounts", many=True, read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "user", "role", "phone", "avatar_url", "bio", "location",
            "wallet_balance", "next_payout_date", "niches", "social_accounts",
            "company_name", "business_type", "website"
        ]

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
        fields = ["id", "name", "type", "status", "deadline", "brief", "link", "screenshot_name"]

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
        fields = ["id", "sender", "sender_name", "text", "file_attachment", "time"]

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
    messages = WorkspaceMessageSerializer(many=True, read_only=True)
    tickets = AdminComplianceTicketSerializer(many=True, read_only=True)

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "brand", "brand_name", "creator", "creator_name",
            "status", "budget", "start_date", "progress", "brief",
            "tasks", "milestones", "deliverables", "payments", "files", "messages", "tickets"
        ]
