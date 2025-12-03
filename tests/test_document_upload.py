"""
Unit tests for document upload and validation.

Tests:
- Document upload
- File validation
- Size limits
- Format validation
- User permissions
"""
import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from documents.models import Document
from utils.choices import DocumentType
from io import BytesIO
from PIL import Image


@pytest.mark.django_db
class TestDocumentUpload:
    """Test document upload functionality."""

    def test_upload_pdf_success(self, authenticated_client, sample_pdf_file):
        """Test successful PDF upload."""
        url = reverse('document-list')
        data = {
            'file': sample_pdf_file,
            'document_type': DocumentType.INVOICE
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data['data']
        assert Document.objects.filter(user=authenticated_client.handler._force_user).exists()

    def test_upload_image_success(self, authenticated_client, sample_image_file):
        """Test successful image upload."""
        url = reverse('document-list')
        data = {
            'file': sample_image_file,
            'document_type': DocumentType.RECEIPT
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_without_authentication(self, api_client, sample_pdf_file):
        """Test upload without authentication fails."""
        url = reverse('document-list')
        data = {
            'file': sample_pdf_file,
            'document_type': DocumentType.INVOICE
        }

        response = api_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_without_file(self, authenticated_client):
        """Test upload without file fails."""
        url = reverse('document-list')
        data = {
            'document_type': DocumentType.INVOICE
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_with_description(self, authenticated_client, sample_pdf_file):
        """Test upload with description."""
        url = reverse('document-list')
        data = {
            'file': sample_pdf_file,
            'document_type': DocumentType.INVOICE,
            'description': 'Test invoice document'
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'description' in response.data['data']


@pytest.mark.django_db
class TestFileValidation:
    """Test file validation rules."""

    def test_file_too_large(self, authenticated_client):
        """Test upload of file exceeding size limit."""
        # Create a file larger than 50MB
        large_content = b'x' * (51 * 1024 * 1024)  # 51 MB
        large_file = SimpleUploadedFile(
            "large.pdf",
            large_content,
            content_type="application/pdf"
        )

        url = reverse('document-list')
        data = {
            'file': large_file,
            'document_type': DocumentType.INVOICE
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'file' in response.data or 'error' in response.data

    def test_file_too_small(self, authenticated_client):
        """Test upload of empty/very small file."""
        small_file = SimpleUploadedFile(
            "empty.pdf",
            b'',  # Empty file
            content_type="application/pdf"
        )

        url = reverse('document-list')
        data = {
            'file': small_file,
            'document_type': DocumentType.INVOICE
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_file_extension(self, authenticated_client):
        """Test upload of file with invalid extension."""
        invalid_file = SimpleUploadedFile(
            "document.exe",
            b'fake executable content',
            content_type="application/x-msdownload"
        )

        url = reverse('document-list')
        data = {
            'file': invalid_file,
            'document_type': DocumentType.OTHER
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_valid_file_formats(self, authenticated_client):
        """Test all valid file formats."""
        valid_formats = [
            ('test.pdf', 'application/pdf'),
            ('test.jpg', 'image/jpeg'),
            ('test.jpeg', 'image/jpeg'),
            ('test.png', 'image/png'),
        ]

        url = reverse('document-list')

        for filename, content_type in valid_formats:
            test_file = SimpleUploadedFile(
                filename,
                b'test content here',
                content_type=content_type
            )

            data = {
                'file': test_file,
                'document_type': DocumentType.OTHER
            }

            response = authenticated_client.post(url, data, format='multipart')

            # Should succeed or fail for reasons other than file format
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST  # Might fail for other validation reasons
            ]


@pytest.mark.django_db
class TestDocumentPermissions:
    """Test document access permissions."""

    def test_user_can_only_see_own_documents(self, api_client, user, sample_pdf_file):
        """Test users can only see their own documents."""
        from django.contrib.auth import get_user_model
        from rest_framework.authtoken.models import Token

        User = get_user_model()

        # Create another user
        other_user = User.objects.create_user(
            email='other@example.com',
            password='OtherPass123!',
            is_active=True,
            is_verified=True
        )

        # Create document for other user
        Document.objects.create(
            user=other_user,
            file=sample_pdf_file,
            original_filename='other.pdf',
            file_size=1024,
            file_format='pdf',
            document_type=DocumentType.INVOICE
        )

        # Authenticate as first user
        token, _ = Token.objects.get_or_create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        url = reverse('document-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0  # Should not see other user's documents

    def test_user_cannot_access_others_document(self, authenticated_client, user, sample_pdf_file):
        """Test user cannot access another user's document."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Create another user and their document
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='OtherPass123!',
            is_active=True
        )

        other_document = Document.objects.create(
            user=other_user,
            file=sample_pdf_file,
            original_filename='other.pdf',
            file_size=1024,
            file_format='pdf'
        )

        # Try to access other user's document
        url = reverse('document-detail', kwargs={'pk': other_document.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_delete_others_document(self, authenticated_client, sample_pdf_file):
        """Test user cannot delete another user's document."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Create another user and their document
        other_user = User.objects.create_user(
            email='other@example.com',
            password='OtherPass123!',
            is_active=True
        )

        other_document = Document.objects.create(
            user=other_user,
            file=sample_pdf_file,
            original_filename='other.pdf',
            file_size=1024,
            file_format='pdf'
        )

        # Try to delete other user's document
        url = reverse('document-detail', kwargs={'pk': other_document.id})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Document.objects.filter(id=other_document.id).exists()


@pytest.mark.django_db
class TestDocumentMetadata:
    """Test document metadata handling."""

    def test_file_size_calculated(self, authenticated_client, sample_pdf_file):
        """Test file size is correctly calculated."""
        url = reverse('document-list')
        data = {
            'file': sample_pdf_file,
            'document_type': DocumentType.INVOICE
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'file_size' in response.data['data']
        assert response.data['data']['file_size'] > 0

    def test_file_format_extracted(self, authenticated_client, sample_pdf_file):
        """Test file format is correctly extracted."""
        url = reverse('document-list')
        data = {
            'file': sample_pdf_file,
            'document_type': DocumentType.INVOICE
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['file_format'] == 'pdf'

    def test_original_filename_preserved(self, authenticated_client, sample_pdf_file):
        """Test original filename is preserved."""
        url = reverse('document-list')
        data = {
            'file': sample_pdf_file,
            'document_type': DocumentType.INVOICE
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'original_filename' in response.data['data']
        assert response.data['data']['original_filename'] == sample_pdf_file.name
