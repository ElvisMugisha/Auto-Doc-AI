# Email Verification - Quick Reference Guide

## 🚀 Quick Start

### Complete User Registration & Verification Flow

```bash
# Step 1: Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'

# Response: User created, OTP sent to email
{
  "message": "Your account has been created successfully. Please check your email for the verification code.",
  "data": {
    "id": "uuid-here",
    "email": "user@example.com",
    "username": "user_12345",
    "is_verified": false
  }
}

# Step 2: Check your email for the 8-digit OTP (or console if using console backend)

# Step 3: Verify your email
curl -X POST http://localhost:8000/api/v1/auth/verify-email/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp": "12345678"
  }'

# Response: Email verified successfully
{
  "message": "Your email has been verified successfully! You can now log in to your account.",
  "data": {
    "email": "user@example.com",
    "username": "user_12345",
    "is_verified": true,
    "verified_at": "2025-12-01T11:00:00.000000Z"
  }
}
```

---

## 📧 Resend OTP

If you didn't receive the OTP or it expired:

```bash
curl -X POST http://localhost:8000/api/v1/auth/resend-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'

# Response: New OTP sent
{
  "message": "A new verification code has been sent to your email.",
  "data": {
    "email": "user@example.com",
    "expires_in": "10 minutes"
  }
}
```

---

## ⚠️ Common Errors & Solutions

### 1. Invalid OTP
```json
{
  "otp": ["Invalid verification code. Please check and try again."]
}
```
**Solution**: Double-check the OTP from your email. Make sure it's exactly 8 digits.

### 2. OTP Expired
```json
{
  "otp": ["This verification code has expired. Please request a new one."]
}
```
**Solution**: Use the resend OTP endpoint to get a new code.

### 3. User Not Found
```json
{
  "email": ["No account found with this email address."]
}
```
**Solution**: Verify the email address is correct. Register if you haven't already.

### 4. Already Verified
```json
{
  "email": ["This account is already verified. You can log in directly."]
}
```
**Solution**: Your account is already verified. Proceed to login.

### 5. Too Many Requests
```json
{
  "error": "An active verification code already exists.",
  "message": "Please use the existing code or wait 8 minute(s) before requesting a new one.",
  "expires_in_minutes": 8
}
```
**Solution**: Use the existing OTP or wait for it to expire.

---

## 🔑 API Endpoints Summary

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/api/v1/auth/register/` | POST | Register new user | No |
| `/api/v1/auth/verify-email/` | POST | Verify email with OTP | No |
| `/api/v1/auth/resend-otp/` | POST | Resend verification OTP | No |

---

## 📝 Request Body Schemas

### Verify Email
```json
{
  "email": "string (required, valid email)",
  "otp": "string (required, exactly 8 digits)"
}
```

### Resend OTP
```json
{
  "email": "string (required, valid email)"
}
```

---

## ✅ Validation Rules

### Email
- ✅ Must be a valid email format
- ✅ Converted to lowercase automatically
- ✅ Whitespace trimmed automatically
- ✅ Must exist in the system (for verification/resend)
- ✅ Must not be already verified (for resend)

### OTP
- ✅ Must be exactly 8 digits
- ✅ Must contain only numbers (0-9)
- ✅ Must not be expired (10-minute validity)
- ✅ Must not be already used
- ✅ Must match the user's email

---

## 🕐 Important Timings

- **OTP Validity**: 10 minutes from generation
- **Rate Limit**: Cannot request new OTP if active one exists
- **Auto-cleanup**: Expired OTPs can be cleaned up periodically

---

## 🧪 Testing in Development

### Using Django Console Email Backend

If your `settings.py` has:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

The OTP will be printed in the console where `manage.py runserver` is running.

Look for output like:
```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: One-Time Passcode for Email Verification
From: noreply@autodocai.com
To: user@example.com

Hi John,

Use the following one-time passcode to verify your email:

OTP: 12345678

This passcode is valid for 10 minutes.
```

---

## 🐍 Python/Requests Example

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/auth"

# Register user
register_data = {
    "email": "test@example.com",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User"
}
response = requests.post(f"{BASE_URL}/register/", json=register_data)
print(response.json())

# Verify email (get OTP from email/console)
verify_data = {
    "email": "test@example.com",
    "otp": "12345678"  # Replace with actual OTP
}
response = requests.post(f"{BASE_URL}/verify-email/", json=verify_data)
print(response.json())

# Resend OTP if needed
resend_data = {
    "email": "test@example.com"
}
response = requests.post(f"{BASE_URL}/resend-otp/", json=resend_data)
print(response.json())
```

---

## 📱 JavaScript/Fetch Example

```javascript
const BASE_URL = "http://localhost:8000/api/v1/auth";

// Register user
async function registerUser() {
  const response = await fetch(`${BASE_URL}/register/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: 'test@example.com',
      password: 'SecurePass123!',
      confirm_password: 'SecurePass123!',
      first_name: 'Test',
      last_name: 'User'
    })
  });
  const data = await response.json();
  console.log(data);
}

// Verify email
async function verifyEmail(otp) {
  const response = await fetch(`${BASE_URL}/verify-email/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: 'test@example.com',
      otp: otp
    })
  });
  const data = await response.json();
  console.log(data);
}

// Resend OTP
async function resendOTP() {
  const response = await fetch(`${BASE_URL}/resend-otp/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: 'test@example.com'
    })
  });
  const data = await response.json();
  console.log(data);
}
```

---

## 🔍 Debugging Tips

### Check Logs
All operations are logged. Check your console for:
- `INFO`: Successful operations
- `WARNING`: Failed validations
- `ERROR`: Server errors

### Common Issues

1. **OTP not in email**: Check spam folder or console output
2. **"Invalid OTP"**: Ensure no extra spaces, must be 8 digits
3. **"User not found"**: Verify email spelling
4. **"Already verified"**: Account is ready, proceed to login
5. **Rate limited**: Wait for current OTP to expire

---

## 📊 HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Continue with next step |
| 400 | Bad Request | Check request data |
| 404 | Not Found | User doesn't exist |
| 410 | Gone | OTP expired, request new one |
| 429 | Too Many Requests | Wait before requesting new OTP |
| 500 | Server Error | Contact support |

---

## 🎯 Best Practices

### For Users
1. Check email immediately after registration
2. Verify within 10 minutes
3. Check spam folder if email not received
4. Use resend if OTP expired
5. Contact support if issues persist

### For Developers
1. Validate input on frontend before sending
2. Handle all HTTP status codes
3. Display clear error messages
4. Implement countdown timer for OTP expiration
5. Provide easy access to resend OTP
6. Log all verification attempts

---

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Review the logs
3. Try resending OTP
4. Contact support with:
   - Email address
   - Error message
   - Timestamp of attempt

---

**Last Updated**: December 1, 2025
**Version**: 1.0.0
