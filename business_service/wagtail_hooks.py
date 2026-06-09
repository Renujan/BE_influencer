from wagtail import hooks
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup
from wagtail.snippets.models import register_snippet
from wagtail.snippets.widgets import SnippetListingButton
from django.urls import reverse
from .models import BusinessService, ServiceCategory

class BusinessServiceViewSet(SnippetViewSet):
    model = BusinessService
    menu_label = "Business Services"
    icon = "cog"
    add_to_admin_menu = False
    exclude_form_fields = ["service_id"]
    list_display = ("service_id", "title", "provider", "category", "rate", "target_audience", "is_active", "created_at")
    list_export = ("service_id", "title", "provider", "category__name", "rate", "speed", "description", "bullet_points", "target_audience", "is_active", "created_at", "updated_at")
    list_filter = ("category", "target_audience", "is_active")
    search_fields = ("service_id", "title", "provider", "description")

class ServiceCategoryViewSet(SnippetViewSet):
    model = ServiceCategory
    menu_label = "Service Categories"
    icon = "tag"
    add_to_admin_menu = False
    list_display = ("name",)
    search_fields = ("name",)

class BusinessServiceGroup(SnippetViewSetGroup):
    items = (BusinessServiceViewSet, ServiceCategoryViewSet)
    menu_icon = "cog"
    menu_label = "Business Services"
    menu_name = "business_services_group"
    menu_order = 300

register_snippet(BusinessServiceGroup)

@hooks.register('register_snippet_listing_buttons')
def add_business_service_buttons(snippet, user, next_url=None):
    """Add custom PDF download button in Business Service listing."""
    if isinstance(snippet, BusinessService):
        buttons = []
        try:
            pdf_url = reverse('business_service:download_business_service_pdf', kwargs={'pk': snippet.pk})
            buttons.append(
                SnippetListingButton(
                    label='Download PDF',
                    url=pdf_url,
                    priority=90,
                    icon_name='download',
                )
            )
        except Exception as e:
            pass
        return buttons
    return []
