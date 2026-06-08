from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.menu import MenuItem
from django.urls import reverse
from .models import UserProfile


# 1. Custom Django Admin Viewsets
class UserProfileViewSet(ModelViewSet):
    model = UserProfile
    menu_label = "User Profiles"
    icon = "user"
    menu_icon = "user"
    menu_item_name = "user_profiles"
    add_to_admin_menu = True
    exclude_form_fields = []
    create_view_enabled = False  # Disable manual creation, hide add button
    list_display_add_buttons = None  # Hide the add button from list display header
    list_display = ("user", "role", "phone", "otp_verified", "get_details", "wallet_balance")
    list_export = ("id", "user__username", "user__email", "role", "phone", "location", "wallet_balance", "otp_verified", "company_name", "business_type", "website")
    list_filter = ("role", "otp_verified")
    search_fields = ("user__username", "user__email", "company_name", "phone")

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy
        
        class NoAddUserProfilePermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action == "add":
                    return False
                return super().user_has_permission(user, action)
        
        return NoAddUserProfilePermissionPolicy(self.model)



# 2. Register Viewsets
@hooks.register("register_admin_viewset")
def register_user_profile_viewset():
    return UserProfileViewSet()

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
    print("SIDEBAR MENU ITEMS:", [item.name for item in menu_items])
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
    # Only show message for Wagtail admin logins
    if '/admin/' in request.path or request.session.get('_auth_user_backend'):
        # Clear any existing messages first
        storage = messages.get_messages(request)
        storage.used = True
        # Add the login success message
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
                // Auto-hide after 5 seconds
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

                // Add close button dynamically if not exists
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

                    // Ensure parent has styling to position button
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



