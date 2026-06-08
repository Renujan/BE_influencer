from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Niche, UserProfile, CreatorSocialAccount
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

