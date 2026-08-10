from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timesince import timesince
from django.utils import timezone
from django.db.models import Q
from .models import Notification
import json

@csrf_exempt
def get_notifications(request):
    if request.method == "GET":
        req_user = request.user
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Token "):
            try:
                from rest_framework.authtoken.models import Token
                token_key = auth_header.split(" ")[1]
                req_user = Token.objects.get(key=token_key).user
            except:
                pass

        is_authenticated = hasattr(req_user, "is_authenticated") and req_user.is_authenticated
        is_admin = is_authenticated and (req_user.is_staff or req_user.is_superuser)
        is_business = is_authenticated and (hasattr(req_user, "business_profile") or (hasattr(req_user, "profile") and req_user.profile.role == "business"))
        is_creator = is_authenticated and not is_business and not is_admin

        if is_admin:
            qs = Notification.objects.all().order_by('-created_at')[:50]
        elif is_business or is_creator:
            qs = Notification.objects.filter(
                user=req_user
            ).exclude(target_role="admin").order_by('-created_at')[:50]
        else:
            qs = Notification.objects.none()

        data = []
        for n in qs:
            if n.target_url:
                front_url = n.target_url
            elif is_business or (not is_authenticated and True):
                front_url = "/dashboard"
                if n.category == "campaign":
                    front_url = "/dashboard/campaigns"
                elif n.category == "payment":
                    front_url = "/dashboard/payments"
                elif n.category == "compliance":
                    front_url = "/dashboard/support"
                elif n.category == "signup":
                    front_url = "/dashboard/settings"
                
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
            updated = Notification.objects.filter(pk=pk, user=req_user).update(is_read=True)
            if not updated and (req_user.is_staff or req_user.is_superuser):
                Notification.objects.filter(pk=pk).update(is_read=True)
        else:
            Notification.objects.filter(pk=pk).update(is_read=True)
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

@csrf_exempt
def mark_all_read_api(request):
    if request.method == "POST":
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
            if req_user.is_staff or req_user.is_superuser:
                Notification.objects.filter(is_read=False).update(is_read=True)
            else:
                Notification.objects.filter(user=req_user, is_read=False).update(is_read=True)
        else:
            Notification.objects.filter(is_read=False).update(is_read=True)
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)
