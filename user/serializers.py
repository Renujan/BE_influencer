from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Niche, BusinessProfile, CreatorProfile, CreatorRate, CreatorSocialAccount
)

class NicheSerializer(serializers.ModelSerializer):
    class Meta:
        model = Niche
        fields = ["id", "name"]

class CreatorRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorRate
        fields = ["id", "content_type", "platforms", "price", "notes"]

class CreatorSocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorSocialAccount
        fields = ["id", "platform", "username", "followers_count", "engagement_rate", "is_connected"]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]

class BusinessProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = BusinessProfile
        fields = [
            "id", "user", "company_name", "business_type", "website", "bio",
            "phone", "secondary_phone", "time_zone", "avatar_url",
            "facebook_url", "instagram_handle", "tiktok_handle", "youtube_url",
            "linkedin_url", "twitter_handle", "otp_verified"
        ]

class CreatorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    niches = NicheSerializer(many=True, read_only=True)
    rates = CreatorRateSerializer(many=True, read_only=True)
    social_accounts = CreatorSocialAccountSerializer(source="user.social_accounts", many=True, read_only=True)

    class Meta:
        model = CreatorProfile
        fields = [
            "id", "user", "phone", "location", "bio", "avatar_url",
            "wallet_balance", "next_payout_date", "niches", "rates",
            "social_accounts", "otp_verified"
        ]
