from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup, IndexView, InspectView
from wagtail.snippets.models import register_snippet
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.views.generic.models import MenuItem as GenericMenuItem
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import path, reverse
from .models import Campaign, CampaignCategory, CampaignLanguage, CampaignDeliverable, CampaignPlatform, Pitch, extract_currency_symbol
from WorkspacePayment.models import WorkspacePaymentNegotiation
from .views import download_campaign_pdf_view

from wagtail.admin.ui.tables import TitleColumn
from django.utils.translation import gettext_lazy

# Custom Index View to customize labels and add PDF download button
class CampaignIndexView(IndexView):
    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            # Prefer inspect_url over edit_url so clicking the campaign name link directly opens the View (inspect) page
            if inspect_url := self.get_inspect_url(instance):
                return inspect_url
            return self.get_edit_url(instance)

        if not self.model:
            return column_class(
                "name",
                label=gettext_lazy("Name"),
                accessor=str,
                get_url=get_url,
            )
        return self._get_custom_column(
            field_name, column_class, get_url=get_url, **kwargs
        )

    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)
        download_url = reverse("download_campaign_pdf", args=[instance.pk])
        buttons.append(
            GenericMenuItem(
                "Download PDF",
                url=download_url,
                icon_name="download",
                priority=25,
            )
        )
        for item in buttons:
            if hasattr(item, "label") and (str(item.label) == "Inspect" or item.label == "Inspect"):
                item.label = "View"
                item.icon_name = "view"
        return buttons

# Custom Inspect View to populate related lists
class CampaignInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        context["instance"] = campaign

        # Fetch Workspace Payment Negotiation & Installments
        negotiation = campaign.payment_negotiations.first()
        workspace_installments = list(campaign.workspace_installments.all().order_by("installment_type", "id"))
        if not workspace_installments and negotiation:
            workspace_installments = list(negotiation.installments.all().order_by("installment_type", "id"))

        # Build Milestones list from Workspace Payment Installments
        milestones_list = []
        if workspace_installments:
            for inst in workspace_installments:
                inst_type_label = "Business (Inbound)" if inst.installment_type == "business" else "Creator (Outbound)"
                status_label = "Released" if (inst.is_paid or inst.status == "released") else ("In Escrow" if inst.status == "in_escrow" else inst.status.replace("_", " ").title())
                milestones_list.append({
                    "title": inst.title,
                    "amount": inst.amount,
                    "type": inst_type_label,
                    "installment_type": inst.installment_type,
                    "status": status_label,
                    "is_done": bool(inst.is_paid or inst.status == "released"),
                    "is_paid": inst.is_paid,
                    "paid_date": inst.paid_date,
                    "receipt_image": inst.receipt_image,
                    "receipt_url": inst.receipt_url,
                })
        elif campaign.milestones.exists():
            for m in campaign.milestones.all():
                milestones_list.append({
                    "title": m.title,
                    "amount": None,
                    "type": "General",
                    "installment_type": "creator",
                    "status": "Done" if m.is_done else "Pending",
                    "is_done": m.is_done,
                    "is_paid": m.is_done,
                    "paid_date": None,
                })

        # Build Tasks list from campaign tasks and deliverables
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
                is_done = d.status in ["Approved", "Published"]
                tasks_list.append({
                    "title": f"{d.name} ({d.type})",
                    "due_date": d.deadline or "-",
                    "is_done": is_done,
                })

        # Build Payments list
        payments_list = []
        if workspace_installments:
            for p in workspace_installments:
                payments_list.append({
                    "title": p.title,
                    "milestone_name": p.title,
                    "installment_type": p.installment_type,
                    "amount": p.amount,
                    "paid_date": p.paid_date,
                    "payment_date": p.paid_date,
                    "receipt_image": p.receipt_image,
                    "receipt_url": p.receipt_url,
                    "status": "Released" if (p.is_paid or p.status == "released") else ("In Escrow" if p.status == "in_escrow" else p.status.replace("_", " ").title()),
                    "is_paid": p.is_paid,
                })
        elif campaign.payments.exists():
            for p in campaign.payments.all():
                payments_list.append({
                    "title": p.milestone_name,
                    "milestone_name": p.milestone_name,
                    "installment_type": "creator",
                    "amount": p.amount,
                    "paid_date": p.payment_date,
                    "payment_date": p.payment_date,
                    "receipt_image": None,
                    "receipt_url": None,
                    "status": p.status,
                    "is_paid": p.status == "Released",
                })

        context["negotiation"] = negotiation
        context["workspace_installments"] = workspace_installments
        context["milestones"] = milestones_list
        context["tasks"] = tasks_list
        context["deliverables"] = campaign.deliverables.all()
        context["payments"] = payments_list
        context["files"] = campaign.files.all()
        context["tickets"] = campaign.tickets.all()
        context["currency_symbol"] = extract_currency_symbol(campaign) or "Rs"
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        status = request.POST.get("status")
        admin_review = request.POST.get("admin_review")

        if status == "Approve_Creator_Counter":
            self.object.status = "Countered"
            messages.success(request, f"Creator counter offer approved for '{self.object.name}'. It is now visible to the business.")
        elif status == "Approve_Business_Counter":
            self.object.status = "Business_Countered"
            messages.success(request, f"Business counter offer approved for '{self.object.name}'. It is now visible to the creator.")
        elif status == "Reject_Counter":
            self.object.status = "Rejected"
            self.object.decline_reason = admin_review or "Counter offer rejected by admin."
            messages.warning(request, f"Counter offer rejected for '{self.object.name}'.")
        elif status in ["Live_Countered", "Approve_Accepted_Counter"] or (status == "Live" and self.object.status == "Accepted_Pending_Admin"):
            if self.object.counter_price:
                self.object.budget = self.object.counter_price
            elif self.object.counter_history and len(self.object.counter_history) > 0:
                last_p = self.object.counter_history[-1].get("price")
                if last_p:
                    self.object.budget = last_p
            self.object.status = "Live"
            self.object.progress = self.object.calculate_flow_progress()
            messages.success(request, f"Counter offer agreement approved! Campaign '{self.object.name}' is now Live.")
        elif status in [choice[0] for choice in self.object.STATUS_CHOICES]:
            if status == "Live":
                self.object.status = "Pending"
                messages.success(request, f"Campaign '{self.object.name}' approved! It is now Pending for creator acceptance.")
            else:
                self.object.status = status
                messages.success(request, f"Campaign status successfully updated to '{self.object.status}'.")

        self.object.admin_review = admin_review or ""
        self.object.save()

        return redirect(self.request.path)



