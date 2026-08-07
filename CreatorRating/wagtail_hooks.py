from wagtail.admin.viewsets.model import ModelViewSet
from wagtail import hooks
from .models import CreatorRating

class CreatorRatingViewSet(ModelViewSet):
    model = CreatorRating
    menu_label = "Rating"
    icon = "star"
    menu_icon = "star"
    menu_item_name = "creator_ratings"
    add_to_admin_menu = False

    list_display = ("get_creator_display", "get_business_display", "get_rating_display", "get_campaign_display", "review", "created_at")
    list_filter = ("rating",)
    search_fields = ("creator__username", "brand__username", "campaign__name", "review")

@hooks.register("register_admin_viewset")
def register_creator_rating_wagtail_viewset():
    return CreatorRatingViewSet()
