from django.test import TestCase
from django.contrib.auth import get_user_model
from authentication.serializers import UserRegistrationSerializer

User = get_user_model()

class EmailNormalizationTest(TestCase):
    def test_email_normalization(self):
        data = {
            "email": "Test@Example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.email, "test@example.com")

    def test_email_uniqueness_case_insensitive(self):
        User.objects.create_user(
            email="existing@example.com",
            username="existing",
            first_name="Existing",
            last_name="User",
            password="password"
        )

        data = {
            "email": "Existing@Example.com", # Different case
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        # Check for the error message we added
        found_error = False
        for error in serializer.errors["email"]:
            if "A user with this email already exists" in str(error):
                found_error = True
                break
        self.assertTrue(found_error, f"Expected error message not found in {serializer.errors['email']}")
