from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.views.generic.models import IndexView, InspectView
from wagtail.admin.ui.tables import TitleColumn
from django.utils.translation import gettext_lazy
from django.urls import reverse
from .models import Guide

class GuideInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["instance"] = self.object
        return context

class GuideIndexView(IndexView):
    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            # Prefer inspect_url over edit_url so clicking the guide_id directly opens the View (inspect) page
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

class GuideViewSet(ModelViewSet):
    model = Guide
    menu_label = "Guide"
    icon = "clipboard-list"
    menu_icon = "clipboard-list"
    menu_item_name = "guide"
    add_to_admin_menu = True
    exclude_form_fields = ["guide_id"]
    inspect_view_enabled = True
    inspect_view_class = GuideInspectView
    inspect_template_name = "guide/inspect_guide.html"
    index_view_class = GuideIndexView
    list_display = ("guide_id", "title", "category", "target_audience", "is_active", "created_at")
    list_export = ("guide_id", "title", "category", "content", "document", "target_audience", "is_active", "created_at", "updated_at")
    list_filter = ("category", "target_audience", "is_active")
    search_fields = ("guide_id", "title", "content")
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

@hooks.register("register_admin_viewset")
def register_guide_viewset():
    return GuideViewSet()
