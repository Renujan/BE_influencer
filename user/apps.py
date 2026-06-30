from django.apps import AppConfig
from wagtail.users.apps import WagtailUsersAppConfig


class UserConfig(AppConfig):
    default = True
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'


class CustomUsersAppConfig(WagtailUsersAppConfig):
    user_viewset = "user.views.CustomUserViewSet"



