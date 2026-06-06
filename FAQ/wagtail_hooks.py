from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from .models import FAQ

class FAQViewSet(ModelViewSet):
    model = FAQ
    menu_label = "FAQs"
    icon = "help"
    menu_icon = "help"
    menu_item_name = "faqs"
    add_to_admin_menu = True
    exclude_form_fields = ["faq_id"]
    list_display = ("faq_id", "question", "target_audience", "is_active", "created_at")
    list_export = ("faq_id", "question", "answer", "target_audience", "is_active", "created_at", "updated_at")
    list_filter = ("target_audience", "is_active")
    search_fields = ("faq_id", "question", "answer")

@hooks.register("register_admin_viewset")
def register_faqs_viewset():
    return FAQViewSet()
