from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse

from .models import CreatorProfile, CreatorSocialAccount
from django.contrib.auth.models import User


def parse_followers_number(v):
    """Parse '1.2M', '840K', '25,000' into a float number."""
    if not v:
        return 0.0
    v_str = str(v).strip().upper().replace(",", "").replace(" ", "")
    try:
        if v_str.endswith("M"):
            return float(v_str[:-1]) * 1_000_000
        elif v_str.endswith("K"):
            return float(v_str[:-1]) * 1_000
        elif v_str.endswith("B"):
            return float(v_str[:-1]) * 1_000_000_000
        else:
            return float(v_str)
    except Exception:
        return 0.0


def format_followers_display(num):
    """Format numeric reach into '1.2M', '840K', or formatted integer."""
    if num >= 1_000_000:
        val = num / 1_000_000
        return f"{val:.1f}M".replace(".0M", "M")
    elif num >= 1_000:
        val = num / 1_000
        return f"{val:.1f}K".replace(".0K", "K")
    elif num > 0:
        return f"{int(num):,}"
    return "0"


def normalize_platform_info(platform_name):
    """Return icon, colors, and clean name for social platforms."""
    plat = (platform_name or "").strip().lower()
    if "insta" in plat:
        return {
            "key": "instagram",
            "name": "Instagram",
            "icon": "fa-brands fa-instagram",
            "color": "#E1306C",
            "gradient": "linear-gradient(135deg, #833ab4, #fd1d1d, #fcb045)",
            "badge_bg": "rgba(225, 48, 108, 0.1)",
            "badge_text": "#E1306C",
        }
    elif "you" in plat or "yt" in plat:
        return {
            "key": "youtube",
            "name": "YouTube",
            "icon": "fa-brands fa-youtube",
            "color": "#FF0000",
            "gradient": "linear-gradient(135deg, #ff0000, #cc0000)",
            "badge_bg": "rgba(255, 0, 0, 0.1)",
            "badge_text": "#FF0000",
        }
    elif "tik" in plat:
        return {
            "key": "tiktok",
            "name": "TikTok",
            "icon": "fa-brands fa-tiktok",
            "color": "#000000",
            "gradient": "linear-gradient(135deg, #010101, #25F4EE)",
            "badge_bg": "rgba(0, 0, 0, 0.08)",
            "badge_text": "#0f172a",
        }
    elif "face" in plat or "fb" in plat:
        return {
            "key": "facebook",
            "name": "Facebook",
            "icon": "fa-brands fa-facebook",
            "color": "#1877F2",
            "gradient": "linear-gradient(135deg, #1877f2, #0d5bbd)",
            "badge_bg": "rgba(24, 119, 242, 0.1)",
            "badge_text": "#1877F2",
        }
    elif "twit" in plat or plat == "x":
        return {
            "key": "twitter",
            "name": "X (Twitter)",
            "icon": "fa-brands fa-x-twitter",
            "color": "#0f172a",
            "gradient": "linear-gradient(135deg, #1e293b, #0f172a)",
            "badge_bg": "rgba(15, 23, 42, 0.1)",
            "badge_text": "#0f172a",
        }
    elif "link" in plat:
        return {
            "key": "linkedin",
            "name": "LinkedIn",
            "icon": "fa-brands fa-linkedin",
            "color": "#0A66C2",
            "gradient": "linear-gradient(135deg, #0a66c2, #004182)",
            "badge_bg": "rgba(10, 102, 194, 0.1)",
            "badge_text": "#0A66C2",
        }
    return {
        "key": "other",
        "name": platform_name.capitalize() if platform_name else "Social Channel",
        "icon": "fa-solid fa-share-nodes",
        "color": "#4f46e5",
        "gradient": "linear-gradient(135deg, #4f46e5, #3730a3)",
        "badge_bg": "rgba(79, 70, 229, 0.1)",
        "badge_text": "#4f46e5",
    }


