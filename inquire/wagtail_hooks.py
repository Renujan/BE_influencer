from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from inquire.models import Inquiry

class InquiryViewSet(ModelViewSet):
    model = Inquiry
    menu_label = "Inquiries"
    icon = "mail"
    menu_icon = "mail"
    menu_item_name = "inquiries"
    add_to_admin_menu = True
    create_view_enabled = False
    exclude_form_fields = ["inquiry_id"]
    list_display = ("inquiry_id", "name", "email", "phone", "role", "subject", "status", "created_at")
    list_export = ("inquiry_id", "name", "email", "phone", "role", "subject", "message", "status", "created_at", "updated_at")
    list_filter = ("role", "status")
    search_fields = ("inquiry_id", "name", "email", "phone", "subject", "message")
    ordering = ("-created_at",)
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddInquiryPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddInquiryPermissionPolicy(self.model)

@hooks.register("register_admin_viewset")
def register_inquiries_viewset():
    return InquiryViewSet()
