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
    CampaignCategory, CampaignLanguage, CampaignDeliverable, CampaignPlatform, Pitch, CampaignNiche
)
from .serializers import (
    CampaignSerializer, WorkspaceMessageSerializer, WorkspaceFileSerializer,
    DeliverableSerializer, AdminComplianceTicketSerializer,
    CampaignCategorySerializer, CampaignLanguageSerializer,
    CampaignDeliverableSerializer, CampaignPlatformSerializer,
    PitchSerializer, CampaignNicheSerializer
)
from notifications.models import Notification
from chat_monitor.models import ChatReview
from user.permissions import IsApprovedBusiness

def build_campaign_pdf_context(campaign, user=None):
    from WorkspacePayment.models import WorkspaceInstallment, WorkspacePaymentNegotiation
    from .models import extract_currency_symbol

    curr_sym = campaign.currency_symbol or extract_currency_symbol(campaign) or "$"
    
    # Check if viewer is a business user
    is_business = False
    if user:
        if hasattr(user, "business_profile") or user == campaign.brand or (not user.is_staff and not hasattr(user, "creator_profile")):
            is_business = True

    # Retrieve related records
    negotiation = campaign.payment_negotiations.first()
    
    inst_qs = campaign.workspace_installments.all()
    if not inst_qs.exists() and negotiation:
        inst_qs = negotiation.installments.all()

    if is_business:
        inst_qs = inst_qs.filter(installment_type="business")

    workspace_installments = list(inst_qs.order_by("installment_type", "id"))

    payments_list = []
    if workspace_installments:
        for inst in workspace_installments:
            inst_type_label = "Business (Inbound)" if inst.installment_type == "business" else "Creator (Outbound)"
            status_label = "Released" if (inst.is_paid or inst.status == "released") else ("In Escrow" if inst.status == "in_escrow" else inst.status.replace("_", " ").title())
            p_date = inst.paid_date.strftime("%b %d, %Y") if inst.paid_date else "-"
            payments_list.append({
                "milestone_name": inst.title,
                "title": inst.title,
                "type_label": inst_type_label,
                "amount": inst.amount,
                "payment_date": p_date,
                "paid_date": p_date,
                "status": status_label,
                "status_display": status_label,
                "status_lower": str(inst.status).lower(),
                "is_paid": bool(inst.is_paid or inst.status == "released"),
            })
    elif campaign.payments.exists():
        for pay in campaign.payments.all():
            payments_list.append({
                "milestone_name": pay.milestone_name,
                "title": pay.milestone_name,
                "type_label": "General",
                "amount": pay.amount,
                "payment_date": pay.payment_date or "-",
                "paid_date": pay.payment_date or "-",
                "status": pay.status,
                "status_display": pay.status,
                "status_lower": str(pay.status).lower(),
                "is_paid": pay.status == "Released",
            })

    milestones_list = []
    if payments_list:
        for p in payments_list:
            milestones_list.append({
                "title": p["title"],
                "amount": p["amount"],
                "type": p.get("type_label", "Installment"),
                "status": p["status_display"],
                "is_done": p.get("is_paid", False),
                "paid_date": p.get("payment_date"),
            })
    elif campaign.milestones.exists():
        for m in campaign.milestones.all():
            milestones_list.append({
                "title": m.title,
                "amount": None,
                "type": "General",
                "status": "Done" if m.is_done else "Pending",
                "is_done": m.is_done,
                "paid_date": None,
            })

    tasks_list = []
    if campaign.tasks.exists():
        for t in campaign.tasks.all():
            tasks_list.append({
                "title": t.title,
                "due_date": t.due_date or "-",
                "is_done": t.is_done,
            })
    elif campaign.deliverables.exists():
        for d in campaign.deliverables.all():
            tasks_list.append({
                "title": f"{d.name} ({d.type})",
                "due_date": d.deadline or "-",
                "is_done": d.status in ["Approved", "Published"],
            })

    deliverables = campaign.deliverables.all()
    files = campaign.files.all()
    tickets = campaign.tickets.all()

    return {
        "instance": campaign,
        "is_business": is_business,
        "negotiation": negotiation,
        "milestones": milestones_list,
        "tasks": tasks_list,
        "deliverables": deliverables,
        "payments": payments_list,
        "files": files,
        "tickets": tickets,
        "currency_symbol": curr_sym,
    }


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
            is_creator = hasattr(user, "creator_profile") or getattr(profile, "role", "") in ["influencer", "creator"]
            is_business = hasattr(user, "business_profile") or getattr(profile, "role", "") in ["business", "brand"]

            if is_creator:
                qs = Campaign.objects.filter(creator=user).exclude(status="Under_Review")
            elif is_business:
                qs = Campaign.objects.filter(brand=user)
            else:
                qs = Campaign.objects.filter(models.Q(creator=user) | models.Q(brand=user))

        # Allow query-param filtering by status
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.distinct()

    def create(self, request, *args, **kwargs):
        # Extract data without using request.data.copy() to avoid pickling BufferedRandom uploaded files
        data = {}
        if hasattr(request.data, "lists"):
            for key, val_list in request.data.lists():
                if key in ["voice_brief", "screenshare_brief", "video_brief"]:
                    val = val_list[-1] if val_list else None
                    if isinstance(val, str):
                        data[key] = val
                elif len(val_list) == 1:
                    data[key] = val_list[0]
                else:
                    data[key] = val_list
        elif isinstance(request.data, dict):
            for key, val in request.data.items():
                if key in ["voice_brief", "screenshare_brief", "video_brief"]:
                    if isinstance(val, str):
                        data[key] = val
                else:
                    data[key] = val
        else:
            for key in request.data:
                val = request.data.get(key)
                if key in ["voice_brief", "screenshare_brief", "video_brief"]:
                    if isinstance(val, str):
                        data[key] = val
                else:
                    data[key] = val

        name_val = str(data.get("name", "")).strip()
        if not name_val:
            return Response({"name": ["Campaign name is required."]}, status=status.HTTP_400_BAD_REQUEST)
        if Campaign.objects.filter(brand=request.user, name__iexact=name_val).exists():
            return Response({"name": ["A campaign with this name already exists. Please choose a unique campaign name."]}, status=status.HTTP_400_BAD_REQUEST)

        # Distinguish Campaign Category and Niche
        cat_val = data.get("campaign_category") or data.get("deliverable_category") or data.get("campaign_type") or data.get("category")
        niche_val = data.get("niche") or data.get("niches")
        if cat_val:
            data["category"] = cat_val
            data["campaign_category"] = cat_val
        if niche_val:
            data["niche"] = niche_val

        # Extract Platform
        platform_val = data.get("platform") or data.get("target_platform") or data.get("medium")
        if not platform_val and "platforms" in data:
            p_val = data.get("platforms")
            if isinstance(p_val, list):
                platform_val = ", ".join(str(x) for x in p_val if x)
            elif isinstance(p_val, str):
                try:
                    import json
                    parsed = json.loads(p_val)
                    if isinstance(parsed, list):
                        platform_val = ", ".join(str(x) for x in parsed if x)
                    else:
                        platform_val = p_val
                except Exception:
                    platform_val = p_val
        if platform_val:
            data["platform"] = platform_val
            data["medium"] = platform_val

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # Only pending campaigns can be edited by non-staff users
        if not (request.user.is_staff or request.user.is_superuser):
            if str(instance.status or "").lower() != "pending":
                return Response(
                    {"detail": "Only pending campaigns can be edited."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Extract data without using request.data.copy() to avoid pickling BufferedRandom uploaded files
        data = {}
        if hasattr(request.data, "lists"):
            for key, val_list in request.data.lists():
                if key in ["voice_brief", "screenshare_brief", "video_brief"]:
                    val = val_list[-1] if val_list else None
                    if isinstance(val, str):
                        data[key] = val
                elif len(val_list) == 1:
                    data[key] = val_list[0]
                else:
                    data[key] = val_list
        elif isinstance(request.data, dict):
            for key, val in request.data.items():
                if key in ["voice_brief", "screenshare_brief", "video_brief"]:
                    if isinstance(val, str):
                        data[key] = val
                else:
                    data[key] = val
        else:
            for key in request.data:
                val = request.data.get(key)
                if key in ["voice_brief", "screenshare_brief", "video_brief"]:
                    if isinstance(val, str):
                        data[key] = val
                else:
                    data[key] = val

        if "name" in data:
            name_val = str(data.get("name", "")).strip()
            if not name_val:
                return Response({"name": ["Campaign name is required."]}, status=status.HTTP_400_BAD_REQUEST)
            if Campaign.objects.filter(brand=request.user, name__iexact=name_val).exclude(id=instance.id).exists():
                return Response({"name": ["A campaign with this name already exists. Please choose a unique campaign name."]}, status=status.HTTP_400_BAD_REQUEST)

        # Distinguish Campaign Category and Niche
        cat_val = data.get("campaign_category") or data.get("deliverable_category") or data.get("campaign_type") or data.get("category")
        niche_val = data.get("niche") or data.get("niches")
        if cat_val:
            data["category"] = cat_val
            data["campaign_category"] = cat_val
        if niche_val:
            data["niche"] = niche_val

        platform_val = data.get("platform") or data.get("target_platform") or data.get("medium")
        if not platform_val and "platforms" in data:
            p_val = data.get("platforms")
            if isinstance(p_val, list):
                platform_val = ", ".join(str(x) for x in p_val if x)
            elif isinstance(p_val, str):
                try:
                    import json
                    parsed = json.loads(p_val)
                    if isinstance(parsed, list):
                        platform_val = ", ".join(str(x) for x in parsed if x)
                    else:
                        platform_val = p_val
                except Exception:
                    platform_val = p_val
        if platform_val:
            data["platform"] = platform_val
            data["medium"] = platform_val
        if "start_date" in data:
            s_date = str(data["start_date"]).strip()
            if s_date:
                import re
                from datetime import datetime
                if not re.search(r'\b(19\d\d|20\d\d)\b', s_date):
                    s_date = f"{s_date}, {datetime.now().year}"
                data["start_date"] = s_date
        if "end_date" in data:
            e_date = str(data["end_date"]).strip()
            if e_date:
                import re
                from datetime import datetime
                if not re.search(r'\b(19\d\d|20\d\d)\b', e_date):
                    e_date = f"{e_date}, {datetime.now().year}"
                data["end_date"] = e_date
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Only pending campaigns can be deleted by non-staff users
        if not (request.user.is_staff or request.user.is_superuser):
            if str(instance.status or "").lower() != "pending":
                return Response(
                    {"detail": "Only pending campaigns can be deleted."},
                    status=status.HTTP_403_FORBIDDEN
                )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        voice_file = self.request.FILES.get("voice_brief")
        screenshare_file = self.request.FILES.get("screenshare_brief")
        video_file = self.request.FILES.get("video_brief")

        from django.core.files.storage import default_storage
        import os
        import urllib.parse

        def clean_media_path(val):
            if not val or not isinstance(val, str):
                return ""
            s = urllib.parse.unquote(val.strip())
            if "://" in s:
                from urllib.parse import urlparse
                s = urlparse(s).path
                s = urllib.parse.unquote(s)
            while s.startswith('/media/'):
                s = s[7:]
            while s.startswith('media/'):
                s = s[6:]
            while s.startswith('/'):
                s = s[1:]
            return s

        voice_brief_path = ""
        if voice_file:
            path = default_storage.save(os.path.join('campaign_briefs', voice_file.name), voice_file)
            voice_brief_path = path
        elif self.request.data.get("voice_brief") and isinstance(self.request.data.get("voice_brief"), str):
            voice_brief_path = clean_media_path(self.request.data.get("voice_brief"))

        screenshare_brief_path = ""
        if screenshare_file:
            path = default_storage.save(os.path.join('campaign_briefs', screenshare_file.name), screenshare_file)
            screenshare_brief_path = path
        elif self.request.data.get("screenshare_brief") and isinstance(self.request.data.get("screenshare_brief"), str):
            screenshare_brief_path = clean_media_path(self.request.data.get("screenshare_brief"))

        video_brief_path = ""
        if video_file:
            path = default_storage.save(os.path.join('campaign_briefs', video_file.name), video_file)
            video_brief_path = path
        elif self.request.data.get("video_brief") and isinstance(self.request.data.get("video_brief"), str):
            video_brief_path = clean_media_path(self.request.data.get("video_brief"))

        start_date = serializer.validated_data.get("start_date") or self.request.data.get("start_date")
        end_date = serializer.validated_data.get("end_date") or self.request.data.get("end_date")
        from datetime import datetime
        import re
        if not start_date:
            start_date = datetime.now().strftime("%b %d, %Y")
        else:
            start_date = str(start_date).strip()
            if not re.search(r'\b(19\d\d|20\d\d)\b', start_date):
                start_date = f"{start_date}, {datetime.now().year}"

        if end_date:
            end_date = str(end_date).strip()
            if not re.search(r'\b(19\d\d|20\d\d)\b', end_date):
                end_date = f"{end_date}, {datetime.now().year}"

        created_time = self.request.data.get("created_time") or serializer.validated_data.get("created_time") or datetime.now().isoformat()
        platform_val = self.request.data.get("platform") or self.request.data.get("target_platform") or self.request.data.get("medium") or serializer.validated_data.get("platform", "") or serializer.validated_data.get("medium", "")
        if not platform_val and "platforms" in self.request.data:
            p_val = self.request.data.get("platforms")
            if isinstance(p_val, list):
                platform_val = ", ".join(str(x) for x in p_val if x)
            elif isinstance(p_val, str):
                try:
                    import json
                    parsed = json.loads(p_val)
                    if isinstance(parsed, list):
                        platform_val = ", ".join(str(x) for x in parsed if x)
                    else:
                        platform_val = p_val
                except Exception:
                    platform_val = p_val
        niche_val = self.request.data.get("niche") or self.request.data.get("niches") or serializer.validated_data.get("niche") or ""
        cat_val = self.request.data.get("campaign_category") or self.request.data.get("deliverable_category") or self.request.data.get("campaign_type") or self.request.data.get("category") or serializer.validated_data.get("category") or ""

        campaign = serializer.save(
            brand=self.request.user,
            start_date=start_date,
            end_date=end_date or serializer.validated_data.get("end_date", ""),
            created_time=created_time,
            voice_brief=voice_brief_path or serializer.validated_data.get("voice_brief", ""),
            screenshare_brief=screenshare_brief_path or serializer.validated_data.get("screenshare_brief", ""),
            video_brief=video_brief_path or serializer.validated_data.get("video_brief", ""),
            platform=platform_val,
            medium=platform_val,
            category=cat_val or serializer.validated_data.get("category", ""),
            campaign_category=cat_val or serializer.validated_data.get("campaign_category", ""),
            niche=niche_val or serializer.validated_data.get("niche", "")
        )

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
                        brief=item.get("brief", ""),
                        status="PENDING_SUBMISSION",
                    )
                    # Automatically add business custom deliverable to Super Admin CampaignDeliverables options list
                    clean_name = del_name.split(" × ", 1)[-1].strip() if " × " in del_name else del_name.strip()
                    if clean_name:
                        plat = item.get("platform") or campaign.platform or campaign.medium or ""
                        cat_id = item.get("category")
                        if not cat_id:
                            target_cat_str = getattr(campaign, "campaign_category", None) or getattr(campaign, "category", None)
                            if target_cat_str and isinstance(target_cat_str, str):
                                cat_obj = CampaignCategory.objects.filter(type__iexact=target_cat_str.strip()).first() or CampaignCategory.objects.filter(name__iexact=target_cat_str.strip()).first()
                                if cat_obj:
                                    cat_id = cat_obj.id

                        defaults = {"platform": plat}
                        if cat_id:
                            try:
                                defaults["category_id"] = int(cat_id)
                            except (ValueError, TypeError):
                                pass

                        cd_obj, created = CampaignDeliverable.objects.get_or_create(name=clean_name, defaults=defaults)
                        if not created:
                            changed = False
                            if plat and not cd_obj.platform:
                                cd_obj.platform = plat
                                changed = True
                            if cat_id and not cd_obj.category_id:
                                try:
                                    cd_obj.category_id = int(cat_id)
                                    changed = True
                                except (ValueError, TypeError):
                                    pass
                            if changed:
                                cd_obj.save()
            except Exception as e:
                print("Error parsing deliverables:", e)

    def perform_update(self, serializer):
        voice_file = self.request.FILES.get("voice_brief")
        screenshare_file = self.request.FILES.get("screenshare_brief")
        video_file = self.request.FILES.get("video_brief")

        from django.core.files.storage import default_storage
        import os
        import urllib.parse

        def clean_media_path(val):
            if not val or not isinstance(val, str):
                return ""
            s = urllib.parse.unquote(val.strip())
            if "://" in s:
                from urllib.parse import urlparse
                s = urlparse(s).path
                s = urllib.parse.unquote(s)
            while s.startswith('/media/'):
                s = s[7:]
            while s.startswith('media/'):
                s = s[6:]
            while s.startswith('/'):
                s = s[1:]
            return s

        kwargs = {}
        if voice_file:
            path = default_storage.save(os.path.join('campaign_briefs', voice_file.name), voice_file)
            kwargs["voice_brief"] = path
        elif self.request.data.get("voice_brief") and isinstance(self.request.data.get("voice_brief"), str):
            kwargs["voice_brief"] = clean_media_path(self.request.data.get("voice_brief"))

        if screenshare_file:
            path = default_storage.save(os.path.join('campaign_briefs', screenshare_file.name), screenshare_file)
            kwargs["screenshare_brief"] = path
        elif self.request.data.get("screenshare_brief") and isinstance(self.request.data.get("screenshare_brief"), str):
            kwargs["screenshare_brief"] = clean_media_path(self.request.data.get("screenshare_brief"))

        if video_file:
            path = default_storage.save(os.path.join('campaign_briefs', video_file.name), video_file)
            kwargs["video_brief"] = path
        elif self.request.data.get("video_brief") and isinstance(self.request.data.get("video_brief"), str):
            kwargs["video_brief"] = clean_media_path(self.request.data.get("video_brief"))

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
                        brief=item.get("brief", ""),
                        status="PENDING_SUBMISSION",
                    )
                    # Automatically add business custom deliverable to Super Admin CampaignDeliverables options list
                    clean_name = del_name.split(" × ", 1)[-1].strip() if " × " in del_name else del_name.strip()
                    if clean_name:
                        plat = item.get("platform") or campaign.platform or campaign.medium or ""
                        cat_id = item.get("category")
                        if not cat_id:
                            target_cat_str = getattr(campaign, "campaign_category", None) or getattr(campaign, "category", None)
                            if target_cat_str and isinstance(target_cat_str, str):
                                cat_obj = CampaignCategory.objects.filter(type__iexact=target_cat_str.strip()).first() or CampaignCategory.objects.filter(name__iexact=target_cat_str.strip()).first()
                                if cat_obj:
                                    cat_id = cat_obj.id

                        defaults = {"platform": plat}
                        if cat_id:
                            try:
                                defaults["category_id"] = int(cat_id)
                            except (ValueError, TypeError):
                                pass

                        cd_obj, created = CampaignDeliverable.objects.get_or_create(name=clean_name, defaults=defaults)
                        if not created:
                            changed = False
                            if plat and not cd_obj.platform:
                                cd_obj.platform = plat
                                changed = True
                            if cat_id and not cd_obj.category_id:
                                try:
                                    cd_obj.category_id = int(cat_id)
                                    changed = True
                                except (ValueError, TypeError):
                                    pass
                            if changed:
                                cd_obj.save()
            except Exception as e:
                print("Error parsing deliverables:", e)

    @action(detail=True, methods=["get"])
    def download_pdf(self, request, pk=None):
        from io import BytesIO
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        from xhtml2pdf import pisa

        campaign = self.get_object()
        context = build_campaign_pdf_context(campaign, user=request.user)
        
        html = render_to_string("campegin/campaign_pdf.html", context)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            clean_name = str(campaign.name or "campaign").replace(" ", "_")
            response['Content-Disposition'] = f'attachment; filename="campaign_{clean_name}.pdf"'
            return response
        return HttpResponse("Error generating PDF", status=500)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Action for super admin to approve and publish a campaign."""
        # For development demo/testing, bypass staff restriction
        # if not (request.user.is_staff or request.user.is_superuser):
        #     return Response({"error": "Admin privileges required."}, status=status.HTTP_403_FORBIDDEN)
        
        campaign = self.get_object()
        campaign.status = "Pending"
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
        text = request.data.get("text", "")
        file_attachment = request.data.get("file_attachment", "") or request.data.get("file", "")
        message_type = request.data.get("message_type", "main")
        file_size = request.data.get("file_size", "1.5 MB")

        # Save actual binary file if uploaded in request.FILES
        uploaded_file = request.FILES.get("file") or request.FILES.get("file_attachment")
        if uploaded_file and not isinstance(uploaded_file, str):
            from django.core.files.storage import FileSystemStorage
            from django.conf import settings
            import os
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            if fs.exists(uploaded_file.name):
                fs.delete(uploaded_file.name)
            saved_filename = fs.save(uploaded_file.name, uploaded_file)
            file_attachment = saved_filename
        
        if not text and not file_attachment:
            return Response({"error": "Text or file attachment is required"}, status=status.HTTP_400_BAD_REQUEST)
            
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
        date_str = now.strftime("%b %d, %Y")
        
        message = WorkspaceMessage.objects.create(
            campaign=campaign,
            sender=user,
            text=text or (f"Shared attachment: {file_attachment}" if file_attachment else ""),
            file_attachment=str(file_attachment or ""),
            message_type=message_type,
            time=time_str
        )

        if file_attachment:
            WorkspaceFile.objects.create(
                campaign=campaign,
                name=str(file_attachment),
                size=file_size,
                sender=user,
                date=date_str,
                time=now.strftime("%I:%M %p")
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
            if request.user.is_staff or request.user.is_superuser:
                message = WorkspaceMessage.objects.get(id=message_id, campaign=campaign)
            else:
                message = WorkspaceMessage.objects.get(id=message_id, campaign=campaign, sender=request.user)

            file_att = (message.file_attachment or "").strip()
            if not file_att and message.text and message.text.startswith("Shared attachment: "):
                file_att = message.text.replace("Shared attachment: ", "").strip()

            if file_att:
                import os
                base_name = os.path.basename(file_att)
                # Delete associated WorkspaceFile entries from database
                WorkspaceFile.objects.filter(
                    campaign=campaign
                ).filter(
                    models.Q(name=file_att) |
                    models.Q(name=base_name) |
                    models.Q(name__icontains=base_name)
                ).delete()

                # Also delete physical file from media storage if present
                from django.core.files.storage import FileSystemStorage
                from django.conf import settings
                try:
                    fs = FileSystemStorage(location=settings.MEDIA_ROOT)
                    for candidate in [file_att, base_name]:
                        if candidate and fs.exists(candidate):
                            fs.delete(candidate)
                except Exception as storage_err:
                    print("Storage delete warning:", storage_err)

            message.delete()
            return Response({"status": "deleted"}, status=status.HTTP_200_OK)
        except WorkspaceMessage.DoesNotExist:
            return Response({"error": "Message not found or you don't have permission to delete it"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"])
    def toggle_pin_message(self, request, pk=None):
        campaign = self.get_object()
        message_id = request.data.get("message_id")
        if not message_id:
            return Response({"error": "message_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            message = WorkspaceMessage.objects.get(id=message_id, campaign=campaign)
            message.is_pinned = not message.is_pinned
            message.save()
            return Response(WorkspaceMessageSerializer(message).data)
        except WorkspaceMessage.DoesNotExist:
            return Response({"error": "Message not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"])
    def upload_file(self, request, pk=None):
        campaign = self.get_object()
        file_name = request.data.get("name") or request.data.get("file_name")
        file_size = request.data.get("size", "2.5 MB")

        uploaded_file = request.FILES.get("file") or request.FILES.get("name")
        if uploaded_file and not isinstance(uploaded_file, str):
            from django.core.files.storage import FileSystemStorage
            from django.conf import settings
            import os
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            if fs.exists(uploaded_file.name):
                fs.delete(uploaded_file.name)
            file_name = fs.save(uploaded_file.name, uploaded_file)

        if not file_name:
            return Response({"error": "File name is required"}, status=status.HTTP_400_BAD_REQUEST)

        import datetime
        now = datetime.datetime.now()
        date_str = now.strftime("%b %d, %Y")
        time_str = now.strftime("%I:%M %p")

        ws_file = WorkspaceFile.objects.create(
            campaign=campaign,
            name=str(file_name),
            size=file_size,
            sender=request.user,
            date=date_str,
            time=time_str
        )
        return Response(WorkspaceFileSerializer(ws_file).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny])
    def submit_deliverable(self, request, pk=None):
        campaign = self.get_object()
        del_id = request.data.get("deliverable_id")
        
        link = request.data.get("link")
        screenshot_name = request.data.get("screenshot_name", "")
        assetDriveLink = request.data.get("assetDriveLink")
        assetFileName = request.data.get("assetFileName", "")
        views = request.data.get("views")
        reach = request.data.get("reach")
        er = request.data.get("er")

        # Save any binary files uploaded in request.FILES
        for file_key in ["assetFileName", "screenshot_name", "file"]:
            f_obj = request.FILES.get(file_key)
            if f_obj and not isinstance(f_obj, str):
                from django.core.files.storage import FileSystemStorage
                from django.conf import settings
                import os
                os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
                fs = FileSystemStorage(location=settings.MEDIA_ROOT)
                if fs.exists(f_obj.name):
                    fs.delete(f_obj.name)
                saved_name = fs.save(f_obj.name, f_obj)
                if file_key == "assetFileName":
                    assetFileName = saved_name
                elif file_key == "screenshot_name" or file_key == "file":
                    screenshot_name = saved_name

        if del_id:
            deliverable = get_object_or_404(Deliverable, campaign=campaign, id=del_id)
        else:
            deliverable = campaign.deliverables.first()
            if not deliverable:
                deliverable = Deliverable.objects.create(
                    campaign=campaign,
                    name=campaign.campaign_category or campaign.category or "Campaign Deliverable",
                    type="video",
                    status="PUBLISHED"
                )

        # Update deliverable(s)
        targets = [deliverable]
        if not del_id or link or screenshot_name:
            all_dels = list(campaign.deliverables.all())
            if all_dels:
                targets = all_dels

        for d in targets:
            if link:
                d.link = link
            if screenshot_name:
                d.screenshot_name = str(screenshot_name)
            if assetDriveLink and (d.id == deliverable.id or not del_id):
                d.assetDriveLink = assetDriveLink
            if assetFileName and (d.id == deliverable.id or not del_id):
                d.assetFileName = str(assetFileName)

            if d.status not in ["PUBLISHED", "Approved", "Published", "PENDING_ADMIN_APPROVAL", "Pending Final Admin Approval"]:
                d.status = "PENDING_BUSINESS_REVIEW"

            if views is not None:
                d.views = str(views)
            if reach is not None:
                d.reach = str(reach)
            if er is not None:
                try:
                    d.er = float(er)
                except (ValueError, TypeError):
                    pass
            d.save()

        return Response(DeliverableSerializer(deliverable).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny])
    def review_deliverable(self, request, pk=None):
        campaign = self.get_object()
        del_id = request.data.get("deliverable_id")
        status_action = request.data.get("status")
        name = request.data.get("name")
        del_type = request.data.get("type")
        brief = request.data.get("brief")
        deadline = request.data.get("deadline")

        if not del_id:
            return Response({"error": "deliverable_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        deliverable = get_object_or_404(Deliverable, campaign=campaign, id=del_id)
        
        revision_notes = request.data.get("revision_notes")
        revision_link = request.data.get("revision_reference_link")
        revision_file = request.FILES.get("revision_reference_file")

        if status_action:
            normalized = str(status_action).strip()
            if normalized in ["PENDING_ADMIN_APPROVAL", "Pending Final Admin Approval"]:
                if request.user.is_staff or request.user.is_superuser:
                    deliverable.status = "PUBLISHED"
                else:
                    deliverable.status = "PENDING_ADMIN_APPROVAL"
            elif normalized in ["REVISION_REQUIRED", "Revision Requested", "Revision Requested (Pending Admin)"]:
                deliverable.status = "REVISION_REQUIRED"
            elif normalized in ["PUBLISHED", "Approved", "Published"]:
                deliverable.status = "PUBLISHED"
            elif normalized in ["PENDING_BUSINESS_REVIEW", "Pending Business Review", "Pending Admin Review", "Pending"]:
                deliverable.status = "PENDING_BUSINESS_REVIEW"
            elif normalized in ["PENDING_SUBMISSION", "Pending Submission"]:
                deliverable.status = "PENDING_SUBMISSION"
            else:
                deliverable.status = normalized
        if name:
            deliverable.name = name
            clean_name = name.split(" × ", 1)[-1].strip() if " × " in name else name.strip()
            if clean_name:
                CampaignDeliverable.objects.get_or_create(name=clean_name)
        if del_type:
            deliverable.type = del_type
        if brief is not None:
            deliverable.brief = brief
        if deadline is not None:
            deliverable.deadline = deadline
        if revision_notes is not None:
            deliverable.revision_notes = revision_notes
        if revision_link is not None:
            deliverable.revision_reference_link = revision_link
        if revision_file is not None:
            deliverable.revision_reference_file = revision_file

        deliverable.save()

        # Update progression based on deliverables
        total_dels = campaign.deliverables.count()
        if total_dels > 0:
            approved_dels = campaign.deliverables.filter(status__in=["PUBLISHED", "Approved", "Published"]).count()
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

        user = request.user
        profile = getattr(user, "profile", None)
        if user == campaign.creator or (campaign.creator and user.id == campaign.creator.id):
            sender_role = "creator"
        elif user == campaign.brand or (campaign.brand and user.id == campaign.brand.id):
            sender_role = "business"
        else:
            sender_role = "creator" if (hasattr(user, "creator_profile") or getattr(profile, "role", "") in ["influencer", "creator"]) else "business"

        ticket = AdminComplianceTicket.objects.create(
            campaign=campaign,
            sender=user,
            sender_role=sender_role,
            target_audience=sender_role,
            category=category,
            message=message,
            status="Pending Review",
            reply="Our specialists will audit the campaign context and chat logs."
        )

        try:
            ChatReview.objects.create(
                campaign=campaign,
                category=category or "Safety / Guidelines",
                review_text=f"[{sender_role.upper()} REQUEST by {user.username}] {message}",
                target_audience="creator" if sender_role in ["creator", "influencer"] else "business"
            )
        except Exception as e:
            print("Error creating ChatReview:", e)

        return Response(AdminComplianceTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def accept_counter(self, request, pk=None):
        campaign = self.get_object()
        if campaign.counter_price:
            campaign.budget = campaign.counter_price
        elif campaign.counter_history and len(campaign.counter_history) > 0:
            last_p = campaign.counter_history[-1].get("price")
            if last_p:
                campaign.budget = last_p
        campaign.status = "Accepted_Pending_Admin"
        campaign.save()

        Notification.objects.create(
            title="Campaign Counter Accepted - Awaiting Admin Approval",
            message=f"The counter offer for campaign '{campaign.name}' was accepted and is awaiting Admin Approval to become Live.",
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

        if counter_price is not None:
            try:
                c_price = float(counter_price)
                if c_price <= 0:
                    return Response({"error": "Counter price must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

                cat_min = float(campaign.min_price or campaign.min_budget or 0)
                cat_max = float(campaign.max_price or campaign.max_budget or campaign.per_creator_budget or 0)

                cat_query = campaign.category
                if cat_query:
                    matched_category = CampaignCategory.objects.filter(
                        models.Q(name__iexact=cat_query) | models.Q(type__iexact=cat_query)
                    ).first()
                    if matched_category:
                        if matched_category.min_price and float(matched_category.min_price) > 0:
                            cat_min = float(matched_category.min_price)
                        if matched_category.max_price and float(matched_category.max_price) > 0:
                            cat_max = float(matched_category.max_price)

                if cat_min > 0 and c_price < cat_min:
                    return Response({"error": f"Counter price cannot be less than minimum allowed price of {cat_min}."}, status=status.HTTP_400_BAD_REQUEST)
                if cat_max > 0 and c_price > cat_max:
                    return Response({"error": f"Counter price cannot exceed maximum allowed price of {cat_max}."}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "Invalid counter price provided."}, status=status.HTTP_400_BAD_REQUEST)

        campaign.counter_price = counter_price
        campaign.counter_note = counter_note
        campaign.status = "Business_Countered"

        history = list(campaign.counter_history or [])
        history.append({
            "round": campaign.counter_round or 1,
            "sender": "Business",
            "sender_name": campaign.brand.username if campaign.brand else "Business",
            "price": str(counter_price),
            "note": counter_note or "",
            "status": "Business_Countered"
        })
        campaign.counter_history = history
        campaign.save()

        Notification.objects.create(
            title="Business Replied to Counter Offer",
            message=f"Business submitted a counter-response of {counter_price} for campaign '{campaign.name}'.",
            category="campaign",
            icon="fas fa-handshake",
            target_url=f"/admin/snippets/campegin/campaign/inspect/{campaign.id}/"
        )
        return Response(CampaignSerializer(campaign).data)


class RequestViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Campaign.objects.none()

        if user.is_staff or user.is_superuser:
            qs = Campaign.objects.all()
        elif hasattr(user, "business_profile"):
            qs = Campaign.objects.filter(brand=user)
        elif hasattr(user, "creator_profile"):
            profile = getattr(user, "creator_profile", None)
            q_filter = models.Q(creator=user)
            if profile:
                q_filter |= models.Q(creator__creator_profile=profile)
            qs = Campaign.objects.filter(q_filter).distinct()
        else:
            qs = Campaign.objects.filter(models.Q(brand=user) | models.Q(creator=user))

        if self.action == "list":
            qs = qs.exclude(created_via="pitch")
            status_param = self.request.query_params.get("status")
            if status_param:
                statuses = [s.strip() for s in status_param.split(",")]
                qs = qs.filter(status__in=statuses)

        return qs

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        campaign = self.get_object()
        if campaign.counter_price:
            campaign.budget = campaign.counter_price
        elif campaign.counter_history and len(campaign.counter_history) > 0:
            last_p = campaign.counter_history[-1].get("price")
            if last_p:
                campaign.budget = last_p

        has_counter = (campaign.counter_round and campaign.counter_round > 0) or (campaign.counter_history and len(campaign.counter_history) > 0) or bool(campaign.counter_price)
        if has_counter:
            campaign.status = "Accepted_Pending_Admin"
        else:
            campaign.status = "Live"
        campaign.save()

        if campaign.status == "Accepted_Pending_Admin":
            Notification.objects.create(
                title="Campaign Counter Accepted - Awaiting Admin Approval",
                message=f"The counter offer for campaign '{campaign.name}' was accepted and is awaiting Admin Approval to become Live.",
                category="campaign",
                icon="fas fa-check-circle",
                target_url=f"/admin/snippets/campegin/campaign/inspect/{campaign.id}/"
            )
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
        if (campaign.counter_round or 0) >= 4:
            return Response({"error": "Maximum counter offer rounds reached."}, status=status.HTTP_400_BAD_REQUEST)
        counter_price = request.data.get("price")
        counter_note = request.data.get("note")

        if counter_price is not None:
            try:
                c_price = float(counter_price)
                if c_price <= 0:
                    return Response({"error": "Counter price must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

                cat_min = float(campaign.min_price or campaign.min_budget or 0)
                cat_max = float(campaign.max_price or campaign.max_budget or campaign.per_creator_budget or 0)

                cat_query = campaign.category
                if cat_query:
                    matched_category = CampaignCategory.objects.filter(
                        models.Q(name__iexact=cat_query) | models.Q(type__iexact=cat_query)
                    ).first()
                    if matched_category:
                        if matched_category.min_price and float(matched_category.min_price) > 0:
                            cat_min = float(matched_category.min_price)
                        if matched_category.max_price and float(matched_category.max_price) > 0:
                            cat_max = float(matched_category.max_price)

                if cat_min > 0 and c_price < cat_min:
                    return Response({"error": f"Counter price cannot be less than minimum allowed price of {cat_min}."}, status=status.HTTP_400_BAD_REQUEST)
                if cat_max > 0 and c_price > cat_max:
                    return Response({"error": f"Counter price cannot exceed maximum allowed price of {cat_max}."}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "Invalid counter price provided."}, status=status.HTTP_400_BAD_REQUEST)

        campaign.counter_price = counter_price
        campaign.counter_note = counter_note
        campaign.counter_round = (campaign.counter_round or 0) + 1
        campaign.status = "Countered"

        history = list(campaign.counter_history or [])
        history.append({
            "round": campaign.counter_round,
            "sender": "Creator",
            "sender_name": campaign.creator.username if campaign.creator else "Creator",
            "price": str(counter_price),
            "note": counter_note or "",
            "status": "Countered"
        })
        campaign.counter_history = history
        campaign.save()
        
        Notification.objects.create(
            title="Campaign Counter Offer",
            message=f"A creator counter offer of {counter_price} was submitted for campaign '{campaign.name}'.",
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
        elif campaign.counter_history and len(campaign.counter_history) > 0:
            last_p = campaign.counter_history[-1].get("price")
            if last_p:
                campaign.budget = last_p
        campaign.status = "Accepted_Pending_Admin"
        campaign.save()
        
        Notification.objects.create(
            title="Campaign Counter Accepted - Awaiting Admin Approval",
            message=f"The counter offer for campaign '{campaign.name}' was accepted and is awaiting Admin Approval to become Live.",
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

        if counter_price is not None:
            try:
                c_price = float(counter_price)
                if c_price <= 0:
                    return Response({"error": "Counter price must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

                cat_min = float(campaign.min_price or campaign.min_budget or 0)
                cat_max = float(campaign.max_price or campaign.max_budget or campaign.per_creator_budget or 0)

                cat_query = campaign.category
                if cat_query:
                    matched_category = CampaignCategory.objects.filter(
                        models.Q(name__iexact=cat_query) | models.Q(type__iexact=cat_query)
                    ).first()
                    if matched_category:
                        if matched_category.min_price and float(matched_category.min_price) > 0:
                            cat_min = float(matched_category.min_price)
                        if matched_category.max_price and float(matched_category.max_price) > 0:
                            cat_max = float(matched_category.max_price)

                if cat_min > 0 and c_price < cat_min:
                    return Response({"error": f"Counter price cannot be less than minimum allowed price of {cat_min}."}, status=status.HTTP_400_BAD_REQUEST)
                if cat_max > 0 and c_price > cat_max:
                    return Response({"error": f"Counter price cannot exceed maximum allowed price of {cat_max}."}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({"error": "Invalid counter price provided."}, status=status.HTTP_400_BAD_REQUEST)

        campaign.counter_price = counter_price
        campaign.counter_note = counter_note
        campaign.status = "Business_Countered"

        history = list(campaign.counter_history or [])
        history.append({
            "round": campaign.counter_round or 1,
            "sender": "Business",
            "sender_name": campaign.brand.username if campaign.brand else "Business",
            "price": str(counter_price),
            "note": counter_note or "",
            "status": "Business_Countered"
        })
        campaign.counter_history = history
        campaign.save()
        
        Notification.objects.create(
            title="Campaign Counter Reply",
            message=f"A business counter offer of {counter_price} was sent for campaign '{campaign.name}'.",
            category="campaign",
            icon="fas fa-exchange-alt",
            target_url=f"/admin/snippets/campegin/campaign/inspect/{campaign.id}/"
        )
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def admin_approve(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = "Live"
        campaign.save()
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def admin_approve_counter(self, request, pk=None):
        campaign = self.get_object()
        if campaign.counter_price:
            campaign.budget = campaign.counter_price
        elif campaign.counter_history and len(campaign.counter_history) > 0:
            last_p = campaign.counter_history[-1].get("price")
            if last_p:
                campaign.budget = last_p
        campaign.status = "Live"
        campaign.progress = campaign.calculate_flow_progress()
        campaign.save()

        Notification.objects.create(
            title="Campaign Live",
            message=f"Campaign '{campaign.name}' is now Live with agreed budget of {campaign.budget}.",
            category="campaign",
            icon="fas fa-play-circle",
            target_url=f"/admin/snippets/campegin/campaign/inspect/{campaign.id}/"
        )
        return Response(CampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def admin_reject_counter(self, request, pk=None):
        campaign = self.get_object()
        reason = request.data.get("reason") or request.data.get("note") or "Counter offer rejected by admin."
        campaign.status = "Rejected"
        campaign.decline_reason = reason
        campaign.save()
        return Response({"message": "Counter offer rejected", "status": "Rejected", "decline_reason": reason})


class CampaignCategoryApiViewSet(viewsets.ModelViewSet):
    queryset = CampaignCategory.objects.all().order_by("id")
    serializer_class = CampaignCategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        platform = self.request.query_params.get("platform")
        if platform:
            qs = qs.filter(platform__iexact=platform)
        return qs


class CampaignNicheViewSet(viewsets.ModelViewSet):
    queryset = CampaignNiche.objects.all().order_by("name")
    serializer_class = CampaignNicheSerializer
    permission_classes = [permissions.AllowAny]


class CampaignDeliverableApiViewSet(viewsets.ModelViewSet):
    queryset = CampaignDeliverable.objects.all().order_by("id")
    serializer_class = CampaignDeliverableSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        platform = self.request.query_params.get("platform")
        category = self.request.query_params.get("category")
        if platform:
            qs = qs.filter(platform__iexact=platform)
        if category:
            qs = qs.filter(category_id=category)
        return qs

    def create(self, request, *args, **kwargs):
        name = request.data.get("name", "")
        category = request.data.get("category")
        platform = request.data.get("platform", "")

        if isinstance(name, str) and ("," in name or "\n" in name):
            items = [line.strip() for chunk in name.replace("\r", "\n").split("\n") for line in chunk.split(",") if line.strip()]
            if len(items) > 1:
                created_objs = []
                for item_name in items:
                    clean_name = item_name.split(" × ", 1)[-1].strip() if " × " in item_name else item_name
                    obj, _ = CampaignDeliverable.objects.get_or_create(
                        name=clean_name,
                        category_id=category,
                        defaults={"platform": platform}
                    )
                    created_objs.append(obj)
                return Response(CampaignDeliverableSerializer(created_objs, many=True).data, status=status.HTTP_201_CREATED)

        return super().create(request, *args, **kwargs)


class CampaignSettingsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        categories = CampaignCategory.objects.all()
        languages = CampaignLanguage.objects.all()
        deliverables = CampaignDeliverable.objects.all()
        platforms = CampaignPlatform.objects.all()
        niches = CampaignNiche.objects.filter(is_active=True)

        return Response({
            "categories": CampaignCategorySerializer(categories, many=True).data,
            "languages": CampaignLanguageSerializer(languages, many=True).data,
            "deliverables": CampaignDeliverableSerializer(deliverables, many=True).data,
            "platforms": CampaignPlatformSerializer(platforms, many=True).data,
            "niches": CampaignNicheSerializer(niches, many=True).data,
        })

    def post(self, request):
        name = request.data.get("name") or request.data.get("deliverable")
        platform = request.data.get("platform") or ""
        category_id = request.data.get("category") or request.data.get("category_id")
        if name and isinstance(name, str) and name.strip():
            raw_name = name.strip()
            clean_name = raw_name.split(" × ", 1)[-1].strip() if " × " in raw_name else raw_name
            defaults = {"platform": platform}
            if category_id:
                try:
                    defaults["category_id"] = int(category_id)
                except (ValueError, TypeError):
                    cat_obj = CampaignCategory.objects.filter(type__iexact=str(category_id).strip()).first() or CampaignCategory.objects.filter(name__iexact=str(category_id).strip()).first()
                    if cat_obj:
                        defaults["category_id"] = cat_obj.id
            obj, created = CampaignDeliverable.objects.get_or_create(name=clean_name, defaults=defaults)
            if not created:
                changed = False
                if platform and obj.platform != platform:
                    obj.platform = platform
                    changed = True
                if category_id:
                    try:
                        cid = int(category_id)
                        if obj.category_id != cid:
                            obj.category_id = cid
                            changed = True
                    except (ValueError, TypeError):
                        cat_obj = CampaignCategory.objects.filter(type__iexact=str(category_id).strip()).first() or CampaignCategory.objects.filter(name__iexact=str(category_id).strip()).first()
                        if cat_obj and obj.category_id != cat_obj.id:
                            obj.category_id = cat_obj.id
                            changed = True
                if changed:
                    obj.save()
            return Response(CampaignDeliverableSerializer(obj).data)
        return Response({"error": "Invalid deliverable name"}, status=status.HTTP_400_BAD_REQUEST)



from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import user_passes_test
from xhtml2pdf import pisa

@user_passes_test(lambda u: u.is_staff)
def download_campaign_pdf_view(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    context = build_campaign_pdf_context(campaign)
    
    html = render_to_string("campegin/campaign_pdf.html", context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        clean_name = str(campaign.name or "campaign").replace(" ", "_")
        response['Content-Disposition'] = f'attachment; filename="campaign_{clean_name}.pdf"'
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

        avg_rating = 0.0
        if has_creator and hasattr(user, "creator_profile"):
            avg_rating = user.creator_profile.average_rating
        elif has_business:
            from CreatorRating.models import BusinessRating
            avg_res = BusinessRating.objects.filter(brand=user).aggregate(avg=Avg("rating"))["avg"]
            avg_rating = round(float(avg_res), 1) if avg_res is not None else 0.0

        return Response({
            "total_campaigns": total_campaigns,
            "live_now": live_now,
            "total_budget": total_budget,
            "avg_engagement": avg_engagement,
            "avg_rating": avg_rating,
            "avg_creator_rating": avg_rating,
            "average_rating": avg_rating,
            "total_reach": total_reach,
            "total_impressions": total_impressions,
            "total_roi": total_roi,
        })

class BusinessAnalyticsView(APIView):
    """Return aggregated business analytics and top campaigns."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum, Avg
        from datetime import datetime
        user = request.user
        qs = Campaign.objects.filter(brand=user)
        total_campaigns_count = qs.count()

        # 1. Average progress across all campaigns created by this business user
        avg_progress = float(qs.aggregate(avg=Avg("progress"))["avg"] or 0) if total_campaigns_count > 0 else 0.0

        # 2. Allocated Budget: Total Decided Final Price from workspace payment negotiations ONLY
        total_allocated_budget = 0.0
        durations = []

        from WorkspacePayment.models import WorkspacePaymentNegotiation
        for c in qs:
            price = None
            try:
                # Check for payment negotiation final_price in workspace endpoint
                neg = WorkspacePaymentNegotiation.objects.filter(campaign_id=c.id).order_by('-id').first()
                if neg and neg.final_price is not None and float(neg.final_price) > 0:
                    price = float(neg.final_price)
            except Exception:
                pass

            if price is None:
                c_via = str(getattr(c, 'created_via', '') or '').lower().strip()
                if not c_via and getattr(c, 'creator', None):
                    c_via = 'direct_request'
                is_direct = ('direct' in c_via) and ('pitch' not in c_via) and ('request' not in c_via)
                if not is_direct:
                    st = str(c.status or '').lower().strip()
                    if st in ['live', 'active', 'completed', 'finished', 'done']:
                        if c.counter_price and float(c.counter_price) > 0:
                            price = float(c.counter_price)

            # Only add to total_allocated_budget if final price was decided!
            if price is not None and price > 0:
                total_allocated_budget += price

            # Calculate duration for each campaign
            days = 0
            if c.start_date and c.end_date:
                try:
                    d1 = datetime.strptime(str(c.start_date).strip(), "%Y-%m-%d")
                    d2 = datetime.strptime(str(c.end_date).strip(), "%Y-%m-%d")
                    days = max(1, (d2 - d1).days)
                except Exception:
                    days = 0

            if days > 0:
                durations.append(days)

        # Average duration calculation across all campaigns
        avg_duration_days = int(sum(durations) / len(durations)) if len(durations) > 0 else 0

        # 3. Total Paid: Business Workspace Payment Installments (installment_type='business', is_paid=True or status='released') + Business Platform Fee
        total_paid_amount = 0.0
        last_paid_milestone = "None"
        try:
            from WorkspacePayment.models import WorkspaceInstallment, WorkspacePaymentNegotiation
            from django.db.models import Sum, Q
            paid_biz_insts = WorkspaceInstallment.objects.filter(
                campaign__brand=user,
                installment_type='business'
            ).filter(Q(is_paid=True) | Q(status__iexact='released'))

            biz_insts_sum = float(paid_biz_insts.aggregate(total=Sum("amount"))["total"] or 0)

            paid_negs = WorkspacePaymentNegotiation.objects.filter(campaign__brand=user, business_fee_is_paid=True)
            biz_fee_sum = 0.0
            for neg in paid_negs:
                biz_fee_sum += float(neg.business_platform_charge_amount or 0)

            total_paid_amount = round(biz_insts_sum + biz_fee_sum, 2)

            last_obj = paid_biz_insts.order_by('-updated_at').first()
            if last_obj:
                last_paid_milestone = last_obj.title
            elif biz_fee_sum > 0:
                last_paid_milestone = "Platform Fee Paid"
        except Exception as e:
            print("Error computing total_paid_amount:", e)

        avg_engagement = round(3.0 + (avg_progress / 100) * 9.0, 1) if total_campaigns_count > 0 else 0.0
        total_reach = int(total_allocated_budget * 1000)
        total_impressions = int(total_allocated_budget * 2500)
        total_roi = 4.1 if total_allocated_budget > 0 else 0.0

        # Top campaigns by engagement/progress
        top_campaigns_qs = qs.exclude(status="Pending").order_by("-progress")[:5] if total_campaigns_count > 0 else []
        top_campaigns = []
        for c in top_campaigns_qs:
            er = round(3.0 + (c.progress / 100) * 9.0, 1) if c.progress else 0.0
            spend = float(c.budget or 0)
            reach_val = f"{round(spend/1000, 1)}M" if spend > 0 else "0"
            top_campaigns.append({
                "name": c.name,
                "er": er,
                "reach": reach_val,
                "roi": "4.1x" if spend > 0 else "0x",
                "spend": spend,
                "trend": "up"
            })

        # Grouped Bar Chart data: Budget vs. Actual Spend (Live campaign details only)
        budget_vs_spend = []
        try:
            from WorkspacePayment.models import WorkspaceInstallment, WorkspacePaymentNegotiation
            from campegin.models import Pitch
            from django.db.models import Sum, Q
            live_statuses = ["live", "active", "admin_approved", "in_progress", "completed", "approved"]
            live_qs = [c for c in qs.order_by('id') if c.status and str(c.status).lower() in live_statuses] if total_campaigns_count > 0 else []
            if not live_qs and total_campaigns_count > 0:
                live_qs = [c for c in qs.order_by('id') if str(c.status).lower() not in ["under_review", "draft", "cancelled"]]
            if not live_qs and total_campaigns_count > 0:
                live_qs = list(qs.order_by('id'))

            for c in live_qs:
                # 1. Target / Max Budget: max_budget if present and > 0, else budget
                t_budget = float(c.max_budget if (c.max_budget and float(c.max_budget) > 0) else (c.budget or 0))

                # 2. Final Committed Price (Purple Bar): Pull directly from WorkspacePaymentNegotiation final_price or counter offer ONLY
                neg = WorkspacePaymentNegotiation.objects.filter(campaign=c).order_by('-id').first()
                f_price = 0.0
                if neg and neg.final_price and float(neg.final_price) > 0:
                    f_price = float(neg.final_price)

                if f_price == 0.0:
                    c_via = str(getattr(c, 'created_via', '') or '').lower().strip()
                    if not c_via and getattr(c, 'creator', None):
                        c_via = 'direct_request'
                    is_direct = ('direct' in c_via) and ('pitch' not in c_via) and ('request' not in c_via)
                    if not is_direct:
                        if c.counter_price and float(c.counter_price) > 0:
                            f_price = float(c.counter_price)

                # 3. Actual Spend / Funds Released (Green Bar): Sum paid business installments + paid business platform fee
                f_released = 0.0
                if neg:
                    rel_biz_insts = neg.installments.filter(installment_type='business').filter(Q(is_paid=True) | Q(status__iexact='released'))
                    if rel_biz_insts.exists():
                        f_released += float(rel_biz_insts.aggregate(total=Sum('amount'))['total'] or 0)
                    if neg.business_fee_is_paid:
                        f_released += float(neg.business_platform_charge_amount or 0)

                # Exact name string from JSON payload for X-Axis mapping
                name_label = c.name if c.name else f"Campaign {c.id}"

                medium_str = c.medium or ""
                deliv_str = ", ".join([d.name for d in c.deliverables.all()])

                if f_price > 0 or f_released > 0:
                    budget_vs_spend.append({
                        "id": c.id,
                        "campaign": name_label,
                        "target_budget": t_budget,
                        "final_price": f_price,
                        "funds_released": f_released,
                        "medium": medium_str,
                        "deliverables_text": deliv_str,
                        "status": c.status,
                    })
        except Exception as e:
            print("Error computing budget_vs_spend:", e)

        return Response({
            "stats": {
                "avg_progress": round(avg_progress, 1),
                "total_allocated_budget": total_allocated_budget,
                "total_paid_amount": total_paid_amount,
                "last_paid_milestone": last_paid_milestone,
                "avg_duration_days": avg_duration_days,
                "total_campaigns_count": total_campaigns_count,
                "total_reach": total_reach,
                "total_impressions": total_impressions,
                "avg_engagement": avg_engagement,
                "total_roi": total_roi,
            },
            "top_campaigns": top_campaigns,
            "budget_vs_spend": budget_vs_spend,
        })

