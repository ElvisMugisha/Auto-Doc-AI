from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from typing import Optional, Dict, Any
from .models import Document, ExtractionJob, ExtractedData
from utils.choices import DocumentType, ProcessingStatus
from utils import loggings

logger = loggings.setup_logging()

# File upload constraints
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'bmp', 'webp']
ALLOWED_MIME_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'image/bmp',
    'image/webp',
]


class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for document upload with comprehensive validation.

    Validates:
    - File size (max 50MB)
    - File extension
    - MIME type
    - File integrity
    """

    class Meta:
        model = Document
        fields = ['file', 'document_type', 'description']

    def validate_file(self, value):
        """
        Comprehensive file validation.

        Args:
            value: Uploaded file

        Returns:
            Validated file

        Raises:
            ValidationError: If file is invalid
        """
        try:
            # Check file size
            if value.size > MAX_FILE_SIZE:
                logger.warning(f"File too large: {value.size} bytes (max: {MAX_FILE_SIZE})")
                raise serializers.ValidationError(
                    f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB. "
                    f"Your file is {value.size // (1024 * 1024)}MB."
                )

            # Check minimum file size (prevent empty files)
            if value.size < 100:  # 100 bytes minimum
                logger.warning(f"File too small: {value.size} bytes")
                raise serializers.ValidationError(
                    "File is too small or empty. Please upload a valid document."
                )

            # Get file extension
            file_extension = value.name.split('.')[-1].lower()

            # Validate extension
            if file_extension not in ALLOWED_EXTENSIONS:
                logger.warning(f"Invalid file extension: {file_extension}")
                raise serializers.ValidationError(
                    f"File type '.{file_extension}' is not supported. "
                    f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
                )

            # Validate MIME type if available
            if hasattr(value, 'content_type') and value.content_type:
                if value.content_type not in ALLOWED_MIME_TYPES:
                    logger.warning(f"Invalid MIME type: {value.content_type}")
                    raise serializers.ValidationError(
                        f"File MIME type '{value.content_type}' is not supported."
                    )

            logger.info(f"File validation passed: {value.name} ({value.size} bytes)")
            return value

        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during file validation: {str(e)}")
            raise serializers.ValidationError(
                "An error occurred while validating the file. Please try again."
            )

    def validate_document_type(self, value):
        """
        Validate document type.

        Args:
            value: Document type

        Returns:
            Validated document type
        """
        if value not in DocumentType.values:
            logger.warning(f"Invalid document type: {value}")
            raise serializers.ValidationError(
                f"Invalid document type. Allowed types: {', '.join(DocumentType.values)}"
            )
        return value

    def create(self, validated_data):
        """
        Create document with proper error handling.

        Args:
            validated_data: Validated data

        Returns:
            Created document

        Raises:
            ValidationError: If creation fails
        """
        try:
            # Get user from request context
            user = self.context['request'].user

            # Extract file info
            uploaded_file = validated_data['file']
            file_extension = uploaded_file.name.split('.')[-1].lower()

            # Create document
            document = Document.objects.create(
                user=user,
                file=uploaded_file,
                original_filename=uploaded_file.name,
                file_size=uploaded_file.size,
                file_format=file_extension,
                document_type=validated_data.get('document_type', DocumentType.OTHER),
                description=validated_data.get('description', '')
            )

            logger.info(
                f"Document created successfully: {document.id} "
                f"(user: {user.email}, size: {document.file_size} bytes)"
            )

            return document

        except Exception as e:
            logger.exception(f"Error creating document: {str(e)}")
            raise serializers.ValidationError(
                "Failed to create document. Please try again."
            )


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for document details with read-only fields.

    Provides comprehensive document information including:
    - File metadata
    - Upload information
    - Related extraction jobs
    """
    file_size_mb = serializers.FloatField(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    extraction_jobs_count = serializers.SerializerMethodField()
    latest_extraction_job = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'user_email', 'original_filename', 'file_size',
            'file_size_mb', 'file_format', 'document_type', 'description',
            'uploaded_at', 'updated_at', 'extraction_jobs_count',
            'latest_extraction_job'
        ]
        read_only_fields = [
            'id', 'user_email', 'file_size', 'file_size_mb',
            'file_format', 'uploaded_at', 'updated_at'
        ]

    @extend_schema_field(OpenApiTypes.INT)
    def get_extraction_jobs_count(self, obj) -> int:
        """Get count of extraction jobs for this document."""
        try:
            return obj.extraction_jobs.count()
        except Exception as e:
            logger.error(f"Error counting extraction jobs: {str(e)}")
            return 0

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_latest_extraction_job(self, obj) -> Optional[Dict[str, Any]]:
        """Get latest extraction job details."""
        try:
            latest_job = obj.extraction_jobs.order_by('-created_at').first()
            if latest_job:
                return {
                    'id': str(latest_job.id),
                    'status': latest_job.status,
                    'created_at': latest_job.created_at,
                    'completed_at': latest_job.completed_at,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting latest extraction job: {str(e)}")
            return None


class ExtractionJobSerializer(serializers.ModelSerializer):
    """
    Serializer for extraction job with detailed status information.
    """
    document_filename = serializers.CharField(source='document.original_filename', read_only=True)
    document_type = serializers.CharField(source='document.document_type', read_only=True)
    has_results = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = ExtractionJob
        fields = [
            'id', 'document', 'document_filename', 'document_type',
            'status', 'started_at', 'completed_at', 'processing_time_seconds',
            'error_message', 'retry_count', 'created_at', 'updated_at',
            'has_results', 'progress_percentage'
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'completed_at',
            'processing_time_seconds', 'error_message', 'retry_count',
            'created_at', 'updated_at'
        ]

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_has_results(self, obj) -> bool:
        """Check if extraction results are available."""
        try:
            return hasattr(obj, 'extracted_data') and obj.extracted_data is not None
        except Exception:
            return False

    @extend_schema_field(OpenApiTypes.INT)
    def get_progress_percentage(self, obj) -> int:
        """Calculate progress percentage based on status."""
        status_progress = {
            ProcessingStatus.PENDING: 0,
            ProcessingStatus.PROCESSING: 50,
            ProcessingStatus.COMPLETED: 100,
            ProcessingStatus.FAILED: 0,
        }
        return status_progress.get(obj.status, 0)


class ExtractionJobCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating extraction jobs with validation.
    """

    class Meta:
        model = ExtractionJob
        fields = ['document']

    def validate_document(self, value):
        """
        Validate document before creating extraction job.

        Args:
            value: Document instance

        Returns:
            Validated document

        Raises:
            ValidationError: If document is invalid or has active jobs
        """
        try:
            # Check if document exists and user has access
            user = self.context['request'].user
            if value.user != user:
                logger.warning(
                    f"User {user.email} attempted to extract document {value.id} "
                    f"owned by {value.user.email}"
                )
                raise serializers.ValidationError(
                    "You don't have permission to extract this document."
                )

            # Check for active extraction jobs
            active_jobs = value.extraction_jobs.filter(
                status__in=[ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]
            )

            if active_jobs.exists():
                active_job = active_jobs.first()
                logger.warning(
                    f"Document {value.id} already has active job {active_job.id}"
                )
                raise serializers.ValidationError(
                    f"Document already has an active extraction job (ID: {active_job.id}). "
                    f"Please wait for it to complete."
                )

            return value

        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error validating document for extraction: {str(e)}")
            raise serializers.ValidationError(
                "An error occurred while validating the document."
            )


class ExtractedDataSerializer(serializers.ModelSerializer):
    """
    Serializer for extracted data with confidence metrics.
    """
    confidence_percentage = serializers.ReadOnlyField()
    extraction_method_display = serializers.SerializerMethodField()

    class Meta:
        model = ExtractedData
        fields = [
            'id', 'data', 'overall_confidence', 'confidence_percentage',
            'field_confidence', 'extraction_method', 'extraction_method_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(OpenApiTypes.STR)
    def get_extraction_method_display(self, obj) -> str:
        """Get human-readable extraction method."""
        method_display = {
            'openai_vision': 'OpenAI GPT-4 Vision',
            'openai_vision_universal': 'OpenAI GPT-4 Vision (Universal)',
            'ocr+ollama': 'Tesseract OCR + Ollama AI',
            'ocr+ai': 'Tesseract OCR + AI',
            'manual': 'Manual Entry',
        }
        return method_display.get(obj.extraction_method, obj.extraction_method)
