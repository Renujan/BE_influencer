from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from campegin.models import Campaign
from .models import ChatMessage, ChatReview
from .serializers import CampaignChatSerializer, WorkspaceMessageSerializer, ChatReviewSerializer
import datetime


@staff_member_required
def chat_monitor_detail_view(request, campaign_id):
    """Comprehensive detail page: chat history + campaign info + business & creator profiles."""
    campaign = get_object_or_404(Campaign, id=campaign_id)
    messages = campaign.chat_messages.all().order_by("id")
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
        "messages": messages,
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
            
            msg = ChatMessage.objects.create(
                campaign=campaign,
                sender=request.user,
                text=text,
                file_attachment=file_attachment,
                time=time_str
            )
            return Response(WorkspaceMessageSerializer(msg).data, status=status.HTTP_201_CREATED)
        else:
            # GET: return all messages ordered by ID
            msgs = campaign.chat_messages.all().order_by("id")
            return Response(WorkspaceMessageSerializer(msgs, many=True).data)

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        campaign = get_object_or_404(Campaign, id=pk)
        
        # Security: verify user is part of the campaign
        if campaign.brand != request.user and campaign.creator != request.user:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
            
        # Filter reviews based on user role (business sees business/both; creator sees creator/both)
        profile = getattr(request.user, "profile", None)
        role = profile.role if profile else "influencer"
        
        if role == "business":
            reviews_qs = campaign.chat_reviews.filter(target_audience__in=["business", "both"]).order_by("-id")
        else:
            reviews_qs = campaign.chat_reviews.filter(target_audience__in=["creator", "both"]).order_by("-id")
            
        return Response(ChatReviewSerializer(reviews_qs, many=True).data)


# --- Wagtail Admin Custom Page Views for View Chat & Reviews ---

@staff_member_required
def chat_monitor_view_chat_view(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    messages = campaign.chat_messages.all().order_by("id")
    context = {
        "campaign": campaign,
        "messages": messages,
    }
    return render(request, "chat_monitor/view_chat.html", context)

@staff_member_required
def chat_monitor_review_view(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    reviews = campaign.chat_reviews.all().order_by("-id")

    if request.method == "POST":
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
            return redirect(reverse("chat_monitor_review", args=[campaign.id]))

    context = {
        "campaign": campaign,
        "reviews": reviews,
    }
    return render(request, "chat_monitor/review_chat.html", context)
