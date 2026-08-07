from rest_framework import serializers
from .models import CreatorRating

class CreatorRatingSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.username", read_only=True)
    creator_name = serializers.CharField(source="creator.username", read_only=True)
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)

    class Meta:
        model = CreatorRating
        fields = [
            "id", "campaign", "campaign_name", "brand", "brand_name",
            "creator", "creator_name", "rating", "review", "created_at", "updated_at"
        ]
        read_only_fields = ["brand", "creator", "created_at", "updated_at"]
