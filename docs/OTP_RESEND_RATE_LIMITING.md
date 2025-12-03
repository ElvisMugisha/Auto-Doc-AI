# ✅ OTP Resend with Smart Rate Limiting - Final Implementation

## Summary

I've implemented **smart rate limiting** for the OTP resend functionality as requested:

### Requirements Met:
1. ✅ Check if user has an **active (unexpired and unused)** OTP before creating a new one
2. ✅ If active OTP exists → inform user and show remaining time (HTTP 429)
3. ✅ Only create new OTP if old one is **expired OR used**
4. ✅ Delete expired OTPs automatically before creating new ones

---

## Implementation Details

### Key Logic in `ResendOTPView`

```python
# 1. Check for existing unused OTP
existing_otp = Passcode.objects.get(
    user=user,
    code_type=choices.CodeType.VERIFICATION,
    is_used=False  # Only check unused OTPs
)

# 2. Check if OTP is still valid (not expired)
if existing_otp.expires_at > timezone.now():
    # OTP is ACTIVE - return error with remaining time
    return HTTP 429 with time remaining
else:
    # OTP is EXPIRED - delete it and create new one
    existing_otp.delete()
    create_and_send_otp(...)
```

---

## Flow Diagram

```
User Requests Resend OTP
         ↓
Check: Does user have unused OTP?
         ↓
    ┌────┴────┐
   NO        YES
    ↓          ↓
Create      Is OTP expired?
New OTP      ↓
    ↓     ┌──┴──┐
Send     NO    YES
Email     ↓      ↓
    ↓   Return Delete OTP
Success  429    ↓
         with  Create New
         time   ↓
              Send Email
                ↓
              Success
```

---

## API Response Examples

### Scenario 1: Active OTP Exists (Not Expired)

**Request:**
```bash
POST /api/v1/auth/resend-otp/
{
  "email": "user@example.com"
}
```

**Response (HTTP 429):**
```json
{
  "error": "An active verification code already exists.",
  "message": "Please use your existing verification code. It will expire in 8 minute(s) and 45 second(s).",
  "expires_in_seconds": 525,
  "expires_in_minutes": 8
}
```

---

### Scenario 2: OTP Expired - New One Created

**Request:**
```bash
POST /api/v1/auth/resend-otp/
{
  "email": "user@example.com"
}
```

**Response (HTTP 200):**
```json
{
  "message": "A new verification code has been sent to your email.",
  "data": {
    "email": "user@example.com",
    "expires_in": "10 minutes"
  }
}
```

---

### Scenario 3: No Existing OTP - New One Created

**Request:**
```bash
POST /api/v1/auth/resend-otp/
{
  "email": "user@example.com"
}
```

**Response (HTTP 200):**
```json
{
  "message": "A new verification code has been sent to your email.",
  "data": {
    "email": "user@example.com",
    "expires_in": "10 minutes"
  }
}
```

---

## Database State Examples

### Example 1: User Requests Resend with Active OTP

**Before Request:**
```
Passcode Table:
| user_id | code_type    | code     | is_used | expires_at          |
|---------|--------------|----------|---------|---------------------|
| user123 | VERIFICATION | 12345678 | FALSE   | 2025-12-01 15:05:00 |
```

**Current Time:** 2025-12-01 14:57:00
**Remaining:** 8 minutes

**Action:** Return HTTP 429 with remaining time
**Database:** No change

---

### Example 2: User Requests Resend with Expired OTP

**Before Request:**
```
Passcode Table:
| user_id | code_type    | code     | is_used | expires_at          |
|---------|--------------|----------|---------|---------------------|
| user123 | VERIFICATION | 12345678 | FALSE   | 2025-12-01 14:50:00 |
```

**Current Time:** 2025-12-01 14:57:00
**Status:** Expired (7 minutes ago)

**Action:** Delete old OTP, create new one

**After Request:**
```
Passcode Table:
| user_id | code_type    | code     | is_used | expires_at          |
|---------|--------------|----------|---------|---------------------|
| user123 | VERIFICATION | 87654321 | FALSE   | 2025-12-01 15:07:00 |
```

