# ⚠️ IMPORTANT: User Model Fix

## Issue
The User model uses `EMAIL_AS_USERNAME`, which means:
- Email is used as the username
- You should NOT pass both `email` and `username` to `create_user()`
- Only pass `email` and `password`

## Fixed Files
- ✅ `conftest.py` - Removed username from fixtures

## Files That Need Fixing

### Test Files with username parameter:
1. `tests/test_authentication.py` - Line 130
2. `tests/test_document_upload.py` - Lines 196, 231, 259
3. `tests/test_rate_limiting.py` - Line 181
4. `tests/test_api.py` - Line 106

## How to Fix

### ❌ WRONG:
```python
User.objects.create_user(
    email='user@example.com',
    username='username',  # ❌ Don't pass this
    password='password'
)
```

### ✅ CORRECT:
```python
User.objects.create_user(
    email='user@example.com',
    password='password'
)
```

## Registration API

The registration endpoint also needs `confirm_password`. Update tests:

### ❌ WRONG:
```python
data = {
    'email': 'user@example.com',
    'username': 'username',  # ❌ Remove
    'password': 'Pass123!'
}
```

### ✅ CORRECT:
```python
data = {
    'email': 'user@example.com',
    'password': 'Pass123!',
    'confirm_password': 'Pass123!',  # ✅ Add this
    'first_name': 'First',
    'last_name': 'Last'
}
```

## Quick Fix Command

Run this to find all occurrences:
```bash
grep -r "username=" tests/
```

Then remove the `username=` parameter from all `create_user()` and `create_superuser()` calls.
