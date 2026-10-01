import os
import urllib.parse
from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin
from django.views.static import serve as static_serve

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views

def serve_media_with_decoding(request, path, document_root=None, show_indexes=False):
    """
    Serves media files while properly decoding percent-encoded characters
    (such as spaces and parentheses) so files stored with real spaces match correctly.
    """
    unquoted = path
    while "%" in unquoted:
        decoded = urllib.parse.unquote(unquoted)
        if decoded == unquoted:
            break
        unquoted = decoded
    if unquoted.startswith("media/"):
        unquoted = unquoted[len("media/"):]
    return static_serve(request, unquoted, document_root=document_root or settings.MEDIA_ROOT, show_indexes=show_indexes)

urlpatterns = [
    re_path(r"^media/(?P<path>.*)$", serve_media_with_decoding, {"document_root": settings.MEDIA_ROOT}),
    path("django-admin/", admin.site.urls),
    path("admin/notifications/", include("notifications.urls")),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("api/", include("user.urls")),
    path("api/campegins/", include("campegin.urls")),
    path("api/complaints/", include("complaint.urls")),
    path("api/terms/", include("terms.urls")),
    path("api/faq/", include("FAQ.urls")),
    path("api/chat_monitor/", include("chat_monitor.urls")),
    path("api/business-services/", include("business_service.urls")),
    path("api/settings/", include("Setting.urls")),
    path("api/inquire/", include("inquire.urls")),
    path("api/portfolio/", include("portfolio.urls")),
    path("api/rate-cards/", include("RateCard.urls")),
    path("api/workspace-payment/", include("WorkspacePayment.urls")),
    path("api/notifications/", include("notifications.api_urls")),
    path("api/analytics/", include("user.analytics_urls")),
    path("api/creator-ratings/", include("CreatorRating.urls")),
    path("api/business-ratings/", include("CreatorRating.business_urls")),
    path("api/privacy-policy/", include("privacy_policy.urls")),
    path("api/guides/", include("guide.urls")),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static files from development server
    urlpatterns += staticfiles_urlpatterns()

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
