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
        indexes = [
            models.Index(fields=["-uploaded_at"]),
            models.Index(fields=["user", "-uploaded_at"]),
            models.Index(fields=["document_type"]),
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
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["document", "-created_at"]),
            models.Index(fields=["status"]),
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
