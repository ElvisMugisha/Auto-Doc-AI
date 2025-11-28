from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from authentication.models import Profile
from utils import choices

User = get_user_model()


class UserListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('user-list')

        # Create a super admin user
        self.super_admin = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            first_name="Admin",
            last_name="User",
            password="AdminPassword123!",
            role=choices.UserRole.SUPER_ADMIN,
            is_verified=True
        )

        # Create a regular user
        self.regular_user = User.objects.create_user(
            email="regular@example.com",
            username="regular",
            first_name="Regular",
            last_name="User",
            password="RegularPassword123!",
            role=choices.UserRole.TEAM_MEMBER,
            is_verified=True
        )

        # Create profiles for users
        Profile.objects.create(
            user=self.super_admin,
            bio="Super Admin Bio",
            phone_number="+1234567890"
        )

        Profile.objects.create(
            user=self.regular_user,
            bio="Regular User Bio",
            phone_number="+0987654321"
        )

    def test_list_users_as_super_admin(self):
        """Test that super admin can list users"""
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 2)

    def test_list_users_as_superuser(self):
        """Test that superuser can list users"""
        superuser = User.objects.create_superuser(
            email="superuser@example.com",
            username="superuser",
            first_name="Super",
            last_name="User",
            password="SuperPassword123!"
        )

        self.client.force_authenticate(user=superuser)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)

    def test_list_users_as_regular_user_forbidden(self):
        """Test that regular users cannot list users"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_users_unauthenticated_forbidden(self):
        """Test that unauthenticated users cannot list users"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_list_includes_profile(self):
        """Test that user list includes profile data"""
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that profile data is included
        users_data = response.data['data']
        for user_data in users_data:
            self.assertIn('profile', user_data)
            if user_data['email'] == self.super_admin.email:
                self.assertEqual(user_data['profile']['bio'], "Super Admin Bio")

    def test_pagination_works(self):
        """Test that pagination is applied"""
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(self.url + '?page_size=1')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['data']), 1)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
