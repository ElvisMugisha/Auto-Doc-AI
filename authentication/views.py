from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import get_user_model

from authentication.serializers import UserRegistrationSerializer, UserListSerializer
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
