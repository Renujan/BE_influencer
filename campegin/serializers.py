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
        fields = ["id", "sender", "sender_name", "text", "file_attachment", "time", "message_type", "is_pinned"]

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
    business_rating = serializers.SerializerMethodField()

    def get_creator_rating(self, obj):
        if hasattr(obj, "rating") and obj.rating:
            return {
                "id": obj.rating.id,
                "rating": obj.rating.rating,
                "review": obj.rating.review,
                "created_at": obj.rating.created_at,
            }
        return None

    def get_business_rating(self, obj):
        if hasattr(obj, "business_rating") and obj.business_rating:
            return {
                "id": obj.business_rating.id,
                "rating": obj.business_rating.rating,
                "review": obj.business_rating.review,
                "created_at": obj.business_rating.created_at,
            }
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        created_via = str(getattr(instance, "created_via", "") or "").lower().strip()
        if created_via == "pitch" or getattr(instance, "is_pitch", False):
            from .models import Pitch
            pitch = Pitch.objects.filter(campaign_name=instance.name, brand=instance.brand, creator=instance.creator).order_by("-id").first() or Pitch.objects.filter(campaign_name=instance.name, brand=instance.brand).order_by("-id").first() or Pitch.objects.filter(brand=instance.brand, creator=instance.creator).order_by("-id").first()
            if pitch:
                if pitch.counter_history and isinstance(pitch.counter_history, list) and len(pitch.counter_history) > 0:
                    last_p = pitch.counter_history[-1].get("price")
                    if last_p:
                        data["budget"] = str(last_p)
                        data["counter_price"] = str(last_p)
                    data["counter_history"] = pitch.counter_history
                elif pitch.counter_offer:
                    data["budget"] = str(pitch.counter_offer)
                    data["counter_price"] = str(pitch.counter_offer)
            elif instance.counter_history and isinstance(instance.counter_history, list) and len(instance.counter_history) > 0:
                last_p = instance.counter_history[-1].get("price")
                if last_p:
                    data["budget"] = str(last_p)
                    data["counter_price"] = str(last_p)
            elif instance.counter_price:
                data["budget"] = str(instance.counter_price)

        if not data.get("min_price") and not data.get("max_price"):
            from .models import CampaignCategory
            from django.db.models import Q
            cat_val = getattr(instance, "category", "") or ""
            if cat_val:
                matched_cat = CampaignCategory.objects.filter(
                    Q(name__iexact=cat_val) | Q(type__iexact=cat_val)
                ).first()
                if not matched_cat and getattr(instance, "medium", None):
                    matched_cat = CampaignCategory.objects.filter(
                        Q(platform__iexact=instance.medium)
                    ).first()
                if matched_cat:
                    if matched_cat.min_price and not data.get("min_price"):
                        data["min_price"] = str(matched_cat.min_price)
                    if matched_cat.max_price and not data.get("max_price"):
                        data["max_price"] = str(matched_cat.max_price)
                    if not data.get("min_budget") and matched_cat.min_price:
                        data["min_budget"] = str(matched_cat.min_price)
                    if not data.get("max_budget") and matched_cat.max_price:
                        data["max_budget"] = str(matched_cat.max_price)

        import re
        for f in ["voice_brief", "screenshare_brief", "video_brief"]:
            val = data.get(f)
            if val and isinstance(val, str):
                data[f] = re.sub(r"^/media/+media/", "/media/", val)

        platform_val = getattr(instance, "platform", "") or getattr(instance, "medium", "") or ""
        if not platform_val:
            from .models import CampaignCategory
            from django.db.models import Q
            cat_val = getattr(instance, "category", "") or getattr(instance, "campaign_category", "") or ""
            if cat_val:
                matched_cat = CampaignCategory.objects.filter(
                    Q(name__iexact=cat_val) | Q(type__iexact=cat_val)
                ).first()
                if matched_cat and matched_cat.platform:
                    platform_val = matched_cat.platform
        if not platform_val and instance.deliverables.exists():
            for d in instance.deliverables.all():
                d_txt = f"{d.name} {getattr(d, 'format', '')} {getattr(d, 'type', '')}".lower()
                if "insta" in d_txt: platform_val = "Instagram"; break
                elif "you" in d_txt or "yt" in d_txt: platform_val = "YouTube"; break
                elif "tik" in d_txt: platform_val = "TikTok"; break
                elif "face" in d_txt or "fb" in d_txt: platform_val = "Facebook"; break
                elif "link" in d_txt: platform_val = "LinkedIn"; break
                elif "twitter" in d_txt or "x " in d_txt: platform_val = "Twitter/X"; break

        if not platform_val:
            platform_val = "Instagram"

        data["platform"] = platform_val
        data["target_platform"] = platform_val
        data["platforms"] = [p.strip() for p in platform_val.split(",") if p.strip()] if platform_val else [platform_val]
        data.pop("medium", None)
        return data

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "brand", "brand_name", "creator", "creator_name",
            "status", "budget", "min_budget", "max_budget", "per_creator_budget", "min_price", "max_price", "rate_card_id", "start_date", "end_date", "progress", "brief", "admin_review",
            "category", "campaign_category", "niche", "delivery_language", "country", "province", "district", "platform", "voice_brief", "screenshare_brief", "video_brief",
            "counter_price", "counter_note", "counter_round", "counter_history", "decline_reason", "created_via", "created_time", "created_at",
            "tasks", "milestones", "deliverables", "payments", "files", "messages", "tickets", "reviews", "creator_rating", "business_rating"
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
    category = serializers.PrimaryKeyRelatedField(
        queryset=CampaignCategory.objects.all(),
        required=True,
        allow_null=False,
        error_messages={"required": "Campaign category is required.", "null": "Campaign category is required."}
    )
    category_name = serializers.SerializerMethodField(read_only=True)
    category_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CampaignDeliverable
        fields = ["id", "name", "platform", "category", "category_name", "category_type"]

    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name or obj.category.type or ""
        return ""

    def get_category_type(self, obj):
        if obj.category:
            return obj.category.type or obj.category.name or ""
        return ""

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

