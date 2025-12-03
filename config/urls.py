from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


# Admin URLs
urlpatterns = [
    path('admin/', admin.site.urls),
]

# Application URLs
urlpatterns += [
    path('auth/', include('authentication.urls')),
    path('documents/', include('documents.urls')),
]

# API URLs
urlpatterns += [
    path('api/', include('rest_framework.urls')),
]

# Static and Media URLs
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# API Documentation URLs
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
