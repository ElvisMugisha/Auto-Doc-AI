import uuid
from django.db import models
from django.contrib.auth import get_user_model
from utils import loggings
from utils.choices import DocumentType, ProcessingStatus

# Initialize logger
logger = loggings.setup_logging()

User = get_user_model()


class Document(models.Model):
    """
    Model to store uploaded documents.

    Stores metadata about uploaded files including type, size, format,
    and links to the user who uploaded it.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documents",
        help_text="User who uploaded this document"
    )

    # File information
    file = models.FileField(
        upload_to="documents/%Y/%m/%d/",
        help_text="The uploaded document file"
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename of the uploaded document"
    )
    file_size = models.IntegerField(
        help_text="File size in bytes"
    )
    file_format = models.CharField(
        max_length=10,
        help_text="File format/extension (e.g., pdf, jpg, png)"
    )

    # Document classification
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
        help_text="Type of document"
    )

    # Metadata
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the document"
    )

    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ["-uploaded_at"]

        # Database indexes for query optimization
        indexes = [
            # Primary query patterns
            models.Index(fields=["-uploaded_at"], name="doc_uploaded_idx"),
            models.Index(fields=["user", "-uploaded_at"], name="doc_user_uploaded_idx"),
            models.Index(fields=["document_type"], name="doc_type_idx"),
            models.Index(fields=["user", "document_type"], name="doc_user_type_idx"),

            # For filtering and searching
            models.Index(fields=["file_format"], name="doc_format_idx"),
            models.Index(fields=["user", "file_format"], name="doc_user_format_idx"),
        ]

        # Database constraints for data integrity
        constraints = [
            # Ensure file size is positive
            models.CheckConstraint(
                check=models.Q(file_size__gt=0),
                name="doc_positive_file_size"
            ),
            # Ensure valid file format
            models.CheckConstraint(
                check=models.Q(file_format__in=['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'bmp', 'webp']),
                name="doc_valid_file_format"
            ),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.document_type})"

    @property
    def file_size_mb(self):
        """Return file size in megabytes."""
        return round(self.file_size / (1024 * 1024), 2)


class ExtractionJob(models.Model):
    """
    Model to track document extraction jobs.

    Each document can have multiple extraction attempts.
    Tracks the processing status, timestamps, and error messages.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="extraction_jobs",
        help_text="Document being processed"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        help_text="Current processing status"
    )

    # Processing details
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When processing started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When processing completed"
    )

    # Error handling
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if processing failed"
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retry attempts"
    )

    # Metadata
    processing_time_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Time taken to process in seconds"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Extraction Job"
        verbose_name_plural = "Extraction Jobs"
        ordering = ["-created_at"]

        # Database indexes for query optimization
        indexes = [
            # Primary query patterns
            models.Index(fields=["-created_at"], name="job_created_idx"),
            models.Index(fields=["document", "-created_at"], name="job_doc_created_idx"),
            models.Index(fields=["status"], name="job_status_idx"),

            # For monitoring and filtering
            models.Index(fields=["status", "-created_at"], name="job_status_created_idx"),
            models.Index(fields=["document", "status"], name="job_doc_status_idx"),

            # For performance tracking
            models.Index(fields=["completed_at"], name="job_completed_idx"),
            models.Index(fields=["processing_time_seconds"], name="job_proc_time_idx"),
        ]

        # Database constraints for data integrity
        constraints = [
            # Ensure retry count is non-negative
            models.CheckConstraint(
                check=models.Q(retry_count__gte=0),
                name="job_non_negative_retry"
            ),
            # Ensure processing time is positive when set
            models.CheckConstraint(
                check=models.Q(processing_time_seconds__isnull=True) | models.Q(processing_time_seconds__gt=0),
                name="job_positive_proc_time"
            ),
            # Ensure completed_at is after started_at when both are set
            models.CheckConstraint(
                check=models.Q(started_at__isnull=True) | models.Q(completed_at__isnull=True) | models.Q(completed_at__gte=models.F('started_at')),
                name="job_valid_timestamps"
            ),
        ]

    def __str__(self):
        return f"Job {self.id} - {self.status}"

    @property
    def is_complete(self):
        """Check if job is completed (success or failed)."""
        return self.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]


class ExtractedData(models.Model):
    """
    Model to store extracted data from documents.

    Stores the structured JSON data extracted from the document,
    along with confidence scores and field-level metadata.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    extraction_job = models.OneToOneField(
        ExtractionJob,
        on_delete=models.CASCADE,
        related_name="extracted_data",
        help_text="The extraction job that produced this data"
    )

    # Extracted data
    data = models.JSONField(
        help_text="Structured extracted data as JSON"
    )

    # Confidence and quality metrics
    overall_confidence = models.FloatField(
        default=0.0,
        help_text="Overall confidence score (0-1)"
    )
    field_confidence = models.JSONField(
        default=dict,
        blank=True,
        help_text="Confidence scores for individual fields"
    )

    # Metadata
    extraction_method = models.CharField(
        max_length=50,
        default="manual",
        help_text="Method used for extraction (e.g., ocr, ai, manual)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Extracted Data"
        verbose_name_plural = "Extracted Data"

    def __str__(self):
        return f"Data for Job {self.extraction_job.id}"

    @property
    def confidence_percentage(self):
        """Return confidence as percentage."""
        return round(self.overall_confidence * 100, 2)
