from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from business_service.models import BusinessService, ServiceCategory, BusinessServiceRequest
from notifications.models import Notification

class BusinessServiceInquiryAPITests(APITestCase):
    def setUp(self):
        # Create categories and services
        self.category, _ = ServiceCategory.objects.get_or_create(name="Marketing")
        self.service = BusinessService.objects.create(
            title="Premium Campaign Strategy",
            provider="Ampli Agency",
            rate="From $2,000 / campaign",
            speed="7 Days",
            category=self.category,
            description="Premium target audience marketing strategy.",
            bullet_points="Audience research\nCampaign roadmap\nConversion tracking",
            target_audience="both",
            is_active=True
        )

        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123"
        )
        # Auth token
        from rest_framework.authtoken.models import Token
        self.token = Token.objects.create(user=self.user)

    def test_inquire_unauthenticated(self):
        url = reverse("business_service:api_business_service_inquiries")
        response = self.client.post(url, {
            "service_id": self.service.id,
            "message": "I would like to inquire about campaign strategy.",
            "budget": "2500",
            "timeline": "Urgent"
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inquire_success(self):
        url = reverse("business_service:api_business_service_inquiries")
        
        # Authenticate using Token header helper or get_user_from_request's token param
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        
        response = self.client.post(url, {
            "service_id": self.service.id,
            "message": "I need standard marketing campaign strategy.",
            "budget": "2000",
            "timeline": "Standard"
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["message"], "Inquiry submitted successfully")
        
        # Verify database record
        inquiry = BusinessServiceRequest.objects.get(message="I need standard marketing campaign strategy.")
        self.assertEqual(inquiry.service, self.service)
        self.assertEqual(inquiry.user, self.user)
        self.assertEqual(inquiry.budget, "2000")
        self.assertEqual(inquiry.timeline, "Standard")
        self.assertEqual(inquiry.status, "pending")

        # Verify admin notification created
        self.assertTrue(Notification.objects.filter(
            title="New Service Inquiry",
            category="campaign"
        ).exists())

    def test_inquire_invalid_service(self):
        url = reverse("business_service:api_business_service_inquiries")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        
        response = self.client.post(url, {
            "service_id": 99999,
            "message": "Invalid service inquiry.",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_inquiries(self):
        # Create some inquiries first
        BusinessServiceRequest.objects.create(
            service=self.service,
            user=self.user,
            message="Inquiry 1",
            budget="1000",
            timeline="Standard"
        )
        BusinessServiceRequest.objects.create(
            service=self.service,
            user=self.user,
            message="Inquiry 2",
            budget="Flexible",
            timeline="Flexible"
        )

        url = reverse("business_service:api_business_service_inquiries")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        inquiries = response.json()["inquiries"]
        self.assertEqual(len(inquiries), 2)
        self.assertEqual(inquiries[0]["message"], "Inquiry 2") # Ordering is -created_at by default
        self.assertEqual(inquiries[1]["message"], "Inquiry 1")


class BusinessServiceInquiryAdminTests(APITestCase):
    def setUp(self):
        self.category, _ = ServiceCategory.objects.get_or_create(name="Legal")
        self.service = BusinessService.objects.create(
            title="Contract Advisory",
            provider="Ampli Legal",
            rate="From $500 / hr",
            speed="Ongoing",
            category=self.category,
            description="Contract review.",
            bullet_points="Review NDA\nReview contract",
            target_audience="both",
            is_active=True
        )

        self.user = User.objects.create_user(
            username="normal_user",
            email="normal@test.com",
            password="password123"
        )
        self.staff_user = User.objects.create_superuser(
            username="staff_user",
            email="staff@test.com",
            password="password123"
        )

        self.request = BusinessServiceRequest.objects.create(
            service=self.service,
            user=self.user,
            message="Need a contract review.",
            budget="500",
            timeline="Flexible"
        )

    def test_admin_connect_request_view_non_staff(self):
        url = reverse("wagtail_connect_business_service_request", args=[self.request.id])
        self.client.force_authenticate(user=self.user)
        # Should redirect to login or deny access
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        
        # Verify status is still pending
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, "pending")

    def test_admin_connect_request_view_success(self):
        url = reverse("wagtail_connect_business_service_request", args=[self.request.id])
        
        # We need session authentication since admin views require login
        self.client.login(username="staff_user", password="password123")
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        
        # Verify status changed to connected
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, "connected")

    def test_admin_decline_request_view_success(self):
        url = reverse("wagtail_decline_business_service_request", args=[self.request.id])
        
        self.client.login(username="staff_user", password="password123")
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        
        # Verify status changed to declined
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, "declined")

