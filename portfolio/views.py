import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.authtoken.models import Token
from .models import PortfolioItem


def get_user_from_request(request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Token "):
        try:
            return Token.objects.get(key=auth_header.split(" ")[1]).user
        except Token.DoesNotExist:
            return None
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
    return None


def build_thumbnail_url(request, item):
    """Return the full absolute URL for a thumbnail, or empty string."""
    if item.thumbnail:
        try:
            return request.build_absolute_uri(item.thumbnail.url)
        except Exception:
            return ""
    return ""


def serialize_item(item, request=None):
    thumbnail_url = build_thumbnail_url(request, item) if request else (
        item.thumbnail.url if item.thumbnail else ""
    )
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
        "is_featured": item.is_featured,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


@csrf_exempt
def portfolio_items_view(request):
    """
    GET  /api/portfolio/items/  — list creator's items + computed stats + rates
    POST /api/portfolio/items/  — create new item (supports multipart for image upload)
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Authentication required"}, status=401)

    if request.method == "GET":
        items = PortfolioItem.objects.filter(creator=user)
        data = [serialize_item(i, request) for i in items]

        # Compute stats from real data
        total = items.count()
        avg_er = round(sum(i.engagement_rate for i in items) / total, 1) if total else 0.0

        def parse_views(v):
            v = str(v).strip().upper().replace(",", "")
            try:
                if v.endswith("M"):
                    return float(v[:-1]) * 1_000_000
                elif v.endswith("K"):
                    return float(v[:-1]) * 1_000
                else:
                    return float(v)
            except Exception:
                return 0

        total_reach_raw = sum(parse_views(i.views) for i in items)
        if total_reach_raw >= 1_000_000:
            total_reach = f"{round(total_reach_raw / 1_000_000, 1)}M"
        elif total_reach_raw >= 1_000:
            total_reach = f"{round(total_reach_raw / 1_000, 1)}K"
        else:
            total_reach = str(int(total_reach_raw))

        brands = set(i.brand for i in items if i.brand and i.brand != "—")

        stats = {
            "total_posts": total,
            "avg_engagement": f"{avg_er}%",
            "total_reach": total_reach or "0",
            "brand_collabs": len(brands),
        }

        # Fetch creator's rate card
        rates = []
        try:
            creator_profile = user.creator_profile
            for r in creator_profile.rates.all():
                rates.append({
                    "id": r.id,
                    "content_type": r.content_type,
                    "platforms": r.platforms,
                    "price": str(r.price),
                    "notes": r.notes or "",
                })
        except Exception:
            pass

        return JsonResponse({"items": data, "stats": stats, "rates": rates}, status=200)

    elif request.method == "POST":
        try:
            # Detect multipart (image upload) vs JSON
            is_multipart = request.content_type and "multipart/form-data" in request.content_type
            if is_multipart:
                body = request.POST
            elif request.content_type and "application/json" in request.content_type:
                body = json.loads(request.body)
            else:
                body = request.POST

            title = (body.get("title") or "").strip()
            if not title:
                return JsonResponse({"error": "title is required"}, status=400)

            item = PortfolioItem(
                creator=user,
                title=title,
                platform=(body.get("platform") or "instagram").lower(),
                media_type=(body.get("type") or body.get("media_type") or "photo").lower(),
                views=body.get("views") or "0",
                engagement_rate=float(body.get("er") or body.get("engagement_rate") or 0),
                brand=body.get("brand") or "",
                post_link=body.get("post_link") or None,
                is_featured=str(body.get("is_featured", "false")).lower() in ("true", "1", "yes"),
            )

            # Handle image upload
            if is_multipart and "thumbnail" in request.FILES:
                item.thumbnail = request.FILES["thumbnail"]

            item.save()
            return JsonResponse({"item": serialize_item(item, request)}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def portfolio_item_detail_view(request, item_id):
    """
    PATCH  /api/portfolio/items/<id>/  — update fields including thumbnail
    DELETE /api/portfolio/items/<id>/  — delete item
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        item = PortfolioItem.objects.get(id=item_id, creator=user)
    except PortfolioItem.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

    if request.method in ("PATCH", "PUT"):
        try:
            is_multipart = request.content_type and "multipart/form-data" in request.content_type
            if is_multipart:
                body = request.POST
            elif request.content_type and "application/json" in request.content_type:
                body = json.loads(request.body)
            else:
                body = request.POST

            if "title" in body and body["title"]:
                item.title = body["title"].strip()
            if "platform" in body:
                item.platform = body["platform"].lower()
            if "type" in body:
                item.media_type = body["type"].lower()
            if "media_type" in body:
                item.media_type = body["media_type"].lower()
            if "views" in body:
                item.views = body["views"]
            if "er" in body:
                item.engagement_rate = float(body["er"])
            if "engagement_rate" in body:
                item.engagement_rate = float(body["engagement_rate"])
            if "brand" in body:
                item.brand = body["brand"]
            if "post_link" in body:
                item.post_link = body["post_link"] or None
            if "is_featured" in body:
                val = body["is_featured"]
                item.is_featured = val in (True, "true", "1", "yes") or val is True

            # Handle image upload on PATCH
            if is_multipart and "thumbnail" in request.FILES:
                # Delete old thumbnail if exists
                if item.thumbnail:
                    try:
                        item.thumbnail.delete(save=False)
                    except Exception:
                        pass
                item.thumbnail = request.FILES["thumbnail"]

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
        item.delete()
        return JsonResponse({"message": "Item deleted"}, status=200)

    return JsonResponse({"error": "Method not allowed"}, status=405)
