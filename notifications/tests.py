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

    def test_admin_notifications_view_access(self):
        # Unauthenticated access redirects to login
        response = self.client.get(reverse("notifications:admin_notifications_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

        # Superuser access renders notifications template successfully
        self.client.login(username="test_admin", password="password123")
        response = self.client.get(reverse("notifications:admin_notifications_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "notifications/admin_notifications.html")
        self.assertIn("notifications", response.context)
        self.assertIn("total_count", response.context)
        self.assertIn("unread_count", response.context)
        self.assertIn("read_count", response.context)

    def test_admin_notifications_filters(self):
        self.client.login(username="test_admin", password="password123")

        # Status filter unread
        response = self.client.get(reverse("notifications:admin_notifications_list") + "?status=unread")
        self.assertEqual(response.status_code, 200)
        for n in response.context["notifications"]:
            self.assertFalse(n.is_read)

        # Mark notification_1 as read
        self.notification_1.is_read = True
        self.notification_1.save()

        # Status filter read
        response = self.client.get(reverse("notifications:admin_notifications_list") + "?status=read")
        self.assertEqual(response.status_code, 200)
        for n in response.context["notifications"]:
            self.assertTrue(n.is_read)

        # Category filter
        response = self.client.get(reverse("notifications:admin_notifications_list") + "?category=signup")
        self.assertEqual(response.status_code, 200)
        for n in response.context["notifications"]:
            self.assertEqual(n.category, "signup")

    def test_toggle_read_notification(self):
        self.client.login(username="test_admin", password="password123")

        # Initially False
        self.assertFalse(self.notification_2.is_read)

        # Toggle to True
        response = self.client.post(
            reverse("notifications:toggle_read", args=[self.notification_2.id]),
            {"ajax": "true"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_read"])
        self.notification_2.refresh_from_db()
        self.assertTrue(self.notification_2.is_read)

        # Toggle back to False
        response = self.client.post(
            reverse("notifications:toggle_read", args=[self.notification_2.id]),
            {"ajax": "true"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_read"])
        self.notification_2.refresh_from_db()
        self.assertFalse(self.notification_2.is_read)

    def test_manual_delete_notification(self):
        self.client.login(username="test_admin", password="password123")

        # GET should be disallowed
        get_res = self.client.get(reverse("notifications:delete_notification", args=[self.notification_1.id]))
        self.assertEqual(get_res.status_code, 405)

        # POST performs explicit manual deletion
        post_res = self.client.post(
            reverse("notifications:delete_notification", args=[self.notification_1.id]),
            {"ajax": "true"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(post_res.status_code, 200)
        self.assertEqual(post_res.json()["status"], "success")
        self.assertFalse(Notification.objects.filter(id=self.notification_1.id).exists())

    def test_bulk_actions(self):
        self.client.login(username="test_admin", password="password123")

        # Bulk mark read
        res = self.client.post(
            reverse("notifications:bulk_action"),
            {"action": "mark_read", "selected_ids": f"{self.notification_1.id},{self.notification_2.id}", "ajax": "true"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(res.status_code, 200)
        self.notification_1.refresh_from_db()
        self.notification_2.refresh_from_db()
        self.assertTrue(self.notification_1.is_read)
        self.assertTrue(self.notification_2.is_read)

        # Bulk delete
        res = self.client.post(
            reverse("notifications:bulk_action"),
            {"action": "delete", "selected_ids": f"{self.notification_1.id}", "ajax": "true"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Notification.objects.filter(id=self.notification_1.id).exists())

    def test_sidebar_menu_ordering(self):
        from wagtail.admin.viewsets import viewsets
        viewsets.populate()
        from wagtail.admin.menu import admin_menu
        from django.test import RequestFactory

        rf = RequestFactory()
        req = rf.get("/admin/")
        req.user = self.user

        items = admin_menu.menu_items_for_request(req)
        sorted_items = sorted(items, key=lambda x: x.order)

        complaints_idx = None
        notif_idx = None
        for idx, item in enumerate(sorted_items):
            if getattr(item, "name", "") == "complaints_group" or getattr(item, "label", "") == "Complaints":
                complaints_idx = idx
            elif getattr(item, "name", "") == "notifications" or getattr(item, "label", "") == "Notifications":
                notif_idx = idx

        self.assertIsNotNone(complaints_idx, "Complaints group not found in menu")
        self.assertIsNotNone(notif_idx, "Notifications item not found in menu")
        # Notifications must immediately follow Complaints
        self.assertEqual(notif_idx, complaints_idx + 1)

