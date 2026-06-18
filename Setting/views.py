from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.contrib.auth import update_session_auth_hash

from user.models import CreatorProfile, BusinessProfile
from .serializers import CreatorFullSettingsSerializer, BusinessFullSettingsSerializer

class CreatorSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Safely get or create creator profile
        creator_profile, _ = CreatorProfile.objects.get_or_create(user=request.user)
        serializer = CreatorFullSettingsSerializer(creator_profile)
        return Response(serializer.data)

    def put(self, request):
        creator_profile, _ = CreatorProfile.objects.get_or_create(user=request.user)
        serializer = CreatorFullSettingsSerializer(creator_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BusinessSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Safely get or create business profile
        business_profile, _ = BusinessProfile.objects.get_or_create(user=request.user)
        serializer = BusinessFullSettingsSerializer(business_profile)
        return Response(serializer.data)

    def put(self, request):
        business_profile, _ = BusinessProfile.objects.get_or_create(user=request.user)
        serializer = BusinessFullSettingsSerializer(business_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")
        confirm_new_password = request.data.get("confirm_new_password")

        if not current_password or not new_password or not confirm_new_password:
            return Response(
                {"error": "Current password, new password, and confirmation are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_new_password:
            return Response(
                {"error": "New passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(current_password):
            return Response(
                {"error": "Invalid current password"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        
        # Keep session/auth active for session authenticated clients
        update_session_auth_hash(request, user)
        
        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
