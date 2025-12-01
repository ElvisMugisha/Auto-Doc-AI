from rest_framework import serializers
from django.contrib.auth import get_user_model
from utils import loggings

# Initialize logger
logger = loggings.setup_logging()

User = get_user_model()


class ResendOTPSerializer(serializers.Serializer):
    """
    Serializer for Resending OTP.

    This serializer handles requests to resend verification OTP to users
    who didn't receive it or whose OTP has expired.
    """

    email = serializers.EmailField(
        required=True,
        help_text="Email address of the user requesting OTP resend."
    )

    def validate_email(self, value):
        """
        Normalize and validate the email address.

        Args:
            value (str): The email address to validate.

        Returns:
            str: Normalized email address (lowercase).

        Raises:
            ValidationError: If email is invalid or user doesn't exist.
        """
        try:
            email = value.lower().strip()
            logger.debug(f"Validating email for OTP resend: {email}")

            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                logger.warning(f"OTP resend attempt for non-existent email: {email}")
                raise serializers.ValidationError(
                    "No account found with this email address."
                )

            # Check if user is already verified
            if user.is_verified:
                logger.info(f"OTP resend attempt for already verified user: {email}")
                raise serializers.ValidationError(
                    "This account is already verified. You can log in directly."
                )

            return email

        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating email for OTP resend: {str(e)}")
            raise serializers.ValidationError("Invalid email format.")
