import json
import os
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.conf import settings
from rest_framework.authtoken.models import Token

from .models import PortfolioItem
from user.models import CreatorProfile


def get_user_from_request(request):
    """Support Token, Bearer, and Session authentication."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Token "):
        try:
            return Token.objects.get(key=auth_header.split(" ")[1]).user
        except Token.DoesNotExist:
            return None
    elif auth_header.startswith("Bearer "):
        try:
            return Token.objects.get(key=auth_header.split(" ")[1]).user
        except Token.DoesNotExist:
            return None

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
    return None


def parse_views_number(v):
    """Parse '1.2M', '840K', '1T', '25000' into a float number."""
    if not v:
        return 0.0
    v_str = str(v).strip().upper().replace(",", "")
    try:
        if v_str.endswith("T"):
            return float(v_str[:-1]) * 1_000_000_000_000.0
        elif v_str.endswith("B"):
            return float(v_str[:-1]) * 1_000_000_000.0
        elif v_str.endswith("M"):
            return float(v_str[:-1]) * 1_000_000.0
        elif v_str.endswith("K"):
            return float(v_str[:-1]) * 1_000.0
        else:
            return float(v_str)
    except Exception:
        return 0.0


def normalize_url(url):
    """Ensure URL has scheme (https:// or http://) so it resolves as external link."""
    if not url:
        return None
    u = str(url).strip()
    if not u:
        return None
    if u.startswith("http://") or u.startswith("https://") or u.startswith("//"):
        return u
    return f"https://{u}"


def format_reach(total_reach_raw):
    """Format numeric reach into '1.2M', '840K', or '120' string."""
    if total_reach_raw >= 1_000_000_000_000:
        val = total_reach_raw / 1_000_000_000_000.0
        return f"{val:.1f}T".replace(".0T", "T")
    elif total_reach_raw >= 1_000_000_000:
        val = total_reach_raw / 1_000_000_000.0
        return f"{val:.1f}B".replace(".0B", "B")
    elif total_reach_raw >= 1_000_000:
        val = total_reach_raw / 1_000_000.0
        return f"{val:.1f}M".replace(".0M", "M")
    elif total_reach_raw >= 1_000:
        val = total_reach_raw / 1_000.0
        return f"{val:.1f}K".replace(".0K", "K")
    else:
        return str(int(total_reach_raw))


def format_reach_by_largest(views_list):
    """
    Given a list of views strings (e.g. ['100k', '1m']):
    Identify the largest unit scale among the items, convert all items to that scale,
    sum them, and return the rounded total value in the largest format (e.g. 1.1M).
    """
    units_order = ["T", "B", "M", "K"]
    highest_unit = None
    parsed_numbers = []

    for v in views_list:
        if not v:
            continue
        v_str = str(v).strip().upper().replace(",", "")
        num = parse_views_number(v)
        parsed_numbers.append(num)

        for u in units_order:
            if v_str.endswith(u):
                if highest_unit is None or units_order.index(u) < units_order.index(highest_unit):
                    highest_unit = u
                break

    total_num = sum(parsed_numbers)
    if not total_num:
        return "0"

    if total_num >= 1_000_000_000_000 or highest_unit == "T":
        val = round(total_num / 1_000_000_000_000.0, 1)
        return f"{val:.1f}T".replace(".0T", "T")
    elif total_num >= 1_000_000_000 or highest_unit == "B":
        val = round(total_num / 1_000_000_000.0, 1)
        return f"{val:.1f}B".replace(".0B", "B")
    elif total_num >= 1_000_000 or highest_unit == "M":
        val = round(total_num / 1_000_000.0, 1)
        return f"{val:.1f}M".replace(".0M", "M")
    elif total_num >= 1_000 or highest_unit == "K":
        val = round(total_num / 1_000.0, 1)
        return f"{val:.1f}K".replace(".0K", "K")
    else:
        return str(int(round(total_num)))


def build_thumbnail_url(request, item):
    """Return the full absolute URL for a thumbnail, or empty string."""
    if item.thumbnail:
        try:
            if request:
                return request.build_absolute_uri(item.thumbnail.url)
            return item.thumbnail.url
        except Exception:
            return ""
    return ""


def build_proof_screenshot_url(request, item):
    """Return the full absolute URL for the proof screenshot, or empty string."""
    if item.proof_screenshot:
        try:
            if request:
                return request.build_absolute_uri(item.proof_screenshot.url)
            return item.proof_screenshot.url
        except Exception:
            return ""
    return ""


def serialize_item(item, request=None):
    thumbnail_url = build_thumbnail_url(request, item)
    proof_screenshot_url = build_proof_screenshot_url(request, item)
    return {
        "id": item.id,
        "title": item.title,
        "platform": item.platform,
        "type": item.media_type,
        "media_type": item.media_type,
        "views": item.views,
        "er": item.engagement_rate,
        "engagement_rate": item.engagement_rate,
        "brand": item.brand or "—",
        "post_link": item.post_link or "",
        "thumbnail_url": thumbnail_url,
        "proof_screenshot_url": proof_screenshot_url,
        "is_featured": item.is_featured,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


# ==========================================
# REST API Endpoints
# ==========================================

@csrf_exempt
def portfolio_items_view(request):
    """
    GET  /api/portfolio/items/  — list creator's items + computed stats + rates
    POST /api/portfolio/items/  — create new item (supports JSON and multipart)
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Authentication required"}, status=401)

    if request.method == "GET":
        items = PortfolioItem.objects.filter(creator=user).order_by("-created_at")
        data = [serialize_item(i, request) for i in items]

        # Compute stats from real data
        total = items.count()
        avg_er = round(sum(i.engagement_rate for i in items) / total, 1) if total else 0.0
        total_reach = format_reach_by_largest([i.views for i in items])
        brands = set(i.brand.strip() for i in items if i.brand and i.brand.strip() not in ("—", "-"))

        stats = {
            "total_posts": total,
            "avg_engagement": f"{avg_er}%",
            "total_reach": total_reach or "0",
            "brand_collabs": len(brands),
        }

        # Fetch creator's rate card if available
        rates = []
        try:
            creator_profile = getattr(user, "creator_profile", None)
            if creator_profile:
                for r in creator_profile.rates.all():
                    rates.append({
                        "id": r.id,
                        "content_type": r.content_type,
                        "platforms": r.platforms,
                        "price": str(r.price),
                        "min_price": str(r.min_price) if r.min_price is not None else str(r.price),
                        "max_price": str(r.max_price) if r.max_price is not None else str(r.price),
                        "notes": r.notes or "",
                    })
        except Exception:
            pass

        return JsonResponse({"items": data, "stats": stats, "rates": rates}, status=200)

    elif request.method == "POST":
        try:
            is_multipart = request.content_type and "multipart/form-data" in request.content_type
            if is_multipart:
                body = request.POST
            elif request.content_type and "application/json" in request.content_type:
                body = json.loads(request.body.decode("utf-8") or "{}")
            else:
                body = request.POST

            title = (body.get("title") or "").strip()
            if not title:
                return JsonResponse({"error": "Title is required"}, status=400)
            if len(title) < 3:
                return JsonResponse({"error": "Title must be at least 3 letters"}, status=400)
            if len(title) > 100:
                return JsonResponse({"error": "Title cannot exceed 100 letters"}, status=400)

            platform = (body.get("platform") or "instagram").lower().strip()
            media_type = (body.get("media_type") or body.get("type") or "photo").lower().strip()
            views = str(body.get("views") or "0").strip()
            
            try:
                er_val = float(body.get("engagement_rate") or body.get("er") or 0.0)
            except (ValueError, TypeError):
                er_val = 0.0

            brand = (body.get("brand") or "").strip()
            if brand and len(brand) > 100:
                return JsonResponse({"error": "Brand cannot exceed 100 letters"}, status=400)
            post_link = normalize_url(body.get("post_link"))
            is_featured = str(body.get("is_featured", "false")).lower() in ("true", "1", "yes")

            item = PortfolioItem(
                creator=user,
                title=title,
                platform=platform,
                media_type=media_type,
                views=views,
                engagement_rate=er_val,
                brand=brand,
                post_link=post_link,
                is_featured=is_featured,
            )

            # Handle file uploads if multipart
            if is_multipart and "thumbnail" in request.FILES:
                item.thumbnail = request.FILES["thumbnail"]
            if is_multipart and "proof_screenshot" in request.FILES:
                item.proof_screenshot = request.FILES["proof_screenshot"]

            item.save()
            return JsonResponse({"item": serialize_item(item, request)}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def portfolio_item_detail_view(request, item_id):
    """
    PATCH / PUT  /api/portfolio/items/<id>/  — update item fields and files
    DELETE       /api/portfolio/items/<id>/  — delete item and clean up disk files
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        item = PortfolioItem.objects.get(id=item_id, creator=user)
    except PortfolioItem.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

    if request.method in ("PATCH", "PUT", "POST"):
        try:
            is_multipart = bool(request.content_type and "multipart/form-data" in request.content_type)
            files = {}
            if is_multipart:
                if request.method == "POST":
                    body = request.POST
                    files = request.FILES
                else:
                    from django.http.multipartparser import MultiPartParser
                    body, files = MultiPartParser(request.META, request, request.upload_handlers).parse()
            elif request.content_type and "application/json" in request.content_type:
                body = json.loads(request.body.decode("utf-8") or "{}")
            else:
                body = request.POST
                files = request.FILES

            if "title" in body:
                t = (body["title"] or "").strip()
                if not t:
                    return JsonResponse({"error": "Title cannot be empty"}, status=400)
                if len(t) < 3:
                    return JsonResponse({"error": "Title must be at least 3 letters"}, status=400)
                if len(t) > 100:
                    return JsonResponse({"error": "Title cannot exceed 100 letters"}, status=400)
                item.title = t
            if "platform" in body:
                item.platform = body["platform"].lower().strip()
            if "media_type" in body:
                item.media_type = body["media_type"].lower().strip()
            elif "type" in body:
                item.media_type = body["type"].lower().strip()
            if "views" in body:
                item.views = str(body["views"]).strip()
            if "engagement_rate" in body:
                try:
                    item.engagement_rate = float(body["engagement_rate"])
                except (ValueError, TypeError):
                    pass
            elif "er" in body:
                try:
                    item.engagement_rate = float(body["er"])
                except (ValueError, TypeError):
                    pass
            if "brand" in body:
                b = str(body["brand"]).strip()
                if len(b) > 100:
                    return JsonResponse({"error": "Brand cannot exceed 100 letters"}, status=400)
                item.brand = b
            if "post_link" in body:
                item.post_link = normalize_url(body.get("post_link"))
            if "is_featured" in body:
                val = body["is_featured"]
                item.is_featured = str(val).lower() in ("true", "1", "yes") or val is True

            # Handle file replacement with automatic disk cleanup
            if is_multipart and "thumbnail" in files:
                if item.thumbnail:
                    try:
                        item.thumbnail.delete(save=False)
                    except Exception:
                        pass
                item.thumbnail = files["thumbnail"]

            if is_multipart and "proof_screenshot" in files:
                if item.proof_screenshot:
                    try:
                        item.proof_screenshot.delete(save=False)
                    except Exception:
                        pass
                item.proof_screenshot = files["proof_screenshot"]

            item.save()
            return JsonResponse({"item": serialize_item(item, request)}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == "DELETE":
        # Delete thumbnail file from disk
        if item.thumbnail:
            try:
                item.thumbnail.delete(save=False)
            except Exception:
                pass
        # Delete proof screenshot file from disk
        if item.proof_screenshot:
            try:
                item.proof_screenshot.delete(save=False)
            except Exception:
                pass
        item.delete()
        return JsonResponse({"message": "Item deleted"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)


# ==========================================
# Wagtail Admin Custom Views
# ==========================================

@user_passes_test(lambda u: u.is_staff)
def admin_portfolio_list_view(request):
    """
    Overview list of creators with their portfolio statistics.
    Accessible at: /admin/portfolios/
    """
    query = request.GET.get("q", "").strip()

    creators_qs = CreatorProfile.objects.select_related("user", "country").prefetch_related("niches", "user__portfolio_items").all()

    if query:
        creators_qs = creators_qs.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(location__icontains=query) |
            Q(country__name__icontains=query) |
            Q(niches__name__icontains=query) |
            Q(user__portfolio_items__title__icontains=query) |
            Q(user__portfolio_items__brand__icontains=query) |
            Q(user__portfolio_items__platform__icontains=query)
        ).distinct()

    creators_data = []
    total_platform_posts = 0
    total_reach_sum = 0.0

    for cp in creators_qs:
        items = list(cp.user.portfolio_items.all())
        post_count = len(items)
        total_platform_posts += post_count

        if post_count > 0:
            avg_er = round(sum(i.engagement_rate for i in items) / post_count, 1)
            reach_sum = sum(parse_views_number(i.views) for i in items)
            total_reach_sum += reach_sum
            formatted_reach = format_reach(reach_sum)
        else:
            avg_er = 0.0
            formatted_reach = "0"

        niches_list = [n.name for n in cp.niches.all()]

        country_name = cp.country.name if cp.country else (cp.location or "—")
        creators_data.append({
            "id": cp.id,
            "user": cp.user,
            "username": cp.user.username,
            "full_name": f"{cp.user.first_name} {cp.user.last_name}".strip() or cp.user.username,
            "avatar_url": cp.avatar_url or "",
            "country": country_name,
            "location": cp.location or (cp.country.name if cp.country else "—"),
            "status": cp.status,
            "niches": niches_list,
            "post_count": post_count,
            "avg_engagement": f"{avg_er}%",
            "total_reach": formatted_reach,
        })

    creators_data.sort(key=lambda c: (c["post_count"], parse_views_number(c["total_reach"])), reverse=True)

    context = {
        "creators": creators_data,
        "total_creators": len(creators_data),
        "total_posts": total_platform_posts,
        "total_reach": format_reach(total_reach_sum),
        "search_query": query,
    }
    return render(request, "portfolio/admin_list.html", context)


@user_passes_test(lambda u: u.is_staff)
def admin_portfolio_detail_view(request, creator_id):
    """
    Individual creator's portfolio detail view with 3-column card grid and proof modal.
    Accessible at: /admin/portfolios/<creator_id>/
    """
    # Accept either CreatorProfile PK or User PK
    creator = (
        CreatorProfile.objects.filter(pk=creator_id).select_related("user", "country").first()
        or CreatorProfile.objects.filter(user_id=creator_id).select_related("user", "country").first()
    )
    if not creator:
        return get_object_or_404(CreatorProfile, pk=creator_id)

    items_qs = PortfolioItem.objects.filter(creator=creator.user).order_by("-is_featured", "-created_at")
    items = list(items_qs)

    total_posts = len(items)
    avg_er = round(sum(i.engagement_rate for i in items) / total_posts, 1) if total_posts else 0.0
    reach_raw = sum(parse_views_number(i.views) for i in items)
    total_reach = format_reach(reach_raw)
    featured_count = sum(1 for i in items if i.is_featured)
    brand_collabs = len(set(i.brand.strip() for i in items if i.brand and i.brand.strip() not in ("—", "-")))

    niches_list = [n.name for n in creator.niches.all()]
    country_name = creator.country.name if creator.country else ""
    location_display = creator.location or country_name or "Location not specified"

    context = {
        "creator": creator,
        "user": creator.user,
        "location_display": location_display,
        "country_name": country_name,
        "niches": niches_list,
        "items": items,
        "stats": {
            "total_posts": total_posts,
            "avg_engagement": f"{avg_er}%",
            "total_reach": total_reach,
            "featured_count": featured_count,
            "brand_collabs": brand_collabs,
        },
    }
    return render(request, "portfolio/admin_detail.html", context)
