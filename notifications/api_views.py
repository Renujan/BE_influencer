from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timesince import timesince
from django.utils import timezone
from .models import Notification
import json

@csrf_exempt
def get_notifications(request):
    if request.method == "GET":
        qs = Notification.objects.all().order_by('-created_at')[:30]
        data = []
        for n in qs:
            # Map to suitable creator frontend routes instead of backend admin URLs
            is_business = False
            req_user = request.user
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Token "):
                try:
                    from rest_framework.authtoken.models import Token
                    token_key = auth_header.split(" ")[1]
                    req_user = Token.objects.get(key=token_key).user
                except:
                    pass

            if hasattr(req_user, "is_authenticated") and req_user.is_authenticated:
                is_business = hasattr(req_user, "business_profile") or (hasattr(req_user, "profile") and req_user.profile.role == "business")

            if is_business:
                front_url = "/dashboard"
                if n.category == "campaign":
                    front_url = "/dashboard/campaigns"
                elif n.category == "payment":
                    front_url = "/dashboard/payments"
                elif n.category == "compliance":
                    front_url = "/dashboard/support"
                elif n.category == "signup":
                    front_url = "/dashboard/settings"
                
                # specific override for requests
                if "request" in n.title.lower() or "request" in n.message.lower():
                    front_url = "/dashboard/requests"
            else:
                front_url = "/creator"
                if n.category == "campaign":
                    front_url = "/creator/campaigns"
                elif n.category == "payment":
                    front_url = "/creator/earnings"
                elif n.category == "compliance":
                    front_url = "/creator/support"
                elif n.category == "signup":
                    front_url = "/creator/profile"

            data.append({
                "id": n.id,
                "title": n.title,
                "body": n.message,
                "time": f"{timesince(n.created_at, timezone.now()).split(',')[0]} ago",
                "read": n.is_read,
                "category": n.category,
                "icon": n.icon,
                "expandDetail": n.message,
                "actionLabel": "View Details",
                "targetUrl": front_url
            })
        return JsonResponse({"notifications": data})
    return JsonResponse({"status": "error"}, status=400)

@csrf_exempt
def mark_read(request, pk):
    if request.method == "POST":
        Notification.objects.filter(pk=pk).update(is_read=True)
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

@csrf_exempt
def mark_all_read_api(request):
    if request.method == "POST":
        Notification.objects.filter(is_read=False).update(is_read=True)
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)
