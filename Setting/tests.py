from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from user.models import CreatorProfile, BusinessProfile, Niche, CreatorRate
from Setting.models import CreatorSettings, BusinessSettings, CreatorPayoutMethod

class SettingAPITests(APITestCase):
    def setUp(self):
        # Create user for creator tests
        self.creator_user = User.objects.create_user(
            username="creator_test",
            email="creator@test.com",
            password="oldpassword123",
            first_name="John",
            last_name="Doe"
        )
        self.creator_profile, _ = CreatorProfile.objects.get_or_create(user=self.creator_user)
        
        # Create user for business tests
        self.business_user = User.objects.create_user(
            username="business_test",
            email="business@test.com",
            password="oldpassword123",
            first_name="Jane",
            last_name="Smith"
        )
        self.business_profile, _ = BusinessProfile.objects.get_or_create(user=self.business_user)

    def test_creator_settings_get(self):
        self.client.force_authenticate(user=self.creator_user)
        url = reverse("creator_settings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return creator settings structures
        self.assertIn("settings", response.data)
        self.assertIn("rates", response.data)
        self.assertIn("payout_methods", response.data)
        self.assertEqual(response.data["first_name"], "John")

    def test_creator_settings_put(self):
        self.client.force_authenticate(user=self.creator_user)
        url = reverse("creator_settings")
        payload = {
            "first_name": "Johnny",
            "last_name": "Does",
            "phone": "+1234567890",
            "location": "New York, NY",
            "bio": "New Bio",
            "niches": ["Lifestyle", "Tech"],
            "settings": {
                "email_new_brand_requests": False,
                "push_brand_requests": False,
                "two_factor_enabled": True
            },
            "rates": [
                {
                    "content_type": "Feed Post (Photo)",
                    "platforms": "Instagram",
                    "price": "100.00",
                    "notes": "Test Note"
                }
            ],
            "payout_methods": [
                {
                    "method_type": "PayPal",
                    "details": "creator@paypal.com",
                    "is_primary": True
                }
            ]
        }
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify changes in DB
        self.creator_user.refresh_from_db()
        self.assertEqual(self.creator_user.first_name, "Johnny")
        self.assertEqual(self.creator_user.last_name, "Does")
        
        self.creator_profile.refresh_from_db()
        self.assertEqual(self.creator_profile.phone, "+1234567890")
        self.assertEqual(self.creator_profile.location, "New York, NY")
        self.assertEqual(self.creator_profile.bio, "New Bio")
        self.assertEqual(self.creator_profile.niches.count(), 2)
        
        creator_settings = CreatorSettings.objects.get(creator=self.creator_profile)
        self.assertFalse(creator_settings.email_new_brand_requests)
        self.assertFalse(creator_settings.push_brand_requests)
        self.assertTrue(creator_settings.two_factor_enabled)
        
        rates = CreatorRate.objects.filter(creator=self.creator_profile)
        self.assertEqual(rates.count(), 1)
        self.assertEqual(rates.first().price, 100)
        
        payouts = CreatorPayoutMethod.objects.filter(creator=self.creator_profile)
        self.assertEqual(payouts.count(), 1)
        self.assertEqual(payouts.first().details, "creator@paypal.com")

    def test_business_settings_get(self):
        self.client.force_authenticate(user=self.business_user)
        url = reverse("business_settings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("settings", response.data)
        self.assertIn("business_types", response.data)
        self.assertEqual(response.data["first_name"], "Jane")

    def test_business_settings_put(self):
        self.client.force_authenticate(user=self.business_user)
        url = reverse("business_settings")
        payload = {
            "first_name": "Janie",
            "last_name": "Smithy",
            "company_name": "Test Company",
            "business_types": ["E-Commerce", "Startup"],
            "website": "https://testcompany.com",
            "bio": "We make things",
            "phone": "+9876543210",
            "time_zone": "UTC+1:00",
            "facebook_url": "https://facebook.com/test",
            "instagram_handle": "@test",
            "settings": {
                "campaign_new_approved": False,
                "slack_connected": True,
                "theme": "Dark"
            }
        }
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify in DB
        self.business_user.refresh_from_db()
        self.assertEqual(self.business_user.first_name, "Janie")
        self.assertEqual(self.business_user.last_name, "Smithy")
        
        self.business_profile.refresh_from_db()
        self.assertEqual(self.business_profile.company_name, "Test Company")
        self.assertEqual(self.business_profile.website, "https://testcompany.com")
        self.assertEqual(self.business_profile.time_zone, "UTC+1:00")
        self.assertEqual(self.business_profile.business_type, "E-Commerce,Startup")
        self.assertEqual(self.business_profile.instagram_handle, "@test")
        
        business_settings = BusinessSettings.objects.get(business=self.business_profile)
        self.assertFalse(business_settings.campaign_new_approved)
        self.assertTrue(business_settings.slack_connected)
        self.assertEqual(business_settings.theme, "Dark")

    def test_change_password_success(self):
        self.client.force_authenticate(user=self.creator_user)
        url = reverse("change_password")
        payload = {
            "current_password": "oldpassword123",
            "new_password": "newpassword123",
            "confirm_new_password": "newpassword123"
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check login with new password
        self.creator_user.refresh_from_db()
        self.assertTrue(self.creator_user.check_password("newpassword123"))

    def test_change_password_mismatched(self):
        self.client.force_authenticate(user=self.creator_user)
        url = reverse("change_password")
        payload = {
            "current_password": "oldpassword123",
            "new_password": "newpassword123",
            "confirm_new_password": "differentpassword"
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "New passwords do not match")

    def test_change_password_wrong_current(self):
        self.client.force_authenticate(user=self.creator_user)
        url = reverse("change_password")
        payload = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
            "confirm_new_password": "newpassword123"
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid current password")
