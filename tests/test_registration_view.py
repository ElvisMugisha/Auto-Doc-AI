from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()

class UserRegistrationViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('register')
        self.valid_payload = {
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        }

    @patch('authentication.views.create_and_send_otp')
    def test_registration_success(self, mock_create_otp):
        # Mock success response from create_and_send_otp
        mock_create_otp.return_value = ("otp_object", None, None)

        response = self.client.post(self.url, self.valid_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, "test@example.com")

    @patch('authentication.views.create_and_send_otp')
    def test_registration_email_failure_rollback(self, mock_create_otp):
        # Mock failure response from create_and_send_otp
        mock_create_otp.return_value = (None, "Email sending failed", status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = self.client.post(self.url, self.valid_payload)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['error'], "Email sending failed")
        # Verify user was deleted (rolled back)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_validation_error(self):
        payload = self.valid_payload.copy()
        payload['password'] = "weak" # Weak password

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)
