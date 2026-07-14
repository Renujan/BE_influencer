from rest_framework import serializers
from django.contrib.auth.models import User
from user.models import CreatorProfile, BusinessProfile, Niche, CreatorRate, CreatorSocialAccount, Country
from user.serializers import CreatorRateSerializer, CreatorSocialAccountSerializer
from .models import CreatorSettings, CreatorPayoutMethod, BusinessSettings

class CreatorPayoutMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorPayoutMethod
        fields = ["id", "method_type", "details", "is_primary"]

class CreatorSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorSettings
        exclude = ["creator"]

class CreatorFullSettingsSerializer(serializers.Serializer):
    # User fields
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)
    email = serializers.EmailField(source="user.email", required=False)
    
    # Profile fields
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    location = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    bio = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    avatar_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    wallet_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    next_payout_date = serializers.CharField(read_only=True, required=False)
    
    # Niches (list of strings)
    niches = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    
    # Rates
    rates = CreatorRateSerializer(many=True, required=False)
    
    # Payout methods
    payout_methods = CreatorPayoutMethodSerializer(many=True, required=False)
    
    # Social accounts (read-only)
    social_accounts = CreatorSocialAccountSerializer(source="user.social_accounts", many=True, read_only=True)
    
    # Settings
    settings = CreatorSettingsSerializer(required=False)

    def to_representation(self, instance):
        # Ensure CreatorSettings exists
        CreatorSettings.objects.get_or_create(creator=instance)
        
        rep = super().to_representation(instance)
        # Representation of niches
        rep["niches"] = [niche.name for niche in instance.niches.all()]
        # Representation of rates
        rep["rates"] = CreatorRateSerializer(instance.rates.all(), many=True).data
        # Representation of payout methods
        rep["payout_methods"] = CreatorPayoutMethodSerializer(instance.payout_methods.all(), many=True).data
        return rep

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        
        # Update user
        if "first_name" in user_data:
            user.first_name = user_data["first_name"]
        if "last_name" in user_data:
            user.last_name = user_data["last_name"]
        if "email" in user_data:
            user.email = user_data["email"]
        user.save()
        
        # Update profile
        instance.phone = validated_data.get("phone", instance.phone)
        instance.location = validated_data.get("location", instance.location)
        instance.bio = validated_data.get("bio", instance.bio)
        instance.avatar_url = validated_data.get("avatar_url", instance.avatar_url)
        
        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None
                
        instance.save()
        
        # Update niches
        if "niches" in validated_data:
            niche_names = validated_data["niches"]
            niche_objects = []
            for name in niche_names:
                niche_obj, _ = Niche.objects.get_or_create(name=name)
                niche_objects.append(niche_obj)
            instance.niches.set(niche_objects)
            
        # Update settings
        settings_data = validated_data.get("settings", {})
        if settings_data or not hasattr(instance, "settings"):
            settings_obj, _ = CreatorSettings.objects.get_or_create(creator=instance)
            for attr, value in settings_data.items():
                setattr(settings_obj, attr, value)
            settings_obj.save()
            
        # Update rates
        if "rates" in validated_data:
            rates_data = validated_data["rates"]
            # Clear old rates
            instance.rates.all().delete()
            # Create new rates
            for rate_item in rates_data:
                CreatorRate.objects.create(
                    creator=instance,
                    content_type=rate_item.get("content_type"),
                    platforms=rate_item.get("platforms"),
                    price=rate_item.get("price"),
                    notes=rate_item.get("notes")
                )
                
        # Update payout methods
        if "payout_methods" in validated_data:
            payouts_data = validated_data["payout_methods"]
            # Clear old payout methods
            instance.payout_methods.all().delete()
            # Create new payout methods
            for payout_item in payouts_data:
                CreatorPayoutMethod.objects.create(
                    creator=instance,
                    method_type=payout_item.get("method_type"),
                    details=payout_item.get("details"),
                    is_primary=payout_item.get("is_primary", False)
                )
                
        return instance


class BusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSettings
        exclude = ["business"]

class BusinessFullSettingsSerializer(serializers.Serializer):
    # User fields
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)
    email = serializers.EmailField(source="user.email", required=False)
    
    # Profile fields
    company_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    business_types = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    website = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    bio = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    secondary_phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    time_zone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    avatar_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    # Social links
    facebook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    instagram_handle = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    tiktok_handle = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    youtube_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    linkedin_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    twitter_handle = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    # Settings
    settings = BusinessSettingsSerializer(required=False)

    def to_representation(self, instance):
        # Ensure BusinessSettings exists
        BusinessSettings.objects.get_or_create(business=instance)
        
        rep = super().to_representation(instance)
        # Parse business types from comma-separated string to list
        if instance.business_type:
            rep["business_types"] = [t.strip() for t in instance.business_type.split(",") if t.strip()]
        else:
            rep["business_types"] = []
        return rep

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        
        # Update user
        if "first_name" in user_data:
            user.first_name = user_data["first_name"]
        if "last_name" in user_data:
            user.last_name = user_data["last_name"]
        if "email" in user_data:
            user.email = user_data["email"]
        user.save()
        
        # Update profile fields
        instance.company_name = validated_data.get("company_name", instance.company_name)
        instance.website = validated_data.get("website", instance.website)
        instance.bio = validated_data.get("bio", instance.bio)
        instance.phone = validated_data.get("phone", instance.phone)
        instance.secondary_phone = validated_data.get("secondary_phone", instance.secondary_phone)
        instance.time_zone = validated_data.get("time_zone", instance.time_zone)
        instance.avatar_url = validated_data.get("avatar_url", instance.avatar_url)
        
        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None
        
        # Update business types as comma-separated string
        if "business_types" in validated_data:
            types_list = validated_data["business_types"]
            instance.business_type = ",".join([t.strip() for t in types_list if t.strip()])
            
        # Update social links
        instance.facebook_url = validated_data.get("facebook_url", instance.facebook_url)
        instance.instagram_handle = validated_data.get("instagram_handle", instance.instagram_handle)
        instance.tiktok_handle = validated_data.get("tiktok_handle", instance.tiktok_handle)
        instance.youtube_url = validated_data.get("youtube_url", instance.youtube_url)
        instance.linkedin_url = validated_data.get("linkedin_url", instance.linkedin_url)
        instance.twitter_handle = validated_data.get("twitter_handle", instance.twitter_handle)
        
        instance.save()
        
        # Update settings
        settings_data = validated_data.get("settings", {})
        if settings_data or not hasattr(instance, "settings"):
            settings_obj, _ = BusinessSettings.objects.get_or_create(business=instance)
            for attr, value in settings_data.items():
                setattr(settings_obj, attr, value)
            settings_obj.save()
            
        return instance
