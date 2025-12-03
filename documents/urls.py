from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create separate routers to avoid URL conflicts
document_router = DefaultRouter()
document_router.register(r'', views.DocumentViewSet, basename='document')

job_router = DefaultRouter()
job_router.register(r'', views.ExtractionJobViewSet, basename='extraction-job')

urlpatterns = [
    # Jobs must come BEFORE documents to avoid conflict
    path('jobs/', include(job_router.urls)),
    path('', include(document_router.urls)),
]