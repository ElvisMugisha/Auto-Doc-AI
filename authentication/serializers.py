from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError
from utils import loggings

# Initialize logger
logger = loggings.setup_logging()

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.

    This serializer is used to retrieve and update user information.
    It includes fields for user identification, profile details, and status.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "is_verified",
            "last_activity",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "is_verified",
            "last_activity",
            "created_at",
            "updated_at",
        ]

    def update(self, instance, validated_data):
        """
        Update and return an existing `User` instance, given the validated data.
        """
        logger.info(f"Updating user {instance.id} with data: {validated_data}")
        return super().update(instance, validated_data)


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for User Registration.

    This serializer handles the creation of a new user. It validates the
    input data, ensures passwords match, and checks for password complexity.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="User's password. Must meet complexity requirements."
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Confirm the user's password."
    )

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "first_name", "last_name", "password",
            "confirm_password", "role", "is_verified", "last_activity",
            "created_at", "updated_at",
        ]

        read_only_fields = [
            "id", "username", "role",
            "is_verified", "last_activity", "created_at", "updated_at"
        ]

    def validate_email(self, value):
        """
        Normalize the email to lowercase and check for uniqueness.
        """
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate(self, attrs):
        """
        Validate the data passed to the serializer.

        Checks:
        1. Passwords match.
        2. Password complexity.
        """
        logger.debug("Starting validation for user registration.")

        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if password != confirm_password:
            logger.warning("Registration failed: Passwords do not match.")
            raise ValidationError({"password": "Passwords do not match."})

        try:
            validate_password(password)
        except ValidationError as e:
            logger.warning(f"Registration failed: Password complexity error - {e}")
            raise serializers.ValidationError({"password": list(e.messages)})

        return attrs

    def create(self, validated_data):
        """
        Create a new user instance.

        Removes 'confirm_password' from the data and uses the UserManager
        to create the user safely.
        """
        logger.info(f"Creating new user with email: {validated_data.get('email')}")

        validated_data.pop("confirm_password")

        try:
            user = User.objects.create_user(**validated_data)
            logger.info(f"User created successfully: {user.id}")
            return user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise ValidationError({"error": "Unable to create user. Please try again."})
