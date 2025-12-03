"""
Unit tests for authentication flows.

Tests:
- User registration
- Email verification
- Login/logout
- Password reset
- Token authentication
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from authentication.models import Passcode

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistration:
    """Test user registration flow."""

    def test_register_user_success(self, api_client):
        """Test successful user registration."""
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'email' in response.data
        assert User.objects.filter(email='newuser@example.com').exists()

    def test_register_duplicate_email(self, api_client, user):
        """Test registration with duplicate email fails."""
        url = reverse('register')
        data = {
            'email': user.email,
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        """Test registration with weak password fails."""
        url = reverse('register')
        data = {
            'email': 'test@example.com',
            'password': '123',  # Too weak
            'confirm_password': '123',
            'first_name': 'Test',
            'last_name': 'User'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_fields(self, api_client):
        """Test registration with missing required fields."""
        url = reverse('register')
        data = {
            'email': 'test@example.com',
            # Missing username, password, etc.
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    """Test user login flow."""

    def test_login_success(self, api_client, user):
        """Test successful login."""
        url = reverse('login')
        data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data

    def test_login_wrong_password(self, api_client, user):
        """Test login with wrong password."""
        url = reverse('login')
        data = {
            'email': user.email,
            'password': 'WrongPassword123!'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent user."""
        url = reverse('login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'SomePass123!'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self, api_client, db):
        """Test login with inactive user."""
        inactive_user = User.objects.create_user(
            email='inactive@example.com',
            password='TestPass123!',
            first_name='Inactive',
            last_name='User',
            is_active=False
        )

        url = reverse('login')
        data = {
            'email': inactive_user.email,
            'password': 'TestPass123!'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTokenAuthentication:
    """Test token-based authentication."""

    def test_token_created_on_login(self, api_client, user):
        """Test that token is created on login."""
        url = reverse('login')
        data = {
            'email': user.email,
            'password': 'TestPass123!'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert Token.objects.filter(user=user).exists()

    def test_authenticated_request(self, authenticated_client):
        """Test making authenticated request."""
        url = reverse('user-profile')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_request(self, api_client):
        """Test making unauthenticated request to protected endpoint."""
        url = reverse('user-profile')

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token(self, api_client):
        """Test request with invalid token."""
        api_client.credentials(HTTP_AUTHORIZATION='Token invalid-token-here')
        url = reverse('user-profile')

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestEmailVerification:
    """Test email verification flow."""

    def test_request_verification_code(self, api_client, user):
        """Test requesting email verification code."""
        # This would test the email verification endpoint
        # Implementation depends on your actual email verification flow
        pass

    def test_verify_email_success(self, api_client, user):
        """Test successful email verification."""
        # Create a passcode for the user
        from django.utils import timezone
        from datetime import timedelta

        passcode = Passcode.objects.create(
            user=user,
            code='123456',
            code_type='email_verification',
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        # Test verification endpoint
        # Implementation depends on your actual verification endpoint
        pass

    def test_verify_email_invalid_code(self, api_client, user):
        """Test email verification with invalid code."""
        pass

    def test_verify_email_expired_code(self, api_client, user):
        """Test email verification with expired code."""
        pass


@pytest.mark.django_db
class TestPasswordReset:
    """Test password reset flow."""

    def test_request_password_reset(self, api_client, user):
        """Test requesting password reset."""
        url = reverse('password-reset-request')
        data = {'email': user.email}

        response = api_client.post(url, data)

        # Should succeed even if email doesn't exist (security)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_reset_password_success(self, api_client, user):
        """Test successful password reset."""
        # Create reset passcode
        from django.utils import timezone
        from datetime import timedelta

        passcode = Passcode.objects.create(
            user=user,
            code='123456',
            code_type='password_reset',
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        # Test reset endpoint with valid code
        # Implementation depends on your actual reset endpoint
        pass

    def test_reset_password_invalid_code(self, api_client, user):
        """Test password reset with invalid code."""
        pass


@pytest.mark.django_db
class TestUserProfile:
    """Test user profile operations."""

    def test_get_profile(self, authenticated_client, user):
        """Test getting user profile."""
        url = reverse('user-profile')

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    def test_update_profile(self, authenticated_client, user):
        """Test updating user profile."""
        url = reverse('user-profile')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }

        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_database()
        assert user.first_name == 'Updated'
