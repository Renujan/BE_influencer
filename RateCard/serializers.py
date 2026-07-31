from rest_framework import serializers
from .models import RateCard
from django.db import models


class RateCardSerializer(serializers.ModelSerializer):
    creator_username = serializers.CharField(source="creator.username", read_only=True, default="")
    creator_niches = serializers.SerializerMethodField()

    class Meta:
        model = RateCard
        fields = [
            "id", "creator", "creator_username", "creator_name", "creator_niches",
            "platform", "type", "duration", "price",
            "min_price", "max_price", "description", "is_active",
            "created_at", "updated_at"
        ]

    def get_creator_niches(self, obj):
        user = obj.creator
        if not user and obj.creator_name:
            from django.contrib.auth.models import User
            user = User.objects.filter(
                models.Q(username__iexact=obj.creator_name) |
                models.Q(first_name__iexact=obj.creator_name)
            ).first()
        if user and hasattr(user, "creator_profile") and user.creator_profile:
            return [n.name for n in user.creator_profile.niches.all()]
        return []
