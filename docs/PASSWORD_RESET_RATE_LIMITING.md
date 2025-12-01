# Password Reset OTP Rate Limiting

## Overview

The password reset request endpoint implements **smart rate limiting** to ensure only one active OTP exists per user at any time. This prevents OTP flooding and ensures database integrity.

## Requirements Met

✅ **Single Active OTP Rule**: Only one unused, unexpired OTP can exist per user per code type
✅ **Automatic Cleanup**: Expired or used OTPs are automatically deleted
✅ **Resend Existing Code**: Active OTPs are resent instead of creating duplicates
✅ **Security Maintained**: Email enumeration prevention still in place
✅ **User-Friendly**: Users receive their code even if they request multiple times

## Implementation Details

### Logic Flow

```
User requests password reset
         ↓
Check if user exists
         ↓
Check for existing PASSWORD_RESET OTP
         ↓
    ┌────────────────────────────────┐
    │  Existing OTP Found?           │
    └────────────────────────────────┘
         ↓                    ↓
        YES                  NO
         ↓                    ↓
    Is it expired?      Create new OTP
         ↓                    ↓
    ┌────┴────┐         Send to email
   YES       NO              ↓
    ↓         ↓         Return success
Delete it  Resend it
    ↓         ↓
Create new  Return success
    ↓
Send to email
    ↓
Return success
```

### Database State Guarantee

**Before Implementation:**
```sql
-- Multiple OTPs could exist for same user + code_type
| user_id | code     | code_type      | is_used | expires_at          |
|---------|----------|----------------|---------|---------------------|
| user123 | 12345678 | PASSWORD_RESET | FALSE   | 2025-12-01 16:10:00 |
| user123 | 87654321 | PASSWORD_RESET | FALSE   | 2025-12-01 16:15:00 | ❌ Problem!
```

**After Implementation:**
```sql
-- Only ONE active OTP per user + code_type
| user_id | code     | code_type      | is_used | expires_at          |
|---------|----------|----------------|---------|---------------------|
| user123 | 12345678 | PASSWORD_RESET | FALSE   | 2025-12-01 16:10:00 | ✅ Only one!
```

## Code Implementation

### Location
`authentication/views.py` → `PasswordResetRequestView.post()`

### Key Logic

```python
# Check for existing OTP
try:
    existing_otp = Passcode.objects.get(
        user=user,
        code_type=choices.CodeType.PASSWORD_RESET,
        is_used=False
    )

    # If still valid, resend it
    if existing_otp.expires_at > timezone.now():
        send_code_to_user(
            email=user.email,
            otp_code=existing_otp.code,  # Same code!
            purpose="password_reset",
            expiry_text=format_expiry_time(existing_otp.expires_at)
        )
        return success_response
    else:
        # Expired - delete and create new
        existing_otp.delete()

except Passcode.DoesNotExist:
    # No existing OTP - proceed to create new
    pass

# Create new OTP (only if no active one exists)
create_and_send_otp(user, code_type, purpose)
```

## Scenarios

### Scenario 1: First Request

**User Action:** Requests password reset for the first time

**System Behavior:**
1. No existing OTP found
2. Creates new 8-digit OTP
3. Saves to database with `is_used=False`
4. Sends OTP via email
5. Returns success

**Database:**
```
| user_id | code     | code_type      | is_used | expires_at          |
|---------|----------|----------------|---------|---------------------|
| user123 | 12345678 | PASSWORD_RESET | FALSE   | 2025-12-01 16:34:00 |
```

### Scenario 2: Duplicate Request (Within 10 Minutes)

**User Action:** Requests password reset again (code still valid)

**System Behavior:**
1. Finds existing active OTP (`12345678`)
2. Checks expiration: Still valid (7 minutes remaining)
3. **Resends the SAME code** (`12345678`) via email
4. Returns success
5. **No new OTP created**

**Database:** (Unchanged)
```
| user_id | code     | code_type      | is_used | expires_at          |
|---------|----------|----------------|---------|---------------------|
| user123 | 12345678 | PASSWORD_RESET | FALSE   | 2025-12-01 16:34:00 |
```

**Email Sent:**
```
Subject: Password Reset Request

Your password reset code is: 12345678

This code expires in 7 minutes.
```

### Scenario 3: Request After Expiration

**User Action:** Requests password reset after 10+ minutes

**System Behavior:**
1. Finds existing OTP (`12345678`)
2. Checks expiration: **Expired**
3. **Deletes expired OTP**
4. Creates new OTP (`87654321`)
5. Sends new OTP via email
6. Returns success

