from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Niche, BusinessType, BusinessProfile, CreatorProfile, CreatorRate, CreatorSocialAccount, Country, Medium, Province, District
)

class NicheSerializer(serializers.ModelSerializer):
    class Meta:
        model = Niche
        fields = ["id", "name"]

class BusinessTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessType
        fields = ["id", "name"]

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "name", "province"]

class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ["id", "name"]

class MediumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medium
        fields = ["id", "name"]

class CountrySerializer(serializers.ModelSerializer):
    provinces = ProvinceSerializer(many=True, read_only=True)
    mediums = MediumSerializer(many=True, read_only=True)
    districts = DistrictSerializer(many=True, read_only=True)

    class Meta:
        model = Country
        fields = ["id", "name", "currency", "country_code", "provinces", "mediums", "districts"]


class CreatorRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorRate
        fields = ["id", "content_type", "platforms", "price", "min_price", "max_price", "notes"]

class CreatorSocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorSocialAccount
        fields = ["id", "platform", "username", "followers_count", "engagement_rate", "is_connected"]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "is_staff", "is_superuser"]

def parse_followers(val_str):
    if not val_str:
        return 0.0
    val_str = str(val_str).strip().upper()
    try:
        if val_str.endswith('M'):
            return float(val_str[:-1]) * 1_000_000
        elif val_str.endswith('K'):
            return float(val_str[:-1]) * 1_000
        return float(val_str)
    except ValueError:
        return 0.0

def format_followers(val):
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M".replace(".0M", "M")
    elif val >= 1_000:
        return f"{val / 1_000:.1f}K".replace(".0K", "K")
    return str(int(val))

class BusinessProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    business_types = BusinessTypeSerializer(many=True, read_only=True)
    country = CountrySerializer(read_only=True)
    province = ProvinceSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    campaign_count = serializers.SerializerMethodField()
    creators_hired_count = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()
    active_campaigns = serializers.SerializerMethodField()


    class Meta:
        model = BusinessProfile
        fields = [
            "id", "user", "company_name", "business_type", "business_types", "website", "bio",
            "phone", "secondary_phone", "time_zone", "avatar_url", "country", "province", "district",
            "facebook_url", "instagram_handle", "tiktok_handle", "youtube_url",
            "linkedin_url", "twitter_handle", "otp_verified", "status",
            "verification_documents_submitted", "business_reg_number", "business_document",
             "campaign_count", "creators_hired_count", "total_spent", "settings",
             "is_featured", "featured_at", "active_campaigns"
        ]

    def get_settings(self, instance):
        return {
            "email_notifications": instance.email_notifications,
            "sms_notifications": instance.sms_notifications,
            "marketing_emails": instance.marketing_emails,
            "two_factor_auth": instance.two_factor_auth,
            "google_analytics_connected": instance.google_analytics_connected,
        }

    def get_campaign_count(self, instance):
        return instance.user.brand_campaigns.filter(creator__isnull=True).count()
        
    def get_active_campaigns(self, instance):
        campaigns = instance.user.brand_campaigns.filter(creator__isnull=True).order_by('-id')[:3]
        return [
            {
                "id": c.id,
                "name": c.name,
                "budget": float(c.budget) if c.budget else 0,
                "status": c.status,
                "category": c.category
            }
            for c in campaigns
        ]

    def get_creators_hired_count(self, instance):
        return instance.user.brand_campaigns.exclude(creator__isnull=True).values('creator').distinct().count()

    def get_total_spent(self, instance):
        from django.db.models import Sum
        total = instance.user.brand_campaigns.aggregate(Sum('budget'))['budget__sum']
        return float(total) if total else 0.0
    
    def get_settings(self, instance):
        from Setting.models import BusinessSettings
        from Setting.serializers import BusinessSettingsSerializer
        settings_obj, _ = BusinessSettings.objects.get_or_create(business=instance)
        return BusinessSettingsSerializer(settings_obj).data

class CreatorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    niches = NicheSerializer(many=True, read_only=True)
    rates = CreatorRateSerializer(many=True, read_only=True)
    country = CountrySerializer(read_only=True)
    province = ProvinceSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    mediums = MediumSerializer(many=True, read_only=True)
    social_accounts = CreatorSocialAccountSerializer(source="user.social_accounts", many=True, read_only=True)
    campaign_count = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()

    class Meta:
        model = CreatorProfile
        fields = [
            "id", "user", "phone", "location", "country", "bio", "avatar_url",
            "wallet_balance", "next_payout_date", "niches", "mediums", "rates",
            "province", "district", 
            "social_accounts", "otp_verified", "status",
            "verification_documents_submitted", "document_type", "document_front",
            "document_back", "other_details", "campaign_count", "followers_count", "settings",
            "is_featured", "featured_at"
        ]

    def get_campaign_count(self, instance):
        return instance.user.creator_campaigns.count()

    def get_followers_count(self, instance):
        accounts = instance.user.social_accounts.all()
        total = sum(parse_followers(a.followers_count) for a in accounts)
        return format_followers(total) if total > 0 else "0"
    
    def get_settings(self, instance):
        from Setting.models import CreatorSettings
        from Setting.serializers import CreatorSettingsSerializer
        settings_obj, _ = CreatorSettings.objects.get_or_create(creator=instance)
        return CreatorSettingsSerializer(settings_obj).data


