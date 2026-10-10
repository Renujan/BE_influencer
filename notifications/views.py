import json
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from notifications.models import Notification
from notifications.utils import resolve_admin_redirect_url


# ==========================================
# Category Metadata Configuration
# ==========================================
CATEGORY_METADATA = {
    "payment": {
        "label": "Billing & Escrow",
        "type_group": "Billing",
        "badge_class": "badge-billing",
        "accent_color": "#10b981",
        "bg_color": "#ecfdf5",
        "text_color": "#047857",
        "border_color": "#a7f3d0",
        "icon": "fas fa-credit-card",
        "emoji": "💳",
    },
    "compliance": {
        "label": "Security & Compliance",
        "type_group": "Security",
        "badge_class": "badge-security",
        "accent_color": "#f43f5e",
        "bg_color": "#fff1f2",
        "text_color": "#be123c",
        "border_color": "#fecdd3",
        "icon": "fas fa-shield-alt",
        "emoji": "🛡️",
    },
    "signup": {
        "label": "User Alert",
        "type_group": "User Alert",
        "badge_class": "badge-user",
        "accent_color": "#f97316",
        "bg_color": "#fff7ed",
        "text_color": "#c2410c",
        "border_color": "#fed7aa",
        "icon": "fas fa-user-shield",
        "emoji": "👤",
    },
    "campaign": {
        "label": "System & Campaign",
        "type_group": "System",
        "badge_class": "badge-system",
        "accent_color": "#3b82f6",
        "bg_color": "#eff6ff",
        "text_color": "#1d4ed8",
        "border_color": "#bfdbfe",
        "icon": "fas fa-bullhorn",
        "emoji": "📢",
    },
}

DEFAULT_METADATA = {
    "label": "System Notice",
    "type_group": "System",
    "badge_class": "badge-default",
    "accent_color": "#6366f1",
    "bg_color": "#f5f3ff",
    "text_color": "#4f46e5",
    "border_color": "#ddd6fe",
    "icon": "fas fa-bell",
    "emoji": "🔔",
}


def get_notification_metadata(category):
    return CATEGORY_METADATA.get(category, DEFAULT_METADATA)


# ==========================================
# Dedicated Super Admin Notifications View
# ==========================================

@user_passes_test(lambda u: u.is_staff and u.is_active)
def admin_notifications_view(request):
    """
    Dedicated Super Admin view for platform notifications.
    Supports status tabs ('All', 'Unread', 'Read'), category filtering,
    search, pagination, manual deletion, and toggling read/unread state.
    """
    status_filter = request.GET.get("status", "all").strip().lower()
    category_filter = request.GET.get("category", "all").strip().lower()
    search_query = request.GET.get("q", "").strip()
    page_number = request.GET.get("page", 1)

    # Base queryset - latest notifications first
    qs = Notification.objects.select_related("user").order_by("-created_at")

    # Global Counter aggregates for header & tabs
    total_count = Notification.objects.count()
    unread_count = Notification.objects.filter(is_read=False).count()
    read_count = Notification.objects.filter(is_read=True).count()

    # Category counts
    billing_count = Notification.objects.filter(category="payment").count()
    security_count = Notification.objects.filter(category="compliance").count()
    user_alert_count = Notification.objects.filter(category="signup").count()
    system_count = Notification.objects.filter(category="campaign").count()

    # Apply Status Filter
    if status_filter == "unread":
        qs = qs.filter(is_read=False)
    elif status_filter == "read":
        qs = qs.filter(is_read=True)

    # Apply Category Filter
    if category_filter and category_filter != "all":
        qs = qs.filter(category=category_filter)

    # Apply Search Filter
    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(target_role__icontains=search_query)
        )

    # Paginate results (20 items per page)
    paginator = Paginator(qs, 20)
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    # Attach category presentation metadata to each item on the page
    for notif in page_obj.object_list:
        notif.meta = get_notification_metadata(notif.category)

    category_options = [
        {"key": "all", "label": "All Types", "count": total_count, "icon": "fas fa-layer-group"},
        {"key": "payment", "label": "Billing & Escrow", "count": billing_count, "icon": "fas fa-credit-card"},
        {"key": "compliance", "label": "Security & Disputes", "count": security_count, "icon": "fas fa-shield-alt"},
        {"key": "signup", "label": "User Alerts", "count": user_alert_count, "icon": "fas fa-user-shield"},
        {"key": "campaign", "label": "System & Campaigns", "count": system_count, "icon": "fas fa-bullhorn"},
    ]

    context = {
        "page_obj": page_obj,
        "notifications": page_obj.object_list,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "search_query": search_query,
        "total_count": total_count,
        "unread_count": unread_count,
        "read_count": read_count,
        "billing_count": billing_count,
        "security_count": security_count,
        "user_alert_count": user_alert_count,
        "system_count": system_count,
        "category_options": category_options,
    }
    return render(request, "notifications/admin_notifications.html", context)


# ==========================================
# Quick Actions: Toggle Read / Unread
# ==========================================