class FlexibleJSONField(serializers.JSONField):
    def to_internal_value(self, data):
        if data is None:
            return []
        if isinstance(data, str):
            data_str = data.strip()
            if not data_str:
                return []
            try:
                import json
                parsed = json.loads(data_str)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, (dict, int, float, bool)):
                    return [parsed]
                else:
                    return [str(parsed)]
            except Exception:
                return [d.strip() for d in data_str.split(",") if d.strip()]
        if isinstance(data, list):
            res = []
            for item in data:
                if isinstance(item, str):
                    try:
                        import json
                        parsed = json.loads(item)
                        if isinstance(parsed, list):
                            res.extend(parsed)
                        else:
                            res.append(parsed)
                    except Exception:
                        res.append(item)
                else:
                    res.append(item)
            return res
        return super().to_internal_value(data)

class PitchSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.username", read_only=True)
    creator_name = serializers.CharField(source="creator.username", read_only=True)
    deliverables = FlexibleJSONField(required=False, allow_null=True, default=list)
    tags = FlexibleJSONField(required=False, allow_null=True, default=list)
    delivery_languages = FlexibleJSONField(required=False, allow_null=True, default=list)
    niches = FlexibleJSONField(required=False, allow_null=True, default=list)
    counter_history = FlexibleJSONField(required=False, allow_null=True, default=list)
    campaign_id = serializers.SerializerMethodField()

    class Meta:
        model = Pitch
        fields = [
            "id", "creator", "creator_name", "brand", "brand_name",
            "campaign_name", "budget", "sent_date", "start_date", "end_date", "platform",
            "country", "province_state", "district_city", "delivery_languages",
            "category", "niche", "niches",
            "tags", "status",
            "description", "deliverables", "counter_offer", "counter_note", "counter_count", "counter_history", "attachment", "decline_reason", "campaign_id"
        ]
        read_only_fields = ["creator"]

    def get_campaign_id(self, obj):
        camp = Campaign.objects.filter(name__iexact=obj.campaign_name.strip(), brand=obj.brand, creator=obj.creator).order_by("-id").first()
        if not camp:
            camp = Campaign.objects.filter(name__icontains=obj.campaign_name.strip(), brand=obj.brand, creator=obj.creator).order_by("-id").first()
        if not camp:
            camp = Campaign.objects.filter(brand=obj.brand, creator=obj.creator, created_via="pitch").order_by("-id").first()
        if not camp:
            camp = Campaign.objects.filter(name__iexact=obj.campaign_name.strip(), creator=obj.creator).order_by("-id").first()
        if not camp:
            camp = Campaign.objects.filter(name__iexact=obj.campaign_name.strip(), brand=obj.brand).order_by("-id").first()
        if not camp:
            camp = Campaign.objects.filter(creator=obj.creator, created_via="pitch").order_by("-id").first()
        if not camp:
            camp = Campaign.objects.filter(name__iexact=obj.campaign_name.strip()).order_by("-id").first()

        # If pitch status has been approved and converted by admin ('accepted'/'live') but no campaign exists yet, create it as fallback
        if not camp and str(obj.status or "").lower() in ["accepted", "live"]:
            from .views import populate_deliverables_from_pitch, extract_pitch_niche_and_platform
            niche_val, platform_val = extract_pitch_niche_and_platform(obj)

            camp = Campaign.objects.create(
                name=obj.campaign_name,
                brand=obj.brand,
                creator=obj.creator,
                budget=obj.counter_offer or obj.budget,
                counter_price=obj.counter_offer or obj.budget,
                counter_note=obj.counter_note,
                counter_history=obj.counter_history,
                category=obj.category or niche_val,
                campaign_category=obj.category or niche_val,
                niche=obj.niche or niche_val,
                delivery_language=(", ".join(obj.delivery_languages) if isinstance(obj.delivery_languages, list) else (obj.delivery_languages or "")),
                country=obj.country or "",
                province=obj.province_state or "",
                district=obj.district_city or "",
                platform=obj.platform or platform_val,
                medium=obj.platform or platform_val,
                brief=obj.description or f"Campaign proposal based on pitch: {obj.campaign_name}",
                status="Live",
                progress=62,
                start_date=obj.sent_date or "2026-08-01",
                created_via="pitch",
            )
            try:
                from WorkspacePayment.models import WorkspacePaymentNegotiation
                neg, _ = WorkspacePaymentNegotiation.objects.get_or_create(campaign=camp)
                neg.final_price = obj.counter_offer or obj.budget
                neg.status = 'creator_accepted'
                neg.save()
            except Exception:
                pass
            populate_deliverables_from_pitch(camp, obj)

        return camp.id if camp else None

    def to_internal_value(self, data):
        mutable_data = data.copy() if hasattr(data, "copy") else dict(data)

        def extract_val(field_name):
            if hasattr(data, "getlist"):
                vals = data.getlist(field_name)
                if vals and vals[0]:
                    return vals[0]
            return data.get(field_name) if hasattr(data, "get") else None

        # Aliases for location
        if not extract_val("province_state"):
            prov = extract_val("province") or extract_val("state")
            if prov:
                mutable_data["province_state"] = prov

        if not extract_val("district_city"):
            dist = extract_val("district") or extract_val("city")
            if dist:
                mutable_data["district_city"] = dist

        # Delivery languages from legacy single-string delivery_language if delivery_languages not provided
        if not extract_val("delivery_languages") and extract_val("delivery_language"):
            dl = extract_val("delivery_language")
            if isinstance(dl, str):
                try:
                    import json
                    parsed = json.loads(dl)
                    mutable_data["delivery_languages"] = parsed if isinstance(parsed, list) else [str(parsed)]
                except Exception:
                    mutable_data["delivery_languages"] = [s.strip() for s in dl.split(",") if s.strip()]
            elif isinstance(dl, list):
                mutable_data["delivery_languages"] = dl

        # Category from deliverable_category / campaign_type if category is not explicitly set
        if not extract_val("category"):
            dc = extract_val("deliverable_category") or extract_val("campaign_type")
            if dc:
                mutable_data["category"] = dc

        # Ensure niche & niches sync cleanly without polluting tags
        incoming_niche = extract_val("niche")
        incoming_niches = extract_val("niches")
        if incoming_niche and not incoming_niches:
            mutable_data["niches"] = [incoming_niche]
        elif incoming_niches and not incoming_niche:
            if isinstance(incoming_niches, list) and len(incoming_niches) > 0:
                first = incoming_niches[0]
                mutable_data["niche"] = first.get("name") if isinstance(first, dict) else str(first)
            elif isinstance(incoming_niches, str):
                try:
                    import json
                    parsed = json.loads(incoming_niches)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        first = parsed[0]
                        mutable_data["niche"] = first.get("name") if isinstance(first, dict) else str(first)
                except Exception:
                    mutable_data["niche"] = incoming_niches.split(",")[0].strip()

        ret = super().to_internal_value(mutable_data)
        return ret

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Fallback / backward-compatibility extraction from tags if legacy record has empty explicit fields
        tags = instance.tags or []
        if isinstance(tags, str):
            try:
                import json
                tags = json.loads(tags)
            except Exception:
                tags = [tags]
        if not isinstance(tags, list):
            tags = [str(tags)]

        known_platforms = {"Instagram", "YouTube", "TikTok", "Facebook", "LinkedIn", "X", "Twitter", "Snapchat", "Pinterest"}
        known_mediums = {"English", "Sinhala", "Tamil", "Hindi", "Malayalam", "Telugu", "Kannada", "Bengali", "Spanish", "French", "German", "Arabic", "Mandarin", "Japanese"}

        found_platform = None
        found_delivery_lang = None
        found_niche = None
        found_niches = []

        for t in tags:
            t_str = str(t).strip()
            if not t_str:
                continue
            if t_str in known_platforms or any(p.lower() == t_str.lower() for p in known_platforms):
                if not found_platform:
                    found_platform = t_str
            elif t_str in known_mediums or any(m.lower() == t_str.lower() for m in known_mediums):
                if not found_delivery_lang:
                    found_delivery_lang = t_str
            else:
                if not found_niche:
                    found_niche = t_str
                found_niches.append(t_str)

        # Niches
        niche_val = instance.niche or found_niche or ""
        niches_list = instance.niches if (instance.niches and isinstance(instance.niches, list)) else (found_niches if found_niches else ([niche_val] if niche_val else []))
        data["niche"] = niche_val
        data["niches"] = niches_list

        # Delivery languages
        if instance.delivery_languages and isinstance(instance.delivery_languages, list) and len(instance.delivery_languages) > 0:
            data["delivery_languages"] = instance.delivery_languages
        elif found_delivery_lang:
            data["delivery_languages"] = [found_delivery_lang]
        else:
            data["delivery_languages"] = []

        # Category (Campaign format e.g. "YouTube Integration")
        data["category"] = instance.category or found_niche or (tags[0] if tags else "")
        data["deliverable_category"] = data["category"]

        # Platform
        data["platform"] = instance.platform or found_platform or ""

        # Location data
        data["country"] = instance.country or ""
        data["province_state"] = instance.province_state or ""
        data["district_city"] = instance.district_city or ""

        return data
