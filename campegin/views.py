from django.db import models
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
from notifications.models import Notification

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
            if hasattr(user, "business_profile"):
                qs = Campaign.objects.filter(brand=user)
            elif hasattr(user, "creator_profile"):
                qs = Campaign.objects.filter(creator=user).exclude(status="Under_Review")
            else:
                qs = Campaign.objects.none()

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

        import json
        deliverables_json = self.request.data.get("deliverables")
        if deliverables_json:
            try:
                deliverables_list = json.loads(deliverables_json)
                for item in deliverables_list:
                    del_name = item.get("text", "Deliverable")[:255]
                    Deliverable.objects.create(
                        campaign=campaign,
                        name=del_name,
                        type="post",
                        brief=item.get("brief", "")
                    )
                    # Automatically add business custom deliverable to Super Admin CampaignDeliverables options list
                    clean_name = del_name.split(" × ", 1)[-1].strip() if " × " in del_name else del_name.strip()
                    if clean_name:
                        CampaignDeliverable.objects.get_or_create(name=clean_name)
            except Exception as e:
                print("Error parsing deliverables:", e)

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

        campaign = serializer.save(**kwargs)

        import json
        deliverables_json = self.request.data.get("deliverables")
        if deliverables_json:
            try:
                deliverables_list = json.loads(deliverables_json)
                campaign.deliverables.all().delete()
                for item in deliverables_list:
                    del_name = item.get("text", "Deliverable")[:255]
                    Deliverable.objects.create(
                        campaign=campaign,
                        name=del_name,
                        type="post",
                        brief=item.get("brief", "")
                    )
                    # Automatically add business custom deliverable to Super Admin CampaignDeliverables options list
                    clean_name = del_name.split(" × ", 1)[-1].strip() if " × " in del_name else del_name.strip()
                    if clean_name:
                        CampaignDeliverable.objects.get_or_create(name=clean_name)
            except Exception as e:
                print("Error parsing deliverables:", e)

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
        if campaign.creator:
            campaign.status = "Pending"
        else:
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
        message_type = request.data.get("message_type", "main")
        
        if not text:
            return Response({"error": "Text is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        user = request.user
        
        # Enforce message type rules
        if not (user.is_staff or user.is_superuser):
            if hasattr(user, "creator_profile") and message_type not in ["main", "admin_creator"]:
                message_type = "main"
            elif hasattr(user, "business_profile") and message_type not in ["main", "admin_business"]:
                message_type = "main"
        
        import datetime
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        
        message = WorkspaceMessage.objects.create(
            campaign=campaign,
            sender=user,
            text=text,
            message_type=message_type,
            time=time_str
        )
        return Response(WorkspaceMessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def edit_message(self, request, pk=None):
        campaign = self.get_object()
        message_id = request.data.get("message_id")
        text = request.data.get("text")
        if not message_id or not text:
            return Response({"error": "message_id and text are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            message = WorkspaceMessage.objects.get(id=message_id, campaign=campaign, sender=request.user)
            message.text = text
            message.save()
            return Response(WorkspaceMessageSerializer(message).data)
        except WorkspaceMessage.DoesNotExist:
            return Response({"error": "Message not found or you don't have permission to edit it"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"])
    def delete_message(self, request, pk=None):
        campaign = self.get_object()
        message_id = request.data.get("message_id")
        if not message_id:
            return Response({"error": "message_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            message = WorkspaceMessage.objects.get(id=message_id, campaign=campaign, sender=request.user)
            message.delete()
            return Response({"status": "deleted"}, status=status.HTTP_200_OK)
        except WorkspaceMessage.DoesNotExist:
            return Response({"error": "Message not found or you don't have permission to delete it"}, status=status.HTTP_404_NOT_FOUND)

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
        
        # Determine if this is a final post or a draft
        link = request.data.get("link")
        screenshot_name = request.data.get("screenshot_name", "")
        assetDriveLink = request.data.get("assetDriveLink")
        assetFileName = request.data.get("assetFileName", "")
        views = request.data.get("views")
        reach = request.data.get("reach")
        er = request.data.get("er")

        if not del_id:
            return Response({"error": "deliverable_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        deliverable = get_object_or_404(Deliverable, campaign=campaign, id=del_id)
        
        if link or screenshot_name:
            if link:
                deliverable.link = link
            if screenshot_name:
                deliverable.screenshot_name = screenshot_name
            deliverable.status = "Published"
        elif assetDriveLink or assetFileName:
            if assetDriveLink:
                deliverable.assetDriveLink = assetDriveLink
            if assetFileName:
                deliverable.assetFileName = assetFileName
            deliverable.status = "Pending Review"

        if views is not None:
            deliverable.views = views
        if reach is not None:
            deliverable.reach = reach
        if er is not None:
            deliverable.er = er
            
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
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        status_param = self.request.query_params.get("status")

        if user.is_staff or user.is_superuser:
            if status_param:
                statuses = [s.strip() for s in status_param.split(",")]
                return Campaign.objects.filter(status__in=statuses)
            return Campaign.objects.all()

        if hasattr(user, "business_profile"):
            return Campaign.objects.filter(brand=user, status__in=["Pending", "Countered", "Business_Countered", "Business_Counter_Pending"])
        elif hasattr(user, "creator_profile"):
            return Campaign.objects.filter(creator=user, status__in=["Pending", "Countered", "Countered_Pending", "Business_Countered"])
        return Campaign.objects.none()

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        campaign = self.get_object()
        if campaign.status == "Business_Countered" and campaign.counter_price:
            campaign.budget = campaign.counter_price
        campaign.status = "Live"
        campaign.progress = 62 # set to default mockup progression
        campaign.save()
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        campaign = self.get_object()
        reason = request.data.get("reason") or request.data.get("note") or request.data.get("message") or "Campaign request declined."
        campaign.status = "Rejected"
        campaign.decline_reason = reason
        campaign.save()

        import datetime
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        
        WorkspaceMessage.objects.create(
            campaign=campaign,
            sender=request.user,
            text=f"Declined: {reason}",
            message_type="main",
            time=time_str
        )

        Notification.objects.create(
            title="Campaign Request Declined",
            message=f"Campaign '{campaign.name}' was declined. Reason: {reason}",
            category="campaign",
            icon="fas fa-times-circle",
            target_url=f"/admin/snippets/campegin/campaign/inspect/{campaign.id}/"
        )
        return Response({"message": "Request successfully declined", "status": "Rejected", "decline_reason": reason})

    @action(detail=True, methods=["post"])
    def counter(self, request, pk=None):
        campaign = self.get_object()
        if (campaign.counter_round or 0) >= 2:
            return Response({"error": "Maximum 2 counter offer rounds reached."}, status=status.HTTP_400_BAD_REQUEST)
        counter_price = request.data.get("price")
        counter_note = request.data.get("note")
        campaign.counter_price = counter_price
        campaign.counter_note = counter_note
        campaign.counter_round = (campaign.counter_round or 0) + 1
        campaign.status = "Countered_Pending"

        history = list(campaign.counter_history or [])
        history.append({
            "round": campaign.counter_round,
            "sender": "Creator",
            "sender_name": campaign.creator.username if campaign.creator else "Creator",
            "price": str(counter_price),
            "note": counter_note or "",
            "status": "Countered_Pending"
        })
        campaign.counter_history = history
        campaign.save()
        
        Notification.objects.create(
            title="Campaign Counter Offer",
            message=f"A creator counter offer was submitted for campaign '{campaign.name}'. Requires Admin Approval.",
            category="campaign",
            icon="fas fa-handshake",
            target_url=f"/admin/snippets/campegin/campaign/inspect/{campaign.id}/"
        )
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def accept_counter(self, request, pk=None):
        campaign = self.get_object()
        if campaign.counter_price:
            campaign.budget = campaign.counter_price
        campaign.status = "Live"
        campaign.progress = 62
        campaign.save()
        
        Notification.objects.create(
            title="Campaign Counter Accepted",
            message=f"The counter offer for campaign '{campaign.name}' was accepted. Campaign is now Live.",
            category="campaign",
            icon="fas fa-check-circle",
            target_url=f"/admin/snippets/campegin/campaign/inspect/{campaign.id}/"
        )
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def decline_counter(self, request, pk=None):
        campaign = self.get_object()
        reason = request.data.get("reason") or request.data.get("note") or request.data.get("message") or "Counter offer declined."
        campaign.status = "Rejected"
        campaign.decline_reason = reason
        campaign.save()

        import datetime
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        
        WorkspaceMessage.objects.create(
            campaign=campaign,
            sender=request.user,
            text=f"Declined Counter Offer: {reason}",
            message_type="main",
            time=time_str
        )
        
        Notification.objects.create(
            title="Campaign Counter Declined",
            message=f"The counter offer for campaign '{campaign.name}' was declined. Reason: {reason}",
            category="campaign",
            icon="fas fa-times-circle",
            target_url=f"/admin/snippets/campegin/campaign/inspect/{campaign.id}/"
        )
        return Response({"message": "Counter offer declined", "status": "Rejected", "decline_reason": reason})

    @action(detail=True, methods=["post"])
    def counter_reply(self, request, pk=None):
        campaign = self.get_object()
        counter_price = request.data.get("price")
        counter_note = request.data.get("note")
        campaign.counter_price = counter_price
        campaign.counter_note = counter_note
        campaign.status = "Business_Counter_Pending"

        history = list(campaign.counter_history or [])
        history.append({
            "round": campaign.counter_round or 1,
            "sender": "Business",
            "sender_name": campaign.brand.username if campaign.brand else "Business",
            "price": str(counter_price),
            "note": counter_note or "",
            "status": "Business_Counter_Pending"
        })
        campaign.counter_history = history
        campaign.save()
        
        Notification.objects.create(
            title="Campaign Counter Reply",
            message=f"A business reply counter offer was sent for campaign '{campaign.name}'. Requires Admin Approval.",
            category="campaign",
            icon="fas fa-exchange-alt",
            target_url=f"/admin/snippets/campegin/campaign/inspect/{campaign.id}/"
        )
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def admin_approve_counter(self, request, pk=None):
        campaign = self.get_object()
        if campaign.status in ["Countered_Pending", "Countered"]:
            campaign.status = "Countered"
        elif campaign.status in ["Business_Counter_Pending", "Business_Countered"]:
            campaign.status = "Business_Countered"
        else:
            campaign.status = "Countered"
        campaign.save()
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def admin_reject_counter(self, request, pk=None):
        campaign = self.get_object()
        reason = request.data.get("reason") or request.data.get("note") or "Counter offer rejected by admin."
        campaign.status = "Rejected"
        campaign.decline_reason = reason
        campaign.save()
        return Response({"message": "Counter offer rejected", "status": "Rejected", "decline_reason": reason})


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

    def post(self, request):
        name = request.data.get("name") or request.data.get("deliverable")
        if name and isinstance(name, str) and name.strip():
            raw_name = name.strip()
            clean_name = raw_name.split(" × ", 1)[-1].strip() if " × " in raw_name else raw_name
            obj, created = CampaignDeliverable.objects.get_or_create(name=clean_name)
            return Response({"id": obj.id, "name": obj.name, "created": created})
        return Response({"error": "Invalid deliverable name"}, status=status.HTTP_400_BAD_REQUEST)



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

        # Generate realistic metrics based on budget
        # Assume approx $1 = 1000 reach, 2500 impressions
        total_reach = int(total_budget * 1000)
        total_impressions = int(total_budget * 2500)
        # ROI proxy
        total_roi = 4.1 if total_budget > 0 else 0.0

        return Response({
            "total_campaigns": total_campaigns,
            "live_now": live_now,
            "total_budget": total_budget,
            "avg_engagement": avg_engagement,
            "total_reach": total_reach,
            "total_impressions": total_impressions,
            "total_roi": total_roi,
        })

class BusinessAnalyticsView(APIView):
    """Return aggregated business analytics and top campaigns."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum, Avg
        user = request.user
        qs = Campaign.objects.filter(brand=user)

        total_budget = float(qs.aggregate(total=Sum("budget"))["total"] or 0)
        avg_progress = float(qs.aggregate(avg=Avg("progress"))["avg"] or 0)
        avg_engagement = round(3.0 + (avg_progress / 100) * 9.0, 1)

        total_reach = int(total_budget * 1000)
        total_impressions = int(total_budget * 2500)
        total_roi = 4.1 if total_budget > 0 else 0.0

        # Top campaigns by engagement/progress
        top_campaigns_qs = qs.exclude(status="Pending").order_by("-progress")[:5]
        top_campaigns = []
        for c in top_campaigns_qs:
            er = round(3.0 + (c.progress / 100) * 9.0, 1) if c.progress else 6.5
            spend = float(c.budget or 0)
            reach_val = f"{round(spend/1000, 1)}M"
            top_campaigns.append({
                "name": c.name,
                "er": er,
                "reach": reach_val,
                "roi": "4.1x" if spend > 0 else "0x",
                "spend": spend,
                "trend": "up"
            })

        return Response({
            "stats": {
                "total_reach": total_reach,
                "total_impressions": total_impressions,
                "avg_engagement": avg_engagement,
                "total_roi": total_roi,
            },
            "top_campaigns": top_campaigns
        })

class PitchViewSet(viewsets.ModelViewSet):
    queryset = Pitch.objects.all()
    serializer_class = PitchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        status_param = self.request.query_params.get("status")

        if user.is_staff or user.is_superuser:
            if status_param:
                statuses = [s.strip() for s in status_param.split(",")]
                return Pitch.objects.filter(status__in=statuses)
            return Pitch.objects.all()

        if hasattr(user, "business_profile"):
            # Business ONLY sees pitches that are admin-approved and visible to them:
            return Pitch.objects.filter(
                brand=user,
                status__in=["pending", "pitch_countered", "biz_counter_pending", "biz_countered", "accepted_by_business", "accepted", "declined"]
            )
        elif hasattr(user, "creator_profile"):
            # Creator sees their sent pitches (all statuses)
            return Pitch.objects.filter(creator=user)
        return Pitch.objects.filter(models.Q(brand=user) | models.Q(creator=user))

    def create(self, request, *args, **kwargs):
        # Enforce 2 pitch requests per day limit for creator
        user = request.user
        if not (user.is_staff or user.is_superuser):
            from datetime import date
            today_str1 = date.today().strftime("%b %d, %Y")
            today_str2 = date.today().strftime("%Y-%m-%d")
            req_date = request.data.get("sent_date")

            query = Pitch.objects.filter(creator=user).filter(
                models.Q(sent_date=today_str1) |
                models.Q(sent_date=today_str2) |
                (models.Q(sent_date=req_date) if req_date else models.Q())
            )
            if query.count() >= 2:
                return Response(
                    {"error": "Daily request limit reached. Creators can only send a maximum of 2 pitch requests per day."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        attachment = self.request.FILES.get("attachment")
        if attachment:
            serializer.save(creator=self.request.user, attachment=attachment, status="pending_admin")
        else:
            serializer.save(creator=self.request.user, status="pending_admin")

    @action(detail=True, methods=["post"])
    def admin_approve(self, request, pk=None):
        """Admin approves initial pitch → forward to business (status: pending)"""
        pitch = self.get_object()
        pitch.status = "pending"
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def admin_reject(self, request, pk=None):
        """Admin rejects a pitch"""
        pitch = self.get_object()
        pitch.status = "declined"
        pitch.decline_reason = request.data.get("reason") or request.data.get("decline_reason") or "Pitch proposal rejected by admin."
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Business accepts pitch → status becomes accepted_by_business (pending admin conversion)"""
        pitch = self.get_object()
        pitch.status = "accepted_by_business"
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        """Decline pitch or counter offer with message"""
        pitch = self.get_object()
        pitch.status = "declined"
        pitch.decline_reason = request.data.get("reason") or request.data.get("decline_reason") or "Pitch proposal declined."
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def business_counter(self, request, pk=None):
        """Business sends counter offer → goes to biz_counter_pending (needs admin approval), max 2 rounds per side"""
        pitch = self.get_object()
        if pitch.counter_count >= 4:
            return Response({"error": "Counter offer limit reached. Maximum 2 counter offer rounds allowed."}, status=400)
        pitch.counter_count += 1
        pitch.status = "biz_counter_pending"
        offer_val = request.data.get("counter_offer") or request.data.get("counter_price")
        note_val = request.data.get("note") or request.data.get("counter_note") or ""
        pitch.counter_offer = offer_val
        pitch.counter_note = note_val

        history = list(pitch.counter_history or [])
        history.append({
            "round": pitch.counter_count,
            "sender": "Business",
            "sender_name": pitch.brand.username if pitch.brand else "Business",
            "price": str(offer_val),
            "note": note_val,
            "status": "biz_counter_pending"
        })
        pitch.counter_history = history
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def creator_counter(self, request, pk=None):
        """Creator sends counter offer → goes to pitch_counter_pending (needs admin approval), max 2 rounds per side"""
        pitch = self.get_object()
        if pitch.counter_count >= 4:
            return Response({"error": "Counter offer limit reached. Maximum 2 counter offer rounds allowed."}, status=400)
        pitch.counter_count += 1
        pitch.status = "pitch_counter_pending"
        offer_val = request.data.get("counter_offer") or request.data.get("counter_price")
        note_val = request.data.get("note") or request.data.get("counter_note") or ""
        pitch.counter_offer = offer_val
        pitch.counter_note = note_val

        history = list(pitch.counter_history or [])
        history.append({
            "round": pitch.counter_count,
            "sender": "Creator",
            "sender_name": pitch.creator.username if pitch.creator else "Creator",
            "price": str(offer_val),
            "note": note_val,
            "status": "pitch_counter_pending"
        })
        pitch.counter_history = history
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def convert_to_campaign(self, request, pk=None):
        """Business accepts pitch → create Live campaign with created_via=pitch"""
        pitch = self.get_object()
        pitch.status = "accepted"
        pitch.save()

        # Create Campaign created via pitch
        campaign = Campaign.objects.create(
            name=request.data.get("name") or pitch.campaign_name,
            brand=pitch.brand,
            creator=pitch.creator,
            budget=request.data.get("budget") or pitch.budget,
            brief=request.data.get("brief") or pitch.description or f"Campaign proposal based on pitch: {pitch.campaign_name}",
            status="Live",
            progress=62,
            start_date=request.data.get("start_date") or pitch.sent_date or "2026-08-01",
            created_via="pitch",
        )
        return Response({
            "message": "Pitch accepted and campaign created.",
            "pitch": PitchSerializer(pitch).data,
            "campaign_id": campaign.id
        })

    @action(detail=True, methods=["post"])
    def accept_counter(self, request, pk=None):
        pitch = self.get_object()
        pitch.status = "accepted_by_business"
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def decline_counter(self, request, pk=None):
        pitch = self.get_object()
        pitch.status = "declined"
        pitch.decline_reason = request.data.get("reason") or request.data.get("decline_reason") or "Counter offer declined."
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def decline_counter(self, request, pk=None):
        pitch = self.get_object()
        pitch.status = "declined"
        pitch.decline_reason = request.data.get("reason", "")
        pitch.save()
        return Response({"status": "Counter-offer declined."}, status=status.HTTP_200_OK)

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
