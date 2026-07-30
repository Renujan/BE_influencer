from rest_framework import serializers
from .models import RateCard


class RateCardSerializer(serializers.ModelSerializer):
    creator_username = serializers.CharField(source="creator.username", read_only=True, default="")

    class Meta:
        model = RateCard
        fields = [
            "id", "creator", "creator_username", "creator_name",
            "platform", "type", "duration", "price",
            "min_price", "max_price", "description", "is_active",
            "created_at", "updated_at"
        ]
