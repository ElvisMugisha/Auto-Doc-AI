from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('verify-email/', views.EmailVerificationView.as_view(), name='verify-email'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
    path('users/', views.UserListView.as_view(), name='user-list'),
]