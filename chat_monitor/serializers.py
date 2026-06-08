from rest_framework import serializers
from django.contrib.auth.models import User
from campegin.models import Campaign
from .models import ChatMessage, ChatReview

class WorkspaceMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = ChatMessage
        fields = ["id", "sender", "sender_name", "text", "file_attachment", "time"]

class CampaignChatSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.username", read_only=True)
    creator_name = serializers.CharField(source="creator.username", read_only=True, default="Open Request")
    
    class Meta:
        model = Campaign
        fields = [
            "id", "name", "brand", "brand_name", "creator", "creator_name",
            "status", "budget", "progress"
        ]

class ChatReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatReview
        fields = ["id", "category", "review_text", "target_audience", "created_at"]
