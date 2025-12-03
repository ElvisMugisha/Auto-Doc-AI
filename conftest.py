import pytest
from io import BytesIO
from reportlab.pdfgen import canvas
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from PIL import Image


User = get_user_model()


@pytest.fixture
def api_client():
    """
    Fixture for DRF API client.
    """
    return APIClient()


@pytest.fixture
def user(db):
    """
    Fixture for creating a test user.
    """
    user = User.objects.create_user(
        email="testuser@example.com",
        password="TestPass123!",
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def authenticated_client(api_client, user):
    """
    Fixture for authenticated API client.
    """
    token, _ = Token.objects.get_or_create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client


@pytest.fixture
def admin_user(db):
    """
    Fixture for creating an admin user.
    """
    admin = User.objects.create_superuser(
        email="admin@example.com",
        password="AdminPass123!",
        first_name="Admin",
        last_name="User"
    )
    return admin


@pytest.fixture
def sample_pdf_file():
    """
    Fixture for creating a sample PDF file for testing.
    """
    # Create a simple PDF in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 750, "Test Invoice")
    p.drawString(100, 730, "Company: ACME Corp")
    p.drawString(100, 710, "Total: $1000.00")
    p.drawString(100, 690, "Date: 2024-12-02")
    p.showPage()
    p.save()

    buffer.seek(0)
    pdf_file = SimpleUploadedFile(
        "test_invoice.pdf",
        buffer.read(),
        content_type="application/pdf"
    )
    return pdf_file


@pytest.fixture
def sample_image_file():
    """
    Fixture for creating a sample image file for testing.
    """

    # Create a simple image
    image = Image.new('RGB', (100, 100), color='white')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)

    image_file = SimpleUploadedFile(
        "test_receipt.png",
        buffer.read(),
        content_type="image/png"
    )
    return image_file
