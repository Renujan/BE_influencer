from rest_framework import serializers
from django.contrib.auth.models import User
from user.models import CreatorProfile, BusinessProfile, Niche, CreatorRate, CreatorSocialAccount, Country
from user.serializers import CreatorRateSerializer, CreatorSocialAccountSerializer
from .models import CreatorSettings, CreatorPayoutMethod, BusinessSettings, BusinessPayoutMethod

class CreatorPayoutMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorPayoutMethod
        fields = ["id", "full_name", "bank_name", "account_number", "bank_book_photo_url", "is_primary"]

class BusinessPayoutMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPayoutMethod
        fields = ["id", "full_name", "bank_name", "account_number", "bank_book_photo_url", "is_primary"]

class CreatorSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorSettings
        exclude = ["creator"]

class CreatorFullSettingsSerializer(serializers.Serializer):
    # User fields
    username = serializers.CharField(source="user.username", required=False, allow_blank=True)
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)
    email = serializers.EmailField(source="user.email", required=False)
    
    # Profile fields
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    location = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    province = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    district = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    bio = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    avatar_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    cover_image_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    wallet_balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    next_payout_date = serializers.CharField(read_only=True, required=False)
    
    # Niches (list of strings)
    niches = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    
    # Mediums (list of strings)
    mediums = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    
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
        # Representation of mediums
        rep["mediums"] = [medium.name for medium in instance.mediums.all()]
        # Province and district are objects if not serialized by CharField properly, let's explicitly add them if needed
        if instance.province:
            rep["province"] = instance.province.name
        if instance.district:
            rep["district"] = instance.district.name
        # Representation of rates
        rep["rates"] = CreatorRateSerializer(instance.rates.all(), many=True).data
        # Representation of payout methods
        rep["payout_methods"] = CreatorPayoutMethodSerializer(instance.payout_methods.all(), many=True).data
        rep["deletion_requested"] = instance.deletion_requested
        rep["deletion_request_date"] = instance.deletion_request_date.isoformat() if instance.deletion_request_date else None
        rep["deletion_reason"] = instance.deletion_reason
        rep["deletion_decline_reason"] = instance.deletion_decline_reason
        return rep

    def validate(self, attrs):
        user_data = attrs.get("user", {})
        if "username" in user_data:
            username = user_data["username"]
            from django.contrib.auth.models import User
            # Check if another user has this username
            if User.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
                raise serializers.ValidationError({"username": "This username is already taken."})
        return attrs

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
        if "username" in user_data:
            user.username = user_data["username"]
        user.save()
        
        # Update profile
        instance.phone = validated_data.get("phone", instance.phone)
        instance.location = validated_data.get("location", instance.location)
        instance.bio = validated_data.get("bio", instance.bio)
        instance.avatar_url = validated_data.get("avatar_url", instance.avatar_url)
        instance.cover_image_url = validated_data.get("cover_image_url", instance.cover_image_url)
        
        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None
                
        if "province" in validated_data:
            from user.models import Province
            province_name = validated_data["province"]
            if province_name:
                province_obj = Province.objects.filter(name=province_name.strip()).first()
                if province_obj:
                    instance.province = province_obj
            else:
                instance.province = None
                
        if "district" in validated_data:
            from user.models import District
            district_name = validated_data["district"]
            if district_name:
                district_obj = District.objects.filter(name=district_name.strip()).first()
                if district_obj:
                    instance.district = district_obj
            else:
                instance.district = None
                
        instance.save()
        
        # Update niches
        niches_data = validated_data.get("niches") if "niches" in validated_data else self.initial_data.get("niches")
        if niches_data is not None:
            if isinstance(niches_data, str):
                niches_data = [x.strip() for x in niches_data.split(",") if x.strip()]
            niche_objects = []
            for name in niches_data:
                clean_name = str(name).strip()
                niche_obj = Niche.objects.filter(name__iexact=clean_name).first()
                if not niche_obj and clean_name:
                    niche_obj = Niche.objects.create(name=clean_name)
                if niche_obj and niche_obj not in niche_objects:
                    niche_objects.append(niche_obj)
            instance.niches.set(niche_objects)
            
        # Update mediums
        mediums_data = validated_data.get("mediums") if "mediums" in validated_data else self.initial_data.get("mediums")
        if mediums_data is not None:
            from user.models import Medium
            if isinstance(mediums_data, str):
                mediums_data = [x.strip() for x in mediums_data.split(",") if x.strip()]
            medium_objects = []
            for name in mediums_data:
                clean_name = str(name).strip()
                if instance.country:
                    medium_obj = Medium.objects.filter(name__iexact=clean_name, country=instance.country).first()
                else:
                    medium_obj = Medium.objects.filter(name__iexact=clean_name).first()
                if not medium_obj:
                    medium_obj = Medium.objects.filter(name__iexact=clean_name).first()
                if not medium_obj and clean_name.isdigit():
                    medium_obj = Medium.objects.filter(id=int(clean_name)).first()
                if not medium_obj and clean_name:
                    medium_obj, _ = Medium.objects.get_or_create(name=clean_name)
                if medium_obj and medium_obj not in medium_objects:
                    medium_objects.append(medium_obj)
            instance.mediums.set(medium_objects)
            
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
                min_p = rate_item.get("min_price")
                max_p = rate_item.get("max_price")
                price_p = rate_item.get("price")
                if price_p is None or float(price_p or 0) == 0:
                    price_p = min_p if min_p is not None else 0.00
                CreatorRate.objects.create(
                    creator=instance,
                    content_type=rate_item.get("content_type"),
                    platforms=rate_item.get("platforms"),
                    price=price_p,
                    min_price=min_p if min_p is not None else price_p,
                    max_price=max_p if max_p is not None else price_p,
                    notes=rate_item.get("notes") or ""
                )
                
        # Update payout methods
        payouts_data = self.initial_data.get("payout_methods") or validated_data.get("payout_methods")
        if payouts_data is not None:
            # Clear old payout methods
            instance.payout_methods.all().delete()
            # Create new payout methods
            for payout_item in payouts_data:
                CreatorPayoutMethod.objects.create(
                    creator=instance,
                    full_name=payout_item.get("full_name"),
                    bank_name=payout_item.get("bank_name") or payout_item.get("method_type") or "",
                    account_number=payout_item.get("account_number") or payout_item.get("details") or "",
                    bank_book_photo_url=payout_item.get("bank_book_photo_url") or "",
                    is_primary=payout_item.get("is_primary", False)
                )

        # Update social accounts
        socials_data = self.initial_data.get("social_accounts") or validated_data.get("social_accounts")
        if socials_data and isinstance(socials_data, list):
            from user.models import CreatorSocialAccount
            for acc_item in socials_data:
                platform_name = acc_item.get("platform") or acc_item.get("name")
                if not platform_name:
                    continue
                sa_obj, _ = CreatorSocialAccount.objects.get_or_create(
                    user=instance.user,
                    platform=platform_name
                )
                sa_obj.username = acc_item.get("username") or acc_item.get("handle") or sa_obj.username or ""
                sa_obj.followers_count = str(acc_item.get("followers_count") or acc_item.get("followers") or sa_obj.followers_count or "")
                sa_obj.proof_link = acc_item.get("proof_link") or acc_item.get("proof_url") or sa_obj.proof_link or ""
                if "is_connected" in acc_item:
                    sa_obj.is_connected = bool(acc_item["is_connected"])
                elif "connected" in acc_item:
                    sa_obj.is_connected = bool(acc_item["connected"])
                if not sa_obj.is_connected:
                    sa_obj.is_verified = False
                sa_obj.save()
                
        return instance


class BusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSettings
        exclude = ["business"]

class BusinessFullSettingsSerializer(serializers.Serializer):
    # User fields
    username = serializers.CharField(source="user.username", required=False, allow_blank=True)
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)
    email = serializers.EmailField(source="user.email", required=False)
    
    # Profile fields
    company_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    business_types = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    mediums = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    website = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    bio = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    secondary_phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    time_zone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    province = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    district = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    avatar_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    cover_image_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    # Social links
    facebook_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    instagram_handle = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    tiktok_handle = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    youtube_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    linkedin_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)
    twitter_handle = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    # Settings
    settings = BusinessSettingsSerializer(required=False)
    payout_methods = BusinessPayoutMethodSerializer(many=True, required=False)

    def to_representation(self, instance):
        # Ensure BusinessSettings exists
        BusinessSettings.objects.get_or_create(business=instance)
        
        rep = super().to_representation(instance)
        # Collect business types from both ManyToMany and CharField
        types_set = []
        if instance.business_types.exists():
            for bt in instance.business_types.all():
                if bt.name and bt.name.strip() not in types_set:
                    types_set.append(bt.name.strip())
        if instance.business_type:
            for t in instance.business_type.replace(",", " ").split():
                if t.strip() and t.strip() not in types_set:
                    types_set.append(t.strip())
        rep["business_types"] = types_set
            
        if getattr(instance, "province", None):
            rep["province"] = instance.province.name
        if getattr(instance, "district", None):
            rep["district"] = instance.district.name
            
        rep["mediums"] = [m.name for m in instance.mediums.all()]
        rep["deletion_requested"] = instance.deletion_requested
        rep["deletion_request_date"] = instance.deletion_request_date.isoformat() if instance.deletion_request_date else None
        rep["deletion_reason"] = instance.deletion_reason
        rep["deletion_decline_reason"] = instance.deletion_decline_reason
        return rep

    def validate(self, attrs):
        user_data = attrs.get("user", {})
        if "username" in user_data:
            username = user_data["username"]
            from django.contrib.auth.models import User
            # Check if another user has this username
            if User.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
                raise serializers.ValidationError({"username": "This username is already taken."})
        return attrs

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
        if "username" in user_data:
            user.username = user_data["username"]
        user.save()
        
        # Update profile fields
        instance.company_name = validated_data.get("company_name", instance.company_name)
        instance.website = validated_data.get("website", instance.website)
        instance.bio = validated_data.get("bio", instance.bio)
        instance.phone = validated_data.get("phone", instance.phone)
        instance.secondary_phone = validated_data.get("secondary_phone", instance.secondary_phone)
        instance.time_zone = validated_data.get("time_zone", instance.time_zone)
        instance.avatar_url = validated_data.get("avatar_url", instance.avatar_url)
        instance.cover_image_url = validated_data.get("cover_image_url", instance.cover_image_url)
        
        if "country" in validated_data:
            country_name = validated_data["country"]
            if country_name:
                country_obj, _ = Country.objects.get_or_create(name=country_name.strip())
                instance.country = country_obj
            else:
                instance.country = None
                
        if "province" in validated_data:
            from user.models import Province
            province_name = validated_data["province"]
            if province_name:
                province_obj = Province.objects.filter(name=province_name.strip()).first()
                if province_obj:
                    instance.province = province_obj
            else:
                instance.province = None
                
        if "district" in validated_data:
            from user.models import District
            district_name = validated_data["district"]
            if district_name:
                district_obj = District.objects.filter(name=district_name.strip()).first()
                if district_obj:
                    instance.district = district_obj
            else:
                instance.district = None
        
        # Update business types as both ManyToMany relation and comma-separated string
        if "business_types" in validated_data:
            from user.models import BusinessType
            types_list = validated_data["business_types"]
            clean_types = [t.strip() for t in types_list if t.strip()]
            instance.business_type = ", ".join(clean_types)
            bt_objects = []
            for t_name in clean_types:
                bt_obj, _ = BusinessType.objects.get_or_create(name=t_name)
                bt_objects.append(bt_obj)
            instance.business_types.set(bt_objects)
            
        # Update social links
        instance.facebook_url = validated_data.get("facebook_url", instance.facebook_url)
        instance.instagram_handle = validated_data.get("instagram_handle", instance.instagram_handle)
        instance.tiktok_handle = validated_data.get("tiktok_handle", instance.tiktok_handle)
        instance.youtube_url = validated_data.get("youtube_url", instance.youtube_url)
        instance.linkedin_url = validated_data.get("linkedin_url", instance.linkedin_url)
        instance.twitter_handle = validated_data.get("twitter_handle", instance.twitter_handle)
        
        instance.save()
        
        # Update mediums
        if "mediums" in validated_data:
            from user.models import Medium
            medium_names = validated_data["mediums"]
            medium_objects = []
            for name in medium_names:
                if instance.country:
                    medium_obj = Medium.objects.filter(name__iexact=name, country=instance.country).first()
                else:
                    medium_obj = Medium.objects.filter(name__iexact=name).first()
                if medium_obj:
                    medium_objects.append(medium_obj)
            instance.mediums.set(medium_objects)
            
        # Update settings
        settings_data = validated_data.get("settings", {})
        if settings_data or not hasattr(instance, "settings"):
            settings_obj, _ = BusinessSettings.objects.get_or_create(business=instance)
            for attr, value in settings_data.items():
                setattr(settings_obj, attr, value)
            settings_obj.save()
            
        # Update payout methods
        if "payout_methods" in validated_data:
            payouts_data = validated_data["payout_methods"]
            instance.payout_methods.all().delete()
            for payout_item in payouts_data:
                BusinessPayoutMethod.objects.create(
                    business=instance,
                    full_name=payout_item.get("full_name"),
                    bank_name=payout_item.get("bank_name"),
                    account_number=payout_item.get("account_number"),
                    bank_book_photo_url=payout_item.get("bank_book_photo_url"),
                    is_primary=payout_item.get("is_primary", False)
                )

        return instance
