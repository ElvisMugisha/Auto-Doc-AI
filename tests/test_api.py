"""
API endpoint tests for documents app.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from documents.models import Document, ExtractionJob
from utils.choices import DocumentType


@pytest.mark.django_db
@pytest.mark.api
class TestDocumentAPI:
    """Tests for Document API endpoints."""

    def test_list_documents_unauthenticated(self, api_client):
        """Test listing documents without authentication fails."""
        url = reverse('document-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_documents_authenticated(self, authenticated_client, user, sample_pdf_file):
        """Test listing documents with authentication."""
        # Create a document
        Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf",
            document_type=DocumentType.INVOICE
        )

        url = reverse('document-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_upload_document(self, authenticated_client, sample_pdf_file):
        """Test uploading a document."""
        url = reverse('document-list')
        data = {
            'file': sample_pdf_file,
            'document_type': DocumentType.INVOICE
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert response.data['document_type'] == DocumentType.INVOICE

    def test_upload_document_without_file(self, authenticated_client):
        """Test uploading without file fails."""
        url = reverse('document-list')
        data = {'document_type': DocumentType.INVOICE}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_document(self, authenticated_client, user, sample_pdf_file):
        """Test retrieving a specific document."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        url = reverse('document-detail', kwargs={'pk': document.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(document.id)

    def test_delete_document(self, authenticated_client, user, sample_pdf_file):
        """Test deleting a document."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        url = reverse('document-detail', kwargs={'pk': document.id})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Document.objects.filter(id=document.id).exists()

    def test_user_can_only_see_own_documents(self, api_client, user, sample_pdf_file):
        """Test users can only see their own documents."""
        from django.contrib.auth import get_user_model
        from rest_framework.authtoken.models import Token

        User = get_user_model()

        # Create another user
        other_user = User.objects.create_user(
            email="other@example.com",
            username="otheruser",
            password="OtherPass123!",
            is_active=True,
            is_verified=True
        )

        # Create document for other user
        Document.objects.create(
            user=other_user,
            file=sample_pdf_file,
            original_filename="other.pdf",
            file_size=1024,
            file_format="pdf"
        )

        # Authenticate as first user
        token, _ = Token.objects.get_or_create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        url = reverse('document-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0  # Should not see other user's documents


@pytest.mark.django_db
@pytest.mark.api
class TestExtractionAPI:
    """Tests for Extraction API endpoints."""

    def test_trigger_extraction(self, authenticated_client, user, sample_pdf_file):
        """Test triggering document extraction."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf",
            document_type=DocumentType.INVOICE
        )

        url = reverse('document-extract', kwargs={'pk': document.id})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'job_id' in response.data

        # Verify job was created
        job_id = response.data['job_id']
        assert ExtractionJob.objects.filter(id=job_id).exists()

    def test_list_extraction_jobs(self, authenticated_client, user, sample_pdf_file):
        """Test listing extraction jobs."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        ExtractionJob.objects.create(document=document)

        url = reverse('extractionjob-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_get_extraction_results(self, authenticated_client, user, sample_pdf_file):
        """Test getting extraction results."""
        from documents.models import ExtractedData, ProcessingStatus

        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        job = ExtractionJob.objects.create(
            document=document,
            status=ProcessingStatus.COMPLETED
        )

        ExtractedData.objects.create(
            extraction_job=job,
            data={"total": 1000, "vendor": "ACME"},
            overall_confidence=0.95
        )

        url = reverse('extractionjob-results', kwargs={'pk': job.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'extracted_data' in response.data
        assert response.data['extracted_data']['data']['total'] == 1000


@pytest.mark.django_db
@pytest.mark.api
class TestAuthenticationAPI:
    """Tests for Authentication API endpoints."""

    def test_register_user(self, api_client):
        """Test user registration."""
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'NewPass123!',
            'first_name': 'New',
            'last_name': 'User'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'email' in response.data

    def test_login_user(self, api_client, user):
        """Test user login."""
        url = reverse('login')
        data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data

    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials."""
        url = reverse('login')
        data = {
            'email': 'wrong@example.com',
            'password': 'WrongPass123!'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
