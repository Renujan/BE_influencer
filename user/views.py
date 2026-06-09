import random
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import (
    Niche, BusinessProfile, CreatorProfile, CreatorRate, CreatorSocialAccount
)
from .serializers import (
    NicheSerializer, BusinessProfileSerializer, CreatorProfileSerializer
)

class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        role = request.data.get("role", "influencer") # Default to creator/influencer
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.filter(email=email).first()
        if not user:
            # Frictionless onboarding placeholder user
            username = email.split("@")[0]
            original_username = username
            idx = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{idx}"
                idx += 1
            user = User.objects.create_user(username=username, email=email, password=User.objects.make_random_password())
            
            # Create corresponding profile
            if role == "business":
                BusinessProfile.objects.create(user=user)
            else:
                CreatorProfile.objects.create(user=user)
        
        # Check which profile exists
        profile = None
        if hasattr(user, "business_profile"):
            profile = user.business_profile
        elif hasattr(user, "creator_profile"):
            profile = user.creator_profile
        else:
            # Default fallback if somehow User exists without profile
            if role == "business":
                profile = BusinessProfile.objects.create(user=user)
            else:
                profile = CreatorProfile.objects.create(user=user)
        
        otp = str(random.randint(100000, 999999))
        profile.otp_code = otp
        profile.otp_verified = False
        profile.save()

        # Log OTP to stdout as if it was sent by email
        print(f"\n[EMAIL OTP] =======================================")
        print(f"[EMAIL OTP] Sent to: {email}")
        print(f"[EMAIL OTP] OTP Code: {otp}")
        print(f"[EMAIL OTP] =======================================\n")

        return Response({"message": f"OTP successfully sent to {email}", "otp_code": otp})

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp_code = request.data.get("otp_code")
        if not email or not otp_code:
            return Response({"error": "Email and otp_code are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        profile = getattr(user, "business_profile", None) or getattr(user, "creator_profile", None)
        if not profile:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if profile.otp_code == otp_code:
            profile.otp_verified = True
            profile.save()
            
            token, _ = Token.objects.get_or_create(user=user)
            role = "business" if hasattr(user, "business_profile") else "influencer"
            
            if role == "business":
                profile_data = BusinessProfileSerializer(user.business_profile).data
            else:
                profile_data = CreatorProfileSerializer(user.creator_profile).data
                
            return Response({
                "message": "OTP verified successfully",
                "token": token.key,
                "role": role,
                "profile": profile_data
            })
        else:
            return Response({"error": "Invalid OTP code"}, status=status.HTTP_400_BAD_REQUEST)

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        role = request.data.get("role") # business or influencer

        if not username or not email or not password or not role:
            return Response({"error": "Username, email, password, and role are required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password,
            first_name=request.data.get("first_name", ""),
            last_name=request.data.get("last_name", "")
        )
        
        profile_data = None
        if role == "business":
            # Create business profile
            profile = BusinessProfile.objects.create(
                user=user,
                company_name=request.data.get("company_name", ""),
                business_type=request.data.get("business_type", ""),
                website=request.data.get("website", ""),
                phone=request.data.get("phone", ""),
                time_zone=request.data.get("time_zone", "UTC+5:30"),
                bio=request.data.get("bio", "")
            )
            profile_data = BusinessProfileSerializer(profile).data
        else:
            # Create creator profile
            profile = CreatorProfile.objects.create(
                user=user,
                phone=request.data.get("phone", ""),
                location=request.data.get("location", ""),
                bio=request.data.get("bio", ""),
            )
            
            # Add niches for influencers
            niches_data = request.data.get("niches", [])
            for niche_name in niches_data:
                niche_obj, _ = Niche.objects.get_or_create(name=niche_name)
                profile.niches.add(niche_obj)
            profile_data = CreatorProfileSerializer(profile).data

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "role": role,
            "profile": profile_data
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username_or_email = request.data.get("username") or request.data.get("email")
        password = request.data.get("password")

        if not username_or_email or not password:
            return Response({"error": "Credentials are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username_or_email, password=password)
        if not user:
            user_obj = User.objects.filter(email=username_or_email).first()
            if user_obj:
                user = authenticate(username=user_obj.username, password=password)

        if not user:
            return Response({"error": "Invalid username/email or password"}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        
        role = "business" if hasattr(user, "business_profile") else "influencer"
        if role == "business":
            profile_data = BusinessProfileSerializer(user.business_profile).data
        else:
            profile_data = CreatorProfileSerializer(user.creator_profile).data

        return Response({
            "token": token.key,
            "role": role,
            "profile": profile_data
        })

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        role = "business" if hasattr(user, "business_profile") else "influencer"
        if role == "business":
            profile = user.business_profile
            return Response(BusinessProfileSerializer(profile).data)
        else:
            profile, _ = CreatorProfile.objects.get_or_create(user=user)
            return Response(CreatorProfileSerializer(profile).data)

    def put(self, request):
        user = request.user
        user.first_name = request.data.get("first_name", user.first_name)
        user.last_name = request.data.get("last_name", user.last_name)
        user.save()
        
        role = "business" if hasattr(user, "business_profile") else "influencer"
        if role == "business":
            profile = user.business_profile
            profile.phone = request.data.get("phone", profile.phone)
            profile.secondary_phone = request.data.get("secondary_phone", profile.secondary_phone)
            profile.bio = request.data.get("bio", profile.bio)
            profile.company_name = request.data.get("company_name", profile.company_name)
            profile.business_type = request.data.get("business_type", profile.business_type)
            profile.website = request.data.get("website", profile.website)
            profile.time_zone = request.data.get("time_zone", profile.time_zone)
            profile.avatar_url = request.data.get("avatar_url", profile.avatar_url)
            
            # Socials
            profile.facebook_url = request.data.get("facebook_url", profile.facebook_url)
            profile.instagram_handle = request.data.get("instagram_handle", profile.instagram_handle)
            profile.tiktok_handle = request.data.get("tiktok_handle", profile.tiktok_handle)
            profile.youtube_url = request.data.get("youtube_url", profile.youtube_url)
            profile.linkedin_url = request.data.get("linkedin_url", profile.linkedin_url)
            profile.twitter_handle = request.data.get("twitter_handle", profile.twitter_handle)
            
            profile.save()
            return Response(BusinessProfileSerializer(profile).data)
        else:
            profile, _ = CreatorProfile.objects.get_or_create(user=user)
            profile.phone = request.data.get("phone", profile.phone)
            profile.bio = request.data.get("bio", profile.bio)
            profile.location = request.data.get("location", profile.location)
            profile.avatar_url = request.data.get("avatar_url", profile.avatar_url)
            profile.save()
            return Response(CreatorProfileSerializer(profile).data)

class NicheViewSet(viewsets.ModelViewSet):
    queryset = Niche.objects.all()
    serializer_class = NicheSerializer
    permission_classes = [permissions.AllowAny]

class CreatorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CreatorProfile.objects.all()
    serializer_class = CreatorProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        niche = self.request.query_params.get("niche")
        location = self.request.query_params.get("location")
        er_min = self.request.query_params.get("er_min")

        if niche and niche.lower() != "all":
            qs = qs.filter(niches__name__iexact=niche)
        
        if location:
            qs = qs.filter(location__icontains=location)

        if er_min:
            qs = qs.filter(user__social_accounts__engagement_rate__gte=float(er_min))

        return qs.distinct()