# ==========================================
# 1. Super Admin Social Accounts Overview List
# ==========================================
@user_passes_test(lambda u: u.is_staff)
def admin_social_account_list_view(request):
    """
    Super Admin Overview page for Creator Social Accounts.
    Accessible at: /admin/social-accounts/
    """
    query = request.GET.get("q", "").strip()
    platform_filter = request.GET.get("platform", "all").strip().lower()
    status_filter = request.GET.get("status", "all").strip().lower()

    # Query all creator profiles
    creators_qs = CreatorProfile.objects.select_related("user", "country").prefetch_related("niches", "user__social_accounts").all()

    if query:
        creators_qs = creators_qs.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(location__icontains=query) |
            Q(country__name__icontains=query) |
            Q(niches__name__icontains=query) |
            Q(user__social_accounts__username__icontains=query) |
            Q(user__social_accounts__platform__icontains=query) |
            Q(user__social_accounts__proof_link__icontains=query)
        ).distinct()

    creators_data = []
    total_accounts_count = 0
    total_verified_count = 0
    total_pending_count = 0
    total_reach_aggregate = 0

    platform_counts = {
        "instagram": 0,
        "youtube": 0,
        "tiktok": 0,
        "facebook": 0,
        "twitter": 0,
        "linkedin": 0,
    }

    all_social_accounts = CreatorSocialAccount.objects.select_related("user").all()
    for sa in all_social_accounts:
        total_accounts_count += 1
        if sa.is_verified:
            total_verified_count += 1
        elif sa.is_connected:
            total_pending_count += 1

        p_info = normalize_platform_info(sa.platform)
        if p_info["key"] in platform_counts:
            platform_counts[p_info["key"]] += 1

        reach_val = parse_followers_number(sa.followers_count)
        total_reach_aggregate += reach_val

    for cp in creators_qs:
        social_accounts = list(cp.user.social_accounts.all().order_by("-is_verified", "-is_connected", "-id"))

        # Apply platform filter if selected
        if platform_filter != "all":
            social_accounts = [sa for sa in social_accounts if platform_filter in sa.platform.lower()]

        # Apply status filter if selected
        if status_filter == "verified":
            social_accounts = [sa for sa in social_accounts if sa.is_verified]
        elif status_filter == "pending":
            social_accounts = [sa for sa in social_accounts if (sa.is_connected and not sa.is_verified)]
        elif status_filter == "disconnected":
            social_accounts = [sa for sa in social_accounts if not sa.is_connected]

        # If filtering is active and no accounts match, skip creator
        if (platform_filter != "all" or status_filter != "all") and not social_accounts:
            continue

        accounts_payload = []
        creator_reach = 0
        verified_in_creator = 0

        for sa in social_accounts:
            reach_val = parse_followers_number(sa.followers_count)
            creator_reach += reach_val
            if sa.is_verified:
                verified_in_creator += 1

            p_info = normalize_platform_info(sa.platform)
            proof_url = (sa.proof_link or "").strip()
            if proof_url and not (proof_url.startswith("http://") or proof_url.startswith("https://")):
                proof_url = f"https://{proof_url}"

            accounts_payload.append({
                "id": sa.id,
                "platform": sa.platform,
                "platform_info": p_info,
                "username": sa.username or cp.user.username,
                "followers_raw": sa.followers_count or "0",
                "followers_formatted": format_followers_display(reach_val) if reach_val else (sa.followers_count or "—"),
                "proof_link": proof_url,
                "engagement_rate": float(sa.engagement_rate or 5.0),
                "is_connected": sa.is_connected,
                "is_verified": sa.is_verified,
            })

        country_name = cp.country.name if cp.country else (cp.location or "—")
        location_str = cp.location or country_name

        creators_data.append({
            "id": cp.id,
            "user_id": cp.user.id,
            "username": cp.user.username,
            "full_name": f"{cp.user.first_name} {cp.user.last_name}".strip() or cp.user.username,
            "avatar_url": cp.avatar_url or "",
            "location": location_str,
            "country_name": country_name,
            "niches": [n.name for n in cp.niches.all()],
            "accounts": accounts_payload,
            "accounts_count": len(accounts_payload),
            "verified_count": verified_in_creator,
            "total_reach": creator_reach,
            "total_reach_formatted": format_followers_display(creator_reach),
            "is_fully_verified": (verified_in_creator > 0 and verified_in_creator == len(accounts_payload)),
        })

    # Sort creators with connected accounts first
    creators_data.sort(key=lambda c: (c["accounts_count"], c["total_reach"]), reverse=True)

    verified_percentage = round((total_verified_count / max(1, total_accounts_count)) * 100, 1)

    context = {
        "creators": creators_data,
        "total_creators": len(creators_data),
        "total_accounts_count": total_accounts_count,
        "total_verified_count": total_verified_count,
        "total_pending_count": total_pending_count,
        "total_reach_formatted": format_followers_display(total_reach_aggregate),
        "verified_percentage": verified_percentage,
        "platform_counts": platform_counts,
        "search_query": query,
        "platform_filter": platform_filter,
        "status_filter": status_filter,
    }
    return render(request, "user/social_account_admin_list.html", context)


