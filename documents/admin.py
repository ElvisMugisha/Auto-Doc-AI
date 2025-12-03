from django.contrib import admin
from .models import Document, ExtractionJob, ExtractedData


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Document model."""
    list_display = [
        'id',
        'original_filename',
        'document_type',
        'user',
        'file_size_mb',
        'uploaded_at'
    ]
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['original_filename', 'user__email', 'description']
    readonly_fields = ['id', 'uploaded_at', 'updated_at', 'file_size_mb']
    ordering = ['-uploaded_at']


@admin.register(ExtractionJob)
class ExtractionJobAdmin(admin.ModelAdmin):
    """Admin interface for ExtractionJob model."""
    list_display = [
        'id',
        'document',
        'status',
        'processing_time_seconds',
        'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'document__original_filename']
    readonly_fields = [
        'id',
        'started_at',
        'completed_at',
        'processing_time_seconds',
        'created_at',
        'updated_at'
    ]
    ordering = ['-created_at']


@admin.register(ExtractedData)
class ExtractedDataAdmin(admin.ModelAdmin):
    """Admin interface for ExtractedData model."""
    list_display = [
        'id',
        'extraction_job',
        'confidence_percentage',
        'extraction_method',
        'created_at'
    ]
    list_filter = ['extraction_method', 'created_at']
    search_fields = ['id', 'extraction_job__id']
    readonly_fields = ['id', 'confidence_percentage', 'created_at', 'updated_at']
    ordering = ['-created_at']
