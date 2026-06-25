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
