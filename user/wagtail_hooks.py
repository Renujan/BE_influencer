from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.menu import Menu, MenuItem, SubmenuMenuItem
from wagtail.admin.views.generic.models import InspectView, IndexView, MenuItem as GenericMenuItem
from django.utils.translation import gettext as _
from django.urls import reverse, path
from .models import BusinessProfile, CreatorProfile, Niche, BusinessType
from Setting.models import CreatorSettings, BusinessSettings
from .views import download_profile_pdf_view, admin_approve_business_view, admin_restrict_business_view, admin_approve_creator_view, admin_restrict_creator_view, admin_toggle_featured_view

from wagtail.admin.ui.tables import TitleColumn
from django.utils.translation import gettext_lazy

# Custom Index View to change the "Inspect" button label to "View"
class ProfileIndexView(IndexView):
    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            # Prefer inspect_url over edit_url so clicking the user links directly opens the View (inspect) page
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
        
        # Identify profile type
        if isinstance(instance, BusinessProfile):
            profile_type = "business"
        elif isinstance(instance, CreatorProfile):
            profile_type = "creator"
        else:
            profile_type = None
            
        if profile_type:
            download_url = reverse("download_profile_pdf", args=[profile_type, instance.pk])
            buttons.append(
                GenericMenuItem(
                    _("Download PDF"),
                    url=download_url,
                    icon_name="download",
                    priority=25,
                )
            )
            
        for item in buttons:
            if hasattr(item, "label") and (str(item.label) == "Inspect" or item.label == _("Inspect")):
                item.label = _("View")
                item.icon_name = "view"
        return buttons

# Custom Inspect Views to supply settings and related objects data
class BusinessProfileInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        business_profile = self.object
        context["instance"] = business_profile
        # Ensure BusinessSettings exists
        BusinessSettings.objects.get_or_create(business=business_profile)
        context["settings"] = getattr(business_profile, "settings", None)
        
        # Pre-split business types (prioritizing ManyToMany relation)
        business_types = []
        if business_profile.business_types.exists():
            business_types = [t.name for t in business_profile.business_types.all()]
        elif business_profile.business_type:
            # handle both comma and space separation
            business_types = [t.strip() for t in business_profile.business_type.replace(",", " ").split() if t.strip()]
        context["business_types"] = business_types
        return context

