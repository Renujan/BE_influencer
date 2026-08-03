from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from .models import PortfolioItem

class PortfolioItemViewSet(SnippetViewSet):
    model = PortfolioItem
    menu_label = "Creator Portfolios"
    icon = "image"
    menu_icon = "image"
    menu_item_name = "creator_portfolios"
    add_to_admin_menu = True
    list_display = ("title", "creator", "platform", "media_type", "views", "engagement_rate", "brand", "is_featured", "created_at")
    list_filter = ("platform", "media_type", "is_featured")
    search_fields = ("title", "creator__username", "brand")

register_snippet(PortfolioItemViewSet)
