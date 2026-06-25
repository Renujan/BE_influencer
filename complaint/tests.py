from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from complaint.models import Complaint, SupportMessage
from notifications.models import Notification
import json

class ComplaintAppTests(TestCase):
    def setUp(self):
        # Set up test client
        self.client = Client()
        
        # Create a test user
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.token = Token.objects.create(user=self.user)
        
    def test_create_complaint_successful(self):
        """
        Verify that a client can successfully raise a support ticket with a valid token.
        """
        payload = {
            "subject": "Late Escrow Release",
            "description": "The brand has approved the reel, but payment remains locked.",
            "category": "payment"
        }
        
        # Fire POST request using Token Auth header
        response = self.client.post(
            "/api/complaints/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["message"], "Complaint raised successfully")
        
        # Verify database record
        complaint = Complaint.objects.get(id=data["complaint_id"])
        self.assertEqual(complaint.subject, "Late Escrow Release")
        self.assertEqual(complaint.category, "payment")
        self.assertEqual(complaint.user, self.user)
        
    def test_create_complaint_signal_trigger(self):
        """
        Verify that creating a Complaint automatically registers a dashboard Notification log.
        """
        payload = {
            "subject": "Disrespectful conduct",
            "description": "Creator is using offensive terms in the workspace chat.",
            "category": "conduct"
        }
        
        response = self.client.post(
            "/api/complaints/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(response.status_code, 201)
        
        # Confirm notification is generated
        notification = Notification.objects.filter(category="compliance").latest("id")
        self.assertIn("Ticket #", notification.message)
        self.assertIn("Disrespectful conduct", notification.message)
        self.assertEqual(notification.title, "New Support Ticket")
        self.assertEqual(notification.icon, "fas fa-exclamation-circle")

    def test_list_complaints(self):
        """
        Verify that a client can retrieve all support tickets they raised.
        """
        # Create some mock complaints
        Complaint.objects.create(user=self.user, subject="Bug 1", description="Details 1", category="technical")
        Complaint.objects.create(user=self.user, subject="Bug 2", description="Details 2", category="technical")
        
        response = self.client.get(
            "/api/complaints/list/",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["complaints"]), 2)
        self.assertEqual(data["complaints"][0]["subject"], "Bug 2")
        self.assertEqual(data["complaints"][1]["subject"], "Bug 1")

    def test_list_chat_messages_empty(self):
        """
        Verify that listing chat messages is empty initially.
        """
        response = self.client.get(
            "/api/complaints/chat/list/",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["messages"], [])

    def test_send_chat_message_success(self):
        """
        Verify user can send message and receives automatic simulated admin response.
        """
        payload = {
            "message": "I have a payment dispute."
        }
        response = self.client.post(
            "/api/complaints/chat/send/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("user_message", data)
        self.assertIn("admin_message", data)
        self.assertEqual(data["user_message"]["message"], "I have a payment dispute.")
        self.assertIn("escrow", data["admin_message"]["message"].lower() or "payment" in data["admin_message"]["message"].lower())

        # Verify DB entries
        messages = SupportMessage.objects.filter(user=self.user).order_by("created_at")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].sender_role, "user")
        self.assertEqual(messages[0].message, "I have a payment dispute.")
        self.assertEqual(messages[1].sender_role, "admin")

    def test_list_chat_messages_populated(self):
        """
        Verify list API returns existing chat history in order.
        """
        SupportMessage.objects.create(user=self.user, sender_role="user", message="Hello admin")
        SupportMessage.objects.create(user=self.user, sender_role="admin", message="Hi user")

        response = self.client.get(
            "/api/complaints/chat/list/",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["messages"]), 2)
        self.assertEqual(data["messages"][0]["message"], "Hello admin")
        self.assertEqual(data["messages"][1]["message"], "Hi user")

    def test_send_chat_message_missing_field(self):
        """
        Verify API returns error when message is empty or missing.
        """
        payload = {}
        response = self.client.post(
            "/api/complaints/chat/send/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_chat_unauthorized(self):
        """
        Verify that unauthorized requests fail.
        """
        response_list = self.client.get("/api/complaints/chat/list/")
        self.assertEqual(response_list.status_code, 401)

        response_send = self.client.post(
            "/api/complaints/chat/send/",
            data=json.dumps({"message": "test"}),
            content_type="application/json"
        )
        self.assertEqual(response_send.status_code, 401)

    def test_wagtail_admin_update_complaint_status_and_reply(self):
        """
        Verify that a staff/admin user can update complaint status and admin reply
        via a POST request to the custom inspect/review page.
        """
        # Create an admin user and log them in
        admin_user = User.objects.create_superuser(username="adminuser", password="adminpassword123", email="admin@example.com")
        self.client.login(username="adminuser", password="adminpassword123")

        # Create a test ticket/complaint
        complaint = Complaint.objects.create(
            user=self.user,
            subject="Campaign payment locked",
            description="The money is stuck.",
            category="payment",
            status="pending",
            admin_reply=""
        )

        from django.urls import reverse
        inspect_url = reverse("complaint_admin:inspect", args=[complaint.pk])

        # Submit the status update form
        payload = {
            "status": "investigating",
            "admin_reply": "We are looking into this escrow issue."
        }
        response = self.client.post(inspect_url, data=payload)

        # Assert status code is a redirect (back to the same page)
        self.assertEqual(response.status_code, 302)

        # Verify database is updated
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "investigating")
        self.assertEqual(complaint.admin_reply, "We are looking into this escrow issue.")

    def test_wagtail_admin_support_chat_reply_and_grouping(self):
        """
        Verify that support messages are grouped by user (latest shown),
        and that posting to a chat inspect view creates an admin message successfully.
        """
        # Create another user for multiple threads testing
        user2 = User.objects.create_user(username="user2", password="password123")

        # Create multiple messages for original user
        SupportMessage.objects.create(user=self.user, sender_role="user", message="Msg 1")
        SupportMessage.objects.create(user=self.user, sender_role="admin", message="Msg 2")
        latest_user1 = SupportMessage.objects.create(user=self.user, sender_role="user", message="Latest Msg User 1")

        # Create messages for user2
        SupportMessage.objects.create(user=user2, sender_role="user", message="Msg 3")
        latest_user2 = SupportMessage.objects.create(user=user2, sender_role="user", message="Latest Msg User 2")

        # Create admin and log them in
        admin_user = User.objects.create_superuser(username="adminuser", password="adminpassword123", email="admin@example.com")
        self.client.login(username="adminuser", password="adminpassword123")

        # Test grouping in index view
        from django.urls import reverse
        index_url = reverse("support_message_admin:index")
        response = self.client.get(index_url)
        self.assertEqual(response.status_code, 200)

        # Verify the grouped queryset logic
        from django.db.models import Max
        latest_ids = SupportMessage.objects.values("user").annotate(latest_id=Max("id")).values_list("latest_id", flat=True)
        grouped_messages = SupportMessage.objects.filter(id__in=latest_ids).order_by("-created_at")
        self.assertEqual(len(grouped_messages), 2)
        self.assertEqual(grouped_messages[0].message, "Latest Msg User 2")
        self.assertEqual(grouped_messages[1].message, "Latest Msg User 1")

        # Test posting a reply via custom Inspect view
        inspect_url = reverse("support_message_admin:inspect", args=[latest_user1.pk])
        
        # Verify inspect view returns full chat logs for the specific user
        response_inspect = self.client.get(inspect_url)
        self.assertEqual(response_inspect.status_code, 200)
        self.assertIn("Msg 1", response_inspect.content.decode())
        self.assertIn("Msg 2", response_inspect.content.decode())
        self.assertIn("Latest Msg User 1", response_inspect.content.decode())
        self.assertNotIn("Latest Msg User 2", response_inspect.content.decode())

        # Admin replies to user1
        payload = {
            "message": "Admin reply message to User 1"
        }
        response_post = self.client.post(inspect_url, data=payload)
        self.assertEqual(response_post.status_code, 302)

        # Verify message created in database
        latest_msg = SupportMessage.objects.filter(user=self.user).latest("id")
        self.assertEqual(latest_msg.sender_role, "admin")
        self.assertEqual(latest_msg.message, "Admin reply message to User 1")

    def test_wagtail_admin_support_chat_premium_actions(self):
        """
        Verify that support chat management actions (edit message, delete message,
        delete chat, file upload) operate successfully via the inspect view.
        """
        # Create persistent thread target message
        main_msg = SupportMessage.objects.create(user=self.user, sender_role="user", message="Thread target message")
        # Create message to edit
        msg_to_edit = SupportMessage.objects.create(user=self.user, sender_role="user", message="Original Text")
        # Create message to delete
        msg_to_delete = SupportMessage.objects.create(user=self.user, sender_role="user", message="To be deleted")
        
        # Log in admin
        admin_user = User.objects.create_superuser(username="adminuser2", password="adminpassword123", email="admin2@example.com")
        self.client.login(username="adminuser2", password="adminpassword123")

        from django.urls import reverse
        inspect_url = reverse("support_message_admin:inspect", args=[main_msg.pk])

        # 1. Test edit message
        edit_payload = {
            "action": "edit_msg",
            "message_id": msg_to_edit.id,
            "message": "Edited Message Text"
        }
        res_edit = self.client.post(inspect_url, data=edit_payload)
        self.assertEqual(res_edit.status_code, 302)
        msg_to_edit.refresh_from_db()
        self.assertEqual(msg_to_edit.message, "Edited Message Text")

        # 2. Test delete message
        delete_payload = {
            "action": "delete_msg",
            "message_id": msg_to_delete.id
        }
        res_delete = self.client.post(inspect_url, data=delete_payload)
        self.assertEqual(res_delete.status_code, 302)
        self.assertFalse(SupportMessage.objects.filter(id=msg_to_delete.id).exists())

        # 3. Test sending message with file upload
        from django.core.files.uploadedfile import SimpleUploadedFile
        file_data = SimpleUploadedFile("test_document.txt", b"Support file content.", content_type="text/plain")
        upload_payload = {
            "action": "send_msg",
            "message": "Uploading document",
            "attachment": file_data
        }
        res_upload = self.client.post(inspect_url, data=upload_payload)
        self.assertEqual(res_upload.status_code, 302)
        
        uploaded_msg = SupportMessage.objects.filter(user=self.user).latest("id")
        self.assertEqual(uploaded_msg.message, "Uploading document")
        self.assertTrue(uploaded_msg.attachment.name.endswith(".txt"))
        self.assertFalse(uploaded_msg.is_voice)

        # 4. Test deleting the whole conversation thread
        clear_payload = {
            "action": "delete_chat"
        }
        res_clear = self.client.post(inspect_url, data=clear_payload)
        self.assertEqual(res_clear.status_code, 302)
        self.assertEqual(SupportMessage.objects.filter(user=self.user).count(), 0)

    def test_support_message_thread_sender_role(self):
        """
        Verify get_thread_sender_role identifies creator/business/admin roles correctly.
        """
        # Create a creator user
        creator_user = User.objects.create_user(username="creator_user", password="password123")
        from user.models import CreatorProfile
        CreatorProfile.objects.create(user=creator_user)
        
        # Create a business user
        business_user = User.objects.create_user(username="business_user", password="password123")
        from user.models import BusinessProfile
        BusinessProfile.objects.create(user=business_user)

        # Message initiated by creator
        msg_c = SupportMessage.objects.create(user=creator_user, sender_role="user", message="Creator message")
        self.assertEqual(msg_c.get_thread_sender_role(), "Creator")

        # Message initiated by business
        msg_b = SupportMessage.objects.create(user=business_user, sender_role="user", message="Business message")
        self.assertEqual(msg_b.get_thread_sender_role(), "Business")

        # Message initiated by admin (fallback test)
        admin_only_user = User.objects.create_user(username="admin_only", password="password123")
        msg_admin = SupportMessage.objects.create(user=admin_only_user, sender_role="admin", message="Admin message")
        self.assertEqual(msg_admin.get_thread_sender_role(), "Admin")

    def test_user_facing_chat_api_actions(self):
        """
        Verify user-facing chat API endpoints (delete, edit, clear, and attachment upload).
        """
        # Create some initial messages
        msg1 = SupportMessage.objects.create(user=self.user, sender_role="user", message="Message 1")
        msg2 = SupportMessage.objects.create(user=self.user, sender_role="admin", message="Message 2")

        # 1. Test listing chat messages includes attachment & is_voice info
        response = self.client.get(
            "/api/complaints/chat/list/",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["messages"]), 2)
        self.assertEqual(data["messages"][0]["message"], "Message 1")
        self.assertIn("attachment", data["messages"][0])
        self.assertIn("is_voice", data["messages"][0])

        # 2. Test sending message with file upload
        from django.core.files.uploadedfile import SimpleUploadedFile
        file_data = SimpleUploadedFile("chat_doc.txt", b"API chat attachment.", content_type="text/plain")
        payload = {
            "message": "Sent via API with file",
            "attachment": file_data
        }
        res_send = self.client.post(
            "/api/complaints/chat/send/",
            data=payload,
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(res_send.status_code, 201)
        send_data = res_send.json()
        self.assertEqual(send_data["user_message"]["message"], "Sent via API with file")
        self.assertIsNotNone(send_data["user_message"]["attachment"])

        # 3. Test editing user's own message
        edit_payload = {
            "message_id": msg1.id,
            "message": "Message 1 Updated"
        }
        res_edit = self.client.post(
            "/api/complaints/chat/edit/",
            data=json.dumps(edit_payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(res_edit.status_code, 200)
        msg1.refresh_from_db()
        self.assertEqual(msg1.message, "Message 1 Updated")

        # Verify editing admin message fails
        res_edit_admin = self.client.post(
            "/api/complaints/chat/edit/",
            data=json.dumps({"message_id": msg2.id, "message": "Trying to edit admin message"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(res_edit_admin.status_code, 404)

        # 4. Test deleting a single message
        delete_payload = {
            "message_id": msg1.id
        }
        res_delete = self.client.post(
            "/api/complaints/chat/delete/",
            data=json.dumps(delete_payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(res_delete.status_code, 200)
        self.assertFalse(SupportMessage.objects.filter(id=msg1.id).exists())

        # 5. Test clearing the entire chat
        res_clear = self.client.post(
            "/api/complaints/chat/clear/",
            HTTP_AUTHORIZATION=f"Token {self.token.key}"
        )
        self.assertEqual(res_clear.status_code, 200)
        self.assertEqual(SupportMessage.objects.filter(user=self.user).count(), 0)
