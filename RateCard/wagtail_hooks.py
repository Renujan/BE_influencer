from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail.snippets.models import register_snippet
from .models import RateCard


class RateCardViewSet(SnippetViewSet):
    model = RateCard
    menu_label = "Rate Cards"
    icon = "doc-full"
    menu_name = "rate_cards"
    menu_order = 250
    add_to_admin_menu = True
    list_display = ("id", "creator", "creator_name", "get_niches", "platform", "type", "display_duration", "price", "is_active")
    list_export = ("id", "creator.username", "creator_name", "get_niches", "platform", "type", "display_duration", "price", "min_price", "max_price", "is_active")
    list_filter = ("platform", "is_active")
    search_fields = ("creator__username", "creator_name", "platform", "type", "description")


register_snippet(RateCardViewSet)
