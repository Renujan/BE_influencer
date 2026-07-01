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
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from .models import (
    Niche, BusinessType, BusinessProfile, CreatorProfile, CreatorRate, CreatorSocialAccount
)
from .serializers import (
    NicheSerializer, BusinessTypeSerializer, BusinessProfileSerializer, CreatorProfileSerializer
)
from notifications.models import Notification

def send_status_update_email(user, status_type, role):
    role_label = "Business" if role == "business" else "Creator"
    
    if status_type == "approved":
        subject = f"Your Ampli Account has been Approved!"
        message = (
            f"Dear {user.first_name or user.username},\n\n"
            f"We are excited to inform you that your Ampli {role_label} account has been reviewed and approved by our team!\n\n"
            f"You can now access your dashboard, connect with campaigns/creators, and explore the platform's features.\n\n"
            f"Log in to get started: {settings.FRONTEND_URL}/auth?mode=signin\n\n"
            f"Best regards,\nThe Ampli Team"
        )
    else: # restricted
        subject = f"Your Ampli Account Status Update"
        message = (
            f"Dear {user.first_name or user.username},\n\n"
            f"We regret to inform you that your Ampli {role_label} account has been restricted following a review by our compliance team.\n\n"
            f"If you believe this was an error or wish to appeal this decision, please reply to this email or contact support@ampli.co.\n\n"
            f"Best regards,\nThe Ampli Compliance Team"
        )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        print(f"\n[EMAIL STATUS UPDATE] Sent to: {user.email} | Status: {status_type}\n")
    except Exception as e:
        print(f"\n[EMAIL STATUS UPDATE] Error sending email: {e}\n")

