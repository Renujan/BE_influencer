import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from django.db import models
from .models import TermsAndCondition

@csrf_exempt
def api_list_terms(request):
    """
    GET view to return active terms and conditions:
    - Default (landing page / no role, or role=public): returns ONLY 'public' terms.
    - role=business: returns 'business' and 'both' terms.
    - role=creator or role=influencer: returns 'creator' and 'both' terms.
    - role=both: returns 'both' terms.
    - role=all: returns all active terms (for super admin / full listings).
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are allowed"}, status=405)

    try:
        # Determine target role strictly from query parameter
        role = request.GET.get("role")
        if role:
            role = role.lower().strip()

        # Build query for active terms
        queryset = TermsAndCondition.objects.filter(is_active=True)

        if role == "business":
            queryset = queryset.filter(
                models.Q(target_audience__iexact="business") | models.Q(target_audience__iexact="both")
            )
        elif role in ("creator", "influencer"):
            queryset = queryset.filter(
                models.Q(target_audience__iexact="creator") | models.Q(target_audience__iexact="both")
            )
        elif role == "both":
            queryset = queryset.filter(target_audience__iexact="both")
        elif role == "all":
            pass  # Return all active terms
        else:
            # Default for landing page (no role specified or role=public): only return public terms
            queryset = queryset.filter(target_audience__iexact="public")

        # Serialize results
        terms_list = []
        for term in queryset.order_by("-id"):
            terms_list.append({
                "id": term.id,
                "terms_id": term.terms_id,
                "title": term.title,
                "content": term.content,
                "target_audience": (term.target_audience or "public").lower(),
                "target_audience_display": term.get_target_audience_display(),
                "created_at": term.created_at.isoformat(),
                "updated_at": term.updated_at.isoformat(),
            })

        return JsonResponse({"terms": terms_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
