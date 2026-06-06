import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authtoken.models import Token
from .models import FAQ

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
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
        
    return None

@csrf_exempt
def api_list_faq(request):
    """
    GET view to return all active FAQs filtered by the user's role:
    - business: shows 'business' and 'both' FAQs.
    - creator/influencer: shows 'creator' and 'both' FAQs.
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

        # Build query for active FAQs
        queryset = FAQ.objects.filter(is_active=True)

        if role:
            role = role.lower()
            if role in ("business",):
                queryset = queryset.filter(target_audience__in=["business", "both"])
            elif role in ("creator", "influencer"):
                queryset = queryset.filter(target_audience__in=["creator", "both"])
            elif role == "both":
                pass # Return all active FAQs
            else:
                pass

        # Serialize results
        faq_list = []
        for faq in queryset.order_by("-id"):
            faq_list.append({
                "id": faq.id,
                "faq_id": faq.faq_id,
                "question": faq.question,
                "answer": faq.answer,
                "target_audience": faq.target_audience,
                "target_audience_display": faq.get_target_audience_display(),
                "created_at": faq.created_at.isoformat(),
                "updated_at": faq.updated_at.isoformat(),
            })

        return JsonResponse({"faqs": faq_list}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
