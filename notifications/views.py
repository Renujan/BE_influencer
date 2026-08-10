from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from notifications.models import Notification
from notifications.utils import resolve_admin_redirect_url

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
