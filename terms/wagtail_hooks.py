from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from .models import TermsAndCondition

class TermsAndConditionViewSet(ModelViewSet):
    model = TermsAndCondition
    menu_label = "Terms & Conditions"
    icon = "doc-full"
    menu_icon = "doc-full"
    menu_item_name = "terms_and_conditions"
    add_to_admin_menu = True
    exclude_form_fields = ["terms_id"]
    list_display = ("terms_id", "title", "target_audience", "is_active", "created_at")
    list_export = ("terms_id", "title", "content", "target_audience", "is_active", "created_at", "updated_at")
    list_filter = ("target_audience", "is_active")
    search_fields = ("terms_id", "title", "content")

@hooks.register("register_admin_viewset")
def register_terms_and_conditions_viewset():
    return TermsAndConditionViewSet()
