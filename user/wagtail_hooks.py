from wagtail import hooks
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.menu import Menu, MenuItem, SubmenuMenuItem
from wagtail.admin.views.generic.models import InspectView, IndexView, EditView, MenuItem as GenericMenuItem
import json

def get_countries_hierarchy_json():
    countries_data = []
    for country in Country.objects.prefetch_related('provinces', 'districts').all():
        countries_data.append({
            'id': country.id,
            'name': country.name,
            'currency': country.currency or '',
            'country_code': country.country_code or '',
            'provinces': [{'id': p.id, 'name': p.name} for p in country.provinces.all()],
            'districts': [{'id': d.id, 'name': d.name, 'province': d.province_id} for d in country.districts.all()],
        })
    return json.dumps(countries_data)

class BusinessProfileEditView(EditView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["countries_json"] = get_countries_hierarchy_json()
        return context

class CreatorProfileEditView(EditView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["countries_json"] = get_countries_hierarchy_json()
        return context
from django.utils.translation import gettext as _
from django.urls import reverse, path
from .models import BusinessProfile, CreatorProfile, Niche, BusinessType, Country, Medium, CreatorSocialAccount
from Setting.models import CreatorSettings, BusinessSettings
from .views import (
    download_profile_pdf_view, admin_approve_business_view, admin_restrict_business_view,
    admin_approve_creator_view, admin_restrict_creator_view, admin_toggle_featured_view,
    admin_accept_delete_creator_view, admin_decline_delete_creator_view,
    admin_accept_delete_business_view, admin_decline_delete_business_view
)
from portfolio.views import admin_portfolio_list_view, admin_portfolio_detail_view
from .social_views import (
    admin_social_account_list_view,
    admin_social_account_detail_view,
    admin_toggle_social_account_verified_view,
    admin_toggle_social_account_connected_view,
)

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
        context["mediums"] = business_profile.mediums.all()
        context["payout_methods"] = business_profile.payout_methods.all()
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
        context["portfolio_items"] = creator_profile.user.portfolio_items.all()
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
    
    # Custom Index, Inspect, and Edit Views
    index_view_class = ProfileIndexView
    inspect_view_enabled = True
    inspect_view_class = BusinessProfileInspectView
    edit_view_class = BusinessProfileEditView
    inspect_template_name = "user/inspect_business_profile.html"
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"
    
    list_display = ("user", "company_name", "business_type", "get_mediums_display", "phone", "otp_verified", "status", "country")
    list_export = ("id", "user.username", "user.email", "company_name", "business_type", "mediums_list", "website", "phone", "otp_verified", "status", "country.name")
    list_filter = ("otp_verified", "status", "mediums")
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
    
    # Custom Index, Inspect, and Edit Views
    index_view_class = ProfileIndexView
    inspect_view_enabled = True
    inspect_view_class = CreatorProfileInspectView
    edit_view_class = CreatorProfileEditView
    inspect_template_name = "user/inspect_creator_profile.html"
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"
    
    list_display = ("user", "phone", "location", "country", "get_formatted_wallet", "otp_verified", "get_status_badge", "get_rating_display")
    list_export = ("id", "user.username", "user.email", "phone", "location", "country.name", "wallet_balance", "otp_verified", "status")
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
    form_fields = ["name", "is_active"]
    list_display = ("name", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name",)
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

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
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

from django import forms
from wagtail.admin.forms.models import WagtailAdminModelForm
from .models import Province

class FlexibleModelChoiceField(forms.ModelChoiceField):
    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, Province):
            return value
        val_str = str(value).strip() if isinstance(value, str) else str(value)
        if val_str.isdigit():
            p = Province.objects.filter(pk=int(val_str)).first()
            if p:
                return p
        p = Province.objects.filter(name__iexact=val_str).first()
        if p:
            return p
        return Province(name=val_str)

    def validate(self, value):
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'], code='required')
        return True

# 5. Country Admin Viewset
class CountryViewSet(ModelViewSet):
    model = Country
    menu_label = "Countries"
    icon = "globe"
    menu_icon = "globe"
    menu_item_name = "countries"
    add_to_admin_menu = False
    list_display = ("name", "currency", "country_code")
    search_fields = ("name", "currency", "country_code")
    edit_template_name = "wagtailadmin/country_edit_premium.html"
    create_template_name = "wagtailadmin/country_edit_premium.html"

    def get_form_class(self, for_update=False):
        BaseFormClass = super().get_form_class(for_update=for_update)
        
        class CustomCountryAdminForm(BaseFormClass):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if hasattr(self, 'formsets') and 'districts' in self.formsets:
                    districts_fs = self.formsets['districts']
                    for f in list(districts_fs.forms) + ([districts_fs.empty_form] if hasattr(districts_fs, 'empty_form') else []):
                        if 'province' in f.fields:
                            f.fields['province'] = FlexibleModelChoiceField(queryset=Province.objects.all(), required=False)

            def save(self, commit=True):
                districts_fs = self.formsets.pop('districts', None) if hasattr(self, 'formsets') else None

                country = super().save(commit=commit)

                if districts_fs is not None:
                    self.formsets['districts'] = districts_fs
                    districts_fs.instance = country

                prov_map = {}
                for p in country.provinces.all():
                    prov_map[str(p.id)] = p
                    prov_map[p.name.strip().lower()] = p

                if districts_fs is not None:
                    for f in districts_fs.forms:
                        f.instance.country = country
                        if hasattr(f, 'cleaned_data') and not f.cleaned_data.get('DELETE'):
                            raw_prov = f.cleaned_data.get('province') or f.data.get(f.add_prefix('province'))
                            if raw_prov:
                                raw_str = raw_prov.name if isinstance(raw_prov, Province) else str(raw_prov).strip()
                                prov_obj = prov_map.get(raw_str.lower()) or prov_map.get(raw_str)
                                if not prov_obj and raw_str.isdigit():
                                    prov_obj = Province.objects.filter(pk=int(raw_str)).first()
                                if not prov_obj and country.pk:
                                    prov_obj = Province.objects.create(country=country, name=raw_str)
                                
                                if prov_obj:
                                    f.instance.province = prov_obj
                                    f.cleaned_data['province'] = prov_obj

                    districts_fs.save(commit=commit)
                    
                return country

        return CustomCountryAdminForm

# 6. Medium Admin Viewset
class MediumViewSet(ModelViewSet):
    model = Medium
    menu_label = "Mediums"
    icon = "tag"
    menu_icon = "tag"
    menu_item_name = "mediums"
    add_to_admin_menu = False
    form_fields = ["name"]
    list_display = ("name",)
    search_fields = ("name",)
    edit_template_name = "wagtailadmin/generic_edit_premium.html"
    create_template_name = "wagtailadmin/generic_create_premium.html"

# Custom Index View for Social Accounts to ensure Inspect / View action is prominent
class SocialAccountIndexView(IndexView):
    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            creator = getattr(instance.user, "creator_profile", None)
            if creator:
                return reverse("admin_social_accounts_detail", args=[creator.pk])
            return reverse("admin_social_accounts_list")

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
        creator = getattr(instance.user, "creator_profile", None)
        detail_url = reverse("admin_social_accounts_detail", args=[creator.pk]) if creator else reverse("admin_social_accounts_list")
        return [
            GenericMenuItem(
                _("View"),
                url=detail_url,
                icon_name="view",
                priority=10,
            )
        ]

# 7. Creator Connected Social Accounts Viewset
class CreatorSocialAccountViewSet(ModelViewSet):
    model = CreatorSocialAccount
    menu_label = "Connected Accounts"
    icon = "link"
    menu_icon = "link"
    menu_item_name = "creator_social_accounts"
    add_to_admin_menu = False
    inspect_view_enabled = True
    index_view_class = SocialAccountIndexView
    form_fields = ["user", "platform", "username", "followers_count", "proof_link", "is_connected", "is_verified"]
    inspect_view_fields = ["user", "platform", "username", "followers_count", "get_proof_link_display", "is_connected", "is_verified"]
    list_display = ("user", "platform", "username", "followers_count", "get_proof_link_display", "is_connected", "is_verified")
    list_editable = ("is_verified", "is_connected")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name", "platform", "username")
    list_filter = ("platform", "is_connected", "is_verified")

# 8. Creator Portfolio Admin Viewset & Index View
class PortfolioIndexView(IndexView):
    def _get_title_column(self, field_name, column_class=TitleColumn, **kwargs):
        column_class = self._get_title_column_class(column_class)

        def get_url(instance):
            return reverse("admin_portfolio_detail", args=[instance.pk])

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

    def get_edit_url(self, instance):
        return reverse("admin_portfolio_detail", args=[instance.pk])

    def get_inspect_url(self, instance):
        return reverse("admin_portfolio_detail", args=[instance.pk])

    def get_list_more_buttons(self, instance):
        return [
            GenericMenuItem(
                _("View"),
                url=reverse("admin_portfolio_detail", args=[instance.pk]),
                icon_name="view",
                priority=10,
            )
        ]


class PortfolioViewSet(ModelViewSet):
    model = CreatorProfile
    menu_label = "Portfolios"
    icon = "folder-open-1"
    menu_icon = "folder-open-1"
    menu_item_name = "portfolios"
    url_namespace = "creator_portfolios_admin"
    url_prefix = "portfolios-admin"
    add_to_admin_menu = False
    index_view_class = PortfolioIndexView
    create_view_enabled = False
    inspect_view_enabled = False
    form_fields = ["user", "phone", "country", "status"]

    list_display = ("user", "country", "get_status_badge")
    search_fields = ("user__username", "user__email", "country__name", "location")

    @property
    def permission_policy(self):
        from wagtail.permissions import ModelPermissionPolicy

        class NoModifyPermissionPolicy(ModelPermissionPolicy):
            def user_has_permission(self, user, action):
                if action in ("add", "edit", "delete"):
                    return False
                return super().user_has_permission(user, action)

        return NoModifyPermissionPolicy(self.model)

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

@hooks.register("register_admin_viewset")
def register_country_viewset():
    return CountryViewSet()

@hooks.register("register_admin_viewset")
def register_medium_viewset():
    return MediumViewSet()

@hooks.register("register_admin_viewset")
def register_creator_social_account_viewset():
    return CreatorSocialAccountViewSet()

@hooks.register("register_admin_viewset")
def register_portfolio_viewset():
    return PortfolioViewSet()

@hooks.register("register_admin_menu_item")
def register_portfolios_sidebar_menu():
    return MenuItem(
        "Portfolios",
        reverse("admin_portfolio_list"),
        icon_name="folder-open-1",
        order=180,
    )

# Register custom nested menu items
@hooks.register("register_admin_menu_item")
def register_custom_user_profiles_menu():
    # Instantiate viewsets to access their dynamic URL helpers
    biz_prof = BusinessProfileViewSet()
    biz_type = BusinessTypeViewSet()
    creator_prof = CreatorProfileViewSet()
    niche_view = NicheViewSet()
    country_view = CountryViewSet()
    medium_view = MediumViewSet()
    niche = NicheViewSet()
    country_viewset = CountryViewSet()

    from CreatorRating.wagtail_hooks import CreatorRatingViewSet, BusinessRatingViewSet
    creator_rating_view = CreatorRatingViewSet()
    biz_rating_view = BusinessRatingViewSet()

    # Business Submenu Items
    business_menu = Menu(items=[
        MenuItem("Business Profiles", biz_prof.menu_url, icon_name="user"),
        MenuItem("Business Types", biz_type.menu_url, icon_name="list-ul"),
        MenuItem("Rating", biz_rating_view.menu_url, icon_name="pick"),
    ])
    business_submenu = SubmenuMenuItem(
        label="Business",
        menu=business_menu,
        icon_name="folder-open-1",
    )

    social_acc_view = CreatorSocialAccountViewSet()

    # Creator Submenu Items
    creator_menu = Menu(items=[
        MenuItem("Creator Profiles", creator_prof.menu_url, icon_name="user"),
        MenuItem("Connected Accounts", reverse("admin_social_accounts_list"), icon_name="link"),
        MenuItem("Niches", niche.menu_url, icon_name="tag"),
        MenuItem("Rating", creator_rating_view.menu_url, icon_name="pick"),
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
        MenuItem("Countries", country_viewset.menu_url, icon_name="globe"),
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

from wagtail.admin.search import admin_search_areas
admin_search_areas.search_items_for_request = lambda request: []

@hooks.register('construct_main_menu')
def hide_unwanted_menu_items(request, menu_items):
    # Hide search, reports, images, documents, help, explorer (Pages), and snippets items from the main menu sidebar
    menu_items[:] = [item for item in menu_items if item.name not in ['search', 'wagtailadmin_search', 'reports', 'images', 'documents', 'help', 'explorer', 'snippets']]

    # Remove Wagtail version / footer_text from all submenu items including Settings
    for item in menu_items:
        if hasattr(item, 'render_component'):
            orig_render = item.render_component
            def make_clean_render(orig_fn):
                def clean_render(req):
                    comp = orig_fn(req)
                    if hasattr(comp, 'footer_text'):
                        comp.footer_text = ""
                    return comp
                return clean_render
            item.render_component = make_clean_render(orig_render)

@hooks.register('construct_settings_menu')
def hide_unwanted_settings_menu_items(request, menu_items):
    # Keep only users and groups inside the settings menu
    menu_items[:] = [item for item in menu_items if item.name in ['users', 'groups']]

from django.utils.safestring import mark_safe

@hooks.register("insert_global_admin_css")
def hide_sidebar_search_and_version_css():
    return mark_safe(
        """
        <style>
            /* Hide Super Admin Sidebar Search Bar & Search Container */
            .w-sidebar form[action*="search"],
            .w-sidebar input[type="search"],
            .w-sidebar [role="search"],
            .w-sidebar input[name="menu-search-q"],
            .sidebar-search,
            .sidebar-search-form,
            .w-sidebar-search,
            .w-sidebar__search,
            .w-sidebar-search-form,
            .sidebar-search__input,
            [data-wagtail-sidebar-search],
            [data-sidebar-search],
            .sidebar-menu-item--search,
            .w-sidebar [class*="search"] {
                display: none !important;
            }

            /* Hide Wagtail version in sidebar settings expansion & footer */
            .sidebar-sub-menu-panel__footer,
            .sidebar-sub-menu__footer,
            .sidebar-footer__version,
            .w-sidebar-footer__version,
            .w-version,
            [class*="sub-menu-panel__footer"],
            [class*="sub-menu__footer"],
            .w-sidebar__footer-version,
            .sidebar-main-menu--open-footer {
                display: none !important;
                visibility: hidden !important;
                height: 0 !important;
                padding: 0 !important;
                margin: 0 !important;
                opacity: 0 !important;
            }
        </style>
        """
    )



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
        path("user-profiles/accept-delete-creator/<int:profile_id>/", admin_accept_delete_creator_view, name="wagtail_accept_delete_creator"),
        path("user-profiles/decline-delete-creator/<int:profile_id>/", admin_decline_delete_creator_view, name="wagtail_decline_delete_creator"),
        path("user-profiles/accept-delete-business/<int:profile_id>/", admin_accept_delete_business_view, name="wagtail_accept_delete_business"),
        path("user-profiles/decline-delete-business/<int:profile_id>/", admin_decline_delete_business_view, name="wagtail_decline_delete_business"),
        path("user-profiles/toggle-featured/<str:profile_type>/<int:profile_id>/", admin_toggle_featured_view, name="wagtail_toggle_featured"),
        path("portfolios/", admin_portfolio_list_view, name="admin_portfolio_list"),
        path("portfolios/<int:creator_id>/", admin_portfolio_detail_view, name="admin_portfolio_detail"),
        path("social-accounts/", admin_social_account_list_view, name="admin_social_accounts_list"),
        path("social-accounts/<int:creator_id>/", admin_social_account_detail_view, name="admin_social_accounts_detail"),
        path("social-accounts/toggle-verify/<int:account_id>/", admin_toggle_social_account_verified_view, name="admin_social_accounts_toggle_verify"),
        path("social-accounts/toggle-connect/<int:account_id>/", admin_toggle_social_account_connected_view, name="admin_social_accounts_toggle_connect"),
    ]


