from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from notifications.models import Notification

@csrf_exempt
def mark_all_read(request):
    """
    AJAX endpoint to mark all notifications as read or clear them.
    This dynamically updates backend state so the unread count becomes 0.
    """
    if request.method == "POST":
        Notification.objects.filter(is_read=False).update(is_read=True)
        return JsonResponse({"status": "success", "message": "All notifications marked as read."})
    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)

@login_required
def read_and_redirect(request, pk):
    """
    Mark a single notification as read and redirect to its target URL.
    """
    notification = get_object_or_404(Notification, pk=pk)
    notification.is_read = True
    notification.save()
    
    if notification.target_url:
        return redirect(notification.target_url)
    return redirect("/admin/")

