from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet, ModelViewSetGroup
from wagtail.admin.menu import MenuItem
from django.urls import reverse
from .models import BusinessProfile, CreatorProfile

# 1. Business Profile Admin Viewset
class BusinessProfileViewSet(ModelViewSet):
    model = BusinessProfile
    menu_label = "Business Profiles"
    icon = "user"
    menu_icon = "user"
    menu_item_name = "business_profiles"
    add_to_admin_menu = False
    exclude_form_fields = []
    create_view_enabled = False
    list_display = ("user", "company_name", "business_type", "phone", "otp_verified", "status")
    list_export = ("id", "user__username", "user__email", "company_name", "business_type", "website", "phone", "otp_verified", "status")
    list_filter = ("otp_verified", "status")
    search_fields = ("user__username", "user__email", "company_name", "phone")

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddPermissionPolicy(self.model)

# 2. Creator Profile Admin Viewset
class CreatorProfileViewSet(ModelViewSet):
    model = CreatorProfile
    menu_label = "Creator Profiles"
    icon = "user"
    menu_icon = "user"
    menu_item_name = "creator_profiles"
    add_to_admin_menu = False
    exclude_form_fields = []
    create_view_enabled = False
    list_display = ("user", "phone", "location", "wallet_balance", "otp_verified", "status")
    list_export = ("id", "user__username", "user__email", "phone", "location", "wallet_balance", "otp_verified", "status")
    list_filter = ("otp_verified", "status")
    search_fields = ("user__username", "user__email", "phone", "location")

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddPermissionPolicy(self.model)

# 3. User Profiles Group
class UserProfileGroup(ModelViewSetGroup):
    items = (BusinessProfileViewSet, CreatorProfileViewSet)
    menu_icon = "user"
    menu_label = "User Profiles"
    menu_name = "user_profiles"
    menu_order = 150

# Register Viewsets
@hooks.register("register_admin_viewset")
def register_user_profile_group():
    return UserProfileGroup()

@hooks.register('register_admin_menu_item')
def register_main_admin_menu_item():
    return MenuItem(
        'Dashboard',
        reverse('wagtailadmin_home'),
        icon_name='home',
        order=1
    )

@hooks.register('construct_main_menu')
def hide_unwanted_menu_items(request, menu_items):
    # Hide reports, images, documents, help, explorer (Pages), and snippets items from the main menu sidebar
    menu_items[:] = [item for item in menu_items if item.name not in ['reports', 'images', 'documents', 'help', 'explorer', 'snippets']]

@hooks.register('construct_settings_menu')
def hide_unwanted_settings_menu_items(request, menu_items):
    # Keep only users and groups inside the settings menu
    menu_items[:] = [item for item in menu_items if item.name in ['users', 'groups']]


from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib import messages

# Hook to display success message after login
@receiver(user_logged_in)
def login_success_message(sender, request, user, **kwargs):
    """Add a success message when user logs in"""
    if '/admin/' in request.path or request.session.get('_auth_user_backend'):
        storage = messages.get_messages(request)
        storage.used = True
        messages.success(request, 'You have been successfully logged in.', extra_tags='login-success')


from django.utils.safestring import mark_safe

@hooks.register('insert_global_admin_js')
def auto_hide_messages():
    """Add JavaScript to automatically hide success messages after 5 seconds and add close buttons"""
    return mark_safe(
        """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            var messages = document.querySelectorAll('.messages li, .messages [class*="messages__item"], .messages .success, .messages .info, .messages .warning');
            messages.forEach(function(message) {
                var hideTimeout = setTimeout(function() {
                    if (message && message.parentNode) {
                        message.style.transition = 'opacity 0.5s ease-out';
                        message.style.opacity = '0';
                        setTimeout(function() {
                            if (message && message.parentNode) {
                                message.remove();
                            }
                        }, 500);
                    }
                }, 5000);

                if (!message.querySelector('.close-msg-btn')) {
                    var closeBtn = document.createElement('button');
                    closeBtn.innerHTML = '&times;';
                    closeBtn.className = 'close-msg-btn';
                    closeBtn.style.position = 'absolute';
                    closeBtn.style.right = '20px';
                    closeBtn.style.top = '50%';
                    closeBtn.style.transform = 'translateY(-50%)';
                    closeBtn.style.background = 'none';
                    closeBtn.style.border = 'none';
                    closeBtn.style.color = 'white';
                    closeBtn.style.fontSize = '20px';
                    closeBtn.style.cursor = 'pointer';
                    closeBtn.style.fontWeight = 'bold';
                    closeBtn.style.opacity = '0.7';
                    closeBtn.style.transition = 'opacity 0.2s';
                    closeBtn.addEventListener('mouseover', function() { closeBtn.style.opacity = '1'; });
                    closeBtn.addEventListener('mouseout', function() { closeBtn.style.opacity = '0.7'; });

                    message.style.position = 'relative';
                    message.style.paddingRight = '50px';

                    closeBtn.addEventListener('click', function() {
                        clearTimeout(hideTimeout);
                        message.style.transition = 'opacity 0.5s ease-out';
                        message.style.opacity = '0';
                        setTimeout(function() {
                            if (message && message.parentNode) {
                                message.remove();
                            }
                        }, 500);
                    });
                    message.appendChild(closeBtn);
                }
            });
        });
        </script>
        """
    )
