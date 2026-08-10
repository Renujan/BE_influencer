from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail import hooks
from django.utils.safestring import mark_safe
from .models import PortfolioItem


class PortfolioItemViewSet(SnippetViewSet):
    model = PortfolioItem
    menu_label = "Creator Portfolios"
    icon = "image"
    menu_icon = "image"
    menu_item_name = "creator_portfolios"
    add_to_admin_menu = True

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddPermissionPolicy(self.model)

    list_display = ("title", "creator", "platform", "media_type", "views", "engagement_rate", "brand", "is_featured", "created_at")
    list_filter = ("platform", "media_type", "is_featured")
    search_fields = ("title", "creator__username", "brand")


register_snippet(PortfolioItemViewSet)


@hooks.register("insert_global_admin_css")
def portfolio_admin_css():
    return mark_safe(
        """
        <style>
            /* Hide any Add Portfolio Item button/link in Wagtail admin */
            a[href*="/portfolioitem/add/"],
            a[href*="/portfolio/portfolioitem/add/"],
            a[href*="/snippets/portfolio/portfolioitem/add/"],
            a[href*="/snippets/Portfolio/portfolioitem/add/"],
            .header-title .action-button[href*="portfolioitem"],
            .action-button[href*="portfolioitem/add"],
            a.button[href*="portfolioitem/add"] {
                display: none !important;
            }
        </style>
        """
    )
