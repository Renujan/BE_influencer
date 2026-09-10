from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timesince import timesince
from django.utils import timezone
from django.db.models import Q
from .models import Notification
from .utils import format_notification_text_currency
from campegin.models import Campaign
import datetime
import json
import re

@csrf_exempt
def get_notifications(request):
    if request.method == "GET":
        req_user = getattr(request, "user", None)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Token "):
            try:
                from rest_framework.authtoken.models import Token
                token_key = auth_header.split(" ")[1]
                req_user = Token.objects.get(key=token_key).user
            except:
                pass

        # Automatically remove notifications older than 14 days
        cutoff_14d = timezone.now() - datetime.timedelta(days=14)
        try:
            Notification.objects.filter(created_at__lt=cutoff_14d).delete()
        except Exception:
            pass

        is_authenticated = hasattr(req_user, "is_authenticated") and req_user.is_authenticated
        is_admin = is_authenticated and (req_user.is_staff or req_user.is_superuser)
        is_business = is_authenticated and hasattr(req_user, "business_profile")
        is_creator = is_authenticated and hasattr(req_user, "creator_profile")

        role_param = request.GET.get("role", "").strip().lower()
        if role_param == "influencer":
            role_param = "creator"

        if role_param == "business" or (is_business and role_param != "admin" and role_param != "creator"):
            # Target notifications for Business account within 14 days
            qs = Notification.objects.filter(
                user=req_user,
                target_role__in=["business", "all"],
                created_at__gte=cutoff_14d
            ).exclude(target_role__in=["creator", "admin"]).order_by('-created_at')[:200]
            if is_admin and qs.count() == 0:
                qs = Notification.objects.filter(target_role="business", created_at__gte=cutoff_14d).order_by('-created_at')[:200]
            active_role = "business"
        elif role_param == "creator" or (is_creator and role_param != "admin"):
            # Target notifications for Creator account within 14 days
            qs = Notification.objects.filter(
                user=req_user,
                target_role__in=["creator", "all"],
                created_at__gte=cutoff_14d
            ).exclude(target_role__in=["business", "admin"]).order_by('-created_at')[:200]
            if is_admin and qs.count() == 0:
                qs = Notification.objects.filter(target_role="creator", created_at__gte=cutoff_14d).order_by('-created_at')[:200]
            active_role = "creator"
        elif is_admin:
            qs = Notification.objects.filter(created_at__gte=cutoff_14d).order_by('-created_at')[:200]
            active_role = "admin"
        else:
            qs = Notification.objects.none()
            active_role = "business" if is_business else "creator"

        data = []
        for n in qs:
            front_url = (n.target_url or "").strip()

            is_payment_action = (
                n.title in ["Installment Payment Action", "Payment Negotiation Update", "Escrow Payment Action"]
                or "installment" in n.title.lower()
                or "payment negotiation" in n.title.lower()
            )

            if is_payment_action:
                if front_url.startswith("/workspace/"):
                    if "tab=" not in front_url:
                        sep = "&" if "?" in front_url else "?"
                        front_url = f"{front_url}{sep}tab=Payments"
                elif front_url in ["/dashboard/payments", "/creator/earnings", "/dashboard", "/creator", ""]:
                    camp_id = None
                    m = re.search(r"(?:for campaign|for) '([^']+)'", n.message)
                    if m:
                        cname = m.group(1).strip()
                        c = Campaign.objects.filter(name__iexact=cname).first()
                        if not c:
                            c = Campaign.objects.filter(name__icontains=cname.split()[0]).first()
                        if c:
                            camp_id = c.id
                    if not camp_id and req_user:
                        if active_role == "business":
                            c = Campaign.objects.filter(brand=req_user).order_by('-created_at').first()
                        else:
                            c = Campaign.objects.filter(creator=req_user).order_by('-created_at').first()
                        if c:
                            camp_id = c.id

                    if camp_id:
                        front_url = f"/workspace/{camp_id}?tab=Payments"
                    else:
                        front_url = "/business-workspace?tab=Payments" if active_role == "business" else "/creator-workspace?tab=Payments"

            if active_role == "business":
                if front_url.startswith("/dashboard/business-services") or front_url.startswith("/creator/business-services"):
                    front_url = "/dashboard/services"
                elif front_url.startswith("/creator/pitches") or front_url.startswith("/dashboard/pitches"):
                    front_url = "/dashboard/requests"
                elif front_url.startswith("/creator/profile") or front_url.startswith("/dashboard/profile"):
                    front_url = "/dashboard/settings"
                elif front_url.startswith("/creator/payments"):
                    front_url = "/dashboard/payments"
                elif "/admin/snippets/campegin/campaign/inspect/" in front_url:
                    camp_match = re.search(r'/campaign/inspect/(\d+)', front_url)
                    front_url = f"/workspace/{camp_match.group(1)}" if camp_match else "/dashboard/campaigns"
                elif front_url.startswith("/admin/"):
                    if "complaint" in front_url or "support" in front_url or "ticket" in front_url:
                        front_url = "/dashboard/support"
                    elif "service" in front_url:
                        front_url = "/dashboard/services"
                    elif "businessprofile" in front_url or "setting" in front_url:
                        front_url = "/dashboard/settings"
                    elif "creatorprofile" in front_url:
                        front_url = "/dashboard/discover"
                    elif "campaign" in front_url:
                        front_url = "/dashboard/campaigns"
                    else:
                        front_url = "/dashboard"
                elif front_url.startswith("/creator/") and not is_payment_action:
                    if "campaign" in front_url:
                        front_url = "/dashboard/campaigns"
                    elif "earning" in front_url or "payment" in front_url:
                        front_url = "/dashboard/payments"
                    elif "request" in front_url or "pitch" in front_url:
                        front_url = "/dashboard/requests"
                    elif "service" in front_url:
                        front_url = "/dashboard/services"
                    elif "support" in front_url:
                        front_url = "/dashboard/support"
                    elif "setting" in front_url or "profile" in front_url:
                        front_url = "/dashboard/settings"
                    else:
                        front_url = "/dashboard"
                elif not front_url:
                    front_url = "/dashboard"
                    if n.category == "campaign":
                        front_url = "/dashboard/campaigns"
                    elif n.category == "payment":
                        front_url = "/dashboard/payments"
                    elif n.category == "compliance":
                        front_url = "/dashboard/support"
                    elif n.category == "signup":
                        front_url = "/dashboard/settings"

                    if "request" in n.title.lower() or "request" in n.message.lower() or "pitch" in n.title.lower():
                        front_url = "/dashboard/requests"
                    elif "service" in n.title.lower() or "service" in n.message.lower():
                        front_url = "/dashboard/services"
            else:
                if front_url.startswith("/creator/business-services") or front_url.startswith("/dashboard/business-services"):
                    front_url = "/creator/services"
                elif front_url.startswith("/creator/pitches") or front_url.startswith("/dashboard/pitches"):
                    front_url = "/creator/requests"
                elif front_url.startswith("/creator/profile") or front_url.startswith("/dashboard/profile"):
                    front_url = "/creator/portfolio"
                elif front_url.startswith("/creator/payments") or front_url.startswith("/dashboard/payments"):
                    front_url = "/creator/earnings"
                elif "/admin/snippets/campegin/campaign/inspect/" in front_url:
                    import re
                    camp_match = re.search(r'/campaign/inspect/(\d+)', front_url)
                    front_url = f"/workspace/{camp_match.group(1)}" if camp_match else "/creator/campaigns"
                elif front_url.startswith("/admin/"):
                    if "complaint" in front_url or "support" in front_url or "ticket" in front_url:
                        front_url = "/creator/support"
                    elif "service" in front_url:
                        front_url = "/creator/services"
                    elif "creatorprofile" in front_url or "setting" in front_url:
                        front_url = "/creator/portfolio"
                    elif "businessprofile" in front_url:
                        front_url = "/creator/brands"
                    elif "campaign" in front_url:
                        front_url = "/creator/campaigns"
                    else:
                        front_url = "/creator"
                elif front_url.startswith("/dashboard/"):
                    if "campaign" in front_url:
                        front_url = "/creator/campaigns"
                    elif "payment" in front_url or "earning" in front_url:
                        front_url = "/creator/earnings"
                    elif "request" in front_url or "pitch" in front_url:
                        front_url = "/creator/requests"
                    elif "service" in front_url:
                        front_url = "/creator/services"
                    elif "support" in front_url:
                        front_url = "/creator/support"
                    elif "setting" in front_url:
                        front_url = "/creator/settings"
                    elif "discover" in front_url:
                        front_url = "/creator/brands"
                    else:
                        front_url = "/creator"
                elif not front_url:
                    front_url = "/creator"
                    if n.category == "campaign":
                        front_url = "/creator/campaigns"
                    elif n.category == "payment":
                        front_url = "/creator/earnings"
                    elif n.category == "compliance":
                        front_url = "/creator/support"
                    elif n.category == "signup":
                        front_url = "/creator/portfolio"

                    if "request" in n.title.lower() or "request" in n.message.lower() or "pitch" in n.title.lower():
                        front_url = "/creator/requests"
                    elif "service" in n.title.lower() or "service" in n.message.lower():
                        front_url = "/creator/services"

            formatted_title = format_notification_text_currency(n.title, req_user)
            formatted_body = format_notification_text_currency(n.message, req_user)
            data.append({
                "id": n.id,
                "title": formatted_title,
                "body": formatted_body,
                "time": f"{timesince(n.created_at, timezone.now()).split(',')[0]} ago",
                "created_at": n.created_at.isoformat(),
                "read": n.is_read,
                "category": n.category,
                "icon": n.icon,
                "expandDetail": formatted_body,
                "actionLabel": "View Details",
                "targetUrl": front_url
            })
        return JsonResponse({"notifications": data})
    return JsonResponse({"status": "error"}, status=400)

@csrf_exempt
def mark_read(request, pk):
    if request.method == "POST":
        cutoff_14d = timezone.now() - datetime.timedelta(days=14)
        try:
            Notification.objects.filter(created_at__lt=cutoff_14d).delete()
        except Exception:
            pass

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
        cutoff_14d = timezone.now() - datetime.timedelta(days=14)
        try:
            Notification.objects.filter(created_at__lt=cutoff_14d).delete()
        except Exception:
            pass

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
