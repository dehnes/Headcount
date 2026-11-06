from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse


class UserTests(TestCase):
    def test_create_user_and_authenticate_with_email(self):
        user = get_user_model().objects.create_user(
            "person@EXAMPLE.COM", "a-strong-password"
        )

        self.assertEqual(user.email, "person@example.com")
        self.assertTrue(user.check_password("a-strong-password"))
        self.assertNotEqual(user.password, "a-strong-password")
        self.assertEqual(
            authenticate(email=user.email, password="a-strong-password"), user
        )
        self.assertIsNone(authenticate(email=user.email, password="wrong-password"))

    def test_user_requires_email(self):
        for email in ("", "   ", None):
            with self.subTest(email=email), self.assertRaises(ValueError):
                get_user_model().objects.create_user(email, "a-strong-password")

    def test_email_must_be_unique(self):
        manager = get_user_model().objects
        manager.create_user("person@example.com", "a-strong-password")
        with self.assertRaises(IntegrityError), transaction.atomic():
            manager.create_user("person@EXAMPLE.COM", "a-strong-password")

    def test_inactive_user_cannot_authenticate(self):
        get_user_model().objects.create_user(
            "person@example.com", "a-strong-password", is_active=False
        )
        self.assertIsNone(
            authenticate(email="person@example.com", password="a-strong-password")
        )

    def test_superuser_permissions_are_required(self):
        manager = get_user_model().objects
        user = manager.create_superuser("admin@example.com", "a-strong-password")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        for field in ("is_staff", "is_superuser"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                manager.create_superuser(
                    "other@example.com", "a-strong-password", **{field: False}
                )

    def test_admin_login_and_user_creation(self):
        get_user_model().objects.create_superuser(
            "admin@example.com", "a-strong-password"
        )
        response = self.client.post(
            reverse("admin:login"),
            {
                "username": "admin@example.com",
                "password": "a-strong-password",
                "next": reverse("admin:index"),
            },
        )
        self.assertRedirects(response, reverse("admin:index"))
        response = self.client.post(
            reverse("admin:users_user_add"),
            {
                "email": "new@example.com",
                "password1": "another-strong-password",
                "password2": "another-strong-password",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            get_user_model()
            .objects.get(email="new@example.com")
            .check_password("another-strong-password")
        )
