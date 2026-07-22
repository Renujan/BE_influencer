from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup, IndexView, InspectView
from wagtail.snippets.models import register_snippet
from wagtail import hooks
from wagtail.admin.views.generic.models import MenuItem as GenericMenuItem
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import path, reverse
from .models import Campaign, CampaignCategory, CampaignLanguage, CampaignDeliverable, CampaignPlatform, Pitch
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
        context["milestones"] = campaign.milestones.all()
        context["tasks"] = campaign.tasks.all()
        context["deliverables"] = campaign.deliverables.all()
        context["payments"] = campaign.payments.all()
        context["files"] = campaign.files.all()
        context["tickets"] = campaign.tickets.all()
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
        elif status == "Live_Countered":
            if self.object.counter_price:
                self.object.budget = self.object.counter_price
            self.object.status = "Live"
            self.object.progress = 62
            messages.success(request, f"Counter offer accepted! Campaign '{self.object.name}' is now Live.")
        elif status in [choice[0] for choice in self.object.STATUS_CHOICES]:
            if status == "Live" and self.object.creator:
                self.object.status = "Pending"
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

class CampaignCategoryViewSet(SnippetViewSet):
    model = CampaignCategory
    menu_label = "Categories"
    icon = "tag"
    add_to_admin_menu = False
    list_export = ("id", "name")
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
    list_export = ("id", "name")
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

class CampaignPlatformViewSet(SnippetViewSet):
    model = CampaignPlatform
    menu_label = "Target Platforms"
    icon = "desktop"
    add_to_admin_menu = False
    list_export = ("id", "platform_id", "name", "color", "logo")
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

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
            if not Campaign.objects.filter(name=self.object.campaign_name, brand=self.object.brand).exists():
                Campaign.objects.create(
                    name=self.object.campaign_name,
                    brand=self.object.brand,
                    creator=self.object.creator,
                    budget=self.object.budget,
                    brief=self.object.description or f"Campaign proposal based on pitch: {self.object.campaign_name}",
                    status="Live",
                    progress=62,
                    start_date=self.object.sent_date or "2026-08-01",
                    created_via="pitch",
                )
            messages.success(request, f"Pitch '{self.object.campaign_name}' accepted and converted to Live Campaign.")

        elif action == "reject_pitch" or status_val == "declined":
            self.object.status = "declined"
            self.object.decline_reason = admin_review or "Pitch proposal rejected by admin."
            self.object.save()
            messages.warning(request, f"Pitch '{self.object.campaign_name}' rejected.")

        elif action == "approve_creator_counter" or status_val == "approve_creator_counter":
            # Admin approves creator's counter → now visible to business
            self.object.status = "pitch_countered"
            self.object.save()
            messages.success(request, f"Creator counter offer approved for '{self.object.campaign_name}'.")

        elif action == "approve_biz_counter" or status_val == "approve_biz_counter":
            # Admin approves business's counter → now visible to creator
            self.object.status = "biz_countered"
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

class CampaignWorkspaceGroup(SnippetViewSetGroup):
    items = (CampaignViewSet, PitchViewSet, CampaignCategoryViewSet, CampaignLanguageViewSet, CampaignDeliverableViewSet, CampaignPlatformViewSet)
    menu_icon = "tasks"
    menu_label = "Campaign Workspaces"
    menu_name = "campaign_workspaces"
    menu_order = 200

register_snippet(CampaignWorkspaceGroup)


@hooks.register("register_admin_urls")
def register_campaign_pdf_urls():
    return [
        path("campaign/download-pdf/<int:campaign_id>/", download_campaign_pdf_view, name="download_campaign_pdf"),
    ]

