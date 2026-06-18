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

    def test_admin_approve_creator_view(self):
        admin_user = User.objects.create_superuser(username="admin_test", email="admin@test.com", password="password123")
        self.client.login(username="admin_test", password="password123")
        
        url = reverse("wagtail_approve_creator", args=[self.creator_profile.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        # Verify it redirects to the creator inspect view (or creator profile index fallback)
        self.assertIn("/admin/creatorprofile/", response.url)
        
        self.creator_profile.refresh_from_db()
        self.assertEqual(self.creator_profile.status, "approved")

    def test_admin_restrict_creator_view(self):
        admin_user = User.objects.create_superuser(username="admin_test2", email="admin2@test.com", password="password123")
        self.client.login(username="admin_test2", password="password123")
        
        url = reverse("wagtail_restrict_creator", args=[self.creator_profile.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("/admin/creatorprofile/", response.url)
        
        self.creator_profile.refresh_from_db()
        self.assertEqual(self.creator_profile.status, "restricted")

    def test_submit_creator_verification_unauthenticated(self):
        url = reverse("creator_submit_verification")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submit_creator_verification_non_creator(self):
        self.client.force_authenticate(user=self.business_user)
        url = reverse("creator_submit_verification")
        response = self.client.post(url, {
            "document_type": "nic",
            "document_front": SimpleUploadedFile("front.jpg", b"front image", content_type="image/jpeg"),
            "document_back": SimpleUploadedFile("back.jpg", b"back image", content_type="image/jpeg"),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Only creator accounts can submit verification documents.")

    def test_submit_creator_verification_missing_params(self):
        self.client.force_authenticate(user=self.creator_user)
        url = reverse("creator_submit_verification")
        
        # Missing type
        response1 = self.client.post(url, {
            "document_front": SimpleUploadedFile("front.jpg", b"front image", content_type="image/jpeg"),
            "document_back": SimpleUploadedFile("back.jpg", b"back image", content_type="image/jpeg"),
        })
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid type
        response2 = self.client.post(url, {
            "document_type": "invalid_type",
            "document_front": SimpleUploadedFile("front.jpg", b"front image", content_type="image/jpeg"),
            "document_back": SimpleUploadedFile("back.jpg", b"back image", content_type="image/jpeg"),
        })
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

        # Missing files
        response3 = self.client.post(url, {
            "document_type": "nic",
        })
        self.assertEqual(response3.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_creator_verification_success(self):
        self.client.force_authenticate(user=self.creator_user)
        url = reverse("creator_submit_verification")
        
        front_file = SimpleUploadedFile("front.jpg", b"front side data", content_type="image/jpeg")
        back_file = SimpleUploadedFile("back.jpg", b"back side data", content_type="image/jpeg")
        
        response = self.client.post(url, {
            "document_type": "passport",
            "document_front": front_file,
            "document_back": back_file,
            "other_details": "My passport is valid until 2030."
        }, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["verification_documents_submitted"])
        self.assertEqual(response.data["document_type"], "passport")
        self.assertIsNotNone(response.data["document_front"])
        self.assertIsNotNone(response.data["document_back"])
        self.assertEqual(response.data["other_details"], "My passport is valid until 2030.")

        # Check DB
        self.creator_profile.refresh_from_db()
        self.assertTrue(self.creator_profile.verification_documents_submitted)
        self.assertEqual(self.creator_profile.document_type, "passport")
        self.assertEqual(self.creator_profile.status, "pending")

        # Check compliance notification created
        from notifications.models import Notification
        self.assertTrue(Notification.objects.filter(
            title="Creator Verification Submitted",
            category="compliance"
        ).exists())

    def test_submit_creator_verification_already_approved(self):
        self.creator_profile.status = "approved"
        self.creator_profile.save()

        self.client.force_authenticate(user=self.creator_user)
        url = reverse("creator_submit_verification")
        response = self.client.post(url, {
            "document_type": "nic",
            "document_front": SimpleUploadedFile("front.jpg", b"front data", content_type="image/jpeg"),
            "document_back": SimpleUploadedFile("back.jpg", b"back data", content_type="image/jpeg"),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Creator profile is already verified and approved.")



