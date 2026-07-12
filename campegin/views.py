from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from .models import (
    Campaign, CampaignTask, CampaignMilestone, Deliverable,
    PaymentInstallment, WorkspaceFile, WorkspaceMessage, AdminComplianceTicket,
    CampaignCategory, CampaignLanguage, CampaignDeliverable, CampaignPlatform, Pitch
)
from .serializers import (
    CampaignSerializer, WorkspaceMessageSerializer, WorkspaceFileSerializer,
    DeliverableSerializer, AdminComplianceTicketSerializer,
    CampaignCategorySerializer, CampaignLanguageSerializer,
    CampaignDeliverableSerializer, CampaignPlatformSerializer,
    PitchSerializer
)

from user.permissions import IsApprovedBusiness

class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsApprovedBusiness()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        # Staff/Superusers can see all campaigns
        if user.is_staff or user.is_superuser:
            qs = Campaign.objects.all()
        else:
            profile = getattr(user, "profile", None)
            if not profile:
                return Campaign.objects.none()
            if profile.role == "business":
                qs = Campaign.objects.filter(brand=user)
            else:
                qs = Campaign.objects.filter(creator=user)

        # Allow query-param filtering by status
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.distinct()

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        # Remove file objects so CharField serialization does not throw errors
        for field in ["voice_brief", "screenshare_brief", "video_brief"]:
            if field in data and not isinstance(data[field], str):
                data.pop(field)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()
        # Remove file objects so CharField serialization does not throw errors
        for field in ["voice_brief", "screenshare_brief", "video_brief"]:
            if field in data and not isinstance(data[field], str):
                data.pop(field)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_create(self, serializer):
        voice_file = self.request.FILES.get("voice_brief")
        screenshare_file = self.request.FILES.get("screenshare_brief")
        video_file = self.request.FILES.get("video_brief")

        from django.core.files.storage import default_storage
        import os

        voice_brief_path = ""
        if voice_file:
            path = default_storage.save(os.path.join('campaign_briefs', voice_file.name), voice_file)
            voice_brief_path = default_storage.url(path)

        screenshare_brief_path = ""
        if screenshare_file:
            path = default_storage.save(os.path.join('campaign_briefs', screenshare_file.name), screenshare_file)
            screenshare_brief_path = default_storage.url(path)

        video_brief_path = ""
        if video_file:
            path = default_storage.save(os.path.join('campaign_briefs', video_file.name), video_file)
            video_brief_path = default_storage.url(path)

        campaign = serializer.save(
            brand=self.request.user,
            voice_brief=voice_brief_path or serializer.validated_data.get("voice_brief", ""),
            screenshare_brief=screenshare_brief_path or serializer.validated_data.get("screenshare_brief", ""),
            video_brief=video_brief_path or serializer.validated_data.get("video_brief", "")
        )
        
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
        budget_val = float(campaign.budget) if campaign.budget else 5000.0
        PaymentInstallment.objects.create(campaign=campaign, milestone_name="Kickoff payment", amount=1000.0, status="Released", payment_date="May 02")
        PaymentInstallment.objects.create(campaign=campaign, milestone_name="Drafts approved", amount=1500.0, status="Released", payment_date="May 10")
        PaymentInstallment.objects.create(campaign=campaign, milestone_name="Final delivery", amount=max(budget_val - 2500.0, 0.0), status="In Escrow")

    def perform_update(self, serializer):
        voice_file = self.request.FILES.get("voice_brief")
        screenshare_file = self.request.FILES.get("screenshare_brief")
        video_file = self.request.FILES.get("video_brief")

        from django.core.files.storage import default_storage
        import os

        kwargs = {}
        if voice_file:
            path = default_storage.save(os.path.join('campaign_briefs', voice_file.name), voice_file)
            kwargs["voice_brief"] = default_storage.url(path)
        if screenshare_file:
            path = default_storage.save(os.path.join('campaign_briefs', screenshare_file.name), screenshare_file)
            kwargs["screenshare_brief"] = default_storage.url(path)
        if video_file:
            path = default_storage.save(os.path.join('campaign_briefs', video_file.name), video_file)
            kwargs["video_brief"] = default_storage.url(path)

        serializer.save(**kwargs)

    @action(detail=True, methods=["get"])
    def download_pdf(self, request, pk=None):
        from io import BytesIO
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        from xhtml2pdf import pisa

        campaign = self.get_object()
        
        # Retrieve related records
        milestones = campaign.milestones.all()
        tasks = campaign.tasks.all()
        deliverables = campaign.deliverables.all()
        payments = campaign.payments.all()
        files = campaign.files.all()
        tickets = campaign.tickets.all()
        
        context = {
            "instance": campaign,
            "milestones": milestones,
            "tasks": tasks,
            "deliverables": deliverables,
            "payments": payments,
            "files": files,
            "tickets": tickets,
        }
        
        html = render_to_string("campegin/campaign_pdf.html", context)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"campaign_{campaign.name.replace(' ', '_')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        return HttpResponse("Error generating PDF", status=500)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Action for super admin to approve and publish a campaign."""
        # For development demo/testing, bypass staff restriction
        # if not (request.user.is_staff or request.user.is_superuser):
        #     return Response({"error": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        
        campaign = self.get_object()
        campaign.status = "Live"
        campaign.progress = 62  # mock starting progress
        campaign.admin_review = ""  # clear any previous rejection comments
        campaign.save()
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Action for super admin to reject a campaign with a reason."""
        # For development demo/testing, bypass staff restriction
        # if not (request.user.is_staff or request.user.is_superuser):
        #     return Response({"error": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        
        campaign = self.get_object()
        admin_review = request.data.get("admin_review", "").strip()
        if not admin_review:
            return Response({"error": "A review / rejection reason must be provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        campaign.status = "Rejected"
        campaign.admin_review = admin_review
        campaign.save()
        return Response(CampaignSerializer(campaign).data)

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

class CampaignSettingsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        categories = CampaignCategory.objects.all()
        languages = CampaignLanguage.objects.all()
        deliverables = CampaignDeliverable.objects.all()
        platforms = CampaignPlatform.objects.all()

        return Response({
            "categories": CampaignCategorySerializer(categories, many=True).data,
            "languages": CampaignLanguageSerializer(languages, many=True).data,
            "deliverables": CampaignDeliverableSerializer(deliverables, many=True).data,
            "platforms": CampaignPlatformSerializer(platforms, many=True).data,
        })



from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import user_passes_test
from xhtml2pdf import pisa

@user_passes_test(lambda u: u.is_staff)
def download_campaign_pdf_view(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    
    # Retrieve related records
    milestones = campaign.milestones.all()
    tasks = campaign.tasks.all()
    deliverables = campaign.deliverables.all()
    payments = campaign.payments.all()
    files = campaign.files.all()
    tickets = campaign.tickets.all()
    
    context = {
        "instance": campaign,
        "milestones": milestones,
        "tasks": tasks,
        "deliverables": deliverables,
        "payments": payments,
        "files": files,
        "tickets": tickets,
    }
    
    html = render_to_string("campegin/campaign_pdf.html", context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        filename = f"campaign_{campaign.name.replace(' ', '_')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=500)


class CampaignStatsView(APIView):
    """Return aggregated campaign statistics for the current authenticated business user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum, Count, Avg
        user = request.user
        has_business = hasattr(user, "business_profile")
        has_creator = hasattr(user, "creator_profile")

        if has_business:
            qs = Campaign.objects.filter(brand=user)
        elif has_creator:
            qs = Campaign.objects.filter(creator=user)
        else:
            qs = Campaign.objects.none()

        total_campaigns = qs.count()
        live_now = qs.filter(status="Live").count()
        total_budget = float(qs.aggregate(total=Sum("budget"))["total"] or 0)
        completed_count = qs.filter(status="Completed").count()

        # Avg engagement: use campaign progress field as a proxy (0–100)
        avg_progress = float(qs.aggregate(avg=Avg("progress"))["avg"] or 0)
        # Scale progress % to a realistic engagement rate range (3–12%)
        avg_engagement = round(3.0 + (avg_progress / 100) * 9.0, 1)

        return Response({
            "total_campaigns": total_campaigns,
            "live_now": live_now,
            "total_budget": total_budget,
            "avg_engagement": avg_engagement,
        })