**Database Before:**
```
| user_id | code     | code_type      | is_used | expires_at          |
|---------|----------|----------------|---------|---------------------|
| user123 | 12345678 | PASSWORD_RESET | FALSE   | 2025-12-01 16:34:00 | (expired)
```

**Database After:**
```
| user_id | code     | code_type      | is_used | expires_at          |
|---------|----------|----------------|---------|---------------------|
| user123 | 87654321 | PASSWORD_RESET | FALSE   | 2025-12-01 16:50:00 | (new)
```

### Scenario 4: Request After Successful Reset

**User Action:** Requests password reset after using previous code

**System Behavior:**
1. Finds existing OTP (`12345678`)
2. Checks `is_used`: **TRUE** (already used)
3. `create_and_send_otp` utility deletes used OTP
4. Creates new OTP (`87654321`)
5. Sends new OTP via email
6. Returns success

**Database Before:**
```
| user_id | code     | code_type      | is_used | expires_at          |
|---------|----------|----------------|---------|---------------------|
| user123 | 12345678 | PASSWORD_RESET | TRUE    | 2025-12-01 16:34:00 | (used)
```

**Database After:**
```
| user_id | code     | code_type      | is_used | expires_at          |
|---------|----------|----------------|---------|---------------------|
| user123 | 87654321 | PASSWORD_RESET | FALSE   | 2025-12-01 16:50:00 | (new)
```

## Benefits

### 1. Database Integrity
- ✅ No duplicate active OTPs
- ✅ Clean database state
- ✅ Easy to query and validate

### 2. User Experience
- ✅ Users can request multiple times without issues
- ✅ Same code works if requested again
- ✅ No confusion from multiple codes

### 3. Security
- ✅ Prevents OTP flooding
- ✅ Limits attack surface
- ✅ Maintains email enumeration protection

### 4. Performance
- ✅ Efficient database queries
- ✅ Automatic cleanup of expired codes
- ✅ No manual cleanup needed

## Logging

### Info Logs
```
Active password reset OTP exists for user@example.com. Resending same code. Expires in 7m
Existing password reset OTP resent to user@example.com
Found expired password reset OTP for user@example.com, deleting it
No active password reset OTP for user@example.com, will create new one
New password reset OTP sent to user@example.com
```

### Warning Logs
```
Password reset requested for non-existent email: unknown@example.com
```

### Error Logs
```
Failed to resend existing OTP: [error details]
Failed to send password reset OTP to user@example.com: [error details]
```

## API Response

**Important:** The API response is **always the same** regardless of whether we resent an existing code or created a new one. This prevents email enumeration attacks.

```json
{
  "message": "If an account exists with this email, a password reset code has been sent.",
  "data": {
    "email": "user@example.com",
    "expires_in": "10 minutes"
  }
}
```

## Comparison with Email Verification OTP

Both `ResendOTPView` (email verification) and `PasswordResetRequestView` now use the same smart rate limiting pattern:

| Feature | Email Verification | Password Reset |
|---------|-------------------|----------------|
| Code Type | `VERIFICATION` | `PASSWORD_RESET` |
| Check Active OTP | ✅ Yes | ✅ Yes |
| Resend if Active | ✅ Yes (429 response) | ✅ Yes (200 response) |
| Delete if Expired | ✅ Yes | ✅ Yes |
| Single Active OTP | ✅ Yes | ✅ Yes |
| Email Enumeration Protection | ❌ No (reveals user status) | ✅ Yes (always success) |

**Key Difference:** Email verification returns `429 Too Many Requests` when active OTP exists (user is authenticated), while password reset returns `200 OK` (user is not authenticated, security concern).

## Testing

### Test Cases

1. **First Request**
   - ✅ Creates new OTP
   - ✅ Sends email
   - ✅ Returns success

2. **Duplicate Request (Active OTP)**
   - ✅ Finds existing OTP
   - ✅ Resends same code
   - ✅ No new OTP created
   - ✅ Returns success

3. **Request After Expiration**
   - ✅ Deletes expired OTP
   - ✅ Creates new OTP
   - ✅ Sends new code
   - ✅ Returns success

4. **Request After Use**
   - ✅ Deletes used OTP
   - ✅ Creates new OTP
   - ✅ Sends new code
   - ✅ Returns success

5. **Non-Existent Email**
   - ✅ No OTP created
   - ✅ Still returns success (security)

## Summary

The password reset request endpoint now ensures **database integrity** by maintaining only one active OTP per user per code type, while still providing a **seamless user experience** and maintaining **security best practices**.

---

**Last Updated:** December 1, 2025
**Version:** 2.0
