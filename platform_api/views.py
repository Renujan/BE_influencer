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
    Niche, UserProfile, CreatorSocialAccount, Campaign, CampaignTask,
    CampaignMilestone, Deliverable, PaymentInstallment, WorkspaceFile,
    WorkspaceMessage, AdminComplianceTicket
)
from .serializers import (
    NicheSerializer, UserProfileSerializer, CampaignSerializer,
    WorkspaceMessageSerializer, WorkspaceFileSerializer, DeliverableSerializer,
    AdminComplianceTicketSerializer, PaymentInstallmentSerializer
)

class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.filter(email=email).first()
        if not user:
            # Let's create a temporary user or profile if they don't exist yet,
            # but for onboarding, we typically send OTP after registering basics, or we let them verify email.
            # To support frictionless login/sign-up, let's create a placeholder user if not found.
            username = email.split("@")[0]
            # Ensure unique username
            original_username = username
            idx = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{idx}"
                idx += 1
            user = User.objects.create_user(username=username, email=email, password=User.objects.make_random_password())
            UserProfile.objects.create(user=user, role="influencer") # default role
        
        profile, created = UserProfile.objects.get_or_create(user=user)
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
        
        profile = user.profile
        if profile.otp_code == otp_code:
            profile.otp_verified = True
            profile.save()
            
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "message": "OTP verified successfully",
                "token": token.key,
                "role": profile.role,
                "profile": UserProfileSerializer(profile).data
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
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # Create profile
        profile = UserProfile.objects.create(
            user=user,
            role=role,
            phone=request.data.get("phone", ""),
            location=request.data.get("location", ""),
            bio=request.data.get("bio", ""),
            company_name=request.data.get("company_name", ""),
            business_type=request.data.get("business_type", ""),
            website=request.data.get("website", ""),
        )

        # Add niches for influencers
        if role == "influencer":
            niches_data = request.data.get("niches", [])
            for niche_name in niches_data:
                niche_obj, _ = Niche.objects.get_or_create(name=niche_name)
                profile.niches.add(niche_obj)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "role": role,
            "profile": UserProfileSerializer(profile).data
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username_or_email = request.data.get("username") or request.data.get("email")
        password = request.data.get("password")

        if not username_or_email or not password:
            return Response({"error": "Credentials are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Try authenticating by username first
        user = authenticate(username=username_or_email, password=password)
        
        # Try by email if username auth fails
        if not user:
            user_obj = User.objects.filter(email=username_or_email).first()
            if user_obj:
                user = authenticate(username=user_obj.username, password=password)

        if not user:
            return Response({"error": "Invalid username/email or password"}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        profile = getattr(user, "profile", None)
        role = profile.role if profile else "influencer"

        return Response({
            "token": token.key,
            "role": role,
            "profile": UserProfileSerializer(profile).data if profile else None
        })

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data)

    def put(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user = request.user
        
        # Basic fields
        user.first_name = request.data.get("first_name", user.first_name)
        user.last_name = request.data.get("last_name", user.last_name)
        user.save()

        profile.phone = request.data.get("phone", profile.phone)
        profile.bio = request.data.get("bio", profile.bio)
        profile.location = request.data.get("location", profile.location)
        profile.avatar_url = request.data.get("avatar_url", profile.avatar_url)

        if profile.role == "business":
            profile.company_name = request.data.get("company_name", profile.company_name)
            profile.business_type = request.data.get("business_type", profile.business_type)
            profile.website = request.data.get("website", profile.website)
        
        profile.save()
        return Response(UserProfileSerializer(profile).data)

class NicheViewSet(viewsets.ModelViewSet):
    queryset = Niche.objects.all()
    serializer_class = NicheSerializer
    permission_classes = [permissions.AllowAny]

class CreatorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserProfile.objects.filter(role="influencer")
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filtering parameters
        niche = self.request.query_params.get("niche")
        location = self.request.query_params.get("location")
        er_min = self.request.query_params.get("er_min")
        followers_min = self.request.query_params.get("followers_min")
        rate_max = self.request.query_params.get("rate_max")
        approved_only = self.request.query_params.get("approved_only")

        if niche and niche.lower() != "all":
            qs = qs.filter(niches__name__iexact=niche)
        
        if location:
            qs = qs.filter(location__icontains=location)

        if er_min:
            qs = qs.filter(user__social_accounts__engagement_rate__gte=float(er_min))

        if rate_max:
            qs = qs.filter(average_rate__lte=float(rate_max))

        if approved_only and approved_only.lower() == "true":
            qs = qs.filter(is_approved=True)

        return qs.distinct()

class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, "profile", None)
        if not profile:
            return Campaign.objects.none()

        if profile.role == "business":
            return Campaign.objects.filter(brand=user)
        else:
            return Campaign.objects.filter(creator=user)

    def perform_create(self, serializer):
        campaign = serializer.save(brand=self.request.user)
        
        # Auto create default tasks for this campaign
        CampaignTask.objects.create(campaign=campaign, title="Brief approval", is_done=True)
        CampaignTask.objects.create(campaign=campaign, title="Content moodboard", is_done=True)
        CampaignTask.objects.create(campaign=campaign, title="Draft #1 review", is_done=False, due_date="May 14")
        CampaignTask.objects.create(campaign=campaign, title="Final delivery", is_done=False, due_date="May 18")

        # Auto create default milestones
        CampaignMilestone.objects.create(campaign=campaign, title="Kickoff", is_done=True)
        CampaignMilestone.objects.create(campaign=campaign, title="Drafts approved", is_done=True)
        CampaignMilestone.objects.create(campaign=campaign, title="Content live", is_done=False)
        CampaignMilestone.objects.create(campaign=campaign, title="Final payout", is_done=False)

        # Auto create default escrow payments
        PaymentInstallment.objects.create(campaign=campaign, milestone_name="Kickoff payment", amount=1000, status="Released", payment_date="May 02")
        PaymentInstallment.objects.create(campaign=campaign, milestone_name="Drafts approved", amount=1500, status="Released", payment_date="May 10")
        PaymentInstallment.objects.create(campaign=campaign, milestone_name="Final delivery", amount=campaign.budget - 2500, status="In Escrow")

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        campaign = self.get_object()
        text = request.data.get("text")
        if not text:
            return Response({"error": "Text is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        import datetime
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        
        message = WorkspaceMessage.objects.create(
            campaign=campaign,
            sender=request.user,
            text=text,
            time=time_str
        )
        return Response(WorkspaceMessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def upload_file(self, request, pk=None):
        campaign = self.get_object()
        file_name = request.data.get("name")
        file_size = request.data.get("size", "2.5 MB")
        if not file_name:
            return Response({"error": "File name is required"}, status=status.HTTP_400_BAD_REQUEST)

        import datetime
        now = datetime.datetime.now()
        date_str = now.strftime("%b %d, %Y")
        time_str = now.strftime("%I:%M %p")

        ws_file = WorkspaceFile.objects.create(
            campaign=campaign,
            name=file_name,
            size=file_size,
            sender=request.user,
            date=date_str,
            time=time_str
        )
        return Response(WorkspaceFileSerializer(ws_file).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit_deliverable(self, request, pk=None):
        campaign = self.get_object()
        del_id = request.data.get("deliverable_id")
        link = request.data.get("link")
        screenshot_name = request.data.get("screenshot_name", "analytics_screenshot.png")

        if not del_id or not link:
            return Response({"error": "deliverable_id and link are required"}, status=status.HTTP_400_BAD_REQUEST)

        deliverable = get_object_or_404(Deliverable, campaign=campaign, id=del_id)
        deliverable.link = link
        deliverable.screenshot_name = screenshot_name
        deliverable.status = "Published"
        deliverable.save()

        return Response(DeliverableSerializer(deliverable).data)

    @action(detail=True, methods=["post"])
    def review_deliverable(self, request, pk=None):
        campaign = self.get_object()
        del_id = request.data.get("deliverable_id")
        status_action = request.data.get("status") # Approved or Revision Requested

        if not del_id or not status_action:
            return Response({"error": "deliverable_id and status are required"}, status=status.HTTP_400_BAD_REQUEST)

        deliverable = get_object_or_404(Deliverable, campaign=campaign, id=del_id)
        deliverable.status = status_action
        deliverable.save()

        # Update progression based on deliverables
        total_dels = campaign.deliverables.count()
        if total_dels > 0:
            approved_dels = campaign.deliverables.filter(status="Approved").count()
            campaign.progress = int((approved_dels / total_dels) * 100)
            campaign.save()

        return Response(DeliverableSerializer(deliverable).data)

    @action(detail=True, methods=["post"])
    def file_ticket(self, request, pk=None):
        campaign = self.get_object()
        category = request.data.get("category")
        message = request.data.get("message")
        if not category or not message:
            return Response({"error": "Category and message are required"}, status=status.HTTP_400_BAD_REQUEST)

        ticket = AdminComplianceTicket.objects.create(
            campaign=campaign,
            category=category,
            message=message,
            status="Pending Review",
            reply="Our specialists will audit the campaign context and chat logs."
        )
        return Response(AdminComplianceTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.filter(status="Pending")
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, "profile", None)
        if not profile:
            return Campaign.objects.none()

        if profile.role == "business":
            return Campaign.objects.filter(brand=user, status="Pending")
        else:
            return Campaign.objects.filter(creator=user, status="Pending")

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = "Live"
        campaign.progress = 62 # set to default mockup progression
        campaign.save()
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        campaign = self.get_object()
        campaign.delete()
        return Response({"message": "Request successfully declined"})
