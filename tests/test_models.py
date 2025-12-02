"""
Unit tests for Document models.
"""
import pytest
from django.contrib.auth import get_user_model
from documents.models import Document, ExtractionJob, ExtractedData
from utils.choices import DocumentType, ProcessingStatus

User = get_user_model()


@pytest.mark.django_db
class TestDocumentModel:
    """Tests for Document model."""

    def test_create_document(self, user, sample_pdf_file):
        """Test creating a document."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf",
            document_type=DocumentType.INVOICE
        )

        assert document.id is not None
        assert document.user == user
        assert document.original_filename == "test.pdf"
        assert document.file_size == 1024
        assert document.document_type == DocumentType.INVOICE

    def test_document_str_representation(self, user, sample_pdf_file):
        """Test document string representation."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="invoice.pdf",
            file_size=2048,
            file_format="pdf",
            document_type=DocumentType.INVOICE
        )

        assert str(document) == "invoice.pdf (invoice)"

    def test_file_size_mb_property(self, user, sample_pdf_file):
        """Test file_size_mb property."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=2097152,  # 2 MB in bytes
            file_format="pdf"
        )

        assert document.file_size_mb == 2.0

    def test_document_ordering(self, user, sample_pdf_file):
        """Test documents are ordered by upload date (newest first)."""
        doc1 = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="old.pdf",
            file_size=1024,
            file_format="pdf"
        )

        doc2 = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="new.pdf",
            file_size=1024,
            file_format="pdf"
        )

        documents = Document.objects.all()
        assert documents[0] == doc2  # Newest first
        assert documents[1] == doc1


@pytest.mark.django_db
class TestExtractionJobModel:
    """Tests for ExtractionJob model."""

    def test_create_extraction_job(self, user, sample_pdf_file):
        """Test creating an extraction job."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        job = ExtractionJob.objects.create(
            document=document,
            status=ProcessingStatus.PENDING
        )

        assert job.id is not None
        assert job.document == document
        assert job.status == ProcessingStatus.PENDING
        assert job.retry_count == 0

    def test_job_is_complete_property(self, user, sample_pdf_file):
        """Test is_complete property."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        # Pending job
        job = ExtractionJob.objects.create(
            document=document,
            status=ProcessingStatus.PENDING
        )
        assert not job.is_complete

        # Completed job
        job.status = ProcessingStatus.COMPLETED
        job.save()
        assert job.is_complete

        # Failed job
        job.status = ProcessingStatus.FAILED
        job.save()
        assert job.is_complete

    def test_job_str_representation(self, user, sample_pdf_file):
        """Test job string representation."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        job = ExtractionJob.objects.create(
            document=document,
            status=ProcessingStatus.PROCESSING
        )

        assert "processing" in str(job).lower()


@pytest.mark.django_db
class TestExtractedDataModel:
    """Tests for ExtractedData model."""

    def test_create_extracted_data(self, user, sample_pdf_file):
        """Test creating extracted data."""
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

        data = ExtractedData.objects.create(
            extraction_job=job,
            data={"total": 1000, "vendor": "ACME"},
            overall_confidence=0.95,
            field_confidence={"total": 0.98, "vendor": 0.92},
            extraction_method="openai_vision"
        )

        assert data.id is not None
        assert data.extraction_job == job
        assert data.data["total"] == 1000
        assert data.overall_confidence == 0.95

    def test_confidence_percentage_property(self, user, sample_pdf_file):
        """Test confidence_percentage property."""
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

        data = ExtractedData.objects.create(
            extraction_job=job,
            data={},
            overall_confidence=0.856
        )

        assert data.confidence_percentage == 85.6