class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        phone = request.data.get("phone")
        otp_method = request.data.get("otp_method", "email") # "email" or "mobile"
        role = request.data.get("role", "influencer") # Default to creator/influencer
        
        # If mobile OTP login (no email provided)
        if otp_method == "mobile" and phone and not email:
            profile = None
            if role == "business":
                profile = BusinessProfile.objects.filter(phone=phone).first()
            else:
                profile = CreatorProfile.objects.filter(phone=phone).first()
                
            if not profile:
                return Response({"error": "No account found with this mobile number. Please sign up first."}, status=status.HTTP_404_NOT_FOUND)
            
            user = profile.user
        else:
            # Email-based check or lookup
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
                user = User.objects.create_user(username=username, email=email, password=get_random_string(32))
                
                # Create corresponding profile
                if role == "business":
                    profile = BusinessProfile.objects.create(user=user, phone=phone if phone else "")
                else:
                    profile = CreatorProfile.objects.create(user=user, phone=phone if phone else "")
            else:
                profile = getattr(user, "business_profile", None) or getattr(user, "creator_profile", None)
                if not profile:
                    if role == "business":
                        profile = BusinessProfile.objects.create(user=user)
                    else:
                        profile = CreatorProfile.objects.create(user=user)
                
                if phone:
                    profile.phone = phone
                    profile.save()
        
        otp = str(random.randint(100000, 999999))
        profile.otp_code = otp
        profile.otp_method = otp_method
        profile.otp_verified = False
        profile.save()

        # Dispatch OTP based on the chosen method
        if otp_method == "mobile":
            # Mobile OTP: log to console (connect SMS provider when ready)
            print(f"\n[MOBILE OTP] =======================================")
            print(f"[MOBILE OTP] Sent to: {phone or profile.phone}")
            print(f"[MOBILE OTP] OTP Code: {otp}")
            print(f"[MOBILE OTP] =======================================\n")
            return Response({"message": f"OTP successfully sent to mobile {phone or profile.phone}", "otp_method": "mobile"})
        else:
            # Email OTP: send via SMTP
            recipient_email = email or user.email
            try:
                send_mail(
                    subject="Your Ampli Verification Code",
                    message=(
                        f"Your Ampli one-time verification code is:\n\n"
                        f"  {otp}\n\n"
                        f"This code expires in 10 minutes. Do not share it with anyone."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                    html_message=(
                        f"""
                        <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#f9f9fb;border-radius:12px;">
                          <h2 style="color:#2F54EB;margin-bottom:8px;">Ampli Verification</h2>
                          <p style="color:#555;font-size:15px;">Use the code below to verify your identity:</p>
                          <div style="background:#fff;border:2px solid #2F54EB;border-radius:10px;padding:24px;text-align:center;margin:24px 0;">
                            <span style="font-size:40px;font-weight:700;letter-spacing:10px;color:#2F54EB;">{otp}</span>
                          </div>
                          <p style="color:#888;font-size:13px;">This code expires in <strong>10 minutes</strong>. Never share it with anyone.</p>
                          <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
                          <p style="color:#bbb;font-size:12px;">Sent by Ampli Platform &middot; atom.lift.1@gmail.com</p>
                        </div>
                        """
                    ),
                )
                print(f"\n[EMAIL OTP] Sent to: {recipient_email} | Code: {otp}\n")
            except Exception as e:
                print(f"\n[EMAIL OTP] SMTP error: {e}")
                print(f"[EMAIL OTP] Fallback code for {recipient_email}: {otp}\n")
                # Return the code in dev mode so flow doesn't break
                return Response({"message": f"OTP generated (email delivery failed): {e}", "otp_code": otp, "otp_method": "email"}, status=status.HTTP_200_OK)

            return Response({"message": f"OTP successfully sent to email {recipient_email}", "otp_method": "email"})

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        phone = request.data.get("phone")
        otp_code = request.data.get("otp_code")
        otp_method = request.data.get("otp_method", "email") # "email" or "mobile"
        
        if not otp_code:
            return Response({"error": "otp_code is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = None
        requested_role = request.data.get("role", "influencer")

        if otp_method == "mobile" and phone and not email:
            # Look up by phone using the role-specific profile table
            profile = None
            if requested_role == "business":
                profile = BusinessProfile.objects.filter(phone=phone).first()
            else:
                profile = CreatorProfile.objects.filter(phone=phone).first()
                
            if not profile:
                role_label = "Business" if requested_role == "business" else "Creator"
                return Response({"error": f"No {role_label} account found with this mobile number."}, status=status.HTTP_404_NOT_FOUND)
            user = profile.user
        else:
            if not email:
                return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            # Validate role against the actual account type
            actual_role = "business" if hasattr(user, "business_profile") else "influencer"
            if requested_role != actual_role:
                role_label = "Business" if requested_role == "business" else "Creator"
                return Response(
                    {"error": f"No {role_label} account found with these credentials. Please check your role selection."},
                    status=status.HTTP_403_FORBIDDEN
                )
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

        phone = request.data.get("phone")
        if phone:
            if BusinessProfile.objects.filter(phone=phone, status="restricted").exists() or CreatorProfile.objects.filter(phone=phone, status="restricted").exists():
                return Response({"error": "This phone number is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)

        # Check if user already exists
        user = User.objects.filter(email=email).first()
        profile = None

        if user:
            # Check if this user has a restricted profile
            p = getattr(user, "business_profile", None) or getattr(user, "creator_profile", None)
            if p and p.status == "restricted":
                return Response({"error": "This email is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)
            
            # Check if user has verified OTP and is completing registration
            if p and p.otp_verified:
                profile = p
                # Check username conflicts with other users
                if User.objects.filter(username=username).exclude(id=user.id).exists():
                    conflicting_user = User.objects.get(username=username)
                    cp = getattr(conflicting_user, "business_profile", None) or getattr(conflicting_user, "creator_profile", None)
                    if cp and cp.status == "restricted":
                        return Response({"error": "This username is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)
                    return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Update user fields
                user.username = username
                user.set_password(password)
                user.first_name = request.data.get("first_name", "")
                user.last_name = request.data.get("last_name", "")
                user.save()
            else:
                return Response({"error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # No user exists with this email, check if username is taken
            if User.objects.filter(username=username).exists():
                conflicting_user = User.objects.get(username=username)
                cp = getattr(conflicting_user, "business_profile", None) or getattr(conflicting_user, "creator_profile", None)
                if cp and cp.status == "restricted":
                    return Response({"error": "This username is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)
                return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

            # Create new user
            user = User.objects.create_user(
                username=username, 
                email=email, 
                password=password,
                first_name=request.data.get("first_name", ""),
                last_name=request.data.get("last_name", "")
            )

        # Check if the role matches the existing profile type
        if profile:
            current_role = "business" if hasattr(user, "business_profile") else "influencer"
            if current_role != role:
                profile.delete()
                profile = None

        profile_data = None
        if role == "business":
            # Get or create business profile
            if not profile:
                profile, _ = BusinessProfile.objects.get_or_create(user=user)
            
            profile.company_name = request.data.get("company_name", "")
            profile.website = request.data.get("website", "")
            profile.phone = request.data.get("phone", "")
            profile.time_zone = request.data.get("time_zone", "UTC+5:30")
            profile.bio = request.data.get("bio", "")
            
            # Add business types (handles both string and list format)
            business_types_data = request.data.get("business_types", [])
            if isinstance(business_types_data, str):
                business_types_data = [x.strip() for x in business_types_data.split(",") if x.strip()]
            
            # Clear and rebuild business types
            profile.business_types.clear()
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
            # Get or create creator profile
            if not profile:
                profile, _ = CreatorProfile.objects.get_or_create(user=user)
            
            profile.phone = request.data.get("phone", "")
            profile.location = request.data.get("location", "")
            profile.bio = request.data.get("bio", "")
            
            # Add niches for influencers (handles both string and list format)
            niches_data = request.data.get("niches", [])
            if isinstance(niches_data, str):
                niches_data = [x.strip() for x in niches_data.split(",") if x.strip()]
                
            profile.niches.clear()
            for niche_name in niches_data:
                niche_obj, _ = Niche.objects.get_or_create(name=niche_name)
                profile.niches.add(niche_obj)
            profile.save()
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
        # Role the user selected on the login screen ("business" or "influencer")
        requested_role = request.data.get("role")

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

        # Determine the actual role of this account
        actual_role = "business" if hasattr(user, "business_profile") else "influencer"

        # If the frontend sent a role, enforce it — reject cross-role logins
        if requested_role and requested_role != actual_role:
            role_label = "Business" if requested_role == "business" else "Creator"
            return Response(
                {"error": f"No {role_label} account found with these credentials. Please check your role selection."},
                status=status.HTTP_403_FORBIDDEN
            )

        token, _ = Token.objects.get_or_create(user=user)

        role = actual_role
        if role == "business":
            profile_data = BusinessProfileSerializer(user.business_profile).data
        else:
            profile_data = CreatorProfileSerializer(user.creator_profile).data

        return Response({
            "token": token.key,
            "role": role,
            "profile": profile_data
        })

class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        access_token = request.data.get("access_token")
        requested_role = request.data.get("role")  # "business" or "influencer"

        if not access_token:
            return Response({"error": "Access token is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Verify access token with Google
        import json
        import urllib.request
        from django.conf import settings
        
        userinfo_url = f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={access_token}"
        try:
            req = urllib.request.Request(userinfo_url)
            with urllib.request.urlopen(req) as response:
                google_user = json.loads(response.read().decode("utf-8"))
        except Exception as e:
            return Response({"error": f"Failed to verify token with Google: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        email = google_user.get("email")
        if not email:
            return Response({"error": "Google account does not provide email"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify client ID if GOOGLE_CLIENT_ID is configured in settings
        google_client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
        if google_client_id:
            try:
                tokeninfo_url = f"https://oauth2.googleapis.com/tokeninfo?access_token={access_token}"
                req = urllib.request.Request(tokeninfo_url)
                with urllib.request.urlopen(req) as response:
                    tokeninfo = json.loads(response.read().decode("utf-8"))
                aud = tokeninfo.get("aud") or tokeninfo.get("azp")
                if aud != google_client_id:
                    return Response({"error": "Invalid token audience"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                # Log error or return failure if token audience verification failed
                return Response({"error": f"Failed to verify token audience: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        given_name = google_user.get("given_name", "")
        family_name = google_user.get("family_name", "")
        picture = google_user.get("picture", "")

        # 2. Check if user already exists
        user = User.objects.filter(email=email).first()
        is_new_user = False

        if user:
            # Check if they have a profile
            has_business = hasattr(user, "business_profile")
            has_creator = hasattr(user, "creator_profile")
            
            if not has_business and not has_creator:
                # User exists but has no profile yet - create it now!
                if not requested_role or requested_role not in ["business", "influencer"]:
                    return Response({"error": "Role is required to create a profile"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if registration details are provided or if we need to collect them
                is_registering = False
                if requested_role == "business" and request.data.get("company_name"):
                    is_registering = True
                elif requested_role == "influencer" and (request.data.get("niches") or request.data.get("phone")):
                    is_registering = True

                if not is_registering:
                    return Response({
                        "is_new_user": True,
                        "email": email,
                        "given_name": given_name,
                        "family_name": family_name,
                        "picture": picture
                    }, status=status.HTTP_200_OK)

                if requested_role == "business":
                    profile = BusinessProfile.objects.create(
                        user=user,
                        company_name=request.data.get("company_name") or f"{given_name} {family_name}".strip() or user.username,
                        website=request.data.get("website", ""),
                        phone=request.data.get("phone", ""),
                        avatar_url=picture,
                        otp_verified=True,
                        status="pending"
                    )
                    business_types_data = request.data.get("business_types", [])
                    if isinstance(business_types_data, str):
                        business_types_data = [x.strip() for x in business_types_data.split(",") if x.strip()]
                    for bt_name in business_types_data:
                        bt_obj, _ = BusinessType.objects.get_or_create(name=bt_name)
                        profile.business_types.add(bt_obj)
                    profile.save()
                else:
                    profile = CreatorProfile.objects.create(
                        user=user,
                        phone=request.data.get("phone", ""),
                        avatar_url=picture,
                        otp_verified=True,
                        status="pending"
                    )
                    niches_data = request.data.get("niches", [])
                    if isinstance(niches_data, str):
                        niches_data = [x.strip() for x in niches_data.split(",") if x.strip()]
                    for niche_name in niches_data:
                        niche_obj, _ = Niche.objects.get_or_create(name=niche_name)
                        profile.niches.add(niche_obj)
                    profile.save()
                
                password = request.data.get("password")
                if password:
                    user.set_password(password)
                    user.save()
                is_new_user = True
            else:
                profile = getattr(user, "business_profile", None) or getattr(user, "creator_profile", None)
                if profile and profile.status == "restricted":
                    return Response({"error": "This account is permanently restricted."}, status=status.HTTP_403_FORBIDDEN)
                
                actual_role = "business" if has_business else "influencer"
                if requested_role and requested_role != actual_role:
                    role_label = "Business" if requested_role == "business" else "Creator"
                    return Response(
                        {"error": f"No {role_label} account found with these credentials. Please check your role selection."},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # If registering and profile already exists (e.g. placeholder created by SendOTPView), update it!
                is_registering = False
                if requested_role == "business" and request.data.get("company_name"):
                    is_registering = True
                elif requested_role == "influencer" and (request.data.get("niches") or request.data.get("phone")):
                    is_registering = True

                if is_registering:
                    if requested_role == "business":
                        profile.company_name = request.data.get("company_name") or profile.company_name or user.username
                        profile.website = request.data.get("website", "")
                        profile.phone = request.data.get("phone", "")
                        profile.avatar_url = picture or profile.avatar_url
                        profile.otp_verified = True
                        
                        business_types_data = request.data.get("business_types", [])
                        if isinstance(business_types_data, str):
                            business_types_data = [x.strip() for x in business_types_data.split(",") if x.strip()]
                        for bt_name in business_types_data:
                            bt_obj, _ = BusinessType.objects.get_or_create(name=bt_name)
                            profile.business_types.add(bt_obj)
                        profile.save()
                    else:
                        profile.phone = request.data.get("phone", "")
                        profile.avatar_url = picture or profile.avatar_url
                        profile.otp_verified = True
                        
                        niches_data = request.data.get("niches", [])
                        if isinstance(niches_data, str):
                            niches_data = [x.strip() for x in niches_data.split(",") if x.strip()]
                        for niche_name in niches_data:
                            niche_obj, _ = Niche.objects.get_or_create(name=niche_name)
                            profile.niches.add(niche_obj)
                        profile.save()
                    
                    password = request.data.get("password")
                    if password:
                        user.set_password(password)
                        user.save()
                    is_new_user = True
        else:
            # New user registration
            if not requested_role or requested_role not in ["business", "influencer"]:
                return Response({"error": "Role is required for new registration"}, status=status.HTTP_400_BAD_REQUEST)

            # Check if registration details are provided or if we need to collect them
            is_registering = False
            if requested_role == "business" and request.data.get("company_name"):
                is_registering = True
            elif requested_role == "influencer" and (request.data.get("niches") or request.data.get("phone")):
                is_registering = True

            if not is_registering:
                return Response({
                    "is_new_user": True,
                    "email": email,
                    "given_name": given_name,
                    "family_name": family_name,
                    "picture": picture
                }, status=status.HTTP_200_OK)

            # Generate unique username
            base_username = email.split("@")[0] or "google_user"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Create User
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=given_name,
                last_name=family_name
            )
            password = request.data.get("password")
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.save()
            is_new_user = True

            # Create appropriate profile based on requested role and save details
            if requested_role == "business":
                profile = BusinessProfile.objects.create(
                    user=user,
                    company_name=request.data.get("company_name") or f"{given_name} {family_name}".strip() or username,
                    website=request.data.get("website", ""),
                    phone=request.data.get("phone", ""),
                    avatar_url=picture,
                    otp_verified=True,
                    status="pending"
                )
                business_types_data = request.data.get("business_types", [])
                if isinstance(business_types_data, str):
                    business_types_data = [x.strip() for x in business_types_data.split(",") if x.strip()]
                for bt_name in business_types_data:
                    bt_obj, _ = BusinessType.objects.get_or_create(name=bt_name)
                    profile.business_types.add(bt_obj)
                profile.save()
            else:
                profile = CreatorProfile.objects.create(
                    user=user,
                    phone=request.data.get("phone", ""),
                    avatar_url=picture,
                    otp_verified=True,
                    status="pending"
                )
                niches_data = request.data.get("niches", [])
                if isinstance(niches_data, str):
                    niches_data = [x.strip() for x in niches_data.split(",") if x.strip()]
                for niche_name in niches_data:
                    niche_obj, _ = Niche.objects.get_or_create(name=niche_name)
                    profile.niches.add(niche_obj)
                profile.save()

        # 3. Retrieve or create Auth Token
        token, _ = Token.objects.get_or_create(user=user)
        role = "business" if hasattr(user, "business_profile") else "influencer"

        if role == "business":
            profile_data = BusinessProfileSerializer(user.business_profile).data
        else:
            profile_data = CreatorProfileSerializer(user.creator_profile).data

        return Response({
            "token": token.key,
            "role": role,
            "profile": profile_data,
            "is_new_user": is_new_user
        }, status=status.HTTP_200_OK if not is_new_user else status.HTTP_201_CREATED)

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        role = "business" if hasattr(user, "business_profile") else "influencer"
        if role == "business":
            profile = user.business_profile
            profile_data = BusinessProfileSerializer(profile).data
        else:
            profile, _ = CreatorProfile.objects.get_or_create(user=user)
            profile_data = CreatorProfileSerializer(profile).data

        # Always include role so the frontend can stay authoritative
        return Response({
            "role": role,
            **profile_data,
        })

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
        budget_min = self.request.query_params.get("budget_min")
        budget_max = self.request.query_params.get("budget_max")

        if niche and niche.lower() != "all":
            qs = qs.filter(niches__name__iexact=niche)
        
        if location:
            qs = qs.filter(location__icontains=location)

        if er_min:
            qs = qs.filter(user__social_accounts__engagement_rate__gte=float(er_min))

        if budget_min:
            qs = qs.filter(rates__price__gte=float(budget_min))

        if budget_max:
            qs = qs.filter(rates__price__lte=float(budget_max))

        return qs.distinct()

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def featured(self, request):
        qs = CreatorProfile.objects.filter(is_featured=True, status="approved").order_by("-featured_at")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            if pk.isdigit():
                obj = get_object_or_404(CreatorProfile, pk=pk)
            else:
                obj = get_object_or_404(CreatorProfile, user__username=pk)
        except Exception:
            obj = get_object_or_404(CreatorProfile, user__username=pk)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)


class BusinessViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BusinessProfile.objects.filter(status="approved")
    serializer_class = BusinessProfileSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def featured(self, request):
        qs = BusinessProfile.objects.filter(is_featured=True, status="approved").order_by("-featured_at")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


from rest_framework.permissions import IsAdminUser

class PendingUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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
                "business_reg_number": bp.business_reg_number or "",
                "business_document": bp.business_document.url if bp.business_document else "",
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
                "document_type": cp.document_type or "",
                "document_front": cp.document_front.url if cp.document_front else "",
                "document_back": cp.document_back.url if cp.document_back else "",
                "other_details": cp.other_details or "",
            })
        return Response(results)

class ApproveUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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
        
        # Send status email
        send_status_update_email(profile.user, "approved", role)
        
        return Response({"message": f"User profile has been successfully approved."})

class RestrictUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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
        
        # Send status email
        send_status_update_email(profile.user, "restricted", role)
        
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
            icon="fas fa-file-contract",
            target_url=f"/admin/businessprofile/inspect/{profile.id}/"
        )
        
        return Response(BusinessProfileSerializer(profile).data, status=status.HTTP_200_OK)


class CreatorSubmitVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = getattr(request.user, "creator_profile", None)
        if not profile:
            return Response({"error": "Only creator accounts can submit verification documents."}, status=status.HTTP_400_BAD_REQUEST)
        
        if profile.status == "approved":
            return Response({"error": "Creator profile is already verified and approved."}, status=status.HTTP_400_BAD_REQUEST)
            
        document_type = request.data.get("document_type")
        document_front = request.FILES.get("document_front")
        document_back = request.FILES.get("document_back")
        other_details = request.data.get("other_details", "")
        
        if not document_type or document_type not in ["nic", "passport", "driving_license"]:
            return Response({"error": "Invalid or missing document type. Allowed types: nic, passport, driving_license."}, status=status.HTTP_400_BAD_REQUEST)
            
        if not document_front or not document_back:
            return Response({"error": "Both front and back document files are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        profile.document_type = document_type
        profile.document_front = document_front
        profile.document_back = document_back
        profile.other_details = other_details
        profile.verification_documents_submitted = True
        profile.save()
        
        # Create Admin Notification
        Notification.objects.create(
            title="Creator Verification Submitted",
            message=f"Creator '{request.user.username}' submitted verification documents ({document_type.upper()}) for admin review.",
            category="compliance",
            icon="fas fa-id-card",
            target_url=f"/admin/creatorprofile/inspect/{profile.id}/"
        )

        
        return Response(CreatorProfileSerializer(profile).data, status=status.HTTP_200_OK)


from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_staff)
def admin_approve_business_view(request, profile_id):
    profile = get_object_or_404(BusinessProfile, pk=profile_id)
    profile.status = "approved"
    profile.save()
    send_status_update_email(profile.user, "approved", "business")
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
    send_status_update_email(profile.user, "restricted", "business")
    messages.warning(request, f"Business '{profile.company_name or profile.user.username}' has been restricted.")
    try:
        from django.urls import reverse
        inspect_url = reverse("businessprofile:inspect", args=[profile_id])
        return redirect(inspect_url)
    except Exception:
        return redirect("/admin/businessprofile/")

@user_passes_test(lambda u: u.is_staff)
def admin_approve_creator_view(request, profile_id):
    profile = get_object_or_404(CreatorProfile, pk=profile_id)
    profile.status = "approved"
    profile.save()
    send_status_update_email(profile.user, "approved", "creator")
    messages.success(request, f"Creator '{profile.user.username}' has been successfully approved.")
    try:
        from django.urls import reverse
        inspect_url = reverse("creatorprofile:inspect", args=[profile_id])
        return redirect(inspect_url)
    except Exception:
        return redirect("/admin/creatorprofile/")

@user_passes_test(lambda u: u.is_staff)
def admin_restrict_creator_view(request, profile_id):
    profile = get_object_or_404(CreatorProfile, pk=profile_id)
    profile.status = "restricted"
    profile.save()
    send_status_update_email(profile.user, "restricted", "creator")
    messages.warning(request, f"Creator '{profile.user.username}' has been restricted.")
    try:
        from django.urls import reverse
        inspect_url = reverse("creatorprofile:inspect", args=[profile_id])
        return redirect(inspect_url)
    except Exception:
        return redirect("/admin/creatorprofile/")


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


@user_passes_test(lambda u: u.is_staff)
def admin_toggle_featured_view(request, profile_type, profile_id):
    if profile_type == "creator":
        profile = get_object_or_404(CreatorProfile, pk=profile_id)
        if request.method == "POST":
            profile.is_featured = (request.POST.get("is_featured") == "on")
        else:
            profile.is_featured = not profile.is_featured
        profile.save()
        status_msg = "featured (Top Creator)" if profile.is_featured else "removed from featured"
        messages.success(request, f"Creator '{profile.user.username}' is now {status_msg}.")
        redirect_url_name = "creatorprofile:inspect"
        fallback_url = "/admin/creatorprofile/"
    else:
        profile = get_object_or_404(BusinessProfile, pk=profile_id)
        if request.method == "POST":
            profile.is_featured = (request.POST.get("is_featured") == "on")
        else:
            profile.is_featured = not profile.is_featured
        profile.save()
        status_msg = "featured (Top Business)" if profile.is_featured else "removed from featured"
        messages.success(request, f"Business '{profile.company_name or profile.user.username}' is now {status_msg}.")
        redirect_url_name = "businessprofile:inspect"
        fallback_url = "/admin/businessprofile/"

    try:
        from django.urls import reverse
        return redirect(reverse(redirect_url_name, args=[profile_id]))
    except Exception:
        return redirect(fallback_url)


from wagtail.users.views.users import (
    UserViewSet as WagtailUserViewSet,
    IndexView as WagtailUserIndexView,
    EditView as WagtailUserEditView,
    DeleteView as WagtailUserDeleteView,
)

class CustomUserIndexView(WagtailUserIndexView):
    def get_base_queryset(self):
        qs = super().get_base_queryset()
        # Filter out users who have an associated Business or Creator profile.
        # This keeps the Settings > Users admin list restricted to staff, superusers, and manually-added admin accounts.
        return qs.filter(business_profile__isnull=True, creator_profile__isnull=True)

class CustomUserEditView(WagtailUserEditView):
    def get_queryset(self):
        qs = super().get_queryset()
        # Filter out users who have an associated Business or Creator profile.
        return qs.filter(business_profile__isnull=True, creator_profile__isnull=True)

class CustomUserDeleteView(WagtailUserDeleteView):
    def get_queryset(self):
        qs = super().get_queryset()
        # Filter out users who have an associated Business or Creator profile.
        return qs.filter(business_profile__isnull=True, creator_profile__isnull=True)

class CustomUserViewSet(WagtailUserViewSet):
    index_view_class = CustomUserIndexView
    edit_view_class = CustomUserEditView
    delete_view_class = CustomUserDeleteView



