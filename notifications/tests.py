from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from notifications.models import Notification

class NotificationTests(TestCase):
    def setUp(self):
        # Create as superuser so they have is_staff and is_superuser access to Wagtail admin
        self.user = User.objects.create_superuser(
            username="test_admin",
            email="admin@test.com",
            password="password123"
        )
        self.notification_1 = Notification.objects.create(
            title="Notification 1",
            message="Message 1",
            category="signup",
            target_url="/admin/snippets/user/creatorprofile/"
        )
        self.notification_2 = Notification.objects.create(
            title="Notification 2",
            message="Message 2",
            category="campaign"
        )

    def test_mark_all_read(self):
        self.client.login(username="test_admin", password="password123")
        url = reverse("notifications:mark_all_read")
        # Post request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        
        # Verify both are read
        self.notification_1.refresh_from_db()
        self.notification_2.refresh_from_db()
        self.assertTrue(self.notification_1.is_read)
        self.assertTrue(self.notification_2.is_read)

    def test_read_and_redirect_unauthenticated(self):
        url = reverse("notifications:read_and_redirect", args=[self.notification_1.id])
        response = self.client.get(url)
        # Should redirect to login page (due to @login_required)
        self.assertEqual(response.status_code, 302)
        self.assertTrue("login" in response.url)

    def test_read_and_redirect_success(self):
        self.client.login(username="test_admin", password="password123")
        url = reverse("notifications:read_and_redirect", args=[self.notification_1.id])
        
        # Ensure it starts unread
        self.assertFalse(self.notification_1.is_read)
        
        response = self.client.get(url)
        # Verify redirect to target_url
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.notification_1.target_url)
        
        # Verify marked as read
        self.notification_1.refresh_from_db()
        self.assertTrue(self.notification_1.is_read)

    def test_read_and_redirect_fallback(self):
        self.client.login(username="test_admin", password="password123")
        url = reverse("notifications:read_and_redirect", args=[self.notification_2.id])
        
        response = self.client.get(url)
        # Verify redirect to /admin/
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/")
        
        # Verify marked as read
        self.notification_2.refresh_from_db()
        self.assertTrue(self.notification_2.is_read)
