from rest_framework import serializers
from .models import WorkspacePaymentNegotiation, WorkspaceInstallment

class WorkspaceInstallmentSerializer(serializers.ModelSerializer):
    receipt_image_url = serializers.SerializerMethodField()

    class Meta:
        model = WorkspaceInstallment
        fields = [
            'id',
            'campaign',
            'negotiation',
            'installment_type',
            'title',
            'amount',
            'status',
            'is_paid',
            'paid_date',
            'receipt_image',
            'receipt_image_url',
            'receipt_url',
            'created_at',
            'updated_at',
        ]

    def get_receipt_image_url(self, obj):
        if obj.receipt_url:
            return obj.receipt_url
        if obj.receipt_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.receipt_image.url)
            url = obj.receipt_image.url
            if not url.startswith('http'):
                return f"http://127.0.0.1:8000{url if url.startswith('/') else '/' + url}"
            return url
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        has_receipt = bool(data.get('receipt_image_url') or data.get('receipt_url') or data.get('receipt_image'))
        if data.get('is_paid') or data.get('status') == 'released':
            data['status'] = 'released'
        elif has_receipt:
            data['status'] = 'in_escrow'
        else:
            data['status'] = 'pending'
        return data


class WorkspacePaymentNegotiationSerializer(serializers.ModelSerializer):
    proposed_by_name = serializers.SerializerMethodField()
    action_by_name = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    min_budget = serializers.SerializerMethodField()
    max_budget = serializers.SerializerMethodField()
    creator_min_price = serializers.SerializerMethodField()
    creator_max_price = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    business_fee_receipt_image_url = serializers.SerializerMethodField()
    creator_fee_receipt_image_url = serializers.SerializerMethodField()
    business_installments = serializers.SerializerMethodField()
    creator_installments = serializers.SerializerMethodField()
    installments = WorkspaceInstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = WorkspacePaymentNegotiation
        fields = [
            'id',
            'campaign',
            'campaign_name',
            'creator_name',
            'brand_name',
            'final_price',
            'platform_charge',
            'business_platform_charge',
            'creator_platform_charge',
            'platform_charge_amount',
            'business_platform_charge_amount',
            'creator_platform_charge_amount',
            'business_total_payment',
            'creator_net_received',
            'total_platform_fee',
            'business_fee_is_paid',
            'business_fee_paid_date',
            'business_fee_receipt_image',
            'business_fee_receipt_image_url',
            'creator_fee_is_paid',
            'creator_fee_paid_date',
            'creator_fee_receipt_image',
            'creator_fee_receipt_image_url',
            'status',
            'revision_reason',
            'proposed_by',
            'proposed_by_name',
            'action_by',
            'action_by_name',
            'min_budget',
            'max_budget',
            'creator_min_price',
            'creator_max_price',
            'currency',
            'country',
            'business_installments',
            'creator_installments',
            'installments',
            'created_at',
            'updated_at',
        ]

    def get_business_fee_receipt_image_url(self, obj):
        if obj.business_fee_receipt_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.business_fee_receipt_image.url)
            url = obj.business_fee_receipt_image.url
            if not url.startswith('http'):
                return f"http://127.0.0.1:8000{url if url.startswith('/') else '/' + url}"
            return url
        return None

    def get_creator_fee_receipt_image_url(self, obj):
        if obj.creator_fee_receipt_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.creator_fee_receipt_image.url)
            url = obj.creator_fee_receipt_image.url
            if not url.startswith('http'):
                return f"http://127.0.0.1:8000{url if url.startswith('/') else '/' + url}"
            return url
        return None

    def get_business_installments(self, obj):
        insts = obj.installments.filter(installment_type='business').order_by('id')
        return WorkspaceInstallmentSerializer(insts, many=True, context=self.context).data

    def get_creator_installments(self, obj):
        insts = obj.installments.filter(installment_type='creator').order_by('id')
        return WorkspaceInstallmentSerializer(insts, many=True, context=self.context).data

    def get_proposed_by_name(self, obj):
        if obj.proposed_by:
            return getattr(obj.proposed_by, 'username', '') or getattr(obj.proposed_by, 'email', '')
        return None

    def get_action_by_name(self, obj):
        if obj.action_by:
            return getattr(obj.action_by, 'username', '') or getattr(obj.action_by, 'email', '')
        return None

    def get_campaign_name(self, obj):
        return obj.campaign.name if obj.campaign else f"Campaign #{obj.campaign_id}"

    def get_creator_name(self, obj):
        if obj.campaign:
            return getattr(obj.campaign, 'creator_name', None) or (obj.campaign.creator.username if getattr(obj.campaign, 'creator', None) else "Creator")
        return "Creator"

    def get_brand_name(self, obj):
        if obj.campaign:
            return getattr(obj.campaign, 'brand_name', None) or (obj.campaign.brand.username if getattr(obj.campaign, 'brand', None) else "Brand")
        return "Brand"

    def get_min_budget(self, obj):
        return getattr(obj.campaign, 'min_budget', None) or getattr(obj.campaign, 'min_price', None) or "10000.00"

    def get_max_budget(self, obj):
        return getattr(obj.campaign, 'max_budget', None) or getattr(obj.campaign, 'max_price', None) or "51000.00"

    def get_creator_min_price(self, obj):
        return getattr(obj.campaign, 'creator_min_price', None) or getattr(obj.campaign, 'min_price', None) or "20000.00"

    def get_creator_max_price(self, obj):
        return getattr(obj.campaign, 'creator_max_price', None) or getattr(obj.campaign, 'max_price', None) or "49000.00"

    def get_currency(self, obj):
        return getattr(obj.campaign, 'currency', None) or getattr(obj.campaign, 'currency_format', None) or "USD ($)"

    def get_country(self, obj):
        return getattr(obj.campaign, 'country', None) or "Sri Lanka"

    def to_representation(self, instance):
        camp = instance.campaign
        if camp and instance.status not in ["revision_requested", "pending_creator_approval", "pending_business_approval"]:
            created_via = str(getattr(camp, "created_via", "") or "").lower().strip()
            if created_via == "pitch" or getattr(camp, "is_pitch", False):
                from campegin.models import Pitch
                pitch = Pitch.objects.filter(campaign_name=camp.name, brand=camp.brand, creator=camp.creator).order_by("-id").first() or Pitch.objects.filter(campaign_name=camp.name, brand=camp.brand).order_by("-id").first() or Pitch.objects.filter(brand=camp.brand, creator=camp.creator).order_by("-id").first()
                pitch_price = None
                if pitch:
                    if pitch.counter_history and isinstance(pitch.counter_history, list) and len(pitch.counter_history) > 0:
                        pitch_price = pitch.counter_history[-1].get("price")
                    elif pitch.counter_offer:
                        pitch_price = pitch.counter_offer
                    elif pitch.budget:
                        pitch_price = pitch.budget
                
                camp_price = None
                if camp.counter_history and isinstance(camp.counter_history, list) and len(camp.counter_history) > 0:
                    camp_price = camp.counter_history[-1].get("price")
                elif camp.counter_price:
                    camp_price = camp.counter_price
                elif camp.budget:
                    camp_price = camp.budget

                resolved_price = pitch_price or camp_price or instance.final_price
                if resolved_price:
                    try:
                        resolved_float = float(resolved_price)
                        if instance.final_price != resolved_float and instance.status != "revision_requested":
                            instance.final_price = resolved_float
                            instance.status = "creator_accepted"
                            instance.save(update_fields=["final_price", "status"])
                    except Exception:
                        pass

        data = super().to_representation(instance)
        return data
