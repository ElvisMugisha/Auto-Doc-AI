from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from datetime import timedelta

from .models import Document, ExtractionJob, ExtractedData, ProcessingStatus
from .serializers import (
    DocumentUploadSerializer,
    DocumentSerializer,
    ExtractionJobSerializer,
    ExtractionJobCreateSerializer,
    ExtractedDataSerializer,
)
from utils.permissions import IsActiveAndVerified
from utils.paginations import CustomPageNumberPagination
from utils import loggings

# Initialize logger
logger = loggings.setup_logging()


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing documents.

    Provides CRUD operations for documents:
    - List user's documents
    - Upload new document
    - Retrieve document details
    - Update document metadata
    - Delete document
    - Trigger extraction
    """
    permission_classes = [IsActiveAndVerified]
    pagination_class = CustomPageNumberPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return DocumentUploadSerializer
        return DocumentSerializer

    def get_queryset(self):
        """
        Return documents for the current user only.

        Optimizes query with select_related and prefetch_related.
        """
        return Document.objects.filter(
            user=self.request.user
        ).prefetch_related('extraction_jobs').order_by('-uploaded_at')

    def create(self, request, *args, **kwargs):
        """
        Upload a new document.

        Steps:
        1. Validate file and metadata
        2. Save document
        3. Return document details
        """
        logger.info(f"Document upload requested by user: {request.user.email}")

        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            try:
                document = serializer.save()
                logger.info(f"Document uploaded successfully: {document.id}")

                # Return full document details
                response_serializer = DocumentSerializer(
                    document,
                    context={'request': request}
                )

                return Response(
                    {
                        "message": "Document uploaded successfully",
                        "data": response_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                logger.exception(f"Error uploading document: {str(e)}")
                return Response(
                    {"error": "Failed to upload document. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        logger.warning(f"Document upload validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """Get details of a specific document."""
        logger.info(f"Document details requested: {kwargs.get('pk')}")
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Update document metadata (not the file itself)."""
        logger.info(f"Document update requested: {kwargs.get('pk')}")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete a document and all related data."""
        document = self.get_object()
        logger.info(f"Document deletion requested: {document.id}")

        try:
            # Delete the file from storage
            if document.file:
                document.file.delete()

            # Delete the document (cascade will handle related objects)
            document.delete()

            logger.info(f"Document deleted successfully: {document.id}")
            return Response(
                {"message": "Document deleted successfully"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.exception(f"Error deleting document: {str(e)}")
            return Response(
                {"error": "Failed to delete document"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def extract(self, request, pk=None):
        """
        Trigger extraction for a document.

        Creates a new extraction job and starts processing.
        """
        document = self.get_object()
        logger.info(f"Extraction requested for document: {document.id}")

        try:
            # Check for active jobs
            active_job = document.extraction_jobs.filter(
                status__in=[ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]
            ).first()

            if active_job:
                logger.warning(f"Active job already exists: {active_job.id}")
                return Response(
                    {
                        "error": "Document already has an active extraction job",
                        "job_id": active_job.id,
                        "status": active_job.status
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create new extraction job
            job = ExtractionJob.objects.create(
                document=document,
                status=ProcessingStatus.PENDING
            )

            logger.info(f"Extraction job created: {job.id}")

            # TODO: Trigger async processing task here
            # For now, we'll process synchronously with mock data
            self._process_document_mock(job)

            serializer = ExtractionJobSerializer(job)

            return Response(
                {
                    "message": "Extraction job created successfully",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.exception(f"Error creating extraction job: {str(e)}")
            return Response(
                {"error": "Failed to create extraction job"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _process_document_mock(self, job):
        """
        Mock document processing.

        This is a placeholder that returns mock extracted data.
        In production, this will be replaced with actual OCR/AI processing.
        """
        try:
            # Update job status
            job.status = ProcessingStatus.PROCESSING
            job.started_at = timezone.now()
            job.save()

            logger.info(f"Processing job {job.id} (MOCK)")

            # Simulate processing time
            import time
            time.sleep(1)

            # Create mock extracted data based on document type
            mock_data = self._generate_mock_data(job.document.document_type)

            # Save extracted data
            extracted_data = ExtractedData.objects.create(
                extraction_job=job,
                data=mock_data,
                overall_confidence=0.95,
                field_confidence={
                    "vendor": 0.98,
                    "total": 0.96,
                    "date": 0.94
                },
                extraction_method="mock"
            )

            # Update job status
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = timezone.now()
            job.processing_time_seconds = (
                job.completed_at - job.started_at
            ).total_seconds()
            job.save()

            logger.info(f"Job {job.id} completed successfully (MOCK)")

        except Exception as e:
            logger.exception(f"Error processing job {job.id}: {str(e)}")
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()

    def _generate_mock_data(self, document_type):
        """Generate mock extracted data based on document type."""
        from datetime import date

        mock_data_templates = {
            "invoice": {
                "vendor": "ACME Corporation",
                "invoice_number": "INV-2024-001234",
                "date": str(date.today()),
                "due_date": str(date.today() + timedelta(days=30)),
                "subtotal": 1250.00,
                "tax": 125.00,
                "total": 1375.00,
                "currency": "USD",
                "items": [
                    {
                        "description": "Professional Services",
                        "quantity": 10,
                        "unit_price": 100.00,
                        "amount": 1000.00
                    },
                    {
                        "description": "Consulting Fee",
                        "quantity": 5,
                        "unit_price": 50.00,
                        "amount": 250.00
                    }
                ]
            },
            "receipt": {
                "store_name": "SuperMart",
                "date": str(date.today()),
                "time": "14:30:00",
                "total": 45.99,
                "payment_method": "Credit Card",
                "items": [
                    {"name": "Product A", "price": 19.99},
                    {"name": "Product B", "price": 26.00}
                ]
            },
            "contract": {
                "title": "Service Agreement",
                "parties": ["Company A", "Company B"],
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=365)),
                "value": 50000.00,
                "key_terms": [
                    "12-month term",
                    "Monthly payments",
                    "30-day notice period"
                ]
            }
        }

        return mock_data_templates.get(
            document_type,
            {"message": "Document processed", "type": document_type}
        )


class ExtractionJobViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing extraction jobs.

    Provides read-only access to extraction jobs:
    - List user's extraction jobs
    - Retrieve job details and status
    - Get extracted data
    """
    permission_classes = [IsActiveAndVerified]
    serializer_class = ExtractionJobSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        """
        Return extraction jobs for documents owned by current user.
        """
        return ExtractionJob.objects.filter(
            document__user=self.request.user
        ).select_related(
            'document', 'extracted_data'
        ).order_by('-created_at')

    def retrieve(self, request, *args, **kwargs):
        """Get details of a specific extraction job."""
        logger.info(f"Extraction job details requested: {kwargs.get('pk')}")
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """
        Get extracted data for a completed job.

        Returns the structured extracted data if job is completed.
        """
        job = self.get_object()
        logger.info(f"Extraction results requested for job: {job.id}")

        if job.status != ProcessingStatus.COMPLETED:
            return Response(
                {
                    "error": "Extraction not completed yet",
                    "status": job.status,
                    "message": "Please check job status and try again when completed"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            extracted_data = job.extracted_data
            serializer = ExtractedDataSerializer(extracted_data)

            return Response(
                {
                    "job_id": job.id,
                    "document_id": job.document.id,
                    "document_filename": job.document.original_filename,
                    "extracted_data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        except ExtractedData.DoesNotExist:
            logger.error(f"No extracted data found for completed job: {job.id}")
            return Response(
                {"error": "No extracted data available"},
                status=status.HTTP_404_NOT_FOUND
            )