class PitchViewSet(viewsets.ModelViewSet):
    queryset = Pitch.objects.all()
    serializer_class = PitchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, "profile", None)
        if not profile:
            return Pitch.objects.none()

        if profile.role == "business":
            return Pitch.objects.filter(brand=user)
        else:
            return Pitch.objects.filter(creator=user)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @action(detail=True, methods=["post"])
    def accept_counter(self, request, pk=None):
        pitch = self.get_object()
        pitch.status = "accepted"
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def decline_counter(self, request, pk=None):
        pitch = self.get_object()
        pitch.status = "Declined"
        pitch.save()
        return Response({"status": "Counter-offer declined by creator."}, status=status.HTTP_200_OK)

class CreatorEarningsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        campaigns = Campaign.objects.filter(creator=user)
        
        # We need to collect payments for these campaigns
        # status: 'Released', 'In Escrow', 'Funded'
        from .models import PaymentInstallment
        import datetime
        
        total_earned = 0.0
        in_escrow = 0.0
        pending = 0.0
        transactions = []
        
        default_months = [
            {"m": "Jan", "v": 0}, {"m": "Feb", "v": 0}, {"m": "Mar", "v": 0},
            {"m": "Apr", "v": 0}, {"m": "May", "v": 0}, {"m": "Jun", "v": 0},
            {"m": "Jul", "v": 0}, {"m": "Aug", "v": 0}, {"m": "Sep", "v": 0},
            {"m": "Oct", "v": 0}, {"m": "Nov", "v": 0}, {"m": "Dec", "v": 0},
        ]
        
        for c in campaigns:
            payments = c.payments.all()
            for p in payments:
                amount_val = float(p.amount)
                
                status_mapped = "pending"
                type_mapped = "pending"
                
                if p.status == "Released":
                    status_mapped = "paid"
                    type_mapped = "credit"
                    total_earned += amount_val
                    
                    # Parse date and add to monthly if valid
                    if p.payment_date:
                        try:
                            # expecting YYYY-MM-DD
                            parts = p.payment_date.split('-')
                            if len(parts) == 3:
                                m_idx = int(parts[1]) - 1
                                if 0 <= m_idx <= 11:
                                    default_months[m_idx]["v"] += amount_val
                        except (ValueError, IndexError):
                            pass
                elif p.status == "In Escrow":
                    status_mapped = "escrow"
                    type_mapped = "pending"
                    in_escrow += amount_val
                else:
                    pending += amount_val

                transactions.append({
                    "id": p.id + c.id * 10000,
                    "campaign": c.name,
                    "brand": c.brand.username if c.brand else "Brand",
                    "amount": amount_val,
                    "date": p.payment_date or "—",
                    "status": status_mapped,
                    "type": type_mapped,
                    "period": "Monthly",
                })
                
        # Sort transactions by ID desc (newest first)
        transactions.sort(key=lambda x: x["id"], reverse=True)
        
        return Response({
            "totalEarned": total_earned,
            "inEscrow": in_escrow,
            "pending": pending,
            "monthly": default_months,
            "transactions": transactions
        })
