from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from user.models import CreatorProfile, BusinessProfile
from django.core.files.uploadedfile import SimpleUploadedFile

class BusinessVerificationAPITests(APITestCase):
    def setUp(self):
        # Creator user
        self.creator_user = User.objects.create_user(
            username="creator_test",
            email="creator@test.com",
            password="password123"
        )
        self.creator_profile, _ = CreatorProfile.objects.get_or_create(user=self.creator_user)

        # Business user (pending/new)
        self.business_user = User.objects.create_user(
            username="business_test",
            email="business@test.com",
            password="password123"
        )
        self.business_profile, _ = BusinessProfile.objects.get_or_create(user=self.business_user)

    def test_submit_verification_unauthenticated(self):
        url = reverse("submit_verification")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_verification_non_business(self):
        self.client.force_authenticate(user=self.creator_user)
        url = reverse("submit_verification")
        response = self.client.post(url, {
            "business_reg_number": "12345",
            "business_document": SimpleUploadedFile("doc.pdf", b"pdf content", content_type="application/pdf")
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Only business accounts can submit verification documents.")

    def test_submit_verification_missing_params(self):
        self.client.force_authenticate(user=self.business_user)
        url = reverse("submit_verification")
        
        # Missing file
        response1 = self.client.post(url, {"business_reg_number": "12345"})
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)

        # Missing reg number
        response2 = self.client.post(url, {
            "business_document": SimpleUploadedFile("doc.pdf", b"pdf content", content_type="application/pdf")
        })
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_verification_success(self):
        self.client.force_authenticate(user=self.business_user)
        url = reverse("submit_verification")
        doc_file = SimpleUploadedFile("reg_cert.pdf", b"certificate data", content_type="application/pdf")
        
        response = self.client.post(url, {
            "business_reg_number": "REG-9988-AA",
            "business_document": doc_file
        }, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["verification_documents_submitted"])
        self.assertEqual(response.data["business_reg_number"], "REG-9988-AA")
        self.assertIsNotNone(response.data["business_document"])

        # Check DB
        self.business_profile.refresh_from_db()
        self.assertTrue(self.business_profile.verification_documents_submitted)
        self.assertEqual(self.business_profile.business_reg_number, "REG-9988-AA")
        self.assertEqual(self.business_profile.status, "pending") # Status must remain pending until approved

        # Check Notification was created
        from notifications.models import Notification
        self.assertTrue(Notification.objects.filter(
            title="Business Verification Submitted",
            category="compliance"
        ).exists())


    def test_submit_verification_already_approved(self):
        # Set status to approved
        self.business_profile.status = "approved"
        self.business_profile.save()

        self.client.force_authenticate(user=self.business_user)
        url = reverse("submit_verification")
        response = self.client.post(url, {
            "business_reg_number": "12345",
            "business_document": SimpleUploadedFile("doc.pdf", b"pdf content", content_type="application/pdf")
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Business profile is already verified and approved.")

    def test_campaign_creation_restricted_for_pending_business(self):
        self.client.force_authenticate(user=self.business_user)
        url = reverse("campaign-list")
        payload = {
            "name": "Summer Launch Campaign",
            "brand": self.business_user.id,
            "budget": "5000.00",
            "status": "Pending",
            "brief": "A campaign for testing."
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"], 
            "You must submit verification documents and be approved by the admin to create campaigns."
        )

    def test_campaign_creation_allowed_for_approved_business(self):
        # Approve business
        self.business_profile.status = "approved"
        self.business_profile.save()

        self.client.force_authenticate(user=self.business_user)
        url = reverse("campaign-list")
        payload = {
            "name": "Summer Launch Campaign",
            "brand": self.business_user.id,
            "budget": "5000.00",
            "status": "Pending",
            "brief": "A campaign for testing."
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Summer Launch Campaign")

