import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from .models import TermsAndCondition

def get_user_from_request(request):
    """
    Helper function to authenticate a user based on Authorization header or GET/POST token parameters.
    """
    # 1. Check HTTP Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Token "):
        token_key = auth_header.split(" ")[1]
        try:
            return Token.objects.get(key=token_key).user
        except Token.DoesNotExist:
            return None

    # 2. Check query params or POST body parameter fallback
    token_key = request.GET.get("token") or request.POST.get("token")
    if not token_key and request.content_type == "application/json":
        try:
            body = json.loads(request.body)
            token_key = body.get("token")
        except:
            pass

    if token_key:
        try:
            return Token.objects.get(key=token_key).user
        except Token.DoesNotExist:
            return None
            
    # 3. Request session user fallback
    if request.user.is_authenticated:
        return request.user
        
    return None

@csrf_exempt
def api_list_terms(request):
    """
    GET view to return all active terms and conditions filtered by the user's role:
    - business: shows 'business' and 'both' terms.
    - creator/influencer: shows 'creator' and 'both' terms.
    Accepts query param ?role=business or ?role=creator (or ?role=influencer) as fallback/override.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are allowed"}, status=405)

    try:
        # Determine target role based on authentication or query parameter
        role = request.GET.get("role")
        
        # Authenticate user if possible
        user = get_user_from_request(request)
        if user and not role:
            # Check user profile role
            try:
                role = user.profile.role
            except AttributeError:
                # Fallback if user doesn't have a profile
                pass

        # Build query for active terms
        queryset = TermsAndCondition.objects.filter(is_active=True)

        if role:
            role = role.lower()
            if role in ("business",):
                queryset = queryset.filter(target_audience__in=["business", "both"])
            elif role in ("creator", "influencer"):
                queryset = queryset.filter(target_audience__in=["creator", "both"])
            elif role == "both":
                pass # Return all active terms
            else:
                pass

        # Serialize results
        terms_list = []
        for term in queryset.order_by("-id"):
            terms_list.append({
                "id": term.id,
                "terms_id": term.terms_id,
                "title": term.title,
                "content": term.content,
                "target_audience": term.target_audience,
                "target_audience_display": term.get_target_audience_display(),
                "created_at": term.created_at.isoformat(),
                "updated_at": term.updated_at.isoformat(),
            })

        return JsonResponse({"terms": terms_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
