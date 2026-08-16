from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from .models import CreatorRating, BusinessRating
from .serializers import CreatorRatingSerializer, BusinessRatingSerializer
from campegin.models import Campaign

class CreatorRatingViewSet(viewsets.ModelViewSet):
    queryset = CreatorRating.objects.all()
    serializer_class = CreatorRatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CreatorRating.objects.all()
        
        if not (user.is_staff or user.is_superuser):
            qs = qs.filter(Q(brand=user) | Q(creator=user))

        campaign_id = self.request.query_params.get("campaign")
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)

        creator_id = self.request.query_params.get("creator")
        if creator_id:
            qs = qs.filter(creator_id=creator_id)

        return qs.distinct()

    def create(self, request, *args, **kwargs):
        campaign_id = request.data.get("campaign")
        if not campaign_id:
            return Response({"error": "Campaign ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)

        if campaign.brand != request.user and not (request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Only the business owner of this campaign can submit a rating."}, status=status.HTTP_403_FORBIDDEN)

        if str(campaign.status).lower() != "completed":
            return Response({"error": "Ratings can only be submitted for completed campaigns."}, status=status.HTTP_400_BAD_REQUEST)

        if not campaign.creator:
            return Response({"error": "This campaign does not have an assigned creator to rate."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rating_val = int(request.data.get("rating", 5))
            if rating_val < 1: rating_val = 1
            if rating_val > 5: rating_val = 5
        except (ValueError, TypeError):
            rating_val = 5

        review_val = str(request.data.get("review", "")).strip()

        rating_obj, created = CreatorRating.objects.update_or_create(
            campaign=campaign,
            defaults={
                "brand": request.user,
                "creator": campaign.creator,
                "rating": rating_val,
                "review": review_val,
            }
        )

        serializer = self.get_serializer(rating_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class BusinessRatingViewSet(viewsets.ModelViewSet):
    queryset = BusinessRating.objects.all()
    serializer_class = BusinessRatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = BusinessRating.objects.all()
        
        if not (user.is_staff or user.is_superuser):
            qs = qs.filter(Q(brand=user) | Q(creator=user))

        campaign_id = self.request.query_params.get("campaign")
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)

        brand_id = self.request.query_params.get("brand")
        if brand_id:
            qs = qs.filter(brand_id=brand_id)

        return qs.distinct()

    def create(self, request, *args, **kwargs):
        campaign_id = request.data.get("campaign")
        if not campaign_id:
            return Response({"error": "Campaign ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)

        if campaign.creator != request.user and not (request.user.is_staff or request.user.is_superuser):
            return Response({"error": "Only the assigned creator of this campaign can submit a rating for the business."}, status=status.HTTP_403_FORBIDDEN)

        if str(campaign.status).lower() != "completed":
            return Response({"error": "Ratings can only be submitted for completed campaigns."}, status=status.HTTP_400_BAD_REQUEST)

        if not campaign.brand:
            return Response({"error": "This campaign does not have an assigned business to rate."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rating_val = int(request.data.get("rating", 5))
            if rating_val < 1: rating_val = 1
            if rating_val > 5: rating_val = 5
        except (ValueError, TypeError):
            rating_val = 5

        review_val = str(request.data.get("review", "")).strip()

        rating_obj, created = BusinessRating.objects.update_or_create(
            campaign=campaign,
            defaults={
                "brand": campaign.brand,
                "creator": request.user,
                "rating": rating_val,
                "review": review_val,
            }
        )

        serializer = self.get_serializer(rating_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

