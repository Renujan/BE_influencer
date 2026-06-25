from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup, IndexView, InspectView
from wagtail.snippets.models import register_snippet
from wagtail import hooks
from wagtail.admin.views.generic.models import MenuItem as GenericMenuItem
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import path, reverse
from .models import Campaign, CampaignCategory, CampaignLanguage, CampaignDeliverable, CampaignPlatform
from .views import download_campaign_pdf_view

# Custom Index View to customize labels and add PDF download button
class CampaignIndexView(IndexView):
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

        if status in [choice[0] for choice in self.object.STATUS_CHOICES]:
            self.object.status = status

        self.object.admin_review = admin_review or ""
        self.object.save()

        messages.success(request, f"Campaign status successfully updated to '{self.object.status}'.")
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

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddCampaignPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddCampaignPermissionPolicy(self.model)
    list_display = ("name", "brand", "creator", "status", "budget", "progress")
    list_export = ("id", "name", "brand__username", "creator__username", "status", "budget", "start_date", "progress")
    list_filter = ("status",)
    search_fields = ("name", "brand__username", "creator__username")

class CampaignCategoryViewSet(SnippetViewSet):
    model = CampaignCategory
    menu_label = "Categories"
    icon = "tag"
    add_to_admin_menu = False
    list_export = ("id", "name")

class CampaignLanguageViewSet(SnippetViewSet):
    model = CampaignLanguage
    menu_label = "Languages"
    icon = "globe"
    add_to_admin_menu = False
    list_export = ("id", "name")

class CampaignDeliverableViewSet(SnippetViewSet):
    model = CampaignDeliverable
    menu_label = "Deliverables"
    icon = "doc-full"
    add_to_admin_menu = False
    list_export = ("id", "name")

class CampaignPlatformViewSet(SnippetViewSet):
    model = CampaignPlatform
    menu_label = "Target Platforms"
    icon = "desktop"
    add_to_admin_menu = False
    list_export = ("id", "platform_id", "name", "color", "logo")

class CampaignWorkspaceGroup(SnippetViewSetGroup):
    items = (CampaignViewSet, CampaignCategoryViewSet, CampaignLanguageViewSet, CampaignDeliverableViewSet, CampaignPlatformViewSet)
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

