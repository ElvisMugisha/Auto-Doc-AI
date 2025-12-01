"""
Comprehensive Test Suite for Email Verification API

This file contains test cases for the email verification functionality.
Run with: python manage.py test authentication.tests.test_email_verification
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from authentication.models import Passcode
from utils import choices

User = get_user_model()


class EmailVerificationTestCase(TestCase):
    """
    Test cases for email verification endpoint.
    """

    def setUp(self):
        """
        Set up test data before each test.
        """
        self.client = APIClient()
        self.verify_url = '/api/v1/auth/verify-email/'

        # Create a test user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            is_verified=False
        )

        # Create a valid OTP
        self.valid_otp = '12345678'
        self.passcode = Passcode.objects.create(
            user=self.user,
            code=self.valid_otp,
            code_type=choices.CodeType.VERIFICATION,
            expires_at=timezone.now() + timedelta(minutes=10),
            is_used=False
        )

    def test_successful_email_verification(self):
        """
        Test successful email verification with valid OTP.
        """
        data = {
            'email': 'testuser@example.com',
            'otp': self.valid_otp
        }

        response = self.client.post(self.verify_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

        # Verify user is marked as verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

        # Verify OTP is marked as used
        self.passcode.refresh_from_db()
        self.assertTrue(self.passcode.is_used)

    def test_invalid_otp(self):
        """
        Test verification with invalid OTP.
        """
        data = {
            'email': 'testuser@example.com',
            'otp': '99999999'
        }

        response = self.client.post(self.verify_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp', response.data)

    def test_expired_otp(self):
        """
        Test verification with expired OTP.
        """
        # Create an expired OTP
        expired_otp = '87654321'
        Passcode.objects.create(
            user=self.user,
            code=expired_otp,
            code_type=choices.CodeType.VERIFICATION,
            expires_at=timezone.now() - timedelta(minutes=5),
            is_used=False
        )

        data = {
            'email': 'testuser@example.com',
            'otp': expired_otp
        }

        response = self.client.post(self.verify_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertIn('otp', response.data)

    def test_nonexistent_user(self):
        """
        Test verification with non-existent email.
        """
        data = {
            'email': 'nonexistent@example.com',
            'otp': '12345678'
        }

        response = self.client.post(self.verify_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('email', response.data)

    def test_already_verified_user(self):
        """
        Test verification for already verified user.
        """
        # Mark user as verified
        self.user.is_verified = True
        self.user.save()

        data = {
            'email': 'testuser@example.com',
            'otp': self.valid_otp
        }

        response = self.client.post(self.verify_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_invalid_otp_format(self):
        """
        Test verification with invalid OTP format.
        """
        data = {
            'email': 'testuser@example.com',
            'otp': 'abc12345'  # Contains letters
        }

        response = self.client.post(self.verify_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp', response.data)

    def test_short_otp(self):
        """
        Test verification with OTP shorter than 8 digits.
        """
        data = {
            'email': 'testuser@example.com',
            'otp': '1234'
        }

        response = self.client.post(self.verify_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp', response.data)

    def test_missing_email(self):
        """
        Test verification without email field.
        """
        data = {
            'otp': self.valid_otp
        }

        response = self.client.post(self.verify_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_missing_otp(self):
        """
        Test verification without OTP field.
        """
        data = {
            'email': 'testuser@example.com'
        }

        response = self.client.post(self.verify_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp', response.data)

    def tearDown(self):
        """
        Clean up after each test.
        """
        User.objects.all().delete()
        Passcode.objects.all().delete()
