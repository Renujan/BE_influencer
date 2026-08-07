from io import BytesIO
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from xhtml2pdf import pisa
from campegin.models import Campaign, WorkspaceMessage
from .models import ChatReview
from .serializers import CampaignChatSerializer, WorkspaceMessageSerializer, ChatReviewSerializer
import datetime


@staff_member_required
def chat_monitor_detail_view(request, campaign_id):
    """Comprehensive detail page: chat history + campaign info + business & creator profiles."""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    # Show all workspace chat messages including main, creator and business admin support channels
    messages = campaign.messages.all().order_by("id")
    # Auto-sync user submitted compliance tickets into ChatReview if missing
    for t in campaign.tickets.all():
        s_role = getattr(t, "sender_role", "both") or "both"
        if s_role == "admin":
            continue
        s_name = getattr(t, "sender_name", "") or (t.sender.username if getattr(t, "sender", None) else "")
        prefix = f"[{s_role.upper()} REQUEST{' by ' + s_name if s_name else ''}]"
        expected_text = f"{prefix} {t.message}"
        if not ChatReview.objects.filter(campaign=campaign, review_text=t.message).exists() and not ChatReview.objects.filter(campaign=campaign, review_text=expected_text).exists():
            ChatReview.objects.create(
                campaign=campaign,
                category=t.category or "Safety / Guidelines",
                review_text=expected_text,
                target_audience="creator" if s_role in ["creator", "influencer"] else ("business" if s_role == "business" else "both")
            )

    reviews = campaign.chat_reviews.all().order_by("-id")

    # Business profile
    business_profile = getattr(campaign.brand, "business_profile", None)
    business_social_accounts = campaign.brand.social_accounts.all() if campaign.brand else []

    # Creator profile
    creator_profile = None
    creator_social_accounts = []
    creator_rates = []
    if campaign.creator:
        creator_profile = getattr(campaign.creator, "creator_profile", None)
        creator_social_accounts = campaign.creator.social_accounts.all()
        if creator_profile:
            creator_rates = creator_profile.rates.all()

    # Campaign extras
    milestones = campaign.milestones.all()
    tasks = campaign.tasks.all()
    deliverables = campaign.deliverables.all()
    payments = campaign.payments.all()

    context = {
        "campaign": campaign,
        "chat_messages": messages,
        "reviews": reviews,
        "business_profile": business_profile,
        "business_social_accounts": business_social_accounts,
        "creator_profile": creator_profile,
        "creator_social_accounts": creator_social_accounts,
        "creator_rates": creator_rates,
        "milestones": milestones,
        "tasks": tasks,
        "deliverables": deliverables,
        "payments": payments,
    }
    return render(request, "chat_monitor/detail_view.html", context)


@user_passes_test(lambda u: u.is_staff)
def chat_monitor_download_pdf_view(request, campaign_id):
    """Generate a PDF report of the chat monitor detail page."""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    # Show all workspace chat messages
    messages = campaign.messages.all().order_by("id")
    reviews = campaign.chat_reviews.all().order_by("-id")

    business_profile = getattr(campaign.brand, "business_profile", None)
    business_social_accounts = campaign.brand.social_accounts.all() if campaign.brand else []

    creator_profile = None
    creator_social_accounts = []
    creator_rates = []
    if campaign.creator:
        creator_profile = getattr(campaign.creator, "creator_profile", None)
        creator_social_accounts = campaign.creator.social_accounts.all()
        if creator_profile:
            creator_rates = creator_profile.rates.all()

    milestones = campaign.milestones.all()
    tasks = campaign.tasks.all()
    deliverables = campaign.deliverables.all()
    payments = campaign.payments.all()

    context = {
        "campaign": campaign,
        "chat_messages": messages,
        "reviews": reviews,
        "business_profile": business_profile,
        "business_social_accounts": business_social_accounts,
        "creator_profile": creator_profile,
        "creator_social_accounts": creator_social_accounts,
        "creator_rates": creator_rates,
        "milestones": milestones,
        "tasks": tasks,
        "deliverables": deliverables,
        "payments": payments,
    }

    html = render_to_string("chat_monitor/chat_monitor_pdf.html", context, request=request)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type="application/pdf")
        filename = f"chat_monitor_{campaign.name.replace(' ', '_')}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    return HttpResponse("Error generating PDF", status=500)


# --- REST API ViewSet for workspace users (Business & Creator) ---

class CampaignChatsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CampaignChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Filter campaigns where the current user is either the brand or the creator
        return Campaign.objects.filter(brand=user) | Campaign.objects.filter(creator=user)

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        campaign = get_object_or_404(Campaign, id=pk)
        
        # Security: verify user is part of the campaign
        if campaign.brand != request.user and campaign.creator != request.user:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        if request.method == "POST":
            text = request.data.get("text", "")
            file_attachment = request.data.get("file_attachment", "")
            if not text and not file_attachment:
                return Response({"error": "Message text or file attachment is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            now = datetime.datetime.now()
            time_str = now.strftime("%H:%M")
            
            msg = WorkspaceMessage.objects.create(
                campaign=campaign,
                sender=request.user,
                text=text,
                file_attachment=file_attachment,
                time=time_str
            )
            return Response(WorkspaceMessageSerializer(msg).data, status=status.HTTP_201_CREATED)
        else:
            # GET: return all messages ordered by ID
            msgs = campaign.messages.filter(message_type="main").order_by("id")
            return Response(WorkspaceMessageSerializer(msgs, many=True).data)

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        campaign = get_object_or_404(Campaign, id=pk)
        
        # Security: verify user is part of the campaign
        if campaign.brand != request.user and campaign.creator != request.user:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
            
        is_creator = (request.user == campaign.creator or (campaign.creator and request.user.id == campaign.creator.id) or hasattr(request.user, "creator_profile"))
        
        if is_creator:
            reviews_qs = campaign.chat_reviews.filter(
                models.Q(target_audience__iexact="creator") |
                models.Q(target_audience__iexact="influencer") |
                models.Q(target_audience__iexact="both") |
                models.Q(target_audience="") |
                models.Q(target_audience__isnull=True)
            ).order_by("-id")
        else:
            reviews_qs = campaign.chat_reviews.filter(
                models.Q(target_audience__iexact="business") |
                models.Q(target_audience__iexact="both") |
                models.Q(target_audience="") |
                models.Q(target_audience__isnull=True)
            ).order_by("-id")
            
        return Response(ChatReviewSerializer(reviews_qs, many=True).data)


# --- Wagtail Admin Custom Page Views for View Chat & Reviews ---

@staff_member_required
def chat_monitor_view_chat_view(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    # Show all workspace chat messages
    messages = campaign.messages.all().order_by("id")
    context = {
        "campaign": campaign,
        "chat_messages": messages,
    }
    return render(request, "chat_monitor/view_chat.html", context)

@staff_member_required
def chat_monitor_review_view(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if request.method == "POST":
        action = request.POST.get("action", "create")
        review_id = request.POST.get("review_id")

        if action == "delete" and review_id:
            rev = ChatReview.objects.filter(id=review_id, campaign=campaign).first()
            if rev:
                raw_text = rev.review_text
                # Delete any associated AdminComplianceTicket so auto-sync will not recreate it
                for t in campaign.tickets.all():
                    s_role = getattr(t, "sender_role", "both") or "both"
                    s_name = getattr(t, "sender_name", "") or (t.sender.username if getattr(t, "sender", None) else "")
                    prefix = f"[{s_role.upper()} REQUEST{' by ' + s_name if s_name else ''}]"
                    expected_text = f"{prefix} {t.message}"
                    
                    if (t.message == raw_text or 
                        expected_text == raw_text or 
                        f"Directive: {raw_text}" == t.message or
                        t.reply == raw_text or
                        (raw_text and raw_text.endswith(t.message))):
                        t.delete()

                rev.delete()
            return redirect(reverse("chat_monitor_review", args=[campaign.id]))

        if action == "edit" and review_id:
            rev = ChatReview.objects.filter(id=review_id, campaign=campaign).first()
            if rev:
                old_text = rev.review_text
                new_text = request.POST.get("review_text", rev.review_text)
                new_category = request.POST.get("category", rev.category)
                new_target = request.POST.get("target_audience", rev.target_audience)
                
                rev.review_text = new_text
                rev.category = new_category
                rev.target_audience = new_target
                rev.save()

                # Update matching AdminComplianceTicket if exists
                for t in campaign.tickets.all():
                    if t.reply == old_text or t.message == f"Directive: {old_text}" or old_text.endswith(t.message):
                        t.category = new_category
                        t.target_audience = new_target
                        t.message = f"Directive: {new_text}"
                        t.reply = new_text
                        t.save()

            return redirect(reverse("chat_monitor_review", args=[campaign.id]))

        category = request.POST.get("category", "Safety / Guidelines")
        target_audience = request.POST.get("target_audience", "both")
        review_text = request.POST.get("review_text", "")
        
        if review_text:
            ChatReview.objects.create(
                campaign=campaign,
                category=category,
                target_audience=target_audience,
                review_text=review_text
            )
            from campegin.models import AdminComplianceTicket
            AdminComplianceTicket.objects.create(
                campaign=campaign,
                category=category,
                message=f"Directive: {review_text}",
                status="Admin Determination",
                reply=review_text,
                sender_role="admin",
                target_audience=target_audience
            )
            return redirect(reverse("chat_monitor_review", args=[campaign.id]))

    # Auto-sync user submitted compliance tickets into ChatReview if missing
    for t in campaign.tickets.all():
        s_role = getattr(t, "sender_role", "both") or "both"
        if s_role == "admin":
            continue
        s_name = getattr(t, "sender_name", "") or (t.sender.username if getattr(t, "sender", None) else "")
        prefix = f"[{s_role.upper()} REQUEST{' by ' + s_name if s_name else ''}]"
        expected_text = f"{prefix} {t.message}"
        if not ChatReview.objects.filter(campaign=campaign, review_text=t.message).exists() and not ChatReview.objects.filter(campaign=campaign, review_text=expected_text).exists():
            ChatReview.objects.create(
                campaign=campaign,
                category=t.category or "Safety / Guidelines",
                review_text=expected_text,
                target_audience="creator" if s_role in ["creator", "influencer"] else ("business" if s_role == "business" else "both")
            )

    all_reviews = campaign.chat_reviews.all().order_by("-id")
    user_requests = []
    admin_directives = []

    for r in all_reviews:
        text = r.review_text or ""
        if text.startswith("[CREATOR REQUEST") or text.startswith("[INFLUENCER REQUEST") or text.startswith("[BUSINESS REQUEST"):
            user_requests.append(r)
        else:
            admin_directives.append(r)

    context = {
        "campaign": campaign,
        "reviews": all_reviews,
        "user_requests": user_requests,
        "admin_directives": admin_directives,
    }
    return render(request, "chat_monitor/review_chat.html", context)
