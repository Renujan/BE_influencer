from wagtail import hooks
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup, InspectView, IndexView
from wagtail.snippets.models import register_snippet
from wagtail.snippets.widgets import SnippetListingButton
from django.urls import reverse, path
from .models import BusinessService, ServiceCategory, BusinessServiceRequest
from .views import admin_connect_request_view, admin_decline_request_view

from wagtail.admin.ui.tables import TitleColumn
from django.utils.translation import gettext_lazy

class BusinessServiceIndexView(IndexView):
    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            # Prefer inspect_url over edit_url so clicking the primary link opens the View (inspect) page
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

class BusinessServiceRequestIndexView(IndexView):
    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            # Prefer inspect_url over edit_url so clicking the primary link opens the View (inspect) page
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

class BusinessServiceInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.object
        context["instance"] = service
        context["bullet_points"] = [pt.strip() for pt in service.bullet_points.split("\n") if pt.strip()] if service.bullet_points else []
        context["service_requests"] = service.requests.select_related("user").order_by("-created_at")
        return context

class BusinessServiceRequestInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["instance"] = self.object
        return context

class BusinessServiceViewSet(SnippetViewSet):
    model = BusinessService
    menu_label = "Business Services"
    icon = "cog"
    add_to_admin_menu = False
    exclude_form_fields = ["service_id"]
    inspect_view_enabled = True
    inspect_view_class = BusinessServiceInspectView
    inspect_template_name = "business_service/inspect_business_service.html"
    index_view_class = BusinessServiceIndexView
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

class BusinessServiceRequestViewSet(SnippetViewSet):
    model = BusinessServiceRequest
    menu_label = "Service Requests"
    icon = "mail"
    add_to_admin_menu = False
    inspect_view_enabled = True
    inspect_view_class = BusinessServiceRequestInspectView
    add_view_enabled = False
    create_view_enabled = False
    inspect_template_name = "business_service/inspect_business_service_request.html"
    index_view_class = BusinessServiceRequestIndexView
    list_display = ("service", "user", "get_user_role", "budget", "timeline", "status", "created_at")

    list_export = ("id", "service__service_id", "service__title", "user__username", "user__email", "message", "budget", "timeline", "status", "created_at", "updated_at")
    list_filter = ("status", "timeline", "service")
    search_fields = ("service__title", "user__username", "message")

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddPermissionPolicy(self.model)


class BusinessServiceGroup(SnippetViewSetGroup):
    items = (BusinessServiceViewSet, ServiceCategoryViewSet, BusinessServiceRequestViewSet)
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

@hooks.register("register_admin_urls")
def register_business_service_request_admin_urls():
    return [
        path(
            "business-services/request/connect/<int:request_id>/",
            admin_connect_request_view,
            name="wagtail_connect_business_service_request",
        ),
        path(
            "business-services/request/decline/<int:request_id>/",
            admin_decline_request_view,
            name="wagtail_decline_business_service_request",
        ),
    ]

