"""
Celery tasks for async document processing with universal extraction.

This module handles background processing of documents using either:
1. OpenAI Vision (universal extraction for ANY document type)
2. Local OCR + Ollama (fallback method)
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
    Async task to process ANY document and extract ALL information.

    This task uses intelligent extraction that works with any document type:
    - Invoices, receipts, contracts
    - ID cards, passports, licenses
    - Forms, applications, certificates
    - Letters, reports, statements
    - And ANY other document type!

    Args:
        job_id: UUID of the ExtractionJob

    Returns:
        Dictionary with processing results including:
            - status: 'success' or 'error'
            - job_id: Job identifier
            - confidence: Extraction confidence score
            - processing_time: Time taken in seconds
    """
    try:
        logger.info("="  * 100)
        logger.info(f"DOCUMENT PROCESSING TASK STARTED - Job ID: {job_id}")
        logger.info("=" * 100)

        # Get the extraction job
        try:
            job = ExtractionJob.objects.select_related('document').get(id=job_id)
            logger.info(f"Job found: {job.id}")
            logger.info(f"Document: {job.document.original_filename}")
            logger.info(f"User: {job.document.user.email}")
        except ExtractionJob.DoesNotExist:
            logger.error(f"ExtractionJob {job_id} not found in database")
            return {'status': 'error', 'message': 'Job not found'}

        # Update job status to processing
        job.status = ProcessingStatus.PROCESSING
        job.started_at = timezone.now()
        job.save(update_fields=['status', 'started_at'])
        logger.info(f"Job status updated to PROCESSING at {job.started_at}")

        # Get document details
        document_type = job.document.document_type
        file_path = job.document.file.path
        file_format = job.document.file_format

        logger.info(f"Document Type: {document_type}")
        logger.info(f"File Format: {file_format}")
        logger.info(f"File Path: {file_path}")

        # Check if OpenAI is enabled
        use_openai = settings.USE_OPENAI and settings.OPENAI_API_KEY
        logger.info(f"OpenAI Enabled: {use_openai}")

        extraction_successful = False
        structured_data = {}
        extraction_method = 'unknown'
        confidence = 0.0

        # OpenAI Vision (Universal Extraction) - Works with ANY document!
        if use_openai:
            try:
                logger.info("=" * 100)
                logger.info("ATTEMPTING UNIVERSAL EXTRACTION WITH OPENAI VISION")
                logger.info("=" * 100)

                # Import OpenAI service
                from .services import OpenAIExtractionService

                # Initialize OpenAI service
                logger.info(f"Initializing OpenAI service (model: {settings.OPENAI_MODEL})")
                openai_service = OpenAIExtractionService(
                    api_key=settings.OPENAI_API_KEY,
                    model=settings.OPENAI_MODEL
                )

                # Universal extraction - analyzes ANY document type automatically
                logger.info("Starting universal document analysis...")
                structured_data = openai_service.extract_universal_data(
                    file_path=file_path,
                    document_type=document_type  # Optional hint
                )

                logger.info("Universal extraction completed")
                logger.info(f"Extracted data contains {len(structured_data)} top-level keys")
                logger.debug(f"Keys: {list(structured_data.keys())}")

                # Check if extraction was successful
                if structured_data.get('extraction_status') != 'failed':
                    extraction_method = 'openai_vision_universal'

                    # Ensure metadata exists
                    if '_metadata' not in structured_data:
                        structured_data['_metadata'] = {}

                    # Add processing metadata
                    structured_data['_metadata'].update({
                        'extraction_method': 'openai_vision_universal',
                        'model': settings.OPENAI_MODEL,
                        'document_type_hint': document_type,
                        'detected_type': structured_data.get('document_type', 'unknown'),
                        'file_format': file_format,
                        'processing_timestamp': timezone.now().isoformat(),
                        'processor': 'openai_gpt4_vision'
                    })

                    # Calculate confidence
                    confidence = calculate_confidence(structured_data, "")
                    extraction_successful = True

                    logger.info("=" * 100)
                    logger.info("✓ OPENAI VISION EXTRACTION SUCCESSFUL")
                    logger.info(f"✓ Detected Document Type: {structured_data.get('document_type', 'unknown')}")
                    logger.info(f"✓ Extraction Confidence: {confidence * 100}%")
                    logger.info(f"✓ Method: {extraction_method}")
                    logger.info("=" * 100)
                else:
                    error_msg = structured_data.get('error', 'Unknown error')
                    logger.warning("=" * 100)
                    logger.warning("⚠ OpenAI returned failed status")
                    logger.warning(f"⚠ Error: {error_msg}")
                    logger.warning("⚠ Falling back to local OCR + Ollama processing")
                    logger.warning("=" * 100)

            except Exception as e:
                logger.error("=" * 100)
                logger.error("✗ OPENAI VISION EXTRACTION FAILED")
                logger.error(f"✗ Error Type: {type(e).__name__}")
                logger.error(f"✗ Error Message: {str(e)}")
                logger.error("=" * 100)
                logger.exception("Full error traceback:")
                logger.info("Falling back to local OCR + Ollama processing...")

        # Local OCR + Ollama (Fallback or Primary Method)
        if not extraction_successful:
            logger.info("=" * 100)
            logger.info("STARTING LOCAL EXTRACTION (OCR + OLLAMA)")
            logger.info("=" * 100)

            try:
                # Initialize services
                logger.info("Initializing OCR service...")
                ocr_service = OCRService(tesseract_cmd=settings.TESSERACT_CMD)

                logger.info("Initializing Ollama AI service...")
                ai_service = AIExtractionService(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL
                )

                # Step 1: Extract text using OCR
                logger.info("Step 1/2: Extracting text with Tesseract OCR...")
                ocr_result = ocr_service.extract_text(file_path)

                extracted_text = ocr_result['text']
                logger.info(f"✓ Extracted {len(extracted_text)} characters")
                logger.info(f"✓ OCR Method: {ocr_result['method']}")
                logger.info(f"✓ Pages: {ocr_result.get('pages', 1)}")

                logger.info("--- OCR EXTRACTED TEXT (First 500 chars) ---")
                logger.info(extracted_text[:500])
                logger.info("--- END OCR TEXT ---")

                if not extracted_text or len(extracted_text) < 10:
                    raise ValueError("Insufficient text extracted from document (less than 10 characters)")

                # Step 2: Extract structured data using Ollama AI
                logger.info("Step 2/2: Extracting structured data with Ollama AI...")
                structured_data = ai_service.extract_data(extracted_text, document_type)

                # Add metadata
                structured_data['_metadata'] = {
                    'ocr_method': ocr_result['method'],
                    'pages': ocr_result.get('pages', 1),
                    'text_length': len(extracted_text),
                    'document_type': document_type,
                    'extraction_method': 'ocr+ollama',
                    'file_format': file_format,
                    'processing_timestamp': timezone.now().isoformat(),
                    'processor': 'tesseract+ollama'
                }

                extraction_method = 'ocr+ollama'
                confidence = calculate_confidence(structured_data, extracted_text)

                logger.info("=" * 100)
                logger.info("✓ LOCAL EXTRACTION COMPLETED")
                logger.info(f"✓ Extraction Confidence: {confidence * 100}%")
                logger.info(f"✓ Method: {extraction_method}")
                logger.info("=" * 100)

            except Exception as e:
                logger.error("=" * 100)
                logger.error("✗ LOCAL EXTRACTION FAILED")
                logger.error(f"✗ Error: {str(e)}")
                logger.error("=" * 100)
                raise  # Re-raise to trigger job failure

        # Save extracted data to database
        logger.info("Saving extracted data to database...")
        extracted_data_obj = ExtractedData.objects.create(
            extraction_job=job,
            data=structured_data,
            overall_confidence=confidence,
            field_confidence=calculate_field_confidence(structured_data),
            extraction_method=extraction_method
        )
        logger.info(f"✓ ExtractedData created with ID: {extracted_data_obj.id}")

        # Update job status to completed
        job.status = ProcessingStatus.COMPLETED
        job.completed_at = timezone.now()
        job.processing_time_seconds = (job.completed_at - job.started_at).total_seconds()
        job.save(update_fields=['status', 'completed_at', 'processing_time_seconds'])

        logger.info("=" * 100)
        logger.info(f"✓✓✓ DOCUMENT PROCESSING COMPLETED SUCCESSFULLY ✓✓✓")
        logger.info(f"✓ Job ID: {job_id}")
        logger.info(f"✓ Processing Time: {job.processing_time_seconds:.2f} seconds")
        logger.info(f"✓ Confidence: {confidence * 100:.1f}%")
        logger.info(f"✓ Method: {extraction_method}")
        logger.info("=" * 100)

        return {
            'status': 'success',
            'job_id': str(job_id),
            'confidence': confidence,
            'processing_time': job.processing_time_seconds,
            'extraction_method': extraction_method
        }

    except Exception as e:
        logger.error("=" * 100)
        logger.error(f"✗✗✗ DOCUMENT PROCESSING FAILED ✗✗✗")
        logger.error(f"✗ Job ID: {job_id}")
        logger.error(f"✗ Error: {str(e)}")
        logger.error("=" * 100)
        logger.exception("Full error traceback:")

        # Update job status to failed
        try:
            job = ExtractionJob.objects.get(id=job_id)
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.retry_count += 1
            job.save(update_fields=['status', 'error_message', 'completed_at', 'retry_count'])
            logger.info(f"Job status updated to FAILED (retry count: {job.retry_count})")
        except Exception as save_error:
            logger.error(f"Failed to update job status: {str(save_error)}")

        # Retry if not exceeded max retries
        if self.request.retries < self.max_retries:
            retry_countdown = 60 * (self.request.retries + 1)
            logger.info(f"Scheduling retry {self.request.retries + 1}/{self.max_retries} in {retry_countdown} seconds")
            raise self.retry(exc=e, countdown=retry_countdown)

        logger.error(f"Max retries ({self.max_retries}) exceeded. Job permanently failed.")
        return {
            'status': 'error',
            'job_id': str(job_id),
            'error': str(e),
            'retry_count': self.request.retries
        }


