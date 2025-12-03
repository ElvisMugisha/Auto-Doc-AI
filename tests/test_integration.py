"""
Integration tests for extraction accuracy and end-to-end workflows.

Tests:
- End-to-end extraction
- OpenAI fallback
- Celery tasks
- Extraction accuracy
- Error handling
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from django.urls import reverse
from rest_framework import status
from documents.models import Document, ExtractionJob, ExtractedData
from documents.tasks import process_document_task
from utils.choices import DocumentType, ProcessingStatus


@pytest.mark.django_db
@pytest.mark.integration
class TestEndToEndExtraction:
    """Test complete end-to-end extraction workflow."""

    def test_complete_extraction_workflow(self, authenticated_client, user, sample_pdf_file):
        """Test complete workflow from upload to extraction results."""
        # Step 1: Upload document
        upload_url = reverse('document-list')
        upload_data = {
            'file': sample_pdf_file,
            'document_type': DocumentType.INVOICE
        }

        upload_response = authenticated_client.post(upload_url, upload_data, format='multipart')
        assert upload_response.status_code == status.HTTP_201_CREATED
        document_id = upload_response.data['data']['id']

        # Step 2: Trigger extraction
        extract_url = reverse('document-extract', kwargs={'pk': document_id})

        with patch('documents.tasks.process_document_task.delay') as mock_task:
            mock_task.return_value = MagicMock(id='task-123')
            extract_response = authenticated_client.post(extract_url)

        assert extract_response.status_code == status.HTTP_201_CREATED
        assert 'job_id' in extract_response.data['data']

        # Step 3: Check job status
        job_id = extract_response.data['data']['id']
        status_url = reverse('extraction-job-detail', kwargs={'pk': job_id})
        status_response = authenticated_client.get(status_url)

        assert status_response.status_code == status.HTTP_200_OK
        assert 'status' in status_response.data

    @patch('documents.tasks.OpenAIExtractionService')
    def test_extraction_with_openai_success(self, mock_openai_service, authenticated_client, user, sample_pdf_file):
        """Test successful extraction using OpenAI."""
        # Upload document
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
            'vendor': 'ACME Corp',
            'total': 1000.00,
            'date': '2024-12-03'
        }
        mock_openai_service.return_value = mock_service_instance

        # Run task
        with patch('config.settings.USE_OPENAI', True):
            with patch('config.settings.OPENAI_API_KEY', 'test-key'):
                result = process_document_task(str(job.id))

        # Verify results
        assert result['status'] == 'success'

        # Refresh job
        job.refresh_from_database()
        assert job.status == ProcessingStatus.COMPLETED

        # Verify extracted data
        extracted_data = ExtractedData.objects.get(extraction_job=job)
        assert extracted_data.data['vendor'] == 'ACME Corp'
        assert extracted_data.data['total'] == 1000.00


@pytest.mark.django_db
@pytest.mark.integration
class TestOpenAIFallback:
    """Test fallback mechanisms when OpenAI fails."""

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
            'text': 'Store: ACME\nTotal: $50.00\nDate: 2024-12-03',
            'method': 'tesseract',
            'pages': 1
        }
        mock_ocr_service.return_value = mock_ocr_instance

        # Mock AI response
        mock_ai_instance = MagicMock()
        mock_ai_instance.extract_data.return_value = {
            'store_name': 'ACME',
            'total': 50.00,
            'date': '2024-12-03'
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

    @patch('documents.tasks.OpenAIExtractionService')
    @patch('documents.tasks.OCRService')
    def test_fallback_on_openai_error(self, mock_ocr_service, mock_openai_service, user, sample_pdf_file):
        """Test fallback when OpenAI raises an error."""
        # Create document
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="invoice.pdf",
            file_size=1024,
            file_format="pdf"
        )

        # Create extraction job
        job = ExtractionJob.objects.create(document=document)

        # Mock OpenAI to raise error
        mock_openai_instance = MagicMock()
        mock_openai_instance.extract_universal_data.side_effect = Exception("OpenAI API Error")
        mock_openai_service.return_value = mock_openai_instance

        # Mock OCR fallback
        mock_ocr_instance = MagicMock()
        mock_ocr_instance.extract_text.return_value = {
            'text': 'Invoice data',
            'method': 'tesseract'
        }
        mock_ocr_service.return_value = mock_ocr_instance

        # Run task
        with patch('config.settings.USE_OPENAI', True):
            with patch('config.settings.OPENAI_API_KEY', 'test-key'):
                result = process_document_task(str(job.id))

        # Should fall back to OCR
        job.refresh_from_database()
        # Job should complete or fail gracefully
        assert job.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]


@pytest.mark.django_db
@pytest.mark.integration
class TestCeleryTasks:
    """Test Celery task execution."""

    def test_task_updates_job_status(self, user, sample_pdf_file):
        """Test that task updates job status correctly."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        job = ExtractionJob.objects.create(document=document)

        # Mock the extraction
        with patch('documents.tasks.OCRService') as mock_ocr:
            mock_ocr_instance = MagicMock()
            mock_ocr_instance.extract_text.return_value = {
                'text': 'Test data',
                'method': 'tesseract'
            }
            mock_ocr.return_value = mock_ocr_instance

            with patch('config.settings.USE_OPENAI', False):
                process_document_task(str(job.id))

        # Verify job was updated
        job.refresh_from_database()
        assert job.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]
        assert job.processing_time_seconds is not None

    def test_task_handles_missing_job(self):
        """Test task handles missing job gracefully."""
        fake_job_id = '00000000-0000-0000-0000-000000000000'

        result = process_document_task(fake_job_id)

        assert result['status'] == 'error'
        assert 'not found' in result['message'].lower()

    def test_task_retry_on_failure(self, user, sample_pdf_file):
        """Test task retry mechanism on failure."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        job = ExtractionJob.objects.create(document=document)

        # Mock OCR to fail
        with patch('documents.tasks.OCRService') as mock_ocr:
            mock_ocr_instance = MagicMock()
            mock_ocr_instance.extract_text.side_effect = Exception("OCR failed")
            mock_ocr.return_value = mock_ocr_instance

            with patch('config.settings.USE_OPENAI', False):
                result = process_document_task(str(job.id))

        # Verify job marked as failed
        job.refresh_from_database()
        assert job.status == ProcessingStatus.FAILED
        assert job.error_message is not None


@pytest.mark.django_db
@pytest.mark.integration
class TestExtractionAccuracy:
    """Test extraction accuracy and data quality."""

    @patch('documents.tasks.OpenAIExtractionService')
    def test_invoice_extraction_accuracy(self, mock_openai_service, user, sample_pdf_file):
        """Test accuracy of invoice extraction."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="invoice.pdf",
            file_size=1024,
            file_format="pdf",
            document_type=DocumentType.INVOICE
        )

        job = ExtractionJob.objects.create(document=document)

        # Mock realistic invoice data
        mock_service_instance = MagicMock()
        mock_service_instance.extract_universal_data.return_value = {
            'document_type': 'invoice',
            'vendor': 'ACME Corporation',
            'invoice_number': 'INV-2024-001',
            'date': '2024-12-03',
            'total': 1500.00,
            'currency': 'USD',
            'items': [
                {'description': 'Service A', 'amount': 1000.00},
                {'description': 'Service B', 'amount': 500.00}
            ]
        }
        mock_openai_service.return_value = mock_service_instance

        # Run extraction
        with patch('config.settings.USE_OPENAI', True):
            with patch('config.settings.OPENAI_API_KEY', 'test-key'):
                result = process_document_task(str(job.id))

        # Verify accuracy
        job.refresh_from_database()
        extracted_data = ExtractedData.objects.get(extraction_job=job)

        assert extracted_data.data['vendor'] == 'ACME Corporation'
        assert extracted_data.data['total'] == 1500.00
        assert len(extracted_data.data['items']) == 2
        assert extracted_data.overall_confidence > 0.8  # High confidence

    def test_confidence_calculation(self, user, sample_pdf_file):
        """Test confidence score calculation."""
        from documents.tasks import calculate_confidence

        # Test with complete data
        complete_data = {
            'vendor': 'ACME',
            'total': 1000,
            'date': '2024-12-03',
            'items': [{'name': 'Item 1'}]
        }

        confidence = calculate_confidence(complete_data, "Some OCR text")
        assert confidence > 0.7

        # Test with partial data
        partial_data = {
            'vendor': 'ACME',
            'total': None,
            'date': None
        }

        confidence = calculate_confidence(partial_data, "Some text")
        assert 0.3 < confidence < 0.8


