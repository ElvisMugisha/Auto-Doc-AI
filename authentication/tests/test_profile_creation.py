from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from authentication.models import Profile

User = get_user_model()

class UserProfileCreateTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='Password123!',
            first_name='Test',
            last_name='User',
            is_verified=True
        )
        self.url = reverse('create-profile')
        self.client.force_authenticate(user=self.user)

    def test_create_profile_success(self):
        data = {
            "bio": "Software Engineer",
            "phone_number": "1234567890",
            "country": "USA",
            "city": "New York"
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
        self.assertEqual(response.data['bio'], "Software Engineer")

    def test_create_profile_already_exists(self):
        # Create a profile first
        Profile.objects.create(user=self.user, bio="Existing bio")

        data = {
            "bio": "New bio"
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Profile already exists", str(response.data))

    def test_create_profile_unauthenticated(self):
        self.client.logout()
        data = {"bio": "Bio"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_profile_invalid_data(self):
        # Assuming there are some validations in ProfileSerializer or model
        # For example, if we send invalid data type (though most fields are strings/null)
        # Let's try sending a very long string for a char field if there's a limit
        # phone_number max_length=20
        data = {
            "phone_number": "a" * 21
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)
