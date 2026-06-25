import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from campegin.models import Campaign
from complaint.models import Complaint, SupportMessage

def get_user_from_request(request):
    """
    Helper function to authenticate a user based on Authorization header or POST token parameters.
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
            
    # 3. Request session user fallback (for developers logged in to browser/Wagtail admin)
    if request.user.is_authenticated:
        return request.user
        
    return None

@csrf_exempt
def api_create_complaint(request):
    """
    Function-based view to handle raising a new support/dispute ticket from the front end.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Invalid or missing authentication token"}, status=401)

    try:
        data = {}
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        subject = data.get("subject")
        description = data.get("description")
        category = data.get("category", "other")
        campaign_id = data.get("campaign_id")
        priority = data.get("priority", "Medium")

        if not subject or not description:
            return JsonResponse({"error": "Subject and description fields are required"}, status=400)

        campaign = None
        if campaign_id:
            try:
                campaign = Campaign.objects.get(id=campaign_id)
            except Campaign.DoesNotExist:
                return JsonResponse({"error": f"Campaign with ID {campaign_id} does not exist"}, status=404)

        complaint = Complaint.objects.create(
            user=user,
            campaign=campaign,
            category=category,
            subject=subject,
            description=description,
            priority=priority,
            status="pending"
        )

        return JsonResponse({
            "message": "Complaint raised successfully",
            "complaint_id": complaint.id,
            "status": complaint.status,
            "category": complaint.category
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def api_list_complaints(request):
    """
    Function-based view to return all support/dispute tickets raised by the authenticated user.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are allowed"}, status=405)

    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Invalid or missing authentication token"}, status=401)

    try:
        complaints = Complaint.objects.filter(user=user).order_by("-id")
        result = []
        for c in complaints:
            result.append({
                "id": c.id,
                "category": c.category,
                "category_display": c.get_category_display(),
                "subject": c.subject,
                "description": c.description,
                "status": c.status,
                "status_display": c.get_status_display(),
                "admin_reply": c.admin_reply,
                "campaign_name": c.campaign.name if c.campaign else None,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            })
        return JsonResponse({"complaints": result}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def api_list_chat_messages(request):
    """
    GET view returning all support messages for the authenticated user.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are allowed"}, status=405)
    
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Invalid or missing token"}, status=401)
        
    try:
        messages = SupportMessage.objects.filter(user=user).order_by("created_at")
        data = [{
            "id": msg.id,
            "sender_role": msg.sender_role,
            "message": msg.message,
            "attachment": request.build_absolute_uri(msg.attachment.url) if msg.attachment else None,
            "is_voice": msg.is_voice,
            "created_at": msg.created_at.isoformat()
        } for msg in messages]
        return JsonResponse({"messages": data}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def api_send_chat_message(request):
    """
    POST view accepting user support chat messages and saving them,
    supporting file and voice uploads, and triggering simulated auto-replies.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)
        
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Invalid or missing token"}, status=401)
        
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST
            
        message_text = data.get("message", "").strip()
        attachment_file = request.FILES.get("attachment")
        is_voice_val = data.get("is_voice") == "true" or data.get("is_voice") is True
        
        if not message_text and not attachment_file:
            return JsonResponse({"error": "Message text or attachment is required"}, status=400)
            
        user_msg = SupportMessage.objects.create(
            user=user,
            sender_role="user",
            message=message_text,
            attachment=attachment_file,
            is_voice=is_voice_val
        )
        
        if message_text:
            msg_lower = message_text.lower()
            reply_text = "Thank you for contacting support! Our admin team has been notified and will review your inquiry shortly. Let us know if you need anything else."
            if "payment" in msg_lower or "escrow" in msg_lower or "money" in msg_lower:
                reply_text = "I see your inquiry is regarding payments or escrow. For security reasons, payouts are held in escrow until deliverables are approved. If you have a dispute, you can file a ticket and our compliance team will investigate within 24 hours."
            elif "campaign" in msg_lower or "hired" in msg_lower or "influencer" in msg_lower:
                reply_text = "Regarding campaigns or influencer contracts: you can review progress in your campaigns tab. If the creator is unresponsive, you can file a dispute ticket."
            elif "technical" in msg_lower or "bug" in msg_lower or "error" in msg_lower or "fail" in msg_lower:
                reply_text = "Sorry you are experiencing a technical issue. Could you please specify which page/action is failing, or submit a support ticket with description so our tech team can debug it?"
        else:
            reply_text = "Thank you for sending the file/voice note. We have received it and will look into it shortly!"
            
        admin_msg = SupportMessage.objects.create(
            user=user,
            sender_role="admin",
            message=reply_text
        )
        
        return JsonResponse({
            "user_message": {
                "id": user_msg.id,
                "sender_role": "user",
                "message": user_msg.message,
                "attachment": request.build_absolute_uri(user_msg.attachment.url) if user_msg.attachment else None,
                "is_voice": user_msg.is_voice,
                "created_at": user_msg.created_at.isoformat()
            },
            "admin_message": {
                "id": admin_msg.id,
                "sender_role": "admin",
                "message": admin_msg.message,
                "attachment": request.build_absolute_uri(admin_msg.attachment.url) if admin_msg.attachment else None,
                "is_voice": admin_msg.is_voice,
                "created_at": admin_msg.created_at.isoformat()
            }
        }, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def api_delete_chat_message(request):
    """
    POST view allowing a user to delete a single support chat message.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)
        
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Invalid or missing token"}, status=401)
        
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST
            
        message_id = data.get("message_id")
        if not message_id:
            return JsonResponse({"error": "message_id is required"}, status=400)
            
        deleted_count, _ = SupportMessage.objects.filter(id=message_id, user=user).delete()
        if deleted_count == 0:
            return JsonResponse({"error": "Message not found or not owned by you"}, status=404)
            
        return JsonResponse({"message": "Message deleted successfully"}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def api_edit_chat_message(request):
    """
    POST view allowing a user to edit their own support chat message.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)
        
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Invalid or missing token"}, status=401)
        
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST
            
        message_id = data.get("message_id")
        new_text = data.get("message", "").strip()
        
        if not message_id or not new_text:
            return JsonResponse({"error": "message_id and message are required"}, status=400)
            
        updated_count = SupportMessage.objects.filter(id=message_id, user=user, sender_role="user").update(message=new_text)
        if updated_count == 0:
            return JsonResponse({"error": "Message not found or cannot be edited by you"}, status=404)
            
        return JsonResponse({"message": "Message updated successfully"}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def api_clear_chat(request):
    """
    POST view allowing a user to clear their support chat history.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)
        
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({"error": "Invalid or missing token"}, status=401)
        
    try:
        SupportMessage.objects.filter(user=user).delete()
        return JsonResponse({"message": "Chat history cleared successfully"}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