# ==========================================
# 2. Super Admin Social Accounts Detail View
# ==========================================
@user_passes_test(lambda u: u.is_staff)
def admin_social_account_detail_view(request, creator_id):
    """
    Detail page for a creator's connected social accounts with rich cards & verification toggles.
    Accessible at: /admin/social-accounts/<creator_id>/
    """
    creator = (
        CreatorProfile.objects.filter(pk=creator_id).select_related("user", "country").first()
        or CreatorProfile.objects.filter(user_id=creator_id).select_related("user", "country").first()
    )
    if not creator:
        return get_object_or_404(CreatorProfile, pk=creator_id)

    social_accounts = list(creator.user.social_accounts.all().order_by("-is_verified", "-is_connected", "-id"))

    accounts_payload = []
    total_reach = 0
    verified_count = 0
    connected_count = 0
    engagement_sum = 0

    for sa in social_accounts:
        reach_val = parse_followers_number(sa.followers_count)
        total_reach += reach_val
        if sa.is_verified:
            verified_count += 1
        if sa.is_connected:
            connected_count += 1
        er = float(sa.engagement_rate or 5.0)
        engagement_sum += er

        p_info = normalize_platform_info(sa.platform)
        proof_url = (sa.proof_link or "").strip()
        if proof_url and not (proof_url.startswith("http://") or proof_url.startswith("https://")):
            proof_url = f"https://{proof_url}"

        accounts_payload.append({
            "id": sa.id,
            "platform": sa.platform,
            "platform_info": p_info,
            "username": sa.username or creator.user.username,
            "followers_raw": sa.followers_count or "0",
            "followers_formatted": format_followers_display(reach_val) if reach_val else (sa.followers_count or "—"),
            "proof_link": proof_url,
            "engagement_rate": er,
            "is_connected": sa.is_connected,
            "is_verified": sa.is_verified,
        })

    avg_engagement = round(engagement_sum / max(1, len(social_accounts)), 2) if social_accounts else 0.0
    country_name = creator.country.name if creator.country else ""
    location_display = creator.location or country_name or "Location not specified"

    context = {
        "creator": creator,
        "social_accounts": accounts_payload,
        "total_accounts": len(accounts_payload),
        "verified_count": verified_count,
        "connected_count": connected_count,
        "total_reach_formatted": format_followers_display(total_reach),
        "avg_engagement": avg_engagement,
        "location_display": location_display,
        "niches": [n.name for n in creator.niches.all()],
    }
    return render(request, "user/social_account_admin_detail.html", context)


# ==========================================
# 3. Super Admin Quick Toggle Verification API
# ==========================================
@user_passes_test(lambda u: u.is_staff)
@require_POST
def admin_toggle_social_account_verified_view(request, account_id):
    """Toggle is_verified status for a social account."""
    account = get_object_or_404(CreatorSocialAccount, pk=account_id)
    account.is_verified = not account.is_verified
    if account.is_verified:
        account.is_connected = True
    account.save(update_fields=["is_verified", "is_connected"])

    status_text = "verified" if account.is_verified else "unverified"
    msg = f"Account @{account.username} ({account.platform}) is now {status_text}."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse({
            "status": "success",
            "account_id": account.id,
            "is_verified": account.is_verified,
            "is_connected": account.is_connected,
            "message": msg,
        })

    messages.success(request, msg)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("admin_social_accounts_list")
    return redirect(next_url)


# ==========================================
# 4. Super Admin Quick Toggle Connected API
# ==========================================
@user_passes_test(lambda u: u.is_staff)
@require_POST
def admin_toggle_social_account_connected_view(request, account_id):
    """Toggle is_connected status for a social account."""
    account = get_object_or_404(CreatorSocialAccount, pk=account_id)
    account.is_connected = not account.is_connected
    if not account.is_connected:
        account.is_verified = False
    account.save(update_fields=["is_connected", "is_verified"])

    status_text = "connected" if account.is_connected else "disconnected"
    msg = f"Account @{account.username} ({account.platform}) is now {status_text}."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("format") == "json":
        return JsonResponse({
            "status": "success",
            "account_id": account.id,
            "is_connected": account.is_connected,
            "is_verified": account.is_verified,
            "message": msg,
        })

    messages.success(request, msg)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("admin_social_accounts_list")
    return redirect(next_url)
