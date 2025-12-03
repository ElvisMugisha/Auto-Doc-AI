# Email Verification API Documentation

## Overview

This document provides comprehensive documentation for the Email Verification API endpoints in the Auto-Doc-AI project. The email verification system ensures that users verify their email addresses before accessing the platform.

## Table of Contents

1. [Architecture](#architecture)
2. [API Endpoints](#api-endpoints)
3. [Request/Response Examples](#requestresponse-examples)
4. [Error Handling](#error-handling)
5. [Security Considerations](#security-considerations)
6. [Testing](#testing)

---

## Architecture

### Flow Diagram

```
User Registration → OTP Generation → Email Sent → User Verifies → Account Activated
                                    ↓
                            OTP Expired/Lost?
                                    ↓
                            Resend OTP Request
```

### Components

1. **EmailVerificationSerializer**: Validates email and OTP input
2. **EmailVerificationView**: Handles verification logic
3. **ResendOTPSerializer**: Validates resend requests
4. **ResendOTPView**: Handles OTP resend logic
5. **Passcode Model**: Stores OTP codes with expiration

---

## API Endpoints

### 1. Verify Email

**Endpoint**: `POST /api/v1/auth/verify-email/`

**Description**: Verify a user's email address using the OTP sent during registration.

**Authentication**: Not required (AllowAny)

**Request Body**:
```json
{
  "email": "user@example.com",
  "otp": "12345678"
}
```

**Success Response** (200 OK):
```json
{
  "message": "Your email has been verified successfully! You can now log in to your account.",
  "data": {
    "email": "user@example.com",
    "username": "user_12345",
    "is_verified": true,
    "verified_at": "2025-12-01T09:30:45.123456Z"
  }
}
```

**Error Responses**:

- **400 Bad Request**: Invalid data or OTP
  ```json
  {
    "otp": ["Invalid verification code. Please check and try again."]
  }
  ```

- **404 Not Found**: User doesn't exist
  ```json
  {
    "email": ["No account found with this email address."]
  }
  ```

- **410 Gone**: OTP expired
  ```json
  {
    "otp": ["This verification code has expired. Please request a new one."]
  }
  ```

- **500 Internal Server Error**: Server error
  ```json
  {
    "error": "An unexpected error occurred during verification. Please try again later."
  }
  ```

---

### 2. Resend OTP

**Endpoint**: `POST /api/v1/auth/resend-otp/`

**Description**: Resend verification OTP to user's email if the original was not received or has expired.

**Authentication**: Not required (AllowAny)

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Success Response** (200 OK):
```json
{
  "message": "A new verification code has been sent to your email.",
  "data": {
    "email": "user@example.com",
    "expires_in": "10 minutes"
  }
}
```

**Error Responses**:

- **400 Bad Request**: User already verified
  ```json
  {
    "email": ["This account is already verified. You can log in directly."]
  }
  ```

- **404 Not Found**: User doesn't exist
  ```json
  {
    "email": ["No account found with this email address."]
  }
  ```

- **429 Too Many Requests**: Active OTP exists
  ```json
  {
    "error": "An active verification code already exists.",
    "message": "Please use the existing code or wait 8 minute(s) before requesting a new one.",
    "expires_in_minutes": 8
  }
  ```

- **500 Internal Server Error**: Server error
  ```json
  {
    "error": "An unexpected error occurred. Please try again later."
  }
  ```

---

## Request/Response Examples

### Example 1: Successful Email Verification

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-email/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "otp": "87654321"
  }'
```

**Response**:
```json
{
  "message": "Your email has been verified successfully! You can now log in to your account.",
  "data": {
    "email": "john.doe@example.com",
    "username": "john_doe_12345",
    "is_verified": true,
    "verified_at": "2025-12-01T11:00:00.000000Z"
  }
}
```

### Example 2: Resend OTP

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/resend-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com"
  }'
```

**Response**:
```json
{
  "message": "A new verification code has been sent to your email.",
  "data": {
    "email": "john.doe@example.com",
    "expires_in": "10 minutes"
  }
}
```

---

## Error Handling

### Validation Errors

All validation errors follow a consistent format:

```json
{
  "field_name": ["Error message 1", "Error message 2"]
}
```

### Common Validation Errors

1. **Invalid OTP Format**:
   ```json
   {
     "otp": ["OTP must contain only digits."]
   }
   ```

2. **OTP Length Error**:
   ```json
   {
     "otp": ["OTP must be exactly 8 digits."]
   }
   ```

3. **Missing Required Fields**:
   ```json
   {
     "email": ["This field is required."],
     "otp": ["This field is required."]
   }
   ```

### Server Errors

All server errors include descriptive messages:

```json
{
  "error": "Description of what went wrong"
}
```

---

## Security Considerations

### 1. OTP Security

- **Length**: 8-digit numeric code
- **Expiration**: 10 minutes from generation
- **Single Use**: OTP is marked as used after successful verification
- **Uniqueness**: Each OTP is unique across the system

### 2. Rate Limiting

- Users cannot request a new OTP if an active one exists
- Prevents OTP spam and abuse
- Returns time remaining until next request is allowed

### 3. Email Normalization

- All emails are converted to lowercase
- Whitespace is trimmed
- Prevents duplicate accounts with case variations

### 4. Database Transactions

- Verification uses atomic transactions
- Ensures data consistency
- Automatic rollback on errors

### 5. Logging

- All verification attempts are logged
- Failed attempts include reason
- Helps with debugging and security monitoring

---

## Testing

### Running Tests

```bash
# Run all authentication tests
python manage.py test authentication

# Run only email verification tests
python manage.py test authentication.tests.test_email_verification

# Run with verbose output
python manage.py test authentication.tests.test_email_verification --verbosity=2
```

### Test Coverage

The test suite includes:

1. ✅ Successful email verification
2. ✅ Invalid OTP
3. ✅ Expired OTP
4. ✅ Non-existent user
5. ✅ Already verified user
6. ✅ Invalid OTP format
7. ✅ Short OTP
8. ✅ Missing email field
9. ✅ Missing OTP field

### Manual Testing with cURL

#### Test Email Verification

```bash
# 1. Register a user first
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User"
  }'

# 2. Check email for OTP (or check console if using EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend')

# 3. Verify email with OTP
curl -X POST http://localhost:8000/api/v1/auth/verify-email/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "otp": "YOUR_OTP_HERE"
  }'
```

#### Test Resend OTP

```bash
curl -X POST http://localhost:8000/api/v1/auth/resend-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }'
```

---

## Database Schema

### Passcode Model

```python
class Passcode(models.Model):
    id = UUIDField(primary_key=True)
    user = ForeignKey(User, on_delete=CASCADE)
    code = CharField(max_length=15, unique=True)
    code_type = CharField(choices=CodeType.choices)
    created_at = DateTimeField(auto_now_add=True)
    expires_at = DateTimeField()
    is_used = BooleanField(default=False)
```

**Constraints**:
- Only one active passcode per user per code_type
- Enforced at database level with UniqueConstraint

---

## Best Practices

### For Frontend Developers

1. **Display Clear Error Messages**: Use the error messages from the API directly
2. **Handle All Status Codes**: Implement specific UI for 400, 404, 410, 429, 500
3. **Show Expiration Time**: Display countdown timer for OTP expiration
4. **Implement Resend Logic**: Provide easy access to resend OTP
5. **Validate Input**: Validate email and OTP format before sending request

### For Backend Developers

1. **Monitor Logs**: Regularly check logs for failed verification attempts
2. **Email Deliverability**: Ensure email service is properly configured
3. **Database Cleanup**: Periodically clean up expired OTPs
4. **Rate Limiting**: Consider implementing additional rate limiting at infrastructure level
5. **Security Audits**: Regularly review and update security measures

---

## Troubleshooting

### Common Issues

1. **OTP Not Received**
   - Check email spam folder
   - Verify email configuration in settings
   - Check email service logs
   - Use resend OTP endpoint

2. **OTP Always Invalid**
   - Verify OTP is exactly 8 digits
   - Check for whitespace in input
   - Ensure OTP hasn't expired
   - Verify email matches registered email

3. **429 Too Many Requests**
   - Wait for existing OTP to expire
   - Check expires_in_minutes in response
   - Consider implementing OTP cancellation feature

---

## API Changelog

### Version 1.0.0 (2025-12-01)
- Initial release
- Email verification endpoint
- Resend OTP endpoint
- Comprehensive error handling
- Rate limiting implementation

---

## Support

For issues or questions:
- **Email**: support@autodocai.com
- **Documentation**: https://docs.autodocai.com
- **GitHub Issues**: https://github.com/ElvisMugisha/Auto-Doc-AI/issues

---

**Last Updated**: December 1, 2025
**API Version**: 1.0.0