@user_passes_test(lambda u: u.is_staff and u.is_active)
def toggle_read_notification(request, pk):
    """
    Toggle a notification's read/unread state.
    Supports both AJAX requests and standard POST redirects.
    """
    notification = get_object_or_404(Notification, pk=pk)
    notification.is_read = not notification.is_read
    notification.save(update_fields=["is_read"])

    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.POST.get("ajax") == "true"
        or request.GET.get("ajax") == "true"
    )

    if is_ajax:
        return JsonResponse({
            "status": "success",
            "id": notification.id,
            "is_read": notification.is_read,
            "total_count": Notification.objects.count(),
            "unread_count": Notification.objects.filter(is_read=False).count(),
            "read_count": Notification.objects.filter(is_read=True).count(),
            "message": f"Notification marked as {'read' if notification.is_read else 'unread'}."
        })

    status_str = "read" if notification.is_read else "unread"
    messages.success(request, f"Notification marked as {status_str}.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("notifications:admin_notifications_list"))


# ==========================================
# Quick Actions: Explicit Manual Deletion Only
# ==========================================

@user_passes_test(lambda u: u.is_staff and u.is_active)
def delete_notification(request, pk):
    """
    Explicit manual deletion of a single notification.
    CRITICAL: Only performed on explicit user request. No auto-purging or cron.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST method required for deletion."}, status=405)

    notification = get_object_or_404(Notification, pk=pk)
    title = notification.title
    notification.delete()

    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.POST.get("ajax") == "true"
    )

    if is_ajax:
        return JsonResponse({
            "status": "success",
            "deleted_id": pk,
            "total_count": Notification.objects.count(),
            "unread_count": Notification.objects.filter(is_read=False).count(),
            "read_count": Notification.objects.filter(is_read=True).count(),
            "message": f"Notification '{title}' permanently deleted."
        })

    messages.success(request, f"Notification '{title}' deleted.")
    return redirect(request.META.get("HTTP_REFERER") or reverse("notifications:admin_notifications_list"))


# ==========================================
# Bulk Actions (Mark Read / Mark Unread / Delete)
# ==========================================

@user_passes_test(lambda u: u.is_staff and u.is_active)
def bulk_action_notification(request):
    """
    Perform bulk operations on selected notifications.
    Supported actions: 'mark_read', 'mark_unread', 'delete', 'mark_all_read'.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST method required."}, status=405)

    action = request.POST.get("action")
    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.POST.get("ajax") == "true"
    )

    if action == "mark_all_read":
        updated = Notification.objects.filter(is_read=False).update(is_read=True)
        msg = f"All {updated} unread notifications marked as read."
        if is_ajax:
            return JsonResponse({
                "status": "success",
                "action": action,
                "count": updated,
                "total_count": Notification.objects.count(),
                "unread_count": 0,
                "read_count": Notification.objects.count(),
                "message": msg
            })
        messages.success(request, msg)
        return redirect(request.META.get("HTTP_REFERER") or reverse("notifications:admin_notifications_list"))

    raw_ids = request.POST.getlist("selected_ids")
    selected_ids = []
    for item in raw_ids:
        for part in str(item).split(","):
            part = part.strip()
            if part.isdigit():
                selected_ids.append(int(part))

    if not selected_ids:
        msg = "No notifications were selected."
        if is_ajax:
            return JsonResponse({"status": "error", "message": msg}, status=400)
        messages.warning(request, msg)
        return redirect(request.META.get("HTTP_REFERER") or reverse("notifications:admin_notifications_list"))

    target_qs = Notification.objects.filter(id__in=selected_ids)
    affected_count = target_qs.count()

    if action == "mark_read":
        target_qs.update(is_read=True)
        msg = f"{affected_count} notification(s) marked as read."
    elif action == "mark_unread":
        target_qs.update(is_read=False)
        msg = f"{affected_count} notification(s) marked as unread."
    elif action == "delete":
        # Explicit manual deletion of selected items
        target_qs.delete()
        msg = f"{affected_count} notification(s) permanently deleted."
    else:
        msg = f"Invalid bulk action '{action}'."
        if is_ajax:
            return JsonResponse({"status": "error", "message": msg}, status=400)
        messages.error(request, msg)
        return redirect(request.META.get("HTTP_REFERER") or reverse("notifications:admin_notifications_list"))

    if is_ajax:
        return JsonResponse({
            "status": "success",
            "action": action,
            "affected_count": affected_count,
            "total_count": Notification.objects.count(),
            "unread_count": Notification.objects.filter(is_read=False).count(),
            "read_count": Notification.objects.filter(is_read=True).count(),
            "message": msg
        })

    messages.success(request, msg)
    return redirect(request.META.get("HTTP_REFERER") or reverse("notifications:admin_notifications_list"))


# ==========================================
# Legacy / Existing Endpoints (Preserved Intact)
# ==========================================

@csrf_exempt
def mark_all_read(request):
    """
    AJAX endpoint to dismiss all notifications from the admin bell dropdown.
    Marks every unread notification as read so they stay hidden after refresh.
    """
    if request.method == "POST":
        Notification.objects.filter(is_read=False).update(is_read=True)
        return JsonResponse({"status": "success", "message": "All notifications cleared."})
    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)


@login_required
def read_and_redirect(request, pk):
    """
    Mark a single notification as read and redirect to its target URL.
    """
    notification = get_object_or_404(Notification, pk=pk)
    notification.is_read = True
    notification.save()

    redirect_url = resolve_admin_redirect_url(notification)
    return redirect(redirect_url)