def populate_deliverables_from_pitch(campaign, pitch):
    if not pitch or not pitch.deliverables:
        return

    deliv_raw = pitch.deliverables
    deliv_list = []

    if isinstance(deliv_raw, str):
        try:
            import json
            parsed = json.loads(deliv_raw)
            if isinstance(parsed, list):
                deliv_list = parsed
            elif isinstance(parsed, str):
                deliv_list = [d.strip() for d in parsed.split(",") if d.strip()]
            else:
                deliv_list = [str(parsed)]
        except Exception:
            deliv_list = [d.strip() for d in deliv_raw.split(",") if d.strip()]
    elif isinstance(deliv_raw, list):
        deliv_list = deliv_raw
    else:
        deliv_list = [str(deliv_raw)]

    import re
    for d in deliv_list:
        if not d:
            continue

        if isinstance(d, str):
            item_text = d.strip()
            item_brief = ""
        elif isinstance(d, dict):
            item_text = (d.get("text") or d.get("name") or d.get("title") or "Deliverable").strip()
            item_brief = (d.get("brief") or d.get("description") or "").strip()
        else:
            item_text = str(d).strip()
            item_brief = ""

        if not item_text:
            continue

        multiplier = 1
        mult_match = re.match(r'^(\d{1,2})\s*(?:[×]|(?:\s+[xX]\s+))\s*(.+)$', item_text)
        if mult_match:
            try:
                multiplier = min(max(1, int(mult_match.group(1))), 10)
                raw_title = mult_match.group(2).strip()
            except (ValueError, TypeError):
                multiplier = 1
                raw_title = item_text
        else:
            raw_title = item_text

        raw_low = raw_title.lower()
        if "reel" in raw_low:
            d_type = "reel"
        elif "story" in raw_low:
            d_type = "story"
        elif "video" in raw_low or "tiktok" in raw_low or "youtube" in raw_low:
            d_type = "video"
        elif "post" in raw_low or "photo" in raw_low or "static" in raw_low:
            d_type = "post"
        else:
            d_type = "post"

        for i in range(max(1, multiplier)):
            deliv_name = f"{raw_title} #{i + 1}" if multiplier > 1 else raw_title
            if not Deliverable.objects.filter(campaign=campaign, name=deliv_name).exists():
                Deliverable.objects.create(
                    campaign=campaign,
                    name=deliv_name,
                    type=d_type,
                    status="Pending Review",
                    brief=item_brief
                )

