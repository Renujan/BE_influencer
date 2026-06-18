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
    Niche, BusinessType, BusinessProfile, CreatorProfile, CreatorRate, CreatorSocialAccount
)
from .serializers import (
    NicheSerializer, BusinessTypeSerializer, BusinessProfileSerializer, CreatorProfileSerializer
)
from notifications.models import Notification

class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        role = request.data.get("role", "influencer") # Default to creator/influencer
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.filter(email=email).first()
        if user:
            profile = getattr(user, "business_profile", None) or getattr(user, "creator_profile", None)
            if profile and profile.status == "restricted":
                return Response({"error": "This account is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)

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
        
        if profile.status == "restricted":
            return Response({"error": "This account is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)
        
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
            existing_user = User.objects.get(username=username)
            p = getattr(existing_user, "business_profile", None) or getattr(existing_user, "creator_profile", None)
            if p and p.status == "restricted":
                return Response({"error": "This username is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)
            return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            existing_user = User.objects.get(email=email)
            p = getattr(existing_user, "business_profile", None) or getattr(existing_user, "creator_profile", None)
            if p and p.status == "restricted":
                return Response({"error": "This email is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)
            return Response({"error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)

        phone = request.data.get("phone")
        if phone:
            if BusinessProfile.objects.filter(phone=phone, status="restricted").exists() or CreatorProfile.objects.filter(phone=phone, status="restricted").exists():
                return Response({"error": "This phone number is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)

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
                website=request.data.get("website", ""),
                phone=request.data.get("phone", ""),
                time_zone=request.data.get("time_zone", "UTC+5:30"),
                bio=request.data.get("bio", "")
            )
            
            # Add business types (handles both string and list format)
            business_types_data = request.data.get("business_types", [])
            if isinstance(business_types_data, str):
                business_types_data = [x.strip() for x in business_types_data.split(",") if x.strip()]
            
            for bt_name in business_types_data:
                bt_obj, _ = BusinessType.objects.get_or_create(name=bt_name)
                profile.business_types.add(bt_obj)
                
            # Legacy field backward compatibility support
            single_bt = request.data.get("business_type")
            if single_bt and not business_types_data:
                bt_obj, _ = BusinessType.objects.get_or_create(name=single_bt)
                profile.business_types.add(bt_obj)
                profile.business_type = single_bt
            elif business_types_data:
                profile.business_type = ", ".join(business_types_data)
            else:
                profile.business_type = ""
                
            profile.save()
            profile_data = BusinessProfileSerializer(profile).data
        else:
            # Create creator profile
            profile = CreatorProfile.objects.create(
                user=user,
                phone=request.data.get("phone", ""),
                location=request.data.get("location", ""),
                bio=request.data.get("bio", ""),
            )
            
            # Add niches for influencers (handles both string and list format)
            niches_data = request.data.get("niches", [])
            if isinstance(niches_data, str):
                niches_data = [x.strip() for x in niches_data.split(",") if x.strip()]
                
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

        profile = getattr(user, "business_profile", None) or getattr(user, "creator_profile", None)
        if profile and profile.status == "restricted":
            return Response({"error": "This account is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)

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
            
            # Handle business types updates
            if "business_types" in request.data:
                business_types_data = request.data.get("business_types", [])
                if isinstance(business_types_data, str):
                    business_types_data = [x.strip() for x in business_types_data.split(",") if x.strip()]
                
                profile.business_types.clear()
                for bt_name in business_types_data:
                    bt_obj, _ = BusinessType.objects.get_or_create(name=bt_name)
                    profile.business_types.add(bt_obj)
                profile.business_type = ", ".join(business_types_data)
            elif "business_type" in request.data:
                profile.business_type = request.data.get("business_type")
                profile.business_types.clear()
                if profile.business_type:
                    bt_obj, _ = BusinessType.objects.get_or_create(name=profile.business_type)
                    profile.business_types.add(bt_obj)

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
            
            # Handle niches updates
            if "niches" in request.data:
                niches_data = request.data.get("niches", [])
                if isinstance(niches_data, str):
                    niches_data = [x.strip() for x in niches_data.split(",") if x.strip()]
                
                profile.niches.clear()
                for niche_name in niches_data:
                    niche_obj, _ = Niche.objects.get_or_create(name=niche_name)
                    profile.niches.add(niche_obj)
                    
            profile.save()
            return Response(CreatorProfileSerializer(profile).data)

class NicheViewSet(viewsets.ModelViewSet):
    queryset = Niche.objects.all()
    serializer_class = NicheSerializer
    permission_classes = [permissions.AllowAny]

class BusinessTypeViewSet(viewsets.ModelViewSet):
    queryset = BusinessType.objects.all()
    serializer_class = BusinessTypeSerializer
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


from rest_framework.permissions import IsAdminUser

class PendingUsersView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        pending_businesses = BusinessProfile.objects.filter(status="pending")
        pending_creators = CreatorProfile.objects.filter(status="pending")

        results = []
        for bp in pending_businesses:
            results.append({
                "profile_id": bp.id,
                "role": "business",
                "name": bp.company_name or bp.user.username,
                "email": bp.user.email,
                "phone": bp.phone or "",
                "category": bp.business_type or "Tech",
            })
        for cp in pending_creators:
            niches = ", ".join([n.name for n in cp.niches.all()])
            results.append({
                "profile_id": cp.id,
                "role": "creator",
                "name": f"{cp.user.first_name} {cp.user.last_name}".strip() or cp.user.username,
                "email": cp.user.email,
                "phone": cp.phone or "",
                "category": niches or "Lifestyle",
            })
        return Response(results)

class ApproveUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        profile_id = request.data.get("profile_id")
        role = request.data.get("role")
        if not profile_id or not role:
            return Response({"error": "profile_id and role are required"}, status=status.HTTP_400_BAD_REQUEST)

        if role == "business":
            profile = get_object_or_404(BusinessProfile, id=profile_id)
        else:
            profile = get_object_or_404(CreatorProfile, id=profile_id)

        profile.status = "approved"
        profile.save()
        return Response({"message": f"User profile has been successfully approved."})

class RestrictUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        profile_id = request.data.get("profile_id")
        role = request.data.get("role")
        if not profile_id or not role:
            return Response({"error": "profile_id and role are required"}, status=status.HTTP_400_BAD_REQUEST)

        if role == "business":
            profile = get_object_or_404(BusinessProfile, id=profile_id)
        else:
            profile = get_object_or_404(CreatorProfile, id=profile_id)

        profile.status = "restricted"
        profile.save()
        return Response({"message": f"User profile has been permanently restricted."})


class SubmitVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = getattr(request.user, "business_profile", None)
        if not profile:
            return Response({"error": "Only business accounts can submit verification documents."}, status=status.HTTP_400_BAD_REQUEST)
        
        if profile.status == "approved":
            return Response({"error": "Business profile is already verified and approved."}, status=status.HTTP_400_BAD_REQUEST)
            
        business_reg_number = request.data.get("business_reg_number")
        business_document = request.FILES.get("business_document")
        
        if not business_reg_number or not business_document:
            return Response({"error": "Both business registration number and document file are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        profile.business_reg_number = business_reg_number
        profile.business_document = business_document
        profile.verification_documents_submitted = True
        profile.save()
        
        # Create Admin Notification
        Notification.objects.create(
            title="Business Verification Submitted",
            message=f"Business '{profile.company_name or request.user.username}' submitted verification details (Reg No: {business_reg_number}) for admin review.",
            category="compliance",
            icon="fas fa-file-contract"
        )
        
        return Response(BusinessProfileSerializer(profile).data, status=status.HTTP_200_OK)


from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_staff)
def admin_approve_business_view(request, profile_id):
    profile = get_object_or_404(BusinessProfile, pk=profile_id)
    profile.status = "approved"
    profile.save()
    messages.success(request, f"Business '{profile.company_name or profile.user.username}' has been successfully approved.")
    try:
        from django.urls import reverse
        inspect_url = reverse("businessprofile:inspect", args=[profile_id])
        return redirect(inspect_url)
    except Exception:
        return redirect("/admin/businessprofile/")

@user_passes_test(lambda u: u.is_staff)
def admin_restrict_business_view(request, profile_id):
    profile = get_object_or_404(BusinessProfile, pk=profile_id)
    profile.status = "restricted"
    profile.save()
    messages.warning(request, f"Business '{profile.company_name or profile.user.username}' has been restricted.")
    try:
        from django.urls import reverse
        inspect_url = reverse("businessprofile:inspect", args=[profile_id])
        return redirect(inspect_url)
    except Exception:
        return redirect("/admin/businessprofile/")



from io import BytesIO


from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import user_passes_test
from xhtml2pdf import pisa
from Setting.models import CreatorSettings, BusinessSettings

@user_passes_test(lambda u: u.is_staff)
def download_profile_pdf_view(request, profile_type, profile_id):
    if profile_type == 'business':
        business_profile = get_object_or_404(BusinessProfile, pk=profile_id)
        BusinessSettings.objects.get_or_create(business=business_profile)
        settings = getattr(business_profile, "settings", None)
        
        # Pre-split business types (prioritizing ManyToMany relation)
        business_types = []
        if business_profile.business_types.exists():
            business_types = [t.name for t in business_profile.business_types.all()]
        elif business_profile.business_type:
            # handle both comma and space separation
            business_types = [t.strip() for t in business_profile.business_type.replace(",", " ").split() if t.strip()]
            
        context = {
            "instance": business_profile,
            "settings": settings,
            "business_types": business_types,
            "profile_type": "Business Profile",
        }
        template_name = "user/profile_pdf.html"
        filename = f"business_profile_{business_profile.company_name or business_profile.user.username}.pdf"
    elif profile_type == 'creator':
        creator_profile = get_object_or_404(CreatorProfile, pk=profile_id)
        CreatorSettings.objects.get_or_create(creator=creator_profile)
        settings = getattr(creator_profile, "settings", None)
        
        # Pre-split platforms list for rates
        rates_data = []
        for rate in creator_profile.rates.all():
            platforms_list = [p.strip() for p in rate.platforms.replace(",", " ").split() if p.strip()]
            rates_data.append({
                "content_type": rate.content_type,
                "platforms_list": platforms_list,
                "price": rate.price,
                "notes": rate.notes
            })
            
        context = {
            "instance": creator_profile,
            "settings": settings,
            "rates": rates_data,
            "payout_methods": creator_profile.payout_methods.all(),
            "social_accounts": creator_profile.user.social_accounts.all(),
            "profile_type": "Creator Profile",
        }
        template_name = "user/profile_pdf.html"
        filename = f"creator_profile_{creator_profile.user.username}.pdf"
    else:
        return HttpResponse("Invalid profile type", status=400)
        
    html = render_to_string(template_name, context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=500)