class CampaignViewSet(SnippetViewSet):
    model = Campaign
    menu_label = "Campaigns"
    icon = "tasks"
    add_to_admin_menu = False
    add_view_enabled = False
    create_view_enabled = False
    exclude_form_fields = []
    
    # Custom Views
    index_view_class = CampaignIndexView
    inspect_view_enabled = True
    inspect_view_class = CampaignInspectView
    inspect_template_name = "campegin/inspect_campaign.html"
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddCampaignPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddCampaignPermissionPolicy(self.model)
    list_display = ("name", "brand", "creator", "status", "budget", "counter_price", "progress")
    list_export = ("id", "name", "brand.username", "creator.username", "status", "budget", "counter_price", "start_date", "progress")
    list_filter = ("status",)
    search_fields = ("name", "brand__username", "creator__username")

import django_filters
from wagtail.admin.filters import WagtailFilterSet

class CampaignCategoryFilterSet(WagtailFilterSet):
    platform = django_filters.CharFilter(field_name="platform", lookup_expr="icontains")

    class Meta:
        model = CampaignCategory
        fields = ["platform"]

class CampaignCategoryViewSet(SnippetViewSet):
    model = CampaignCategory
    menu_label = "Categories"
    icon = "tag"
    add_to_admin_menu = False
    filterset_class = CampaignCategoryFilterSet
    list_display = ("platform", "type", "duration", "min_price", "max_price")
    list_export = ("id", "platform", "type", "duration", "name", "min_price", "max_price")
    list_filter = ("platform",)
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

class CampaignLanguageViewSet(SnippetViewSet):
    model = CampaignLanguage
    menu_label = "Languages"
    icon = "globe"
    add_to_admin_menu = False
    list_export = ("id", "name")
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

class CampaignDeliverableViewSet(SnippetViewSet):
    model = CampaignDeliverable
    menu_label = "Deliverables"
    icon = "doc-full"
    add_to_admin_menu = False
    list_display = ("id", "platform", "name")
    list_export = ("id", "platform", "name")
    list_filter = ("platform",)
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

class CampaignPlatformViewSet(SnippetViewSet):
    model = CampaignPlatform
    menu_label = "Target Platforms"
    icon = "desktop"
    add_to_admin_menu = False
    list_display = ("id", "platform_id", "name", "color", "logo_preview")
    list_export = ("id", "platform_id", "name", "color", "logo")

class PitchIndexView(IndexView):
    """Custom index view so the list row action says 'View' instead of 'Inspect'."""
    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            if inspect_url := self.get_inspect_url(instance):
                return inspect_url
            return self.get_edit_url(instance)

        if not self.model:
            return column_class("campaign_name", label=gettext_lazy("Campaign Name"), accessor=str, get_url=get_url)
        return self._get_custom_column(field_name, column_class, get_url=get_url, **kwargs)

    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)
        for item in buttons:
            if hasattr(item, "label") and (str(item.label) == "Inspect" or item.label == "Inspect"):
                item.label = "View"
                item.icon_name = "view"
        return buttons


