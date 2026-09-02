import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from .models import Guide

@csrf_exempt
def api_list_guides(request):
    """
    GET view to return active guides:
    - role query parameter: 'creator', 'business', 'both', 'public', 'creator_support', 'business_support', 'all'.
    - category query parameter: 'handbook', 'protection', 'payment', 'brand_request', 'deliverable', 'general'.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are allowed"}, status=405)

    try:
        role = request.GET.get("role")
        category = request.GET.get("category")
        if role:
            role = role.lower().strip()
        if category:
            category = category.lower().strip()

        queryset = Guide.objects.filter(is_active=True)

        if role in ("creator", "influencer"):
            queryset = queryset.filter(
                models.Q(target_audience__iexact="creator") | models.Q(target_audience__iexact="both")
            )
        elif role in ("business", "brand"):
            queryset = queryset.filter(
                models.Q(target_audience__iexact="business") | models.Q(target_audience__iexact="both")
            )
        elif role in ("creator_support", "creator support", "influencer_support"):
            queryset = queryset.filter(
                models.Q(target_audience__iexact="creator_support") | models.Q(target_audience__iexact="both")
            )
        elif role in ("business_support", "business support", "biz_support"):
            queryset = queryset.filter(
                models.Q(target_audience__iexact="business_support") | models.Q(target_audience__iexact="both")
            )
        elif role == "both":
            queryset = queryset.filter(target_audience__iexact="both")
        elif role == "public":
            queryset = queryset.filter(target_audience__iexact="public")
        elif role == "all":
            pass

        if category:
            queryset = queryset.filter(category__iexact=category)

        guides_list = []
        for g in queryset.order_by("id"):
            guides_list.append({
                "id": g.id,
                "guide_id": g.guide_id,
                "title": g.title,
                "category": g.category,
                "category_display": g.get_category_display(),
                "content": g.content,
                "document": request.build_absolute_uri(g.document.url) if g.document else None,
                "document_name": g.document.name.split("/")[-1] if g.document else None,
                "target_audience": (g.target_audience or "creator").lower(),
                "target_audience_display": g.get_target_audience_display(),
                "created_at": g.created_at.isoformat(),
                "updated_at": g.updated_at.isoformat(),
            })

        return JsonResponse({"guides": guides_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
