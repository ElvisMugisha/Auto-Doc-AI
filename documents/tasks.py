"""
Celery tasks for async document processing.
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import ExtractionJob, ExtractedData, ProcessingStatus
from .services import OCRService, AIExtractionService
from utils import loggings

logger = loggings.setup_logging()


@shared_task(bind=True, max_retries=3)
def process_document_task(self, job_id: str):
    """
    Async task to process a document and extract data.

    Args:
        job_id: UUID of the ExtractionJob

    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Starting document processing task for job: {job_id}")

        # Get the extraction job
        try:
            job = ExtractionJob.objects.select_related('document').get(id=job_id)
        except ExtractionJob.DoesNotExist:
            logger.error(f"ExtractionJob {job_id} not found")
            return {'status': 'error', 'message': 'Job not found'}

        # Update job status to processing
        job.status = ProcessingStatus.PROCESSING
        job.started_at = timezone.now()
        job.save(update_fields=['status', 'started_at'])

        logger.info(f"Processing document: {job.document.original_filename}")

        # Initialize services
        ocr_service = OCRService(tesseract_cmd=settings.TESSERACT_CMD)
        ai_service = AIExtractionService(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL
        )

        # Step 1: Extract text using OCR
        logger.info("Step 1: Extracting text with OCR")
        file_path = job.document.file.path
        ocr_result = ocr_service.extract_text(file_path)

        extracted_text = ocr_result['text']
        logger.info(f"Extracted {len(extracted_text)} characters using {ocr_result['method']}")
        logger.info(f"=== OCR EXTRACTED TEXT (First 500 chars) ===")
        logger.info(extracted_text[:500])
        logger.info(f"=== END OCR TEXT ===")

        if not extracted_text or len(extracted_text) < 10:
            raise ValueError("No text could be extracted from document")

        # Step 2: Extract structured data using AI
        logger.info("Step 2: Extracting structured data with AI")
        document_type = job.document.document_type
        structured_data = ai_service.extract_data(extracted_text, document_type)

        # Add metadata
        structured_data['_metadata'] = {
            'ocr_method': ocr_result['method'],
            'pages': ocr_result.get('pages', 1),
            'text_length': len(extracted_text),
            'document_type': document_type,
        }

        # Step 3: Calculate confidence score
        confidence = calculate_confidence(structured_data, extracted_text)

        # Step 4: Save extracted data
        logger.info("Step 3: Saving extracted data")
        extracted_data = ExtractedData.objects.create(
            extraction_job=job,
            data=structured_data,
            overall_confidence=confidence,
            field_confidence=calculate_field_confidence(structured_data),
            extraction_method='ocr+ai'
        )

        # Update job status to completed
        job.status = ProcessingStatus.COMPLETED
        job.completed_at = timezone.now()
        job.processing_time_seconds = (job.completed_at - job.started_at).total_seconds()
        job.save(update_fields=['status', 'completed_at', 'processing_time_seconds'])

        logger.info(f"Document processing completed successfully for job: {job_id}")

        return {
            'status': 'success',
            'job_id': str(job_id),
            'confidence': confidence,
            'processing_time': job.processing_time_seconds
        }

    except Exception as e:
        logger.exception(f"Error processing document for job {job_id}: {str(e)}")

        # Update job status to failed
        try:
            job = ExtractionJob.objects.get(id=job_id)
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.retry_count += 1
            job.save(update_fields=['status', 'error_message', 'completed_at', 'retry_count'])
        except Exception as save_error:
            logger.error(f"Failed to update job status: {str(save_error)}")

        # Retry if not exceeded max retries
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

        return {
            'status': 'error',
            'job_id': str(job_id),
            'error': str(e)
        }


def calculate_confidence(data: dict, text: str) -> float:
    """
    Calculate overall confidence score for extracted data.

    Args:
        data: Extracted structured data
        text: Original OCR text

    Returns:
        Confidence score between 0 and 1
    """
    # Simple confidence calculation based on data completeness
    total_fields = 0
    filled_fields = 0

    for key, value in data.items():
        if key.startswith('_'):  # Skip metadata fields
            continue

        total_fields += 1

        if value and value != 'Unknown' and value != 'N/A' and value != []:
            filled_fields += 1

    if total_fields == 0:
        return 0.0

    # Base confidence on field completion
    base_confidence = filled_fields / total_fields

    # Adjust based on text length (more text = potentially more accurate)
    text_factor = min(len(text) / 1000, 1.0)  # Cap at 1.0

    # Combine factors
    confidence = (base_confidence * 0.7) + (text_factor * 0.3)

    return round(confidence, 2)


def calculate_field_confidence(data: dict) -> dict:
    """
    Calculate confidence scores for individual fields.

    Args:
        data: Extracted structured data

    Returns:
        Dictionary of field confidence scores
    """
    field_confidence = {}

    for key, value in data.items():
        if key.startswith('_'):  # Skip metadata
            continue

        # Simple heuristic: filled fields get higher confidence
        if value and value != 'Unknown' and value != 'N/A' and value != []:
            if isinstance(value, (int, float)):
                field_confidence[key] = 0.9
            elif isinstance(value, str) and len(value) > 3:
                field_confidence[key] = 0.85
            elif isinstance(value, list) and len(value) > 0:
                field_confidence[key] = 0.8
            else:
                field_confidence[key] = 0.7
        else:
            field_confidence[key] = 0.3

    return field_confidence
