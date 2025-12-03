# Password Reset API Documentation

## Overview

The Password Reset API provides a secure, three-step process for users to reset their forgotten passwords using OTP (One-Time Passcode) verification. This system reuses the existing `Passcode` model with `PASSWORD_RESET` code type.

## Flow Diagram

```
User Forgot Password
         ↓
1. Request Reset (Email) → OTP Sent
         ↓
2. Verify OTP → Code Validated
         ↓
3. Reset Password → Password Updated
```

## Endpoints

### 1. Request Password Reset

**URL:** `/api/v1/auth/password/reset/request/`
**Method:** `POST`
**Authentication:** Not Required

#### Request Body

```json
{
  "email": "user@example.com"
}
```

#### Success Response (200 OK)

```json
{
  "message": "If an account exists with this email, a password reset code has been sent.",
  "data": {
    "email": "user@example.com",
    "expires_in": "10 minutes"
  }
}
```

**Note:** For security, the response is always successful to prevent email enumeration attacks.

---

### 2. Verify Reset Code

**URL:** `/api/v1/auth/password/reset/verify/`
**Method:** `POST`
**Authentication:** Not Required

#### Request Body

```json
{
  "email": "user@example.com",
  "otp": "12345678"
}
```

#### Success Response (200 OK)

```json
{
  "message": "Reset code verified successfully. You can now reset your password.",
  "data": {
    "email": "user@example.com",
    "verified": true
  }
}
```

#### Error Responses

**400 Bad Request - Invalid OTP**
```json
{
  "otp": ["Invalid or expired reset code."]
}
```

**410 Gone - Expired OTP**
```json
{
  "otp": ["This reset code has expired. Please request a new one."]
}
```

---

### 3. Reset Password

**URL:** `/api/v1/auth/password/reset/confirm/`
**Method:** `POST`
**Authentication:** Not Required

#### Request Body

```json
{
  "email": "user@example.com",
  "otp": "12345678",
  "new_password": "NewSecurePassword123!",
  "confirm_new_password": "NewSecurePassword123!"
}
```

#### Success Response (200 OK)

```json
{
  "message": "Password reset successfully. You can now log in with your new password.",
  "data": {
    "email": "user@example.com",
    "reset_at": "2025-12-01T16:07:15.123456Z"
  }
}
```

#### Error Responses

**400 Bad Request - Passwords Don't Match**
```json
{
  "confirm_new_password": ["Passwords do not match."]
}
```

**400 Bad Request - Weak Password**
```json
{
  "new_password": [
    "This password is too short. It must contain at least 8 characters.",
    "This password is too common."
  ]
}
```

**410 Gone - Expired OTP**
```json
{
  "otp": ["This reset code has expired. Please request a new one."]
}
```

---

## Complete Flow Example

### Step 1: Request Reset

```bash
curl -X POST http://localhost:8000/api/v1/auth/password/reset/request/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**Response:**
```json
{
  "message": "If an account exists with this email, a password reset code has been sent.",
  "data": {
    "email": "user@example.com",
    "expires_in": "10 minutes"
  }
}
```

### Step 2: Verify Code (Optional but Recommended)

```bash
curl -X POST http://localhost:8000/api/v1/auth/password/reset/verify/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp": "12345678"
  }'
```

**Response:**
```json
{
  "message": "Reset code verified successfully. You can now reset your password.",
  "data": {
    "email": "user@example.com",
    "verified": true
  }
}
```

### Step 3: Reset Password

```bash
curl -X POST http://localhost:8000/api/v1/auth/password/reset/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp": "12345678",
    "new_password": "NewSecurePassword123!",
    "confirm_new_password": "NewSecurePassword123!"
  }'
