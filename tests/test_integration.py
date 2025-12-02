"""
Integration tests for document extraction workflow.
"""
import pytest
from unittest.mock import patch, MagicMock
from documents.tasks import process_document_task, calculate_confidence
from documents.models import Document, ExtractionJob, ExtractedData
from utils.choices import ProcessingStatus, DocumentType


@pytest.mark.django_db
@pytest.mark.integration
class TestExtractionWorkflow:
    """Integration tests for the complete extraction workflow."""

    @patch('documents.tasks.OpenAIExtractionService')
    def test_successful_extraction_with_openai(self, mock_openai_service, user, sample_pdf_file):
        """Test successful document extraction using OpenAI."""
        # Create document
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="invoice.pdf",
            file_size=1024,
            file_format="pdf",
            document_type=DocumentType.INVOICE
        )

        # Create extraction job
        job = ExtractionJob.objects.create(document=document)

        # Mock OpenAI response
        mock_service_instance = MagicMock()
        mock_service_instance.extract_universal_data.return_value = {
            'document_type': 'invoice',
            'total': 1000,
            'vendor': 'ACME Corp',
            'date': '2024-12-02'
        }
        mock_openai_service.return_value = mock_service_instance

        # Run task
        with patch('config.settings.USE_OPENAI', True):
            with patch('config.settings.OPENAI_API_KEY', 'test-key'):
                result = process_document_task(str(job.id))

        # Verify results
        assert result['status'] == 'success'

        # Refresh job from database
        job.refresh_from_database()
        assert job.status == ProcessingStatus.COMPLETED
        assert job.processing_time_seconds is not None

        # Verify extracted data
        extracted_data = ExtractedData.objects.get(extraction_job=job)
        assert extracted_data.data['total'] == 1000
        assert extracted_data.data['vendor'] == 'ACME Corp'

    @patch('documents.tasks.OCRService')
    @patch('documents.tasks.AIExtractionService')
    def test_fallback_to_local_extraction(self, mock_ai_service, mock_ocr_service, user, sample_pdf_file):
        """Test fallback to local OCR + Ollama when OpenAI fails."""
        # Create document
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="receipt.pdf",
            file_size=1024,
            file_format="pdf",
            document_type=DocumentType.RECEIPT
        )

        # Create extraction job
        job = ExtractionJob.objects.create(document=document)

        # Mock OCR response
        mock_ocr_instance = MagicMock()
        mock_ocr_instance.extract_text.return_value = {
            'text': 'Store: ACME\nTotal: $50.00\nDate: 2024-12-02',
            'method': 'tesseract',
            'pages': 1
        }
        mock_ocr_service.return_value = mock_ocr_instance

        # Mock AI response
        mock_ai_instance = MagicMock()
        mock_ai_instance.extract_data.return_value = {
            'store_name': 'ACME',
            'total': 50.00,
            'date': '2024-12-02'
        }
        mock_ai_service.return_value = mock_ai_instance

        # Run task (OpenAI disabled)
        with patch('config.settings.USE_OPENAI', False):
            result = process_document_task(str(job.id))

        # Verify results
        assert result['status'] == 'success'

        # Refresh job
        job.refresh_from_database()
        assert job.status == ProcessingStatus.COMPLETED

        # Verify extracted data
        extracted_data = ExtractedData.objects.get(extraction_job=job)
        assert extracted_data.data['store_name'] == 'ACME'
        assert extracted_data.extraction_method == 'ocr+ollama'

    def test_extraction_job_failure_handling(self, user, sample_pdf_file):
        """Test extraction job failure handling."""
        # Create document
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="bad.pdf",
            file_size=1024,
            file_format="pdf"
        )

        # Create extraction job
        job = ExtractionJob.objects.create(document=document)

        # Mock OCR to raise exception
        with patch('documents.tasks.OCRService') as mock_ocr:
            mock_ocr_instance = MagicMock()
            mock_ocr_instance.extract_text.side_effect = Exception("OCR failed")
            mock_ocr.return_value = mock_ocr_instance

            # Run task
            with patch('config.settings.USE_OPENAI', False):
                result = process_document_task(str(job.id))

        # Verify failure handling
        assert result['status'] == 'error'

        # Refresh job
        job.refresh_from_database()
        assert job.status == ProcessingStatus.FAILED
        assert job.error_message is not None
        assert 'OCR failed' in job.error_message


@pytest.mark.unit
class TestConfidenceCalculation:
    """Tests for confidence calculation functions."""

    def test_calculate_confidence_all_fields_filled(self):
        """Test confidence calculation with all fields filled."""
        data = {
            'total': 1000,
            'vendor': 'ACME',
            'date': '2024-12-02',
            'items': [{'name': 'Item 1', 'price': 500}]
        }

        confidence = calculate_confidence(data, "Some OCR text here")

        assert confidence > 0.7  # Should be high confidence
        assert confidence <= 1.0

    def test_calculate_confidence_partial_fields(self):
        """Test confidence calculation with partial fields."""
        data = {
            'total': 1000,
            'vendor': None,
            'date': '2024-12-02',
            'items': []
        }

        confidence = calculate_confidence(data, "Some text")

        assert 0.3 < confidence < 0.8  # Medium confidence

    def test_calculate_confidence_empty_data(self):
        """Test confidence calculation with empty data."""
        data = {}

        confidence = calculate_confidence(data, "")

        assert confidence >= 0.0
        assert confidence <= 1.0

    def test_calculate_confidence_with_metadata(self):
        """Test that metadata fields are ignored in confidence calculation."""
        data = {
            'total': 1000,
            '_metadata': {'method': 'openai'},
            '_internal': 'value'
        }

        confidence = calculate_confidence(data, "")

        # Should only consider 'total', not metadata fields
        assert confidence > 0.5


@pytest.mark.django_db
@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end tests for complete user workflows."""

    def test_complete_document_processing_workflow(self, authenticated_client, user, sample_pdf_file):
        """Test complete workflow from upload to extraction results."""
        from django.urls import reverse

        # Step 1: Upload document
        upload_url = reverse('document-list')
        upload_data = {
            'file': sample_pdf_file,
            'document_type': DocumentType.INVOICE
        }

        upload_response = authenticated_client.post(upload_url, upload_data, format='multipart')
        assert upload_response.status_code == 201
        document_id = upload_response.data['id']

        # Step 2: Trigger extraction
        extract_url = reverse('document-extract', kwargs={'pk': document_id})

        with patch('documents.tasks.process_document_task.delay') as mock_task:
            mock_task.return_value = MagicMock(id='task-123')
            extract_response = authenticated_client.post(extract_url)

        assert extract_response.status_code == 201
        assert 'job_id' in extract_response.data

        # Step 3: Check job status
        job_id = extract_response.data['job_id']
        status_url = reverse('extractionjob-detail', kwargs={'pk': job_id})
        status_response = authenticated_client.get(status_url)

        assert status_response.status_code == 200
        assert 'status' in status_response.data
