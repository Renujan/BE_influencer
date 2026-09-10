import re

from django.urls import NoReverseMatch, reverse


LEGACY_ADMIN_URL_MAP = {
    "/admin/snippets/complaint/complaint/": "/admin/complaint/",
}

CATEGORY_ADMIN_FALLBACKS = {
    "signup": "businessprofile:index",
    "campaign": "wagtailsnippets_campegin_campaign:list",
    "payment": "wagtailsnippets_campegin_campaign:list",
    "compliance": "admincomplianceticket:index",
}

FRONTEND_ADMIN_ROUTE_MAP = {
    "/dashboard": "businessprofile:index",
    "/dashboard/campaigns": "wagtailsnippets_campegin_campaign:list",
    "/dashboard/payments": "wagtailsnippets_campegin_campaign:list",
    "/dashboard/support": "admincomplianceticket:index",
    "/dashboard/requests": "wagtailsnippets_campegin_campaign:list",
    "/dashboard/settings": "businessprofile:index",
    "/dashboard/business-services": "inquiry:index",
    "/dashboard/services": "inquiry:index",
    "/creator": "creatorprofile:index",
    "/creator/campaigns": "wagtailsnippets_campegin_campaign:list",
    "/creator/earnings": "wagtailsnippets_campegin_campaign:list",
    "/creator/requests": "wagtailsnippets_campegin_campaign:list",
    "/creator/support": "admincomplianceticket:index",
    "/creator/pitches": "wagtailsnippets_campegin_campaign:list",
    "/creator/profile": "creatorprofile:index",
    "/creator/portfolio": "creatorprofile:index",
    "/creator/business-services": "inquiry:index",
    "/creator/services": "inquiry:index",
}


def _safe_reverse(view_name, args=None):
    try:
        if args:
            return reverse(view_name, args=args)
        return reverse(view_name)
    except NoReverseMatch:
        return None


def resolve_admin_redirect_url(notification):
    """
    Resolve a notification click target to a valid Wagtail admin URL.
    Handles legacy admin paths, frontend app routes, and category fallbacks.
    """
    url = (notification.target_url or "").strip()

    if url in LEGACY_ADMIN_URL_MAP:
        url = LEGACY_ADMIN_URL_MAP[url]

    if url.startswith("/admin/"):
        return url

    workspace_match = re.match(r"^/workspace/(\d+)/?$", url)
    if workspace_match:
        campaign_id = workspace_match.group(1)
        resolved = _safe_reverse("wagtailsnippets_campegin_campaign:inspect", args=[campaign_id])
        if resolved:
            return resolved
        resolved = _safe_reverse("wagtailsnippets_campegin_campaign:list")
        if resolved:
            return resolved

    normalized = url.rstrip("/") or url
    for prefix, view_name in sorted(FRONTEND_ADMIN_ROUTE_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        if normalized == prefix or normalized.startswith(f"{prefix}/"):
            resolved = _safe_reverse(view_name)
            if resolved:
                return resolved

    if notification.category == "signup":
        combined = f"{notification.title} {notification.message}".lower()
        if "creator" in combined:
            inspect_match = re.search(r"/admin/creatorprofile/inspect/(\d+)/?", url)
            if inspect_match:
                resolved = _safe_reverse("creatorprofile:inspect", args=[inspect_match.group(1)])
                if resolved:
                    return resolved
            resolved = _safe_reverse("creatorprofile:index")
            if resolved:
                return resolved
        inspect_match = re.search(r"/admin/businessprofile/inspect/(\d+)/?", url)
        if inspect_match:
            resolved = _safe_reverse("businessprofile:inspect", args=[inspect_match.group(1)])
            if resolved:
                return resolved

    fallback_view = CATEGORY_ADMIN_FALLBACKS.get(notification.category)
    if fallback_view:
        resolved = _safe_reverse(fallback_view)
        if resolved:
            return resolved

    return "/admin/"


def get_user_currency_symbol(user):
    if not user:
        return "Rs"
    profile = getattr(user, 'business_profile', None) or getattr(user, 'creator_profile', None)
    if profile:
        country = getattr(profile, 'country', None)
        phone = getattr(profile, 'phone', None)
        if country or phone:
            try:
                from Setting.models import get_country_currency_format
                from campegin.models import extract_currency_symbol
                fmt = get_country_currency_format(country, phone)
                s = extract_currency_symbol(fmt)
                if s:
                    return s
            except Exception:
                pass
        sym = getattr(profile, 'currency_symbol', None)
        if sym:
            return sym
    return "Rs"


def format_currency_amount(amount, user):
    sym = get_user_currency_symbol(user)
    sep = "" if sym in ["$", "₹", "£", "€", "¥"] else " "
    try:
        amt_float = float(amount or 0)
        return f"{sym}{sep}{amt_float:,.2f}"
    except Exception:
        return f"{sym}{sep}{amount}"


def format_notification_text_currency(text, user_or_sym):
    if not text:
        return ""
    if isinstance(user_or_sym, str):
        sym = user_or_sym
    else:
        sym = get_user_currency_symbol(user_or_sym)

    if not sym or sym == "$":
        return str(text)

    sep = "" if sym in ["₹", "£", "€", "¥"] else " "

    # 1. Replace $amount or USD amount (e.g. $20,000.00, $20,000, USD 20000)
    formatted = re.sub(r'(?:\$|USD\s*)\s*([\d,]+(?:\.\d+)?)', rf'{sym}{sep}\1', str(text))

    # 2. Phrasing like counter-response of 20000 or budget of 20000
    formatted = re.sub(r'(counter-response of|budget of|price of|payment of)\s+([\d,]+(?:\.\d+)?)(?!\s*[\w])', rf'\1 {sym}{sep}\2', formatted, flags=re.IGNORECASE)

    return formatted

