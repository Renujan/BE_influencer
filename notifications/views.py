from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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
