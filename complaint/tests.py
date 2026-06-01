from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from complaint.models import Complaint
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