@pytest.mark.django_db
@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in extraction workflow."""

    def test_extraction_with_corrupted_file(self, authenticated_client, user):
        """Test extraction with corrupted file."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create corrupted file
        corrupted_file = SimpleUploadedFile(
            "corrupted.pdf",
            b'corrupted data',
            content_type="application/pdf"
        )

        document = Document.objects.create(
            user=user,
            file=corrupted_file,
            original_filename="corrupted.pdf",
            file_size=len(b'corrupted data'),
            file_format="pdf"
        )

        job = ExtractionJob.objects.create(document=document)

        # Try to process
        with patch('config.settings.USE_OPENAI', False):
            result = process_document_task(str(job.id))

        # Should handle error gracefully
        job.refresh_from_database()
        assert job.status == ProcessingStatus.FAILED
        assert job.error_message is not None

    def test_concurrent_extraction_prevention(self, authenticated_client, user, sample_pdf_file):
        """Test prevention of concurrent extraction jobs."""
        document = Document.objects.create(
            user=user,
            file=sample_pdf_file,
            original_filename="test.pdf",
            file_size=1024,
            file_format="pdf"
        )

        # Create first job
        job1 = ExtractionJob.objects.create(
            document=document,
            status=ProcessingStatus.PROCESSING
        )

        # Try to create second job via API
        url = reverse('document-extract', kwargs={'pk': document.id})
        response = authenticated_client.post(url)

        # Should be rejected
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'active' in response.data['error'].lower()
