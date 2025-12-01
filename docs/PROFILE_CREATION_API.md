# User Profile Creation API

## Overview

The User Profile Creation API allows authenticated users to create their profile information. This is a one-time action per user, as each user can only have one profile.

## Endpoint

**URL:** `/api/v1/auth/profile/create/`
**Method:** `POST`
**Authentication:** Required (Bearer Token)

## Request

### Headers
- `Authorization`: `Bearer <access_token>`
- `Content-Type`: `application/json` (or `multipart/form-data` if uploading image)

### Body Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bio` | string | No | User's biography |
| `phone_number` | string | No | Contact phone number (max 20 chars) |
| `dob` | date | No | Date of birth (YYYY-MM-DD) |
| `profile_picture` | file | No | Profile image file |
| `gender` | string | No | Gender (MALE, FEMALE, OTHER) |
| `occupation` | string | No | User's occupation |
| `country` | string | No | Country of residence |
| `city` | string | No | City of residence |
| `street` | string | No | Street address |
| `zip_code` | string | No | Postal/Zip code |

### Example Request

```json
{
  "bio": "Experienced software engineer passionate about AI.",
  "phone_number": "+1234567890",
  "dob": "1990-01-01",
  "gender": "MALE",
  "occupation": "Software Engineer",
  "country": "USA",
  "city": "San Francisco",
  "street": "123 Tech Lane",
  "zip_code": "94105"
}
```

## Response

### Success (201 Created)

Returns the created profile data.

```json
{
  "bio": "Experienced software engineer passionate about AI.",
  "phone_number": "+1234567890",
  "dob": "1990-01-01",
  "profile_picture": null,
  "gender": "MALE",
  "occupation": "Software Engineer",
  "country": "USA",
  "city": "San Francisco",
  "street": "123 Tech Lane",
  "zip_code": "94105"
}
```

### Error (400 Bad Request)

- **Profile Already Exists:**
  ```json
  {
    "error": "Profile already exists for this user. Please use the update endpoint to modify your profile."
  }
  ```

- **Validation Error:**
  ```json
  {
    "phone_number": [
      "Ensure this field has no more than 20 characters."
    ]
  }
  ```

### Error (401 Unauthorized)

- **Authentication Failed:**
  ```json
  {
    "detail": "Authentication credentials were not provided."
  }
  ```

## Implementation Details

- **View Class:** `UserProfileCreateView` in `authentication/views.py`
- **Serializer:** `ProfileSerializer` in `authentication/serializers.py`
- **Permissions:** `IsAuthenticated`
- **Logic:**
  - Checks if `request.user` already has a related `user_profile`.
  - If yes, returns 400 Bad Request.
  - If no, validates data and saves the profile with `user=request.user`.