def calculate_confidence(data: dict, text: str) -> float:
    """
    Calculate overall confidence score for extracted data.

    Analyzes data completeness and quality to determine confidence level.

    Args:
        data: Extracted structured data
        text: Original OCR text (empty string for vision-based extraction)

    Returns:
        Confidence score between 0.0 and 1.0
    """
    try:
        # Count total and filled fields
        total_fields = 0
        filled_fields = 0

        for key, value in data.items():
            # Skip metadata and internal fields
            if key.startswith('_') or key in ['extraction_status', 'error']:
                continue

            total_fields += 1

            # Check if field has meaningful value
            if value and value != 'Unknown' and value != 'N/A' and value != [] and value is not None:
                # For nested objects, check if they have content
                if isinstance(value, dict):
                    if any(v for v in value.values() if v):
                        filled_fields += 1
                else:
                    filled_fields += 1

        if total_fields == 0:
            logger.warning("No fields found for confidence calculation")
            return 0.5  # Default confidence

        # Base confidence on field completion
        base_confidence = filled_fields / total_fields

        # Adjust based on text length for OCR-based extraction
        if text:
            text_factor = min(len(text) / 1000, 1.0)  # Cap at 1.0
            confidence = (base_confidence * 0.7) + (text_factor * 0.3)
        else:
            # For vision-based extraction, give higher weight to completion
            confidence = base_confidence * 0.95

        # Ensure confidence is between 0 and 1
        confidence = max(0.0, min(1.0, confidence))

        logger.debug(f"Confidence calculation: {filled_fields}/{total_fields} fields = {confidence:.2f}")
        return round(confidence, 2)

    except Exception as e:
        logger.error(f"Error calculating confidence: {str(e)}")
        return 0.5  # Return default confidence on error


