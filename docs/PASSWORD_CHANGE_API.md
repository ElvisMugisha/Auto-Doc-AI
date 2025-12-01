# Password Change API Documentation

## Overview

The Password Change API allows authenticated users to securely change their password by providing their current password for verification and a new password that meets complexity requirements.

## Endpoint

**URL:** `/api/v1/auth/password/change/`
**Method:** `POST`
**Authentication:** Required (Bearer Token)

## Request

### Headers
- `Authorization`: `Bearer <access_token>`
- `Content-Type`: `application/json`

### Body Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `old_password` | string | Yes | Current password for verification |
| `new_password` | string | Yes | New password (must meet complexity requirements) |
| `confirm_new_password` | string | Yes | Confirmation of new password |

### Password Requirements

The new password must meet Django's default password validation requirements:
- Minimum 8 characters
- Cannot be too similar to other personal information
- Cannot be a commonly used password
- Cannot be entirely numeric

### Example Request

```json
{
  "old_password": "OldPassword123!",
  "new_password": "NewSecurePassword456!",
  "confirm_new_password": "NewSecurePassword456!"
}
```

## Response

### Success (200 OK)

```json
{
  "message": "Password changed successfully.",
  "data": {
    "email": "user@example.com",
    "changed_at": "2025-12-01T15:54:26.123456Z"
  }
}
```

### Error Responses

#### 400 Bad Request - Incorrect Old Password

```json
{
  "old_password": [
    "Current password is incorrect."
  ]
}
```

#### 400 Bad Request - Passwords Don't Match

```json
{
  "confirm_new_password": [
    "New passwords do not match."
  ]
}
```

#### 400 Bad Request - New Password Same as Old

```json
{
  "new_password": [
    "New password must be different from current password."
  ]
}
```

#### 400 Bad Request - Password Complexity Error

```json
{
  "new_password": [
    "This password is too short. It must contain at least 8 characters.",
    "This password is too common."
  ]
}
```

#### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### 500 Internal Server Error

```json
{
  "error": "An unexpected error occurred while changing password. Please try again later."
}
```

## Implementation Details

### Serializer: `PasswordChangeSerializer`

Located in `authentication/serializers.py`

**Validation Steps:**
1. **Old Password Validation** (`validate_old_password`):
   - Verifies the old password matches the user's current password
   - Uses Django's `check_password()` method

2. **New Password Complexity** (`validate_new_password`):
   - Validates against Django's password validators
   - Checks length, similarity, common passwords, etc.

3. **Cross-field Validation** (`validate`):
   - Ensures new passwords match
   - Ensures new password differs from old password

### View: `PasswordChangeView`

Located in `authentication/views.py`

**Features:**
- Requires authentication (`IsAuthenticated` permission)
- Passes request context to serializer for user access
- Uses `set_password()` to properly hash the new password
- Updates only the password field for efficiency
- Comprehensive logging for security monitoring
- Detailed error handling and user feedback

## Security Considerations

1. **Authentication Required**: Only authenticated users can change passwords
2. **Old Password Verification**: Prevents unauthorized password changes
3. **Password Hashing**: Uses Django's secure password hashing
4. **Complexity Requirements**: Enforces strong password policies
5. **Logging**: All password change attempts are logged for security monitoring
6. **No Password Exposure**: Passwords are write-only fields

## Usage Example

### Using cURL

```bash
curl -X POST http://localhost:8000/api/v1/auth/password/change/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "OldPassword123!",
    "new_password": "NewSecurePassword456!",
    "confirm_new_password": "NewSecurePassword456!"
  }'
```

### Using Python Requests

```python
import requests

url = "http://localhost:8000/api/v1/auth/password/change/"
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "old_password": "OldPassword123!",
    "new_password": "NewSecurePassword456!",
    "confirm_new_password": "NewSecurePassword456!"
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

## Testing

### Test Cases

1. **Successful Password Change**
   - Valid old password
   - Strong new password
   - Matching confirmation

2. **Incorrect Old Password**
   - Should return 400 with specific error

3. **Weak New Password**
   - Should return 400 with complexity errors

4. **Mismatched New Passwords**
   - Should return 400 with mismatch error

5. **Same Old and New Password**
   - Should return 400 with error

6. **Unauthenticated Request**
   - Should return 401

## Best Practices

1. **Force Re-login**: Consider invalidating existing tokens after password change
2. **Email Notification**: Send email notification when password is changed
3. **Rate Limiting**: Implement rate limiting to prevent brute force attacks
4. **Password History**: Consider preventing reuse of recent passwords
5. **Session Management**: Invalidate all other sessions when password changes

## Related Endpoints

- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/verify-email/` - Email verification
- `POST /api/v1/auth/profile/create/` - Profile management

---

**Last Updated:** December 1, 2025
**Version:** 1.0
