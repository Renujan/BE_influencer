from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from notifications.models import Notification
from notifications.utils import resolve_admin_redirect_url

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
            target_url="/admin/creatorprofile/"
        )
        self.notification_2 = Notification.objects.create(
            title="Notification 2",
            message="Message 2",
            category="campaign"
        )
        self.notification_3 = Notification.objects.create(
            title="Campaign Update",
            message="Your campaign was updated.",
            category="campaign",
            target_url="/dashboard/campaigns"
        )
        self.notification_4 = Notification.objects.create(
            title="Legacy Complaint Ticket",
            message="A dispute was filed.",
            category="compliance",
            target_url="/admin/snippets/complaint/complaint/"
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
        # Campaign notifications without a target URL should fall back to campaigns admin
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/snippets/campegin/campaign/")
        
        # Verify marked as read
        self.notification_2.refresh_from_db()
        self.assertTrue(self.notification_2.is_read)

    def test_read_and_redirect_frontend_url_maps_to_admin(self):
        self.client.login(username="test_admin", password="password123")
        url = reverse("notifications:read_and_redirect", args=[self.notification_3.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/snippets/campegin/campaign/")
        self.notification_3.refresh_from_db()
        self.assertTrue(self.notification_3.is_read)

    def test_read_and_redirect_legacy_admin_url(self):
        self.client.login(username="test_admin", password="password123")
        url = reverse("notifications:read_and_redirect", args=[self.notification_4.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/complaint/")
        self.notification_4.refresh_from_db()
        self.assertTrue(self.notification_4.is_read)

    def test_resolve_admin_redirect_url_workspace(self):
        notification = Notification.objects.create(
            title="Workspace Message",
            message="New message in workspace.",
            category="compliance",
            target_url="/workspace/42/"
        )

        self.assertEqual(
            resolve_admin_redirect_url(notification),
            "/admin/snippets/campegin/campaign/inspect/42/"
        )

    def test_api_notifications_routing_and_retention(self):
        import datetime
        from django.utils import timezone
        from rest_framework.authtoken.models import Token
        from user.models import CreatorProfile, BusinessProfile

        creator_user = User.objects.create_user(username="test_creator_u", email="c@test.com", password="pw")
        CreatorProfile.objects.create(user=creator_user)
        token_c = Token.objects.create(user=creator_user)

        # 1. Old notification (> 14 days ago)
        old_time = timezone.now() - datetime.timedelta(days=15)
        old_notif = Notification.objects.create(
            user=creator_user,
            target_role="creator",
            title="Old Notification",
            message="Too old",
            category="campaign",
            target_url="/creator/requests"
        )
        Notification.objects.filter(id=old_notif.id).update(created_at=old_time)

        # 2. Fresh pitch notification with legacy /creator/pitches URL
        pitch_notif = Notification.objects.create(
            user=creator_user,
            target_role="creator",
            title="Pitch Submitted",
            message="Your pitch was submitted",
            category="campaign",
            target_url="/creator/pitches"
        )

        # 3. Support complaint notification
        complaint_notif = Notification.objects.create(
            user=creator_user,
            target_role="creator",
            title="Support Ticket Created",
            message="Ticket #5 has been opened.",
            category="compliance",
            target_url="/admin/complaint/inspect/5/"
        )

        # Call API as creator
        response = self.client.get(
            "/api/notifications/?role=creator",
            HTTP_AUTHORIZATION=f"Token {token_c.key}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json().get("notifications", [])

        # Old notification must be deleted or excluded
        ids = [item["id"] for item in data]
        self.assertNotIn(old_notif.id, ids)
        self.assertIn(pitch_notif.id, ids)
        self.assertIn(complaint_notif.id, ids)

        # Legacy /creator/pitches mapped to /creator/requests
        p_item = next(item for item in data if item["id"] == pitch_notif.id)
        self.assertEqual(p_item["targetUrl"], "/creator/requests")

        # Support complaint mapped to /creator/support
        c_item = next(item for item in data if item["id"] == complaint_notif.id)
        self.assertEqual(c_item["targetUrl"], "/creator/support")
