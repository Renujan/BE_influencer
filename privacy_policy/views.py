import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from .models import PrivacyPolicy

@csrf_exempt
def api_list_privacy_policies(request):
    """
    GET view to return active privacy policies:
    - Default (landing page / no role, or role=public): returns ONLY 'public' policies.
    - role=business: returns 'business' and 'both' policies.
    - role=creator or role=influencer: returns 'creator' and 'both' policies.
    - role=business_support: returns 'business_support' and 'both' policies.
    - role=creator_support: returns 'creator_support' and 'both' policies.
    - role=both: returns 'both' policies.
    - role=all: returns all active policies.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are allowed"}, status=405)

    try:
        role = request.GET.get("role")
        if role:
            role = role.lower().strip()

        queryset = PrivacyPolicy.objects.filter(is_active=True)

        if role in ("business", "brand"):
            queryset = queryset.filter(
                models.Q(target_audience__iexact="business") | models.Q(target_audience__iexact="both")
            )
        elif role in ("creator", "influencer"):
            queryset = queryset.filter(
                models.Q(target_audience__iexact="creator") | models.Q(target_audience__iexact="both")
            )
        elif role in ("business_support", "business support", "biz_support"):
            queryset = queryset.filter(
                models.Q(target_audience__iexact="business_support") | models.Q(target_audience__iexact="both")
            )
        elif role in ("creator_support", "creator support", "influencer_support"):
            queryset = queryset.filter(
                models.Q(target_audience__iexact="creator_support") | models.Q(target_audience__iexact="both")
            )
        elif role == "both":
            queryset = queryset.filter(target_audience__iexact="both")
        elif role == "all":
            pass
        else:
            queryset = queryset.filter(target_audience__iexact="public")

        policies_list = []
        for policy in queryset.order_by("-id"):
            policies_list.append({
                "id": policy.id,
                "policy_id": policy.policy_id,
                "title": policy.title,
                "content": policy.content,
                "target_audience": (policy.target_audience or "public").lower(),
                "target_audience_display": policy.get_target_audience_display(),
                "created_at": policy.created_at.isoformat(),
                "updated_at": policy.updated_at.isoformat(),
            })

        return JsonResponse({"privacy_policies": policies_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