def extract_pitch_niche_and_platform(pitch):
    niche_val = (getattr(pitch, "niche", "") or "").strip()
    if not niche_val and getattr(pitch, "niches", None):
        if isinstance(pitch.niches, list) and len(pitch.niches) > 0:
            first_n = pitch.niches[0]
            niche_val = str(first_n.get("name") if isinstance(first_n, dict) else first_n).strip()

    tags = pitch.tags or []
    if isinstance(tags, str):
        try:
            import json
            tags = json.loads(tags)
        except Exception:
            tags = [tags]
    if not isinstance(tags, list):
        tags = [str(tags)]

    known_platforms = {"instagram", "youtube", "tiktok", "facebook", "linkedin", "x", "twitter", "snapchat", "pinterest", "threads"}
    known_languages = {"english", "sinhala", "tamil", "all languages", "arabic", "french", "spanish", "german", "mandarin", "hindi"}
    known_countries = {"sri lanka", "india", "united states", "usa", "uk", "united kingdom", "canada", "australia", "singapore", "malaysia", "uae", "dubai"}
    known_general = {"general", "all", "deliverable", "post", "reel", "story", "video"}

    if not niche_val:
        for t in tags:
            if isinstance(t, dict):
                s = str(t.get("name") or t.get("type") or t.get("niche") or "").strip()
            else:
                s = str(t).strip()
            s_low = s.lower()
            if s and s_low not in known_platforms and s_low not in known_languages and s_low not in known_countries and s_low not in known_general and "sri lanka" not in s_low:
                niche_val = s
                break

    if not niche_val and pitch.creator and hasattr(pitch.creator, "creator_profile") and pitch.creator.creator_profile and pitch.creator.creator_profile.niches:
        cr_niches = pitch.creator.creator_profile.niches
        if isinstance(cr_niches, list) and cr_niches:
            first_n = cr_niches[0]
            if isinstance(first_n, dict):
                niche_val = str(first_n.get("name") or first_n.get("type") or "").strip()
            else:
                niche_val = str(first_n).strip()

    if not niche_val:
        niche_val = "Fashion"

    platform_val = pitch.platform or ""
    if not platform_val:
        for t in tags:
            s = str(t).strip()
            if s.lower() in known_platforms:
                platform_val = s.capitalize()
                break
    if not platform_val:
        platform_val = "Instagram"

    return niche_val, platform_val

