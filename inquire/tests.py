from django.test import TestCase
from django.urls import reverse
from inquire.models import Inquiry

class InquiryTests(TestCase):
    def setUp(self):
        self.submit_url = reverse("inquire:submit_inquiry")

    def test_submit_valid_inquiry_brand(self):
        payload = {
            "name": "Sarah Jenkins",
            "email": "sarah@company.com",
            "phone": "+1 (555) 019-2834",
            "role": "brand",
            "subject": "Enterprise Pricing Inquiry",
            "message": "We would like to setup a workspace for our marketing team."
        }
        response = self.client.post(self.submit_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("inquiry_id", response.json())
        self.assertEqual(response.json()["role"], "brand")
        self.assertTrue(response.json()["inquiry_id"].endswith("-BR"))
        self.assertEqual(Inquiry.objects.count(), 1)

    def test_submit_valid_inquiry_creator(self):
        payload = {
            "name": "Alex Logan",
            "email": "alex@youtube.com",
            "phone": "+1 (555) 381-1928",
            "role": "creator",
            "subject": "Creator Verification",
            "message": "Hi, I am an influencer interested in signing up."
        }
        response = self.client.post(self.submit_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["inquiry_id"].endswith("-CR"))
        self.assertEqual(Inquiry.objects.count(), 1)

    def test_submit_invalid_email(self):
        payload = {
            "name": "Sarah Jenkins",
            "email": "invalid-email",
            "phone": "+1 (555) 019-2834",
            "role": "brand",
            "subject": "Enterprise Pricing Inquiry",
            "message": "Hello!"
        }
        response = self.client.post(self.submit_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_submit_missing_fields(self):
        payload = {
            "name": "Sarah Jenkins",
            "email": "sarah@company.com"
        }
        response = self.client.post(self.submit_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.json())
        self.assertIn("subject", response.json())
        self.assertIn("message", response.json())

    def test_inquiry_id_incrementation(self):
        # Create first inquiry
        i1 = Inquiry.objects.create(
            name="John Doe",
            email="john@example.com",
            phone="12345",
            role="brand",
            subject="Test 1",
            message="Msg 1"
        )
        self.assertEqual(i1.inquiry_id, "INQ001-BR")

        # Create second inquiry with different role
        i2 = Inquiry.objects.create(
            name="Jane Doe",
            email="jane@example.com",
            phone="67890",
            role="creator",
            subject="Test 2",
            message="Msg 2"
        )
        self.assertEqual(i2.inquiry_id, "INQ002-CR")