class CreatorProfileInspectView(InspectView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        creator_profile = self.object
        context["instance"] = creator_profile
        # Ensure CreatorSettings exists
        CreatorSettings.objects.get_or_create(creator=creator_profile)
        context["settings"] = getattr(creator_profile, "settings", None)
        
        # Pre-split platforms list for rates
        rates_data = []
        for rate in creator_profile.rates.all():
            platforms_list = [p.strip() for p in rate.platforms.replace(",", " ").split() if p.strip()]
            rates_data.append({
                "content_type": rate.content_type,
                "platforms_list": platforms_list,
                "price": rate.price,
                "notes": rate.notes
            })
        context["rates"] = rates_data
        
        context["payout_methods"] = creator_profile.payout_methods.all()
        context["social_accounts"] = creator_profile.user.social_accounts.all()
        return context

# 1. Business Profile Admin Viewset
class BusinessProfileViewSet(ModelViewSet):
    model = BusinessProfile
    menu_label = "Business Profiles"
    icon = "user"
    menu_icon = "user"
    menu_item_name = "business_profiles"
    add_to_admin_menu = False
    exclude_form_fields = ["featured_at"]
    create_view_enabled = False
    
    # Custom Index and Inspect Views
    index_view_class = ProfileIndexView
    inspect_view_enabled = True
    inspect_view_class = BusinessProfileInspectView
    inspect_template_name = "user/inspect_business_profile.html"
    
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
    exclude_form_fields = ["featured_at"]
    create_view_enabled = False
    
    # Custom Index and Inspect Views
    index_view_class = ProfileIndexView
    inspect_view_enabled = True
    inspect_view_class = CreatorProfileInspectView
    inspect_template_name = "user/inspect_creator_profile.html"
    
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

# 3. Niche Admin Viewset
class NicheViewSet(ModelViewSet):
    model = Niche
    menu_label = "Niches"
    icon = "tag"
    menu_icon = "tag"
    menu_item_name = "niches"
    add_to_admin_menu = False
    form_fields = ["name"]
    list_display = ("name",)
    search_fields = ("name",)

# 4. Business Type Admin Viewset
class BusinessTypeViewSet(ModelViewSet):
    model = BusinessType
    menu_label = "Business Types"
    icon = "list-ul"
    menu_icon = "list-ul"
    menu_item_name = "business_types"
    add_to_admin_menu = False
    form_fields = ["name"]
    list_display = ("name",)
    search_fields = ("name",)

# Register Viewsets directly (without adding to sidebar directly, as we will use custom menu items)
@hooks.register("register_admin_viewset")
def register_business_profile_viewset():
    return BusinessProfileViewSet()

@hooks.register("register_admin_viewset")
def register_creator_profile_viewset():
    return CreatorProfileViewSet()

@hooks.register("register_admin_viewset")
def register_niche_viewset():
    return NicheViewSet()

@hooks.register("register_admin_viewset")
def register_business_type_viewset():
    return BusinessTypeViewSet()

# Register custom nested menu items
@hooks.register("register_admin_menu_item")
def register_custom_user_profiles_menu():
    # Instantiate viewsets to access their dynamic URL helpers
    biz_prof = BusinessProfileViewSet()
    biz_type = BusinessTypeViewSet()
    creator_prof = CreatorProfileViewSet()
    niche = NicheViewSet()

    # Business Submenu Items
    business_menu = Menu(items=[
        MenuItem("Business Profiles", biz_prof.menu_url, icon_name="user"),
        MenuItem("Business Types", biz_type.menu_url, icon_name="list-ul"),
    ])
    business_submenu = SubmenuMenuItem(
        label="Business",
        menu=business_menu,
        icon_name="folder-open-1",
    )

    # Creator Submenu Items
    creator_menu = Menu(items=[
        MenuItem("Creator Profiles", creator_prof.menu_url, icon_name="user"),
        MenuItem("Niches", niche.menu_url, icon_name="tag"),
    ])
    creator_submenu = SubmenuMenuItem(
        label="Creator",
        menu=creator_menu,
        icon_name="folder-open-1",
    )

    # Main User Profiles Parent Submenu
    main_menu = Menu(items=[
        business_submenu,
        creator_submenu,
    ])

    return SubmenuMenuItem(
        label="User Profiles",
        menu=main_menu,
        icon_name="user",
        order=150,
    )

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

@receiver(user_logged_in)
def login_success_message(sender, request, user, **kwargs):
    """Add a success message when user logs in"""
    if request and hasattr(request, '_messages'):
        if '/admin/' in request.path or (hasattr(request, 'session') and request.session.get('_auth_user_backend')):
            storage = messages.get_messages(request)
            if hasattr(storage, 'used'):
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


@hooks.register("register_admin_urls")
def register_user_profile_pdf_urls():
    return [
        path("user-profiles/download-pdf/<str:profile_type>/<int:profile_id>/", download_profile_pdf_view, name="download_profile_pdf"),
        path("user-profiles/approve/<int:profile_id>/", admin_approve_business_view, name="wagtail_approve_business"),
        path("user-profiles/restrict/<int:profile_id>/", admin_restrict_business_view, name="wagtail_restrict_business"),
        path("user-profiles/approve-creator/<int:profile_id>/", admin_approve_creator_view, name="wagtail_approve_creator"),
        path("user-profiles/restrict-creator/<int:profile_id>/", admin_restrict_creator_view, name="wagtail_restrict_creator"),
        path("user-profiles/toggle-featured/<str:profile_type>/<int:profile_id>/", admin_toggle_featured_view, name="wagtail_toggle_featured"),
    ]