def _execute_pitch_conversion(pitch, request_data=None):
    """Automatically convert an accepted pitch or accepted pitch counter into an active Live Campaign."""
    if request_data is None:
        request_data = {}
    last_price = (pitch.counter_history[-1].get("price") if pitch.counter_history else None) or pitch.counter_offer or pitch.budget
    final_budget = last_price
    pitch.budget = final_budget
    pitch.counter_offer = final_budget
    pitch.status = "accepted"
    pitch.save()

    niche_val, platform_val = extract_pitch_niche_and_platform(pitch)
    category_val = pitch.category or niche_val
    niche_val_final = pitch.niche or niche_val
    deliv_lang_str = ", ".join(pitch.delivery_languages) if isinstance(pitch.delivery_languages, list) else str(pitch.delivery_languages or "")
    country_val = pitch.country or ""
    province_val = pitch.province_state or ""
    district_val = pitch.district_city or ""

    # Check if Campaign already exists for this pitch
    campaign = Campaign.objects.filter(
        brand=pitch.brand,
        creator=pitch.creator,
        name=pitch.campaign_name,
        created_via="pitch"
    ).first()

    if not campaign:
        campaign = Campaign.objects.create(
            name=request_data.get("name") or pitch.campaign_name,
            brand=pitch.brand,
            creator=pitch.creator,
            budget=final_budget,
            counter_price=final_budget,
            counter_history=pitch.counter_history,
            category=category_val,
            campaign_category=category_val,
            niche=niche_val_final,
            delivery_language=deliv_lang_str,
            country=country_val,
            province=province_val,
            district=district_val,
            platform=pitch.platform or platform_val,
            medium=pitch.platform or platform_val,
            brief=request_data.get("brief") or pitch.description or f"Campaign proposal based on pitch: {pitch.campaign_name}",
            status="Live",
            start_date=pitch.start_date or request_data.get("start_date") or pitch.sent_date or "2026-08-01",
            end_date=pitch.end_date or request_data.get("end_date") or "",
            created_via="pitch",
        )
    else:
        campaign.budget = final_budget
        campaign.counter_price = final_budget
        campaign.counter_history = pitch.counter_history
        campaign.status = "Live"
        campaign.category = category_val
        campaign.campaign_category = category_val
        campaign.niche = niche_val_final
        if pitch.start_date:
            campaign.start_date = pitch.start_date
        if pitch.end_date:
            campaign.end_date = pitch.end_date
        if deliv_lang_str:
            campaign.delivery_language = deliv_lang_str
        if country_val:
            campaign.country = country_val
        if province_val:
            campaign.province = province_val
        if district_val:
            campaign.district = district_val
        if not campaign.platform:
            campaign.platform = pitch.platform or platform_val
            campaign.medium = pitch.platform or platform_val
        campaign.save()

    try:
        from WorkspacePayment.models import WorkspacePaymentNegotiation
        neg, _ = WorkspacePaymentNegotiation.objects.get_or_create(campaign=campaign)
        neg.final_price = final_budget
        neg.status = 'creator_accepted'
        neg.save()
    except Exception as e:
        print("Error creating WorkspacePaymentNegotiation:", e)

    populate_deliverables_from_pitch(campaign, pitch)
    return campaign

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

        camp_name = str(request.data.get("campaign_name", "")).strip()
        brand_id = request.data.get("brand")
        if camp_name:
            if Campaign.objects.filter(name__iexact=camp_name).filter(models.Q(brand_id=brand_id) | models.Q(brand=request.user)).exists():
                return Response(
                    {"campaign_name": ["A campaign with this name already exists. Please choose a unique campaign name."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        attachment = self.request.FILES.get("attachment")
        if attachment:
            serializer.save(creator=self.request.user, attachment=attachment, status="pending_admin")
        else:
            serializer.save(creator=self.request.user, status="pending_admin")

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.status == "accepted_by_business":
            last_p = (instance.counter_history[-1].get("price") if (instance.counter_history and isinstance(instance.counter_history, list) and len(instance.counter_history) > 0) else None) or instance.counter_offer or instance.budget
            if last_p:
                instance.budget = last_p
                instance.counter_offer = last_p
                if instance.counter_history and isinstance(instance.counter_history, list) and len(instance.counter_history) > 0:
                    history = list(instance.counter_history)
                    history[-1]["status"] = "accepted_by_business"
                    instance.counter_history = history
                instance.save()

    def perform_destroy(self, instance):
        if instance.brand and instance.creator:
            Campaign.objects.filter(brand=instance.brand, creator=instance.creator, created_via="pitch", name=instance.campaign_name).delete()
        instance.delete()

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
        """Business accepts pitch → status becomes accepted_by_business (awaiting admin conversion)"""
        pitch = self.get_object()
        last_p = (pitch.counter_history[-1].get("price") if (pitch.counter_history and isinstance(pitch.counter_history, list) and len(pitch.counter_history) > 0) else None) or pitch.counter_offer or pitch.budget
        if last_p:
            pitch.budget = last_p
            pitch.counter_offer = last_p
        pitch.status = "accepted_by_business"
        if pitch.counter_history and isinstance(pitch.counter_history, list) and len(pitch.counter_history) > 0:
            history = list(pitch.counter_history)
            history[-1]["status"] = "accepted_by_business"
            pitch.counter_history = history
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
        """Business sends counter offer → goes to biz_countered (directly visible to creator)"""
        pitch = self.get_object()
        if pitch.counter_count >= 4:
            return Response({"error": "Counter offer limit reached. Maximum counter offer rounds allowed."}, status=400)
        pitch.counter_count += 1
        pitch.status = "biz_countered"
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
            "status": "biz_countered"
        })
        pitch.counter_history = history
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def creator_counter(self, request, pk=None):
        """Creator sends counter offer → goes to pitch_countered (directly visible to business)"""
        pitch = self.get_object()
        if pitch.counter_count >= 4:
            return Response({"error": "Counter offer limit reached. Maximum counter offer rounds allowed."}, status=400)
        pitch.counter_count += 1
        pitch.status = "pitch_countered"
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
            "status": "pitch_countered"
        })
        pitch.counter_history = history
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def convert_to_campaign(self, request, pk=None):
        """Admin converts pitch to Live campaign"""
        pitch = self.get_object()
        campaign = _execute_pitch_conversion(pitch, request.data)
        return Response({
            "message": "Pitch accepted and campaign created by admin.",
            "pitch": PitchSerializer(pitch).data,
            "campaign_id": campaign.id
        })

    @action(detail=True, methods=["post"])
    def accept_counter(self, request, pk=None):
        """Creator or Business accepts counter offer → status becomes accepted_by_business (awaiting admin conversion)"""
        pitch = self.get_object()
        last_p = (pitch.counter_history[-1].get("price") if (pitch.counter_history and isinstance(pitch.counter_history, list) and len(pitch.counter_history) > 0) else None) or pitch.counter_offer or pitch.budget
        if last_p:
            pitch.budget = last_p
            pitch.counter_offer = last_p
        pitch.status = "accepted_by_business"
        if pitch.counter_history and isinstance(pitch.counter_history, list) and len(pitch.counter_history) > 0:
            history = list(pitch.counter_history)
            history[-1]["status"] = "accepted_by_business"
            pitch.counter_history = history
        pitch.save()
        return Response(PitchSerializer(pitch).data)

    @action(detail=True, methods=["post"])
    def decline_counter(self, request, pk=None):
        pitch = self.get_object()
        pitch.status = "declined"
        pitch.decline_reason = request.data.get("reason") or request.data.get("decline_reason") or "Counter offer declined."
        pitch.save()
        return Response(PitchSerializer(pitch).data)