class PitchInspectView(InspectView):
    STATUS_CHOICES = (
        ("pending_admin", "Pending Admin Approval"),
        ("pending", "Pending Business Review"),
        ("accepted_by_business", "Accepted by Business – Awaiting Admin Conversion"),
        ("counter_offer", "Counter Offer Sent by Business"),
        ("pitch_counter_pending", "Creator Counter Pending Admin"),
        ("pitch_countered", "Creator Counter Approved"),
        ("biz_counter_pending", "Business Counter Pending Admin"),
        ("biz_countered", "Business Counter Approved"),
        ("accepted", "Accepted – Converted to Campaign"),
        ("declined", "Declined"),
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pitch = self.get_object()
        st = str(pitch.status).lower().strip()
        context["instance"] = pitch
        context["object"] = pitch
        context["pitch_status"] = st
        context["status"] = st
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("action", "")
        status_val = request.POST.get("status", "")
        admin_review = request.POST.get("admin_review") or ""

        if action == "approve_pitch" or status_val == "pending":
            # Admin approves initial pitch → visible to business
            self.object.status = "pending"
            self.object.save()
            messages.success(request, f"Pitch '{self.object.campaign_name}' approved and forwarded to the brand.")

        elif action == "accept_pitch" or status_val == "accepted":
            # Admin accepts pitch directly and converts to live campaign
            self.object.status = "accepted"
            self.object.save()
            from .models import Campaign
            campaign = Campaign.objects.filter(name=self.object.campaign_name, brand=self.object.brand).first()
            tags = self.object.tags or []
            if isinstance(tags, str):
                try:
                    import json
                    tags = json.loads(tags)
                except Exception:
                    tags = [tags]
            if not isinstance(tags, list):
                tags = [str(tags)]
            known_platforms = {"Instagram", "YouTube", "TikTok", "Facebook", "LinkedIn", "X", "Twitter", "Snapchat", "Pinterest"}
            niche_val = next((str(t).strip() for t in tags if str(t).strip() and not any(p.lower() == str(t).strip().lower() for p in known_platforms)), "")
            if not niche_val and self.object.creator and hasattr(self.object.creator, "creator_profile") and self.object.creator.creator_profile.niches:
                cr_niches = self.object.creator.creator_profile.niches
                if isinstance(cr_niches, list) and cr_niches:
                    niche_val = str(cr_niches[0]).strip()
            if not niche_val:
                niche_val = "Tech"
            platform_val = next((str(t).strip() for t in tags if any(p.lower() == str(t).strip().lower() for p in known_platforms)), "Instagram")

            if not campaign:
                campaign = Campaign.objects.create(
                    name=self.object.campaign_name,
                    brand=self.object.brand,
                    creator=self.object.creator,
                    budget=self.object.budget,
                    category=niche_val,
                    medium=platform_val,
                    brief=self.object.description or f"Campaign proposal based on pitch: {self.object.campaign_name}",
                    status="Live",
                    progress=62,
                    start_date=self.object.sent_date or "2026-08-01",
                    created_via="pitch",
                )
            else:
                if not campaign.category or campaign.category == "General":
                    campaign.category = niche_val
                    campaign.save(update_fields=["category"])
            from .views import populate_deliverables_from_pitch
            populate_deliverables_from_pitch(campaign, self.object)
            messages.success(request, f"Pitch '{self.object.campaign_name}' accepted and converted to Live Campaign.")

        elif action == "reject_pitch" or status_val == "declined":
            self.object.status = "declined"
            self.object.decline_reason = admin_review or "Pitch proposal rejected by admin."
            self.object.save()
            messages.warning(request, f"Pitch '{self.object.campaign_name}' rejected.")

        elif action == "approve_creator_counter" or status_val == "approve_creator_counter":
            # Admin approves creator's counter → now visible to business
            self.object.status = "pitch_countered"
            if self.object.counter_history:
                history = list(self.object.counter_history)
                if history:
                    history[-1]["status"] = "pitch_countered"
                    self.object.counter_history = history
            self.object.save()
            messages.success(request, f"Creator counter offer approved for '{self.object.campaign_name}'.")

        elif action == "approve_biz_counter" or status_val == "approve_biz_counter":
            # Admin approves business's counter → now visible to creator
            self.object.status = "biz_countered"
            if self.object.counter_history:
                history = list(self.object.counter_history)
                if history:
                    history[-1]["status"] = "biz_countered"
                    self.object.counter_history = history
            self.object.save()
            messages.success(request, f"Business counter offer approved for '{self.object.campaign_name}'.")

        elif action == "reject_counter" or status_val == "reject_counter":
            self.object.status = "declined"
            self.object.decline_reason = admin_review or "Counter offer rejected by admin."
            self.object.save()
            messages.warning(request, f"Counter offer rejected for '{self.object.campaign_name}'.")

        elif status_val == "pending_admin":
            self.object.status = "pending_admin"
            self.object.save()
            messages.info(request, f"Pitch '{self.object.campaign_name}' status reset to Pending Admin Approval.")

        elif action == "save_notes":
            messages.success(request, f"Notes saved for pitch '{self.object.campaign_name}'.")

        return redirect(self.request.path)


class PitchViewSet(SnippetViewSet):
    model = Pitch
    menu_label = "Pitches"
    icon = "mail"
    add_to_admin_menu = False
    add_view_enabled = False
    create_view_enabled = False
    index_view_class = PitchIndexView
    inspect_view_enabled = True
    inspect_view_class = PitchInspectView
    inspect_template_name = "campegin/inspect_pitch.html"
    list_display = ("campaign_name", "creator", "brand", "budget", "status", "sent_date")
    list_export = ("id", "campaign_name", "creator.username", "brand.username", "budget", "status", "sent_date")
    list_filter = ("status",)
    search_fields = ("campaign_name", "creator__username", "brand__username")

from .models import Campaign, CampaignCategory, CampaignLanguage, CampaignDeliverable, CampaignPlatform, Pitch, CampaignNiche
from wagtail.permission_policies.base import ModelPermissionPolicy
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.ui.tables import Column

class CampaignNichePermissionPolicy(ModelPermissionPolicy):
    def user_has_permission(self, user, action):
        if action in ["add", "delete"]:
            return False
        return super().user_has_permission(user, action)

    def user_has_any_permission(self, user, actions):
        allowed = [a for a in actions if a not in ["add", "delete"]]
        if not allowed:
            return False
        return super().user_has_any_permission(user, allowed)

class CampaignNicheForm(WagtailAdminModelForm):
    class Meta:
        model = CampaignNiche
        fields = ["name", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "name" in self.fields:
            self.fields["name"].disabled = True
            self.fields["name"].required = False

class CampaignNicheViewSet(SnippetViewSet):
    model = CampaignNiche
    base_form_class = CampaignNicheForm
    permission_policy = CampaignNichePermissionPolicy(CampaignNiche)
    menu_label = "Niches"
    icon = "tag"
    menu_name = "campaign_niches"
    list_display = ("name", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name",)

import re

class WorkspacePaymentIndexView(IndexView):
    def auto_create_negotiations(self):
        try:
            live_campaigns = Campaign.objects.filter(status__in=["Live", "Completed"])
            for camp in live_campaigns:
                WorkspacePaymentNegotiation.objects.get_or_create(
                    campaign=camp,
                    defaults={
                        "final_price": camp.counter_price or camp.budget or 0,
                        "status": "admin_approved" if str(getattr(camp, "created_via", "")).lower() in ["pitch", "request"] else "pending_creator_approval",
                    }
                )
        except Exception as e:
            pass

    def get_base_queryset(self):
        self.auto_create_negotiations()
        qs = super().get_base_queryset() if hasattr(super(), "get_base_queryset") else self.model.objects.all()
        return qs.filter(campaign__status__in=["Live", "Completed"])

    def get_queryset(self):
        self.auto_create_negotiations()
        qs = super().get_queryset() if hasattr(super(), "get_queryset") else self.model.objects.all()
        return qs.filter(campaign__status__in=["Live", "Completed"])

    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            if inspect_url := self.get_inspect_url(instance):
                return inspect_url
            return self.get_edit_url(instance)

        if not self.model:
            return column_class("campaign", label=gettext_lazy("Campaign"), accessor=str, get_url=get_url)
        return self._get_custom_column(field_name, column_class, get_url=get_url, **kwargs)

    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)
        for item in buttons:
            if hasattr(item, "label") and (str(item.label) == "Inspect" or item.label == "Inspect"):
                item.label = "View / Divide Payment"
                item.icon_name = "view"
        return buttons


class WorkspacePaymentInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        negotiation = self.object
        campaign = negotiation.campaign

        context['instance'] = negotiation
        context['brand_name'] = getattr(campaign, 'brand_name', None) or (campaign.brand.username if campaign and campaign.brand else "Brand")
        context['creator_name'] = getattr(campaign, 'creator_name', None) or (campaign.creator.username if campaign and campaign.creator else "Creator")

        created_via = str(getattr(campaign, 'created_via', 'direct_request') or 'direct_request').lower().strip()
        is_direct_request = (created_via == 'direct_request')
        context['created_via'] = created_via
        context['is_direct_request'] = is_direct_request

        min_budg = getattr(campaign, 'min_budget', None) or getattr(campaign, 'min_price', None) or "10000.00"
        max_budg = getattr(campaign, 'max_budget', None) or getattr(campaign, 'max_price', None) or "51000.00"
        cr_min = getattr(campaign, 'creator_min_price', None) or getattr(campaign, 'min_price', None) or "20000.00"
        cr_max = getattr(campaign, 'creator_max_price', None) or getattr(campaign, 'max_price', None) or "49000.00"

        symbol = "Rs"
        if campaign and campaign.country:
            country_currency_map = {
                "Sri Lanka": "LKR (Rs)",
                "United States": "USD ($)",
                "United Kingdom": "GBP (£)",
                "India": "INR (₹)",
                "United Arab Emirates": "AED (AED)",
                "European Union": "EUR (€)",
                "Canada": "CAD ($)",
                "Australia": "AUD ($)",
                "Singapore": "SGD ($)",
            }
            c_name = str(campaign.country.name) if hasattr(campaign.country, "name") else str(campaign.country)
            curr_str = country_currency_map.get(c_name, "LKR (Rs)")
            match = re.search(r'\(([^)]+)\)', curr_str)
            if match:
                symbol = match.group(1)

        try:
            cr_min_val = float(cr_min)
            cr_max_val = float(cr_max)
            min_budg_val = float(min_budg)
            max_budg_val = float(max_budg)

            if not is_direct_request:
                eff_price = getattr(campaign, 'counter_price', None) or getattr(campaign, 'budget', 0)
                final_val = float(negotiation.final_price or eff_price or 0)
                if (not negotiation.final_price or float(negotiation.final_price) == 0) and final_val > 0:
                    negotiation.final_price = final_val
                    negotiation.save(update_fields=['final_price'])
            else:
                final_val = float(negotiation.final_price or 0)
        except (ValueError, TypeError):
            cr_min_val, cr_max_val, min_budg_val, max_budg_val, final_val = 20000, 49000, 10000, 51000, 0

        business_platform_charge_pct = float(negotiation.platform_charge if negotiation.platform_charge is not None else 2.5)
        creator_platform_charge_pct = float(negotiation.creator_platform_charge if negotiation.creator_platform_charge is not None else 1.5)

        business_charge_amt = float(negotiation.business_platform_charge_amount)
        creator_charge_amt = float(negotiation.creator_platform_charge_amount)

        business_total = float(negotiation.business_total_payment)
        creator_net = float(negotiation.creator_net_received)
        total_platform_fee = float(negotiation.total_platform_fee)

        context['platform_charge_pct'] = business_platform_charge_pct
        context['business_platform_charge_pct'] = business_platform_charge_pct
        context['creator_platform_charge_pct'] = creator_platform_charge_pct
        context['formatted_platform_charge'] = f"{business_platform_charge_pct}%"
        context['formatted_business_platform_charge'] = f"{business_platform_charge_pct}%"
        context['formatted_creator_platform_charge'] = f"{creator_platform_charge_pct}%"

        context['charge_amt'] = business_charge_amt
        context['business_charge_amt'] = business_charge_amt
        context['formatted_charge_amt'] = f"{symbol}{business_charge_amt:,.2f}"
        context['formatted_business_charge_amt'] = f"{symbol}{business_charge_amt:,.2f}"
        context['creator_charge_amt'] = creator_charge_amt
        context['formatted_creator_charge_amt'] = f"{symbol}{creator_charge_amt:,.2f}"

        context['business_total'] = business_total
        context['formatted_business_total'] = f"{symbol}{business_total:,.2f}"
        context['creator_net'] = creator_net
        context['formatted_creator_net'] = f"{symbol}{creator_net:,.2f}"
        context['total_platform_fee'] = total_platform_fee
        context['formatted_total_platform_fee'] = f"{symbol}{total_platform_fee:,.2f}"

        context['creator_rate_range'] = f"{symbol}{cr_min_val:,.0f} – {symbol}{cr_max_val:,.0f}"
        context['business_budget_range'] = f"{symbol}{min_budg_val:,.0f} – {symbol}{max_budg_val:,.0f}"
        context['formatted_final_price'] = f"{symbol}{final_val:,.2f}"

        # Business Installments (Inbound Payments from Business to Admin)
        business_installments = negotiation.installments.filter(installment_type='business').order_by('id')
        total_allocated_business = sum(float(inst.amount or 0) for inst in business_installments)
        target_business_pool = final_val  # 55000 rupees base accepted final price
        remaining_business = max(0.0, target_business_pool - total_allocated_business)
        is_fully_allocated_business = (target_business_pool > 0 and (total_allocated_business >= target_business_pool or abs(total_allocated_business - target_business_pool) < 0.01))

        context['business_installments'] = business_installments
        context['target_business_pool'] = target_business_pool
        context['formatted_target_business_pool'] = f"{symbol}{target_business_pool:,.2f}"
        context['total_allocated_business'] = total_allocated_business
        context['formatted_total_allocated_business'] = f"{symbol}{total_allocated_business:,.2f}"
        context['remaining_business'] = remaining_business
        context['formatted_remaining_business'] = f"{symbol}{remaining_business:,.2f}"
        context['is_fully_allocated_business'] = is_fully_allocated_business

        # Creator Installments (Outbound Payments from Admin to Creator)
        creator_installments = negotiation.installments.filter(installment_type='creator').order_by('id')
        total_allocated_creator = sum(float(inst.amount or 0) for inst in creator_installments)
        target_creator_pool = creator_net if creator_net > 0 else final_val  # 54175 rupees net received pool
        remaining_creator = max(0.0, target_creator_pool - total_allocated_creator)
        is_fully_allocated_creator = (target_creator_pool > 0 and (total_allocated_creator >= target_creator_pool or abs(total_allocated_creator - target_creator_pool) < 0.01))

        context['creator_installments'] = creator_installments
        context['target_creator_pool'] = target_creator_pool
        context['formatted_target_creator_pool'] = f"{symbol}{target_creator_pool:,.2f}"
        context['total_allocated_creator'] = total_allocated_creator
        context['formatted_total_allocated_creator'] = f"{symbol}{total_allocated_creator:,.2f}"
        context['remaining_creator'] = remaining_creator
        context['formatted_remaining_creator'] = f"{symbol}{remaining_creator:,.2f}"
        context['is_fully_allocated_creator'] = is_fully_allocated_creator

        # Backward compatibility context
        context['installments'] = creator_installments
        context['total_allocated'] = total_allocated_creator
        context['formatted_total_allocated'] = f"{symbol}{total_allocated_creator:,.2f}"
        context['remaining_amount'] = remaining_creator
        context['formatted_remaining_amount'] = f"{symbol}{remaining_creator:,.2f}"
        context['is_fully_allocated'] = is_fully_allocated_creator

        return context

    def post(self, request, *args, **kwargs):
        negotiation = self.get_object()
        campaign = negotiation.campaign
        action_type = request.POST.get('action_type')

        if action_type == 'update_platform_charge':
            biz_charge_val = request.POST.get('business_platform_charge') or request.POST.get('platform_charge')
            creator_charge_val = request.POST.get('creator_platform_charge')

            updated_fields = []
            if biz_charge_val is not None:
                try:
                    c_val = float(str(biz_charge_val).replace('%', '').strip())
                    negotiation.platform_charge = c_val
                    updated_fields.append('platform_charge')
                except ValueError:
                    messages.error(request, "Invalid Business platform charge percentage.")

            if creator_charge_val is not None:
                try:
                    cr_val = float(str(creator_charge_val).replace('%', '').strip())
                    negotiation.creator_platform_charge = cr_val
                    updated_fields.append('creator_platform_charge')
                except ValueError:
                    messages.error(request, "Invalid Creator platform charge percentage.")

            if updated_fields:
                negotiation.save(update_fields=updated_fields)
                messages.success(request, f"Successfully updated platform charges (Business: {negotiation.platform_charge}%, Creator: {negotiation.creator_platform_charge}%).")

            return redirect(request.path)

        elif action_type == 'update_business_fee_status':
            is_paid = request.POST.get('business_fee_is_paid') == 'true'
            paid_date = request.POST.get('business_fee_paid_date')
            negotiation.business_fee_is_paid = is_paid
            if paid_date:
                negotiation.business_fee_paid_date = paid_date
            elif is_paid and not negotiation.business_fee_paid_date:
                from django.utils import timezone
                negotiation.business_fee_paid_date = timezone.now().date()
            if request.FILES.get('business_fee_receipt_image'):
                negotiation.business_fee_receipt_image = request.FILES.get('business_fee_receipt_image')
            negotiation.save()
            messages.success(request, "Updated Business Platform Fee payment status and receipt.")
            return redirect(request.path)

        elif action_type == 'reset_business_fee':
            negotiation.business_fee_is_paid = False
            negotiation.business_fee_paid_date = None
            negotiation.business_fee_receipt_image = None
            negotiation.save()
            messages.warning(request, "Reset Business Platform Fee status to unpaid.")
            return redirect(request.path)

        elif action_type == 'update_creator_fee_status':
            is_paid = request.POST.get('creator_fee_is_paid') == 'true'
            paid_date = request.POST.get('creator_fee_paid_date')
            receipt_file = request.FILES.get('creator_fee_receipt_image')
            negotiation.creator_fee_is_paid = is_paid
            if paid_date:
                negotiation.creator_fee_paid_date = paid_date
            elif is_paid and not negotiation.creator_fee_paid_date:
                from django.utils import timezone
                negotiation.creator_fee_paid_date = timezone.now().date()
            if receipt_file:
                negotiation.creator_fee_receipt_image = receipt_file

            negotiation.save()
            messages.success(request, "Updated Creator Platform Fee payment status & receipt proof.")
            return redirect(request.path)

        elif action_type == 'reset_creator_fee':
            negotiation.creator_fee_is_paid = False
            negotiation.creator_fee_paid_date = None
            negotiation.creator_fee_receipt_image = None
            negotiation.save()
            messages.warning(request, "Reset Creator Platform Fee status to unpaid.")
            return redirect(request.path)

        elif action_type == 'divide_installments':
            preset = request.POST.get('preset')
            installment_type = request.POST.get('installment_type', 'creator')

            if installment_type == 'business':
                target_pool = float(negotiation.final_price or 0)
            else:
                target_pool = float(negotiation.creator_net_received or negotiation.final_price or 0)

            from WorkspacePayment.models import WorkspaceInstallment

            WorkspaceInstallment.objects.filter(campaign=campaign, installment_type=installment_type).delete()

            if preset == '3_milestones':
                items = [
                    ('Kickoff payment', target_pool * 0.3),
                    ('Drafts approved', target_pool * 0.4),
                    ('Final delivery', target_pool * 0.3),
                ]
            else:
                items = [
                    ('Installment 1 (50%)', target_pool * 0.5),
                    ('Installment 2 (50%)', target_pool * 0.5),
                ]

            for title, amt in items:
                WorkspaceInstallment.objects.create(
                    campaign=campaign,
                    negotiation=negotiation,
                    installment_type=installment_type,
                    title=title,
                    amount=amt,
                    status='in_escrow'
                )
            party_label = "Business" if installment_type == 'business' else "Creator"
            messages.success(request, f"Divided {party_label} pool ({target_pool:,.2f}) into milestone installments.")

        elif action_type == 'add_installment_manual':
            installment_type = request.POST.get('installment_type', 'creator')
            if installment_type == 'business':
                target_pool = float(negotiation.final_price or 0)
                current_total = sum(float(inst.amount or 0) for inst in negotiation.installments.filter(installment_type='business'))
            else:
                target_pool = float(negotiation.creator_net_received or negotiation.final_price or 0)
                current_total = sum(float(inst.amount or 0) for inst in negotiation.installments.filter(installment_type='creator'))

            if target_pool > 0 and (current_total >= target_pool or abs(current_total - target_pool) < 0.01):
                messages.warning(request, f"Cannot add installment: target pool amount ({target_pool:,.2f}) is already fully allocated.")
                return redirect(request.path)

            title = request.POST.get('title', '').strip() or 'Installment'
            amount_str = request.POST.get('amount', '0')
            paid_date = request.POST.get('paid_date')
            is_paid = request.POST.get('is_paid') == 'true'
            receipt_file = request.FILES.get('receipt_image')

            try:
                amount = float(amount_str)
            except (ValueError, TypeError):
                amount = 0.0

            status = 'released' if is_paid else 'in_escrow'

            from WorkspacePayment.models import WorkspaceInstallment
            inst = WorkspaceInstallment(
                campaign=campaign,
                negotiation=negotiation,
                installment_type=installment_type,
                title=title,
                amount=amount,
                status=status,
                is_paid=is_paid,
            )
            if receipt_file:
                inst.receipt_image = receipt_file

            if paid_date:
                inst.paid_date = paid_date
            elif is_paid:
                from django.utils import timezone
                inst.paid_date = timezone.now().date()

            inst.save()
            messages.success(request, f"Successfully added manual installment '{inst.title}'.")

        elif action_type == 'delete_installment_row':
            inst_id = request.POST.get('installment_id')
            from WorkspacePayment.models import WorkspaceInstallment
            try:
                inst = WorkspaceInstallment.objects.get(id=inst_id)
                inst_title = inst.title
                inst.delete()
                messages.warning(request, f"Deleted installment '{inst_title}'.")
            except WorkspaceInstallment.DoesNotExist:
                pass

        elif action_type == 'update_installment_row':
            inst_id = request.POST.get('installment_id')
            title = request.POST.get('title')
            amount = request.POST.get('amount')
            paid_date = request.POST.get('paid_date')
            is_paid = request.POST.get('is_paid') == 'true'
            receipt_file = request.FILES.get('receipt_image')

            from WorkspacePayment.models import WorkspaceInstallment
            try:
                inst = WorkspaceInstallment.objects.get(id=inst_id)
                if title:
                    inst.title = title.strip()
                if amount:
                    try:
                        inst.amount = float(amount)
                    except ValueError:
                        pass
                inst.is_paid = is_paid
                if receipt_file:
                    inst.receipt_image = receipt_file

                if is_paid:
                    inst.status = 'released'
                    if paid_date:
                        inst.paid_date = paid_date
                    elif not inst.paid_date:
                        from django.utils import timezone
                        inst.paid_date = timezone.now().date()
                else:
                    inst.status = 'in_escrow'
                    if paid_date:
                        inst.paid_date = paid_date

                inst.save()
                messages.success(request, f"Updated installment '{inst.title}'.")
            except WorkspaceInstallment.DoesNotExist:
                pass

        return redirect(request.path)


class WorkspacePaymentViewSet(SnippetViewSet):
    model = WorkspacePaymentNegotiation
    menu_label = "Workspace Payment"
    icon = "order"
    menu_icon = "order"
    menu_name = "workspace_payment"
    index_view_class = WorkspacePaymentIndexView
    inspect_view_enabled = True
    inspect_view_class = WorkspacePaymentInspectView
    inspect_template_name = "campegin/inspect_workspace_payment.html"
    list_display = ("campaign", "final_price", "get_platform_charge_display", "get_platform_fee_display", "get_creator_net_display", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("campaign__name", "revision_reason")

    def get_platform_charge_display(self, obj):
        if hasattr(obj, "get_platform_charge_display"):
            return obj.get_platform_charge_display()
        return f"{obj.platform_charge if getattr(obj, 'platform_charge', None) is not None else 2.5}%"
    get_platform_charge_display.short_description = "Platform Charge %"

    def get_platform_fee_display(self, obj):
        if hasattr(obj, "get_platform_fee_display"):
            return obj.get_platform_fee_display()
        return f"${getattr(obj, 'platform_charge_amount', 0):,.2f}"
    get_platform_fee_display.short_description = "Calculated Platform Fee"

    def get_creator_net_display(self, obj):
        if hasattr(obj, "get_creator_net_display"):
            return obj.get_creator_net_display()
        return f"${getattr(obj, 'creator_net_received', 0):,.2f}"
    get_creator_net_display.short_description = "Creator Net Received"

    def get_queryset(self, request=None):
        try:
            live_campaigns = Campaign.objects.filter(status__in=["Live", "Completed"])
            for camp in live_campaigns:
                WorkspacePaymentNegotiation.objects.get_or_create(
                    campaign=camp,
                    defaults={
                        "final_price": camp.counter_price or camp.budget or 0,
                        "status": "admin_approved" if str(getattr(camp, "created_via", "")).lower() in ["pitch", "request"] else "pending_creator_approval",
                    }
                )
        except Exception as e:
            pass
        return WorkspacePaymentNegotiation.objects.filter(campaign__status__in=["Live", "Completed"])

import json
import calendar
from django.utils import timezone
from django.shortcuts import render
from wagtail.admin.menu import MenuItem

def admin_campaign_analytics_view(request):
    """
    Super Admin Campaign Analytics Console View.
    Calculates Funnel Statuses, Platform Revenue Charges, Escrow Vault Analytics,
    and trends.
    """
    campaigns = list(Campaign.objects.all().select_related("brand", "creator").prefetch_related("deliverables"))
    negotiations = list(WorkspacePaymentNegotiation.objects.all().select_related("campaign").prefetch_related("installments"))

    # 1. FUNNEL & STATUS STATS
    total = len(campaigns)
    live = 0
    under_review = 0
    pending = 0
    completed = 0
    rejected = 0

    for c in campaigns:
        st = str(c.status or "").lower()
        if st in ["live", "active", "in_progress"]:
            live += 1
        elif st in ["under_review", "submitted"]:
            under_review += 1
        elif st in ["pending", "draft"]:
            pending += 1
        elif st in ["completed", "approved"]:
            completed += 1
        elif st in ["rejected", "cancelled"]:
            rejected += 1
        else:
            live += 1

    approved_count = live + completed + under_review
    live_count = live + completed
    conversion_rate = round((completed / total) * 100, 1) if total > 0 else 0.0

    funnel_stats = {
        "total": total,
        "live": live,
        "under_review": under_review,
        "pending": pending,
        "completed": completed,
        "rejected": rejected,
        "approved_count": approved_count,
        "approved_pct": round((approved_count / (total or 1)) * 100, 1),
        "live_count": live_count,
        "live_pct": round((live_count / (total or 1)) * 100, 1),
        "conversion_rate": conversion_rate,
    }

    # Distributions
    cat_map = {}
    niche_map = {}
    plat_map = {}
    country_map = {}

    for c in campaigns:
        cat_name = getattr(c, "category", None)
        if hasattr(cat_name, "name"):
            cat_name = cat_name.name
        elif not cat_name:
            cat_name = "General"
        cat_map[str(cat_name)] = cat_map.get(str(cat_name), 0) + 1

        niche_name = getattr(c, "niche", None) or getattr(c, "target_niche", None)
        if hasattr(niche_name, "name"):
            niche_name = niche_name.name
        elif not niche_name:
            niche_name = "Lifestyle"
        niche_map[str(niche_name)] = niche_map.get(str(niche_name), 0) + 1

        plat_name = str(c.medium or getattr(c, "platform", None) or "Instagram")
        plat_map[plat_name] = plat_map.get(plat_name, 0) + 1

        country_name = getattr(c, "country", None)
        if hasattr(country_name, "name"):
            country_name = country_name.name
        elif not country_name:
            country_name = "Global"
        country_map[str(country_name)] = country_map.get(str(country_name), 0) + 1

    def format_top5(m):
        return [
            {"name": k, "count": v, "pct": round((v / (total or 1)) * 100, 1)}
            for k, v in sorted(m.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

    distributions = {
        "categories": format_top5(cat_map),
        "niches": format_top5(niche_map),
        "platforms": format_top5(plat_map),
        "countries": format_top5(country_map),
    }

    # 2. PLATFORM REVENUE STATS
    total_rev = 0.0
    collected_rev = 0.0
    pending_rev = 0.0
    sum_biz_pct = 0.0
    sum_creator_pct = 0.0
    custom_overrides = 0
    neg_count = len(negotiations) or 1

    neg_by_camp = {}
    for n in negotiations:
        cid = n.campaign_id
        if cid:
            neg_by_camp[cid] = n

        f_price = float(n.final_price or 0)
        biz_pct = float(n.business_platform_charge if n.business_platform_charge is not None else (n.platform_charge if n.platform_charge is not None else 2.5))
        creator_pct = float(n.creator_platform_charge if n.creator_platform_charge is not None else 1.5)

        if biz_pct != 2.5 or creator_pct != 1.5:
            custom_overrides += 1

        sum_biz_pct += biz_pct
        sum_creator_pct += creator_pct

        biz_amt = float(n.business_platform_charge_amount) if n.business_platform_charge_amount is not None else (f_price * (biz_pct / 100))
        creator_amt = float(n.creator_platform_charge_amount) if n.creator_platform_charge_amount is not None else (f_price * (creator_pct / 100))

        tot_fee = biz_amt + creator_amt
        total_rev += tot_fee

        if n.business_fee_is_paid:
            collected_rev += biz_amt
        else:
            pending_rev += biz_amt

        if n.creator_fee_is_paid:
            collected_rev += creator_amt
        else:
            pending_rev += creator_amt

    revenue_stats = {
        "total_revenue": total_rev,
        "collected_revenue": collected_rev,
        "pending_revenue": pending_rev,
        "avg_biz_fee": round(sum_biz_pct / neg_count, 2),
        "avg_creator_fee": round(sum_creator_pct / neg_count, 2),
        "custom_overrides_count": custom_overrides,
    }

    # 3. FINANCIAL / ESCROW STATS
    total_gmv = 0.0
    total_escrowed = 0.0
    total_released = 0.0

    inst_escrowed_cnt = 0
    inst_escrowed_amt = 0.0
    inst_paid_cnt = 0
    inst_paid_amt = 0.0
    inst_rel_cnt = 0
    inst_rel_amt = 0.0

    for n in negotiations:
        f_price = float(n.final_price or 0)
        total_gmv += f_price

        for inst in n.installments.all():
            amt = float(inst.amount or 0)
            st = str(inst.status or "").lower()
            is_paid = inst.is_paid

            if st == "released" or is_paid:
                inst_rel_cnt += 1
                inst_rel_amt += amt
            elif st in ["paid", "verified"]:
                inst_paid_cnt += 1
                inst_paid_amt += amt
            else:
                inst_escrowed_cnt += 1
                inst_escrowed_amt += amt

            if is_paid or st in ["paid", "verified", "released"]:
                total_escrowed += amt
                if st == "released":
                    total_released += amt

    if total_gmv == 0:
        for c in campaigns:
            total_gmv += float(c.budget or c.max_budget or 0)
        total_escrowed = total_gmv * 0.7
        total_released = total_gmv * 0.35

    total_held = max(0.0, total_escrowed - total_released)

    top_by_rev = []
    for c in campaigns:
        neg = neg_by_camp.get(c.id)
        f_price = float(neg.final_price if (neg and neg.final_price) else (c.budget or 0))
        fee = f_price * 0.04
        b_name = c.brand.name if hasattr(c.brand, "name") else (getattr(c.brand, "company_name", None) or "Brand")
        c_sym = getattr(c, "currency_symbol", "$") or "$"
        top_by_rev.append({
            "name": c.name,
            "brand_name": b_name,
            "base_price": f_price,
            "fee_generated": fee,
            "currency_symbol": c_sym,
        })
    top_by_rev = sorted(top_by_rev, key=lambda x: x["fee_generated"], reverse=True)[:5]

    escrow_stats = {
        "total_gmv": total_gmv,
        "total_escrowed": total_escrowed,
        "total_released": total_released,
        "total_held": total_held,
        "milestones": {
            "escrowed": {"count": inst_escrowed_cnt, "amount": inst_escrowed_amt},
            "paid": {"count": inst_paid_cnt, "amount": inst_paid_amt},
            "released": {"count": inst_rel_cnt, "amount": inst_rel_amt},
        },
        "top_by_revenue": top_by_rev,
    }

    # User's default currency symbol determination
    user_currency_symbol = "Rs"
    user_currency_format = "LKR (Rs)"
    if request.user and request.user.is_authenticated:
        try:
            if hasattr(request.user, "creator_profile") and request.user.creator_profile:
                cp = request.user.creator_profile
                if hasattr(cp, "settings") and cp.settings and cp.settings.currency:
                    user_currency_format = cp.settings.currency
                    user_currency_symbol = extract_currency_symbol(cp.settings.currency) or "Rs"
                elif cp.country and cp.country.currency:
                    user_currency_format = cp.country.currency
                    user_currency_symbol = extract_currency_symbol(cp.country.currency) or "Rs"
        except Exception:
            pass
        try:
            if hasattr(request.user, "business_profile") and request.user.business_profile:
                bp = request.user.business_profile
                if bp.country and bp.country.currency:
                    user_currency_format = bp.country.currency
                    user_currency_symbol = extract_currency_symbol(bp.country.currency) or "Rs"
        except Exception:
            pass

    # JSON Payload for client table & charts
    camp_payload = []
    for c in campaigns:
        neg = neg_by_camp.get(c.id)
        f_price = float(neg.final_price if (neg and neg.final_price) else (c.budget or 0))
        b_name = c.brand.name if hasattr(c.brand, "name") else (getattr(c.brand, "company_name", None) or "Brand")
        cr_name = c.creator.name if hasattr(c.creator, "name") else (getattr(c.creator, "user", None) and getattr(c.creator.user, "username", None) or "Creator")
        
        biz_pct = float(neg.business_platform_charge if (neg and neg.business_platform_charge is not None) else 2.5)
        creator_pct = float(neg.creator_platform_charge if (neg and neg.creator_platform_charge is not None) else 1.5)
        biz_fee = float(neg.business_platform_charge_amount) if (neg and neg.business_platform_charge_amount is not None) else (f_price * (biz_pct / 100))
        creator_fee = float(neg.creator_platform_charge_amount) if (neg and neg.creator_platform_charge_amount is not None) else (f_price * (creator_pct / 100))
        tot_f = biz_fee + creator_fee

        c_sym = getattr(c, "currency_symbol", user_currency_symbol) or user_currency_symbol
        created_str = c.created_at.isoformat() if getattr(c, "created_at", None) else (c.start_date or "")

        # Collect business and creator installments
        inst_list = []
        biz_insts = []
        creator_insts = []
        if neg:
            for inst in neg.installments.all():
                proof_url = None
                if inst.receipt_image:
                    try:
                        proof_url = request.build_absolute_uri(inst.receipt_image.url)
                    except Exception:
                        proof_url = str(inst.receipt_image.url) if hasattr(inst.receipt_image, 'url') else str(inst.receipt_image)
                elif inst.receipt_url:
                    proof_url = str(inst.receipt_url)

                i_data = {
                    "id": inst.id,
                    "title": inst.title or "Milestone Installment",
                    "amount": float(inst.amount or 0),
                    "installment_type": inst.installment_type or "creator",
                    "status": inst.status or "in_escrow",
                    "is_paid": bool(inst.is_paid or inst.status == "released"),
                    "paid_date": inst.paid_date.strftime("%Y-%m-%d") if inst.paid_date else None,
                    "receipt_image_url": proof_url,
                }
                inst_list.append(i_data)
                if inst.installment_type == "business":
                    biz_insts.append(i_data)
                else:
                    creator_insts.append(i_data)

        camp_payload.append({
            "id": c.id,
            "name": c.name,
            "brand_name": b_name,
            "creator_name": cr_name,
            "status": c.status or "Draft",
            "progress": c.progress or (100 if c.status == "Completed" else 50),
            "platform": c.medium or getattr(c, "platform", None) or "Instagram",
            "category": c.category.name if hasattr(c.category, "name") else (str(c.category) if getattr(c, "category", None) else "General"),
            "budget": float(c.budget or 0),
            "final_price": f_price,
            "biz_fee": biz_fee,
            "creator_fee": creator_fee,
            "total_fee": tot_f,
            "biz_fee_paid": bool(neg and neg.business_fee_is_paid),
            "creator_fee_paid": bool(neg and neg.creator_fee_is_paid),
            "currency_symbol": c_sym,
            "created_at": created_str,
            "installments": inst_list,
            "business_installments": biz_insts,
            "creator_installments": creator_insts,
        })

    # Actual trends data: a point for every campaign created in chronological order
    now = timezone.now()
    sorted_campaigns = sorted(campaigns, key=lambda x: (x.created_at or now, x.id))

    labels = []
    campaigns_count = []
    revenue_amount = []
    per_campaign_fees = []
    campaign_names = []
    campaign_dates = []

    cum_rev = 0.0
    for idx, c in enumerate(sorted_campaigns, 1):
        neg = neg_by_camp.get(c.id)
        f_price = float(neg.final_price if (neg and neg.final_price is not None) else (c.budget or 0))
        biz_pct = float(neg.business_platform_charge if (neg and neg.business_platform_charge is not None) else (neg.platform_charge if (neg and neg.platform_charge is not None) else 2.5))
        creator_pct = float(neg.creator_platform_charge if (neg and neg.creator_platform_charge is not None) else 1.5)
        biz_fee = float(neg.business_platform_charge_amount) if (neg and neg.business_platform_charge_amount is not None) else (f_price * (biz_pct / 100))
        creator_fee = float(neg.creator_platform_charge_amount) if (neg and neg.creator_platform_charge_amount is not None) else (f_price * (creator_pct / 100))
        tot_fee = biz_fee + creator_fee

        cum_rev += tot_fee

        c_date = c.created_at.strftime("%b %d") if c.created_at else (c.start_date or "N/A")
        label = c.name if len(c.name) <= 15 else (c.name[:13] + "..")
        labels.append(label)
        campaign_names.append(c.name)
        campaign_dates.append(c_date)
        campaigns_count.append(idx)
        revenue_amount.append(round(cum_rev, 2))
        per_campaign_fees.append(round(tot_fee, 2))

    if not sorted_campaigns:
        trends_payload = {
            "labels": ["No Campaigns"],
            "campaign_names": ["No Campaigns"],
            "campaign_dates": ["N/A"],
            "campaigns_count": [0],
            "revenue_amount": [0.0],
            "per_campaign_fees": [0.0],
        }
    else:
        trends_payload = {
            "labels": labels,
            "campaign_names": campaign_names,
            "campaign_dates": campaign_dates,
            "campaigns_count": campaigns_count,
            "revenue_amount": revenue_amount,
            "per_campaign_fees": per_campaign_fees,
        }

    budget_vs_spend_payload = []
    for c in campaigns[:6]:
        neg = neg_by_camp.get(c.id)
        t_b = float(c.max_budget or c.budget or 2000)
        f_p = float(neg.final_price if (neg and neg.final_price) else (c.budget or 1500))
        a_s = f_p if c.status == "Completed" else (f_p * 0.5)
        budget_vs_spend_payload.append({
            "campaign": c.name,
            "target_budget": t_b,
            "final_price": f_p,
            "funds_released": a_s,
        })

    context = {
        "currency_symbol": user_currency_symbol,
        "user_currency_symbol": user_currency_symbol,
        "user_currency_format": user_currency_format,
        "funnel_stats": funnel_stats,
        "distributions": distributions,
        "revenue_stats": revenue_stats,
        "escrow_stats": escrow_stats,
        "categories": CampaignCategory.objects.all(),
        "campaigns_json": camp_payload,
        "trends_json": trends_payload,
        "budget_vs_spend_json": budget_vs_spend_payload,
    }
    return render(request, "wagtailadmin/campaign_analytics.html", context)


class CampaignWorkspaceGroup(SnippetViewSetGroup):
    items = (
        CampaignViewSet,
        PitchViewSet,
        WorkspacePaymentViewSet,
        CampaignCategoryViewSet,
        CampaignLanguageViewSet,
        CampaignDeliverableViewSet,
        CampaignPlatformViewSet,
        CampaignNicheViewSet,
    )
    menu_icon = "tasks"
    menu_label = "Campaign Workspaces"
    menu_name = "campaign_workspaces"
    menu_order = 200

    def get_submenu_items(self):
        items = list(super().get_submenu_items())
        analytics_item = MenuItem(
            "Campaign Analytics",
            reverse("admin_campaign_analytics"),
            icon_name="view",
            order=0,
        )
        return [analytics_item] + items


register_snippet(CampaignWorkspaceGroup)


@hooks.register("register_admin_urls")
def register_campaign_admin_urls():
    return [
        path("campaign-analytics/", admin_campaign_analytics_view, name="admin_campaign_analytics"),
        path("campaign/download-pdf/<int:campaign_id>/", download_campaign_pdf_view, name="download_campaign_pdf"),
    ]


@hooks.register("construct_main_menu")
def add_campaign_analytics_to_workspace_menu(request, menu_items):
    for it in menu_items:
        if it.name == "campaign_workspaces" and hasattr(it, "menu"):
            orig_fn = it.menu.menu_items_for_request
            def make_clean_items(req, ofn=orig_fn):
                sub_items = ofn(req)
                if not any(getattr(s, "name", "") == "campaign_analytics" or getattr(s, "label", "") == "Campaign Analytics" for s in sub_items):
                    sub_items.insert(0, MenuItem("Campaign Analytics", reverse("admin_campaign_analytics"), icon_name="view", order=0))
                return sub_items
            it.menu.menu_items_for_request = make_clean_items



