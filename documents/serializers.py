from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Document, ExtractionJob, ExtractedData, DocumentType, ProcessingStatus
from utils import loggings

# Initialize logger
logger = loggings.setup_logging()

User = get_user_model()


class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for uploading documents.

    Handles file upload validation and metadata extraction.
    """
    file = serializers.FileField(
        required=True,
        help_text="Document file to upload (PDF, JPG, PNG)"
    )
    document_type = serializers.ChoiceField(
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
        help_text="Type of document being uploaded"
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "file",
            "document_type",
            "description",
            "original_filename",
            "file_size",
            "file_format",
            "uploaded_at",
        ]
        read_only_fields = [
            "id",
            "original_filename",
            "file_size",
            "file_format",
            "uploaded_at",
        ]

    def validate_file(self, value):
        """
        Validate uploaded file.

        Checks file size and format.
        """
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum allowed size of {max_size / (1024 * 1024)}MB"
            )

        # Check file format
        allowed_formats = ['pdf', 'jpg', 'jpeg', 'png']
        file_ext = value.name.split('.')[-1].lower()

        if file_ext not in allowed_formats:
            raise serializers.ValidationError(
                f"File format '{file_ext}' not supported. Allowed formats: {', '.join(allowed_formats)}"
            )

        logger.debug(f"File validation passed: {value.name}, size: {value.size} bytes")
        return value

    def create(self, validated_data):
        """
        Create document instance with extracted metadata.
        """
        file = validated_data['file']

        # Extract metadata from file
        validated_data['original_filename'] = file.name
        validated_data['file_size'] = file.size
        validated_data['file_format'] = file.name.split('.')[-1].lower()

        # Set user from context
        validated_data['user'] = self.context['request'].user

        logger.info(f"Creating document: {file.name} for user {validated_data['user'].email}")

        return super().create(validated_data)


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for document details.

    Includes all document information and related extraction jobs.
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.FloatField(read_only=True)
    extraction_jobs_count = serializers.SerializerMethodField()
    latest_job_status = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "user_email",
            "file",
            "file_url",
            "original_filename",
            "file_size",
            "file_size_mb",
            "file_format",
            "document_type",
            "description",
            "extraction_jobs_count",
            "latest_job_status",
            "uploaded_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_email",
            "file_url",
            "original_filename",
            "file_size",
            "file_size_mb",
            "file_format",
            "extraction_jobs_count",
            "latest_job_status",
            "uploaded_at",
            "updated_at",
        ]

    def get_file_url(self, obj) -> str:
        """Get the full URL of the uploaded file."""
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_extraction_jobs_count(self, obj) -> int:
        """Get the count of extraction jobs for this document."""
        return obj.extraction_jobs.count()

    def get_latest_job_status(self, obj) -> str:
        """Get the status of the latest extraction job."""
        latest_job = obj.extraction_jobs.first()
        return latest_job.status if latest_job else None


class ExtractedDataSerializer(serializers.ModelSerializer):
    """
    Serializer for extracted data.
    """
    confidence_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = ExtractedData
        fields = [
            "id",
            "data",
            "overall_confidence",
            "confidence_percentage",
            "field_confidence",
            "extraction_method",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "confidence_percentage",
            "created_at",
            "updated_at",
        ]


class ExtractionJobSerializer(serializers.ModelSerializer):
    """
    Serializer for extraction jobs.

    Includes job status, timing, and extracted data if available.
    """
    document_id = serializers.UUIDField(source='document.id', read_only=True)
    document_filename = serializers.CharField(source='document.original_filename', read_only=True)
    extracted_data = ExtractedDataSerializer(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = ExtractionJob
        fields = [
            "id",
            "document_id",
            "document_filename",
            "status",
            "started_at",
            "completed_at",
            "processing_time_seconds",
            "error_message",
            "retry_count",
            "extracted_data",
            "is_complete",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "document_id",
            "document_filename",
            "started_at",
            "completed_at",
            "processing_time_seconds",
            "error_message",
            "retry_count",
            "extracted_data",
            "is_complete",
            "created_at",
            "updated_at",
        ]


class ExtractionJobCreateSerializer(serializers.Serializer):
    """
    Serializer for creating extraction jobs.

    Validates document ownership before creating job.
    """
    document_id = serializers.UUIDField(
        required=True,
        help_text="ID of the document to extract data from"
    )

    def validate_document_id(self, value):
        """
        Validate that document exists and belongs to user.
        """
        request = self.context.get('request')

        try:
            document = Document.objects.get(id=value, user=request.user)
        except Document.DoesNotExist:
            raise serializers.ValidationError(
                "Document not found or you don't have permission to access it."
            )

        # Check if there's already a pending/processing job
        active_job = document.extraction_jobs.filter(
            status__in=[ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]
        ).first()

        if active_job:
            raise serializers.ValidationError(
                f"Document already has an active extraction job (ID: {active_job.id}, Status: {active_job.status})"
            )

        return value
