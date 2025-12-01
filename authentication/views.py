from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import get_user_model

from authentication.serializers import (
    UserRegistrationSerializer,
    UserListSerializer,
    EmailVerificationSerializer,
    ResendOTPSerializer,
    ProfileSerializer
)
from utils import loggings, choices
from utils.utils import create_and_send_otp
from utils.permissions import IsSuperAdminOrSuperUser
from utils.paginations import CustomPageNumberPagination

# Initialize logger
logger = loggings.setup_logging()

User = get_user_model()


class UserRegistrationView(APIView):
    """
    API View for User Registration.

    Handles the creation of a new user account, generation of a verification passcode,
    and sending the passcode via email.
    """
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    @extend_schema(
        summary="Register a new user",
        description="Create a new user account and send a verification email.",
        request=UserRegistrationSerializer,
        responses={
            201: UserRegistrationSerializer,
            400: OpenApiResponse(description="Bad Request"),
            500: OpenApiResponse(description="Internal Server Error")
        }
    )
    def post(self, request):
        """
        Handle POST request to register a new user.

        Steps:
        1. Validate input data.
        2. Create user.
        3. Generate and send OTP.
        4. If OTP/Email fails, rollback (delete) user.
        """
        logger.info("Received user registration request.")

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            user = None
            try:
                # Save the user
                user = serializer.save()
                logger.info(f"User created successfully: {user.email}")

                # Create and send OTP
                # This function handles creating the Passcode record and sending the email.
                # It returns (otp_object, error_message, status_code).
                otp, error_msg, error_status = create_and_send_otp(
                    user=user,
                    code_type=choices.CodeType.VERIFICATION,
                    purpose="verification"
                )

                if error_msg:
                    logger.error(f"Failed to send OTP to {user.email}: {error_msg}")
                    # Delete the user if OTP sending fails (Rollback)
                    user.delete()
                    logger.info(f"Rolled back user creation for {user.email}")
                    return Response(
                        {"error": error_msg},
                        status=error_status
                    )

                logger.info(f"Registration flow completed successfully for {user.email}")
                return Response(
                    {
                        "message": "Your account has been created successfully. Please check your email for the verification code.",
                        "data": serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                logger.exception(f"Unexpected error during registration: {str(e)}")
                # Ensure user is deleted if an unexpected exception occurs after creation
                if user:
                    user.delete()
                    logger.info(f"Rolled back user creation for {user.email} due to exception")

                return Response(
                    {"error": "An unexpected error occurred. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        logger.warning(f"Registration validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(APIView):
    """
    API View for listing all users.

    Only Super Admins and Superusers can access this view.
    Returns paginated list of users with their profile information.
    """
    permission_classes = [IsSuperAdminOrSuperUser]
    serializer_class = UserListSerializer
    pagination_class = CustomPageNumberPagination

    @extend_schema(
        summary="List all users",
        description="Retrieve a paginated list of all users with their profile information. Only accessible by Super Admins and Superusers.",
        responses={
            200: UserListSerializer(many=True),
            403: OpenApiResponse(description="Forbidden - Insufficient permissions"),
            500: OpenApiResponse(description="Internal Server Error")
        }
    )
    def get(self, request):
        """
        Handle GET request to list all users.

        Returns:
            Paginated list of users with profile data.
        """
        logger.info(f"User list requested by: {request.user.email}")

        try:
            # Get all users and prefetch related profile data for optimization
            queryset = User.objects.select_related('user_profile').all().order_by('-created_at')

            # Apply pagination
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(queryset, request, view=self)

            # Serialize the data
            serializer = self.serializer_class(paginated_queryset, many=True)

            logger.info(f"Successfully retrieved {len(serializer.data)} users for {request.user.email}")

            # Return paginated response
            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            logger.exception(f"Error retrieving user list: {str(e)}")
            return Response(
                {"error": "An error occurred while retrieving users."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmailVerificationView(APIView):
    """
    API View for Email Verification.

    Handles the verification of a user's email address using a one-time passcode (OTP).
    Upon successful verification, the user's account is marked as verified and the OTP
    is marked as used to prevent reuse.
    """
    permission_classes = [AllowAny]
    serializer_class = EmailVerificationSerializer

    @extend_schema(
        summary="Verify user email",
        description="Verify a user's email address using the OTP sent during registration.",
        request=EmailVerificationSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully"),
            400: OpenApiResponse(description="Bad Request - Invalid data or OTP"),
            404: OpenApiResponse(description="User not found"),
            410: OpenApiResponse(description="OTP expired"),
            500: OpenApiResponse(description="Internal Server Error")
        }
    )
    def post(self, request):
        """
        Handle POST request to verify user email.

        Steps:
        1. Validate input data (email and OTP).
        2. Verify OTP is valid, not expired, and not used.
        3. Mark user as verified.
        4. Mark OTP as used.
        5. Return success response.

        Args:
            request: HTTP request containing email and otp.

        Returns:
            Response: Success or error message with appropriate status code.
        """
        logger.info("Received email verification request")

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            try:
                # Extract validated data
                validated_data = serializer.validated_data
                user = validated_data['user']
                passcode = validated_data['passcode']

                logger.info(f"Processing email verification for user: {user.email}")

                # Use database transaction to ensure atomicity
                from django.db import transaction

                try:
                    with transaction.atomic():
                        # Mark the user as verified
                        user.is_verified = True
                        user.save(update_fields=['is_verified'])
                        logger.info(f"User {user.email} marked as verified")

                        # Mark the passcode as used
                        passcode.is_used = True
                        passcode.save(update_fields=['is_used'])
                        logger.info(f"Passcode marked as used for user {user.email}")

                except Exception as db_error:
                    logger.exception(f"Database error during verification: {str(db_error)}")
                    return Response(
                        {"error": "Failed to update verification status. Please try again."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                # Send success email notification (optional)
                try:
                    from utils.utils import send_normal_email

                    email_data = {
                        "to_email": user.email,
                        "email_subject": "Email Verification Successful",
                        "email_body": (
                            f"Hi {user.first_name},\n\n"
                            f"Your email has been successfully verified!\n\n"
                            f"You can now access all features of your AutoDocAI account.\n\n"
                            f"If you didn't perform this action, please contact our support team immediately.\n\n"
                            f"Best regards,\n"
                            f"AutoDocAI Team"
                        )
                    }
                    send_normal_email(email_data)
                    logger.info(f"Verification success email sent to {user.email}")
                except Exception as email_error:
                    # Log the error but don't fail the verification
                    logger.warning(f"Failed to send verification success email: {str(email_error)}")

                logger.info(f"Email verification completed successfully for {user.email}")

                return Response(
                    {
                        "message": "Your email has been verified successfully! You can now log in to your account.",
                        "data": {
                            "email": user.email,
                            "username": user.username,
                            "is_verified": user.is_verified,
                            "verified_at": user.updated_at
                        }
                    },
                    status=status.HTTP_200_OK
                )

            except KeyError as ke:
                logger.error(f"Missing key in validated data: {str(ke)}")
                return Response(
                    {"error": "Invalid verification data. Please try again."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            except Exception as e:
                logger.exception(f"Unexpected error during email verification: {str(e)}")
                return Response(
                    {"error": "An unexpected error occurred during verification. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Validation failed
        logger.warning(f"Email verification validation failed: {serializer.errors}")

        # Check for specific error types to return appropriate status codes
        errors = serializer.errors

        # If OTP expired
        if 'otp' in errors and any('expired' in str(err).lower() for err in errors['otp']):
            return Response(serializer.errors, status=status.HTTP_410_GONE)

        # If user not found
        if 'email' in errors and any('not found' in str(err).lower() for err in errors['email']):
            return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)

        # Default to bad request
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    """
    API View for Resending OTP.

    Handles requests to resend verification OTP to users who didn't receive
    the original code or whose code has expired.

    Rate Limiting Logic:
    - Checks if user has an active (unexpired and unused) OTP
    - If active OTP exists, returns error with remaining time
    - Only creates new OTP if old one is expired or used
    """
    permission_classes = [AllowAny]
    serializer_class = ResendOTPSerializer

    @extend_schema(
        summary="Resend verification OTP",
        description="Resend a verification OTP to the user's email address. A new OTP will only be sent if the previous one has expired or been used.",
        request=ResendOTPSerializer,
        responses={
            200: OpenApiResponse(description="OTP resent successfully"),
            400: OpenApiResponse(description="Bad Request - Invalid email or user already verified"),
            404: OpenApiResponse(description="User not found"),
            429: OpenApiResponse(description="Too Many Requests - Active OTP still valid"),
            500: OpenApiResponse(description="Internal Server Error")
        }
    )
    def post(self, request):
        """
        Handle POST request to resend OTP.

        Steps:
        1. Validate email address.
        2. Check if user exists and is not verified.
        3. Check if user has active (unexpired and unused) OTP.
        4. If active OTP exists, return error with remaining time.
        5. If OTP is expired or used, delete it and create new one.
        6. Send new OTP via email.
        7. Return success response.

        Args:
            request: HTTP request containing email.

        Returns:
            Response: Success or error message with appropriate status code.
        """
        logger.info("Received OTP resend request")

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            try:
                email = serializer.validated_data['email']
                logger.info(f"Processing OTP resend for email: {email}")

                # Get the user
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    logger.error(f"User not found for email: {email}")
                    return Response(
                        {"error": "User not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )

                # Check for existing OTP for this user and code_type
                from django.utils import timezone
                from authentication.models import Passcode

                try:
                    existing_otp = Passcode.objects.get(
                        user=user,
                        code_type=choices.CodeType.VERIFICATION,
                        is_used=False
                    )

                    # Check if OTP is still valid (not expired)
                    if existing_otp.expires_at > timezone.now():
                        # OTP is still active - don't create new one
                        remaining_time = existing_otp.expires_at - timezone.now()
                        total_seconds = int(remaining_time.total_seconds())
                        minutes_remaining = total_seconds // 60
                        seconds_remaining = total_seconds % 60

                        logger.warning(
                            f"Active OTP already exists for {email}. "
                            f"Expires in {minutes_remaining}m {seconds_remaining}s"
                        )

                        # Format time remaining message
                        if minutes_remaining > 0:
                            time_msg = f"{minutes_remaining} minute(s) and {seconds_remaining} second(s)"
                        else:
                            time_msg = f"{seconds_remaining} second(s)"

                        return Response(
                            {
                                "error": "An active verification code already exists.",
                                "message": f"Please use your existing verification code. It will expire in {time_msg}.",
                                "expires_in_seconds": total_seconds,
                                "expires_in_minutes": minutes_remaining
                            },
                            status=status.HTTP_429_TOO_MANY_REQUESTS
                        )
                    else:
                        # OTP exists but is expired - delete it
                        logger.info(f"Found expired OTP for {email}, deleting it")
                        existing_otp.delete()

                except Passcode.DoesNotExist:
                    # No existing OTP found, or it was used - proceed to create new one
                    logger.info(f"No active OTP found for {email}, will create new one")
                    pass

                # Create and send new OTP
                # Note: create_and_send_otp will delete any remaining OTPs (used ones)
                # and create a fresh one
                otp, error_msg, error_status = create_and_send_otp(
                    user=user,
                    code_type=choices.CodeType.VERIFICATION,
                    purpose="verification"
                )

                if error_msg:
                    logger.error(f"Failed to create/send OTP for {email}: {error_msg}")
                    return Response(
                        {"error": error_msg},
                        status=error_status
                    )

                logger.info(f"OTP successfully resent to {email}")

                return Response(
                    {
                        "message": "A new verification code has been sent to your email.",
                        "data": {
                            "email": email,
                            "expires_in": "10 minutes"
                        }
                    },
                    status=status.HTTP_200_OK
                )

            except Exception as e:
                logger.exception(f"Unexpected error during OTP resend: {str(e)}")
                return Response(
                    {"error": "An unexpected error occurred. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Validation failed
        logger.warning(f"OTP resend validation failed: {serializer.errors}")

        # Check for specific error types
        errors = serializer.errors

        # If user not found
        if 'email' in errors and any('not found' in str(err).lower() for err in errors['email']):
            return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)

        # Default to bad request
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class UserProfileManageView(APIView):
    """
    API View for managing user profile.

    Handles both creation and update of the user profile.
    - If profile exists: Updates it (Partial update).
    - If profile does not exist: Creates it.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    @extend_schema(
        summary="Create or Update user profile",
        description="Create a profile if it doesn't exist, or update the existing one (partial update).",
        request=ProfileSerializer,
        responses={
            200: OpenApiResponse(description="Profile updated successfully"),
            201: OpenApiResponse(description="Profile created successfully"),
            400: OpenApiResponse(description="Bad Request - Invalid data"),
            401: OpenApiResponse(description="Unauthorized"),
            500: OpenApiResponse(description="Internal Server Error")
        }
    )
    def post(self, request):
        """
        Handle POST request to create or update user profile.

        Steps:
        1. Check if user has a profile.
        2. If exists: Update (partial).
        3. If not: Create new.

        Args:
            request: HTTP request containing profile data.

        Returns:
            Response: Profile data and status code (200 or 201).
        """
        logger.info(f"Profile manage request by user: {request.user.email}")

        try:
            # Check if profile exists
            if hasattr(request.user, 'user_profile'):
                # Update existing profile
                profile = request.user.user_profile
                logger.info(f"Updating existing profile for user: {request.user.email}")

                serializer = self.serializer_class(instance=profile, data=request.data, partial=True)

                if serializer.is_valid():
                    serializer.save()
                    logger.info(f"Profile updated successfully for user: {request.user.email}")
                    return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # Create new profile
                logger.info(f"Creating new profile for user: {request.user.email}")

                serializer = self.serializer_class(data=request.data)

                if serializer.is_valid():
                    serializer.save(user=request.user)
                    logger.info(f"Profile created successfully for user: {request.user.email}")
                    return Response(serializer.data, status=status.HTTP_201_CREATED)

            # If validation failed
            logger.warning(f"Profile validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"Error managing profile for user {request.user.email}: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