```

**Response:**
```json
{
  "message": "Password reset successfully. You can now log in with your new password.",
  "data": {
    "email": "user@example.com",
    "reset_at": "2025-12-01T16:07:15Z"
  }
}
```

---

## Implementation Details

### Serializers

1. **`PasswordResetRequestSerializer`**
   - Validates email format
   - Doesn't reveal if user exists (security)

2. **`PasswordResetVerifySerializer`**
   - Validates OTP format (8 digits)
   - Checks OTP exists and not expired
   - Marks expired OTPs as used

3. **`PasswordResetConfirmSerializer`**
   - Validates OTP
   - Validates password complexity
   - Ensures passwords match

### Views

1. **`PasswordResetRequestView`**
   - Creates OTP with `PASSWORD_RESET` code type
   - Sends email with reset code
   - Always returns success (prevents email enumeration)

2. **`PasswordResetVerifyView`**
   - Validates OTP without consuming it
   - Useful for frontend validation

3. **`PasswordResetConfirmView`**
   - Validates OTP and password
   - Updates user password
   - Marks OTP as used
   - Sends confirmation email

### Database Schema

Uses existing `Passcode` model:

```python
Passcode:
  - user: ForeignKey to User
  - code: 8-digit OTP
  - code_type: PASSWORD_RESET
  - expires_at: 10 minutes from creation
  - is_used: False initially, True after use
```

---

## Security Features

1. **Email Enumeration Prevention**
   - Request endpoint always returns success
   - Doesn't reveal if email exists

2. **OTP Expiration**
   - Codes expire after 10 minutes
   - Expired codes automatically marked as used

3. **Single-Use Codes**
   - OTP marked as `is_used=True` after successful reset
   - Cannot reuse the same code

4. **Password Complexity**
   - Enforces Django's password validators
   - Minimum 8 characters
   - Cannot be too common

5. **Comprehensive Logging**
   - All attempts logged for security monitoring
   - Failed attempts tracked

6. **Atomic Transactions**
   - Password update and OTP marking happen atomically
   - Prevents inconsistent state

---

## Email Templates

### Reset Request Email

```
Subject: Password Reset Request

Hi [First Name],

You requested to reset your password for your AutoDocAI account.

Your password reset code is: [OTP]

This code will expire in 10 minutes.

If you didn't request this, please ignore this email.

Best regards,
AutoDocAI Team
```

### Reset Confirmation Email

```
Subject: Password Reset Successful

Hi [First Name],

Your password has been successfully reset.

If you didn't perform this action, please contact our support team immediately.

Best regards,
AutoDocAI Team
```

---

## Error Handling

### Common Errors

| Error Code | Scenario | Response |
|------------|----------|----------|
| 400 | Invalid email format | `{"email": ["Enter a valid email address."]}` |
| 400 | Invalid OTP format | `{"otp": ["OTP must be exactly 8 digits."]}` |
| 400 | Passwords don't match | `{"confirm_new_password": ["Passwords do not match."]}` |
| 404 | User not found | `{"email": ["No account found with this email address."]}` |
| 410 | OTP expired | `{"otp": ["This reset code has expired. Please request a new one."]}` |
| 500 | Server error | `{"error": ["An unexpected error occurred."]}` |

---

## Testing

### Test Scenarios

1. **Successful Reset Flow**
   - Request → Verify → Confirm
   - All steps succeed

2. **Invalid Email**
   - Non-existent email
   - Still returns success (security)

3. **Invalid OTP**
   - Wrong code
   - Returns 400 error

4. **Expired OTP**
   - Wait 10+ minutes
   - Returns 410 error

5. **Weak Password**
   - Too short, too common
   - Returns 400 with details

6. **Mismatched Passwords**
   - Different passwords
   - Returns 400 error

7. **Reuse OTP**
   - Try to use same code twice
   - Second attempt fails

---

## Best Practices

1. **Rate Limiting**
   - Implement rate limiting on request endpoint
   - Prevent abuse/spam

2. **Email Delivery**
   - Use reliable email service
   - Handle delivery failures gracefully

3. **Frontend Implementation**
   - Show countdown timer for OTP expiration
   - Clear instructions for users
   - Validate password strength client-side

4. **Security Monitoring**
   - Monitor failed reset attempts
   - Alert on suspicious patterns
   - Track reset frequency per user

5. **User Experience**
   - Provide clear error messages
   - Allow resending OTP if expired
   - Confirm successful reset

---

## Related Endpoints

- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/password/change/` - Change password (authenticated)
- `POST /api/v1/auth/resend-otp/` - Resend verification OTP

---

**Last Updated:** December 1, 2025
**Version:** 1.0
