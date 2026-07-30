from rest_framework import viewsets, permissions
from .models import RateCard
from .serializers import RateCardSerializer


class RateCardViewSet(viewsets.ModelViewSet):
    queryset = RateCard.objects.all().order_by("-id")
    serializer_class = RateCardSerializer
    permission_classes = [permissions.AllowAny]