from authentication.models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the Profile model.
    """
    class Meta:
        model = Profile
        fields = [
            "bio",
            "phone_number",
            "dob",
            "profile_picture",
            "gender",
            "occupation",
            "country",
            "city",
            "street",
            "zip_code",
        ]


class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for Email Verification.

    This serializer handles the verification of a user's email address using
    a one-time passcode (OTP). It validates the email, OTP code, checks expiration,
    and ensures the code hasn't been used.
    """

    email = serializers.EmailField(
        required=True,
        help_text="Email address of the user to verify."
    )
    otp = serializers.CharField(
        required=True,
        min_length=8,
        max_length=8,
        help_text="8-digit one-time passcode sent to the user's email."
    )

    def validate_email(self, value):
        """
        Normalize and validate the email address.

        Args:
            value (str): The email address to validate.

        Returns:
            str: Normalized email address (lowercase).

        Raises:
            ValidationError: If email format is invalid.
        """
        try:
            email = value.lower().strip()
            logger.debug(f"Validating email for verification: {email}")
            return email
        except Exception as e:
            logger.error(f"Error normalizing email: {str(e)}")
            raise serializers.ValidationError("Invalid email format.")

    def validate_otp(self, value):
        """
        Validate the OTP format.

        Args:
            value (str): The OTP code to validate.

        Returns:
            str: Cleaned OTP code.

        Raises:
            ValidationError: If OTP format is invalid.
        """
        try:
            otp = value.strip()

            # Ensure OTP is exactly 8 digits
            if not otp.isdigit():
                logger.warning(f"Invalid OTP format: contains non-digit characters")
                raise serializers.ValidationError("OTP must contain only digits.")

            if len(otp) != 8:
                logger.warning(f"Invalid OTP length: {len(otp)}")
                raise serializers.ValidationError("OTP must be exactly 8 digits.")

            logger.debug("OTP format validation passed")
            return otp

        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating OTP: {str(e)}")
            raise serializers.ValidationError("Invalid OTP format.")

    def validate(self, attrs):
        """
        Validate the complete verification request.

        This method performs comprehensive validation:
        1. Checks if user exists with the provided email
        2. Checks if user is already verified
        3. Validates the OTP exists and matches
        4. Checks if OTP has expired
        5. Checks if OTP has already been used

        Args:
            attrs (dict): Dictionary containing email and otp.

        Returns:
            dict: Validated attributes with user and passcode objects.

        Raises:
            ValidationError: If any validation check fails.
        """
        from django.utils import timezone
        from authentication.models import Passcode
        from utils import choices

        email = attrs.get('email')
        otp = attrs.get('otp')

        logger.info(f"Starting email verification validation for: {email}")

        try:
            # Check if user exists
            try:
                user = User.objects.get(email=email)
                logger.debug(f"User found: {user.id}")
            except User.DoesNotExist:
                logger.warning(f"Verification attempt for non-existent email: {email}")
                raise serializers.ValidationError({
                    "email": "No account found with this email address."
                })

            # Check if user is already verified
            if user.is_verified:
                logger.info(f"User {email} is already verified")
                raise serializers.ValidationError({
                    "email": "This account is already verified."
                })

            # Retrieve the OTP for this user
            try:
                passcode = Passcode.objects.get(
                    user=user,
                    code=otp,
                    code_type=choices.CodeType.VERIFICATION,
                    is_used=False
                )
                logger.debug(f"Passcode found for user {email}")
            except Passcode.DoesNotExist:
                logger.warning(f"Invalid OTP attempt for user {email}")
                raise serializers.ValidationError({
                    "otp": "Invalid verification code. Please check and try again."
                })

            # Check if OTP has expired
            if passcode.expires_at < timezone.now():
                logger.warning(f"Expired OTP used for user {email}")
                # Mark as used to prevent reuse
                passcode.is_used = True
                passcode.save(update_fields=['is_used'])
                raise serializers.ValidationError({
                    "otp": "This verification code has expired. Please request a new one."
                })

            # Store user and passcode in validated data for use in the view
            attrs['user'] = user
            attrs['passcode'] = passcode

            logger.info(f"Email verification validation successful for: {email}")
            return attrs

        except serializers.ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            # Catch any unexpected errors
            logger.exception(f"Unexpected error during verification validation: {str(e)}")
            raise serializers.ValidationError({
                "error": "An unexpected error occurred during verification. Please try again."
            })


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing users with their profile.
    """
    profile = ProfileSerializer(source='user_profile', read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "is_verified",
            "last_activity",
            "created_at",
            "updated_at",
            "profile",
        ]


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


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing user password.

    Validates old password, ensures new password meets complexity requirements,
    and confirms new password matches confirmation.
    """

    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="Current password for verification"
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="New password. Must meet complexity requirements."
    )
    confirm_new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="Confirm the new password"
    )

    def validate_old_password(self, value):
        """
        Validate that the old password is correct.

        Args:
            value (str): The old password provided by user.

        Returns:
            str: The validated old password.

        Raises:
            ValidationError: If old password is incorrect.
        """
        user = self.context.get('request').user

        if not user.check_password(value):
            logger.warning(f"Incorrect old password attempt for user: {user.email}")
            raise serializers.ValidationError("Current password is incorrect.")

        logger.debug(f"Old password validated for user: {user.email}")
        return value

    def validate_new_password(self, value):
        """
        Validate new password complexity.

        Args:
            value (str): The new password.

        Returns:
            str: The validated new password.

        Raises:
            ValidationError: If password doesn't meet complexity requirements.
        """
        try:
            validate_password(value)
            logger.debug("New password meets complexity requirements")
            return value
        except ValidationError as e:
            logger.warning(f"Password complexity validation failed: {e}")
            raise serializers.ValidationError(list(e.messages))

    def validate(self, attrs):
        """
        Validate that new passwords match and differ from old password.

        Args:
            attrs (dict): Dictionary containing all password fields.

        Returns:
            dict: Validated attributes.

        Raises:
            ValidationError: If passwords don't match or new password same as old.
        """
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        confirm_new_password = attrs.get('confirm_new_password')

        # Check if new passwords match
        if new_password != confirm_new_password:
            logger.warning("New password and confirmation do not match")
            raise serializers.ValidationError({
                "confirm_new_password": "New passwords do not match."
            })

        # Check if new password is different from old password
        if old_password == new_password:
            logger.warning("New password is same as old password")
            raise serializers.ValidationError({
                "new_password": "New password must be different from current password."
            })

        logger.debug("Password change validation successful")
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting password reset.

    Validates email and initiates password reset process by sending OTP.
    """

    email = serializers.EmailField(
        required=True,
        help_text="Email address of the account to reset password for"
    )

    def validate_email(self, value):
        """
        Validate and normalize email address.

        Args:
            value (str): Email address provided.

        Returns:
            str: Normalized email address.

        Raises:
            ValidationError: If user with email doesn't exist.
        """
        email = value.lower().strip()
        logger.debug(f"Validating email for password reset: {email}")

        try:
            user = User.objects.get(email=email)
            logger.debug(f"User found for password reset: {user.id}")
        except User.DoesNotExist:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            # For security, don't reveal if email exists or not
            # Return success anyway to prevent email enumeration
            pass

        return email


class PasswordResetVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying password reset OTP.

    Validates the OTP code sent to user's email for password reset.
    """

    email = serializers.EmailField(
        required=True,
        help_text="Email address of the account"
    )
    otp = serializers.CharField(
        required=True,
        min_length=8,
        max_length=8,
        help_text="8-digit OTP code sent to email"
    )

    def validate_email(self, value):
        """
        Normalize email address.

        Args:
            value (str): Email address.

        Returns:
            str: Normalized email.
        """
        return value.lower().strip()

    def validate_otp(self, value):
        """
        Validate OTP format.

        Args:
            value (str): OTP code.

        Returns:
            str: Cleaned OTP.

        Raises:
            ValidationError: If OTP format is invalid.
        """
        otp = value.strip()

        if not otp.isdigit():
            logger.warning("Invalid OTP format: contains non-digit characters")
            raise serializers.ValidationError("OTP must contain only digits.")

        if len(otp) != 8:
            logger.warning(f"Invalid OTP length: {len(otp)}")
            raise serializers.ValidationError("OTP must be exactly 8 digits.")

        return otp

    def validate(self, attrs):
        """
        Validate OTP against database.

        Args:
            attrs (dict): Dictionary containing email and otp.

        Returns:
            dict: Validated attributes with user and passcode objects.

        Raises:
            ValidationError: If validation fails.
        """
        from django.utils import timezone
        from authentication.models import Passcode
        from utils import choices

        email = attrs.get('email')
        otp = attrs.get('otp')

        logger.info(f"Verifying password reset OTP for: {email}")

        try:
            # Get user
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                logger.warning(f"OTP verification for non-existent email: {email}")
                raise serializers.ValidationError({
                    "email": "No account found with this email address."
                })

            # Get passcode
            try:
                passcode = Passcode.objects.get(
                    user=user,
                    code=otp,
                    code_type=choices.CodeType.PASSWORD_RESET,
                    is_used=False
                )
            except Passcode.DoesNotExist:
                logger.warning(f"Invalid password reset OTP for {email}")
                raise serializers.ValidationError({
                    "otp": "Invalid or expired reset code."
                })

            # Check if expired
            if passcode.expires_at < timezone.now():
                logger.warning(f"Expired password reset OTP for {email}")
                passcode.is_used = True
                passcode.save(update_fields=['is_used'])
                raise serializers.ValidationError({
                    "otp": "This reset code has expired. Please request a new one."
                })

            # Store for use in view
            attrs['user'] = user
            attrs['passcode'] = passcode

            logger.info(f"Password reset OTP verified for: {email}")
            return attrs

        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error verifying password reset OTP: {str(e)}")
            raise serializers.ValidationError({
                "error": "An error occurred during verification."
            })


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming password reset with new password.

    Validates email, OTP, and new password before resetting.
    """

    email = serializers.EmailField(
        required=True,
        help_text="Email address of the account"
    )
    otp = serializers.CharField(
        required=True,
        min_length=8,
        max_length=8,
        help_text="8-digit OTP code"
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="New password"
    )
    confirm_new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="Confirm new password"
    )

    def validate_email(self, value):
        """Normalize email."""
        return value.lower().strip()

    def validate_otp(self, value):
        """Validate OTP format."""
        otp = value.strip()

        if not otp.isdigit() or len(otp) != 8:
            raise serializers.ValidationError("Invalid OTP format.")

        return otp

    def validate_new_password(self, value):
        """
        Validate new password complexity.

        Args:
            value (str): New password.

        Returns:
            str: Validated password.

        Raises:
            ValidationError: If password doesn't meet requirements.
        """
        try:
            validate_password(value)
            return value
        except ValidationError as e:
            logger.warning(f"Password reset: weak password provided")
            raise serializers.ValidationError(list(e.messages))

    def validate(self, attrs):
        """
        Validate OTP and password confirmation.

        Args:
            attrs (dict): All attributes.

        Returns:
            dict: Validated attributes with user and passcode.

        Raises:
            ValidationError: If validation fails.
        """
        from django.utils import timezone
        from authentication.models import Passcode
        from utils import choices

        email = attrs.get('email')
        otp = attrs.get('otp')
        new_password = attrs.get('new_password')
        confirm_new_password = attrs.get('confirm_new_password')

        # Check passwords match
        if new_password != confirm_new_password:
            logger.warning("Password reset: passwords don't match")
            raise serializers.ValidationError({
                "confirm_new_password": "Passwords do not match."
            })

        logger.info(f"Confirming password reset for: {email}")

        try:
            # Get user
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                logger.warning(f"Password reset confirm for non-existent email: {email}")
                raise serializers.ValidationError({
                    "email": "No account found with this email address."
                })

            # Get and validate passcode
            try:
                passcode = Passcode.objects.get(
                    user=user,
                    code=otp,
                    code_type=choices.CodeType.PASSWORD_RESET,
                    is_used=False
                )
            except Passcode.DoesNotExist:
                logger.warning(f"Invalid password reset OTP for {email}")
                raise serializers.ValidationError({
                    "otp": "Invalid or expired reset code."
                })

            # Check if expired
            if passcode.expires_at < timezone.now():
                logger.warning(f"Expired password reset OTP for {email}")
                passcode.is_used = True
                passcode.save(update_fields=['is_used'])
                raise serializers.ValidationError({
                    "otp": "This reset code has expired. Please request a new one."
                })

            # Store for use in view
            attrs['user'] = user
            attrs['passcode'] = passcode

            logger.info(f"Password reset validation successful for: {email}")
            return attrs

        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error in password reset confirmation: {str(e)}")
            raise serializers.ValidationError({
                "error": "An error occurred during password reset."
            })