---

### Example 3: User Requests Resend with Used OTP

**Before Request:**
```
Passcode Table:
| user_id | code_type    | code     | is_used | expires_at          |
|---------|--------------|----------|---------|---------------------|
| user123 | VERIFICATION | 12345678 | TRUE    | 2025-12-01 15:05:00 |
```

**Action:** No OTP found (query filters `is_used=False`), create new one

**After Request:**
```
Passcode Table:
| user_id | code_type    | code     | is_used | expires_at          |
|---------|--------------|----------|---------|---------------------|
| user123 | VERIFICATION | 12345678 | TRUE    | 2025-12-01 15:05:00 |
| user123 | VERIFICATION | 99999999 | FALSE   | 2025-12-01 15:07:00 |
```

**Note:** Old used OTP remains in database (for audit trail)

---

## Complete Code

The correct implementation is saved in: `RESEND_OTP_VIEW_CORRECT.txt`

### Key Features:

1. **Rate Limiting Check**
   ```python
   existing_otp = Passcode.objects.get(
       user=user,
       code_type=choices.CodeType.VERIFICATION,
       is_used=False
   )
   ```

2. **Expiration Check**
   ```python
   if existing_otp.expires_at > timezone.now():
       # Still active - return 429
   else:
       # Expired - delete and create new
   ```

3. **Time Remaining Calculation**
   ```python
   remaining_time = existing_otp.expires_at - timezone.now()
   total_seconds = int(remaining_time.total_seconds())
   minutes_remaining = total_seconds // 60
   seconds_remaining = total_seconds % 60
   ```

4. **User-Friendly Message**
   ```python
   if minutes_remaining > 0:
       time_msg = f"{minutes_remaining} minute(s) and {seconds_remaining} second(s)"
   else:
       time_msg = f"{seconds_remaining} second(s)"
   ```

---

## Integration Steps

### To integrate the correct code into `authentication/views.py`:

1. **Locate the `ResendOTPView` class** (around line 306)
2. **Replace the entire class** with the code from `RESEND_OTP_VIEW_CORRECT.txt`
3. **Save the file**
4. **Restart the Django server**

---

## Testing

### Test 1: Request Resend with Active OTP

```bash
# 1. Register user
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User"
  }'

# 2. Immediately request resend (should get 429)
curl -X POST http://localhost:8000/api/v1/auth/resend-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }'

# Expected: HTTP 429 with remaining time
```

### Test 2: Request Resend After Expiration

```bash
# 1. Wait 10+ minutes after registration
# 2. Request resend
curl -X POST http://localhost:8000/api/v1/auth/resend-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }'

# Expected: HTTP 200 with new OTP sent
```

### Test 3: Request Resend After Verification

```bash
# 1. Verify email first
curl -X POST http://localhost:8000/api/v1/auth/verify-email/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "otp": "12345678"
  }'

# 2. Try to resend
curl -X POST http://localhost:8000/api/v1/auth/resend-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }'

# Expected: HTTP 400 (user already verified)
```

---

## Benefits

### 1. **Prevents OTP Spam**
- Users can't request unlimited OTPs
- Must wait for current OTP to expire

### 2. **Better User Experience**
- Clear message about remaining time
- No confusion about which OTP to use

### 3. **Security**
- Limits brute force attempts
- Prevents OTP flooding

### 4. **Clean Database**
- Expired OTPs automatically deleted
- Only one active OTP per user per type

---

## Summary

### What Changed:
- ✅ Added check for existing unused OTP
- ✅ Added expiration validation
- ✅ Return HTTP 429 if OTP still active
- ✅ Delete expired OTPs before creating new ones
- ✅ Show remaining time in error message

### What Stayed the Same:
- ✅ OTP created with `is_used=False`
- ✅ OTP marked as `is_used=True` only on verification
- ✅ `create_otp_for_user()` deletes all existing OTPs

---

**Implementation Date**: December 1, 2025
**Status**: ✅ Complete - Code Ready in `RESEND_OTP_VIEW_CORRECT.txt`
**Next Step**: Copy code from txt file to `authentication/views.py`
