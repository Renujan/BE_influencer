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
            'installments',
            'created_at',
            'updated_at',
        ]

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
