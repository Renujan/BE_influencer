from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.snippets.models import register_snippet
from wagtail import hooks
from django.utils.safestring import mark_safe
from .models import RateCard


class RateCardViewSet(SnippetViewSet):
    model = RateCard
    menu_label = "Rate Cards"
    icon = "doc-full"
    menu_name = "rate_cards"
    menu_order = 250
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

    list_display = ("id", "creator", "creator_name", "get_niches", "get_country", "get_province", "get_district", "get_medium", "platform", "type", "display_duration", "formatted_min_price", "formatted_max_price", "is_active")
    list_export = ("id", "creator.username", "creator_name", "get_niches", "get_country", "get_province", "get_district", "get_medium", "platform", "type", "display_duration", "price", "min_price", "max_price", "is_active")
    list_filter = ("platform", "country", "medium", "is_active")
    search_fields = ("creator__username", "creator_name", "country", "province", "district", "medium", "platform", "type", "description")


register_snippet(RateCardViewSet)


@hooks.register("insert_global_admin_css")
def global_admin_css():
    return mark_safe(
        """
        <style>
            /* Enable horizontal scroll on Wagtail listing tables & snippet tables */
            .w-table-wrapper,
            .listing-wrapper,
            .table-wrapper,
            div:has(> table.listing),
            div:has(> table.w-table) {
                overflow-x: auto !important;
                max-width: 100% !important;
                -webkit-overflow-scrolling: touch !important;
            }
            table.listing, .w-table {
                width: max-content !important;
                min-width: 100% !important;
            }
            table.listing td, table.listing th, .w-table td, .w-table th {
                white-space: nowrap !important;
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
            }

            /* Hide any Add Rate Card button/link in Wagtail admin */
            a[href*="/ratecard/add/"],
            a[href*="/ratecard/new/"],
            a[href*="/snippets/RateCard/ratecard/add/"],
            a[href*="/snippets/ratecard/ratecard/add/"],
            .header-title .action-button[href*="ratecard"],
            .action-button[href*="ratecard/add"],
            a.button[href*="ratecard/add"] {
                display: none !important;
            }
        </style>
        """
    )