class CampaignStatsView(APIView):
    """Return aggregated campaign statistics for the current authenticated business user or creator."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum, Count, Avg
        user = request.user
        has_business = hasattr(user, "business_profile")
        has_creator = hasattr(user, "creator_profile")

        active_statuses = ["Live", "live", "Active", "active", "Completed", "completed", "Approved", "approved", "In_Progress", "in_progress", "Payment_Verified", "accepted"]

        if has_business:
            qs = Campaign.objects.filter(brand=user)
            total_campaigns = qs.count()
            live_now = qs.filter(status__in=["Live", "live", "Active", "active"]).count()
            total_budget = float(qs.aggregate(total=Sum("budget"))["total"] or 0)
        elif has_creator:
            qs = Campaign.objects.filter(creator=user)
            active_qs = qs.filter(status__in=active_statuses)
            total_campaigns = active_qs.count()
            live_now = active_qs.filter(status__in=["Live", "live", "Active", "active"]).count()
            total_budget = float(active_qs.aggregate(total=Sum("budget"))["total"] or 0)
        else:
            qs = Campaign.objects.none()
            total_campaigns = 0
            live_now = 0
            total_budget = 0.0

        avg_progress = float(qs.aggregate(avg=Avg("progress"))["avg"] or 0)
        avg_engagement = round(3.0 + (avg_progress / 100) * 9.0, 1)

        total_reach = int(total_budget * 1000)
        total_impressions = int(total_budget * 2500)
        total_roi = 4.1 if total_budget > 0 else 0.0

        avg_creator_rating = 0.0
        if has_creator and hasattr(user, "creator_profile"):
            avg_creator_rating = user.creator_profile.average_rating
        elif has_business:
            from CreatorRating.models import BusinessRating
            avg_res = BusinessRating.objects.filter(brand=user).aggregate(avg=Avg("rating"))["avg"]
            avg_creator_rating = round(float(avg_res), 1) if avg_res is not None else 0.0

        return Response({
            "total_campaigns": total_campaigns,
            "live_now": live_now,
            "total_budget": total_budget,
            "avg_engagement": avg_engagement,
            "avg_rating": avg_creator_rating,
            "avg_creator_rating": avg_creator_rating,
            "average_rating": avg_creator_rating,
            "total_reach": total_reach,
            "total_impressions": total_impressions,
            "total_roi": total_roi,
        })

class CreatorEarningsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        campaigns = Campaign.objects.filter(creator=user)
        from .models import PaymentInstallment
        
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
        
        active_statuses = {"active", "live", "completed", "approved", "in_progress", "payment_verified", "accepted"}
        dropped_statuses = {"declined", "rejected", "cancelled"}

        released_sum = 0.0
        pending_sum = 0.0

        for c in campaigns:
            st = str(c.status or "").strip().lower()
            neg_final = 0.0
            try:
                from WorkspacePayment.models import WorkspacePaymentNegotiation
                neg_obj = WorkspacePaymentNegotiation.objects.filter(campaign=c).order_by('-id').first()
                if neg_obj and neg_obj.final_price and float(neg_obj.final_price) > 0:
                    neg_final = float(neg_obj.final_price)
            except Exception:
                pass

            camp_amount = neg_final if neg_final > 0 else float(c.counter_price or c.per_creator_budget or c.budget or 0)
            brand_name = c.brand.username if c.brand else "Brand"

            if st in dropped_statuses:
                continue

            if st in active_statuses:
                total_earned += camp_amount
                if st == "completed":
                    date_val = c.start_date or c.created_at or c.due_date
                    if date_val:
                        try:
                            m_idx = date_val.month - 1
                            if 0 <= m_idx <= 11:
                                default_months[m_idx]["v"] += camp_amount
                        except Exception:
                            pass

            workspace_insts = []
            if neg_obj:
                workspace_insts = list(neg_obj.installments.filter(installment_type='creator').order_by('id'))
            if not workspace_insts:
                workspace_insts = list(c.workspace_installments.filter(installment_type='creator').order_by('id'))

            if workspace_insts:
                for inst in workspace_insts:
                    amount_val = float(inst.amount or 0)
                    is_rel = bool(inst.is_paid or str(inst.status or '').lower() == 'released')
                    if is_rel:
                        released_sum += amount_val
                        paid_dt = inst.paid_date or inst.updated_at or inst.created_at
                        if paid_dt:
                            try:
                                if hasattr(paid_dt, 'month'):
                                    m_idx = paid_dt.month - 1
                                else:
                                    m_idx = int(str(paid_dt).split('-')[1]) - 1
                                if 0 <= m_idx <= 11:
                                    default_months[m_idx]["v"] += amount_val
                            except Exception:
                                pass
                        transactions.append({
                            "id": inst.id + c.id * 10000,
                            "campaign": f"{c.name} ({inst.title})" if inst.title else c.name,
                            "brand": brand_name,
                            "amount": amount_val,
                            "date": str(inst.paid_date or "Paid"),
                            "status": "paid",
                            "type": "credit",
                            "period": "Monthly",
                        })
                    else:
                        pending_sum += amount_val
                        transactions.append({
                            "id": inst.id + c.id * 10000,
                            "campaign": f"{c.name} ({inst.title})" if inst.title else c.name,
                            "brand": brand_name,
                            "amount": amount_val,
                            "date": str(inst.created_at or "Pending"),
                            "status": "escrow",
                            "type": "pending",
                            "period": "Monthly",
                        })
            else:
                payments = c.payments.all()
                if payments.exists():
                    for p in payments:
                        amount_val = float(p.amount)
                        p_st = str(p.status or "").strip().lower()
                        if p_st in dropped_statuses:
                            continue
                        
                        if p_st in ("released", "paid"):
                            released_sum += amount_val
                            if p.payment_date:
                                try:
                                    parts = str(p.payment_date).split('-')
                                    if len(parts) >= 2:
                                        m_idx = int(parts[1]) - 1
                                        if 0 <= m_idx <= 11:
                                            default_months[m_idx]["v"] += amount_val
                                except Exception:
                                    pass
                            transactions.append({
                                "id": p.id + c.id * 10000,
                                "campaign": c.name,
                                "brand": brand_name,
                                "amount": amount_val,
                                "date": str(p.payment_date or "Paid"),
                                "status": "paid",
                                "type": "credit",
                                "period": "Monthly",
                            })
                        else:
                            pending_sum += amount_val
                            transactions.append({
                                "id": p.id + c.id * 10000,
                                "campaign": c.name,
                                "brand": brand_name,
                                "amount": amount_val,
                                "date": str(p.payment_date or "Pending"),
                                "status": "escrow",
                                "type": "pending",
                                "period": "Monthly",
                            })
                else:
                    if st == "completed":
                        released_sum += camp_amount
                        transactions.append({
                            "id": c.id * 10000,
                            "campaign": c.name,
                            "brand": brand_name,
                            "amount": camp_amount,
                            "date": "Completed",
                            "status": "paid",
                            "type": "credit",
                            "period": "Monthly",
                        })
                    else:
                        pending_sum += camp_amount
                        transactions.append({
                            "id": c.id * 10000,
                            "campaign": c.name,
                            "brand": brand_name,
                            "amount": camp_amount,
                            "date": "Pending",
                            "status": "escrow",
                            "type": "pending",
                            "period": "Monthly",
                        })
                
        transactions.sort(key=lambda x: x["id"], reverse=True)
        in_escrow = pending_sum
        
        return Response({
            "totalEarned": round(total_earned, 2),
            "inEscrow": round(in_escrow, 2),
            "pending": round(pending, 2),
            "monthly": default_months,
            "transactions": transactions
        })
