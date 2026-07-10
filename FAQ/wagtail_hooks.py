from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.views.generic.models import IndexView
from wagtail.admin.ui.tables import TitleColumn
from django.utils.translation import gettext_lazy
from django.urls import reverse
from .models import FAQ

class FAQIndexView(IndexView):
    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            # Prefer inspect_url over edit_url so clicking the faq_id directly opens the View (inspect) page
            if inspect_url := self.get_inspect_url(instance):
                return inspect_url
            return self.get_edit_url(instance)

        if not self.model:
            return column_class(
                "name",
                label=gettext_lazy("Name"),
                accessor=str,
                get_url=get_url,
            )
        return self._get_custom_column(
            field_name, column_class, get_url=get_url, **kwargs
        )

    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)
        for item in buttons:
            if hasattr(item, "label") and (str(item.label) == "Inspect" or item.label == "Inspect"):
                item.label = "View"
                item.icon_name = "view"
        return buttons

class FAQViewSet(ModelViewSet):
    model = FAQ
    menu_label = "FAQs"
    icon = "help"
    menu_icon = "help"
    menu_item_name = "faqs"
    add_to_admin_menu = True
    exclude_form_fields = ["faq_id"]
    inspect_view_enabled = True
    inspect_template_name = "FAQ/inspect_faq.html"
    index_view_class = FAQIndexView
    list_display = ("faq_id", "question", "target_audience", "is_active", "created_at")
    list_export = ("faq_id", "question", "answer", "target_audience", "is_active", "created_at", "updated_at")
    list_filter = ("target_audience", "is_active")
    search_fields = ("faq_id", "question", "answer")
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

@hooks.register("register_admin_viewset")
def register_faqs_viewset():
    return FAQViewSet()