def calculate_field_confidence(data: dict) -> dict:
    """
    Calculate confidence scores for individual fields.

    Provides granular confidence metrics for each extracted field.

    Args:
        data: Extracted structured data

    Returns:
        Dictionary mapping field names to confidence scores (0.0-1.0)
    """
    try:
        field_confidence = {}

        for key, value in data.items():
            # Skip metadata and internal fields
            if key.startswith('_') or key in ['extraction_status', 'error']:
                continue

            # Assign confidence based on value type and quality
            if value and value != 'Unknown' and value != 'N/A' and value != [] and value is not None:
                if isinstance(value, (int, float)) and value != 0:
                    # Numeric values are generally reliable
                    field_confidence[key] = 0.95
                elif isinstance(value, str) and len(value) > 3:
                    # Longer strings are more likely to be accurate
                    field_confidence[key] = 0.90
                elif isinstance(value, list) and len(value) > 0:
                    # Non-empty lists
                    field_confidence[key] = 0.85
                elif isinstance(value, dict):
                    # Nested objects - check if they have content
                    if any(v for v in value.values() if v):
                        field_confidence[key] = 0.85
                    else:
                        field_confidence[key] = 0.30
                else:
                    # Other filled values
                    field_confidence[key] = 0.80
            else:
                # Empty or unknown values
                field_confidence[key] = 0.30

        logger.debug(f"Calculated confidence for {len(field_confidence)} fields")
        return field_confidence

    except Exception as e:
        logger.error(f"Error calculating field confidence: {str(e)}")
        return {}
