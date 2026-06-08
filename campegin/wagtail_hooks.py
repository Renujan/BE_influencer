from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup
from wagtail.snippets.models import register_snippet
from .models import Campaign, CampaignCategory, CampaignLanguage, CampaignDeliverable, CampaignPlatform

class CampaignViewSet(SnippetViewSet):
    model = Campaign
    menu_label = "Campaigns"
    icon = "tasks"
    add_to_admin_menu = False
    add_view_enabled = False
    create_view_enabled = False
    exclude_form_fields = []

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
