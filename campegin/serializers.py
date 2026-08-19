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
        return data

    platform = serializers.SerializerMethodField()

    def get_platform(self, obj):
        return obj.medium or ""

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "brand", "brand_name", "creator", "creator_name",
            "status", "budget", "min_budget", "max_budget", "per_creator_budget", "min_price", "max_price", "rate_card_id", "start_date", "end_date", "progress", "brief", "admin_review",
            "category", "delivery_language", "country", "province", "district", "medium", "platform", "voice_brief", "screenshare_brief", "video_brief",
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
    counter_history = FlexibleJSONField(required=False, allow_null=True, default=list)
    campaign_id = serializers.SerializerMethodField()

    class Meta:
        model = Pitch
        fields = [
            "id", "creator", "creator_name", "brand", "brand_name",
            "campaign_name", "budget", "sent_date", "tags", "status",
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

        # If pitch status is accepted or live but no campaign exists, auto-create it so workspace is immediately available
        if not camp and str(obj.status or "").lower() in ["accepted", "accepted_by_business", "live"]:
            from .views import populate_deliverables_from_pitch
            tags = obj.tags or []
            if isinstance(tags, str):
                try:
                    import json
                    tags = json.loads(tags)
                except Exception:
                    tags = [tags]
            if not isinstance(tags, list):
                tags = [str(tags)]
            known_platforms = {"Instagram", "YouTube", "TikTok", "Facebook", "LinkedIn", "X", "Twitter", "Snapchat", "Pinterest"}
            niche_val = next((str(t).strip() for t in tags if str(t).strip() and not any(p.lower() == str(t).strip().lower() for p in known_platforms)), "")
            if not niche_val and obj.creator and hasattr(obj.creator, "creator_profile") and obj.creator.creator_profile.niches:
                cr_niches = obj.creator.creator_profile.niches
                if isinstance(cr_niches, list) and cr_niches:
                    niche_val = str(cr_niches[0]).strip()
            if not niche_val:
                niche_val = "Tech"
            platform_val = next((str(t).strip() for t in tags if any(p.lower() == str(t).strip().lower() for p in known_platforms)), "Instagram")

            camp = Campaign.objects.create(
                name=obj.campaign_name,
                brand=obj.brand,
                creator=obj.creator,
                budget=obj.counter_offer or obj.budget,
                counter_price=obj.counter_offer or obj.budget,
                counter_note=obj.counter_note,
                counter_history=obj.counter_history,
                category=niche_val,
                medium=platform_val,
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
        ret = super().to_internal_value(data)
        incoming_tags = ret.get("tags") or []
        if isinstance(incoming_tags, str):
            try:
                import json
                incoming_tags = json.loads(incoming_tags)
            except Exception:
                incoming_tags = [incoming_tags]
        if not isinstance(incoming_tags, list):
            incoming_tags = [str(incoming_tags)]

        def extract_val(field_name):
            if hasattr(data, "getlist"):
                vals = data.getlist(field_name)
                if vals and vals[0]:
                    return vals[0]
            return data.get(field_name)

        niche = extract_val("niche")
        if niche and niche not in incoming_tags:
            incoming_tags.append(niche)

        niches = extract_val("niches")
        if niches:
            if isinstance(niches, str):
                try:
                    import json
                    niches = json.loads(niches)
                except Exception:
                    niches = [n.strip() for n in niches.split(",") if n.strip()]
            if isinstance(niches, list):
                for n in niches:
                    if n and n not in incoming_tags:
                        incoming_tags.append(n)

        platform = extract_val("platform")
        if platform and platform not in incoming_tags:
            incoming_tags.append(platform)

        category = extract_val("category")
        if category and category not in incoming_tags:
            incoming_tags.append(category)

        delivery_language = extract_val("delivery_language")
        if delivery_language and delivery_language not in incoming_tags:
            incoming_tags.append(delivery_language)

        ret["tags"] = incoming_tags
        return ret

    def to_representation(self, instance):
        data = super().to_representation(instance)
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

        data["niche"] = found_niche or ""
        data["niches"] = found_niches if found_niches else ([found_niche] if found_niche else [])
        data["category"] = found_niche or (tags[0] if tags else "General")
        data["platform"] = found_platform or ""
        data["delivery_language"] = found_delivery_lang or ""
        return data
