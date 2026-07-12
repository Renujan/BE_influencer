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
