# Authentication Specification (Initial)

## Overview
Provides email+password registration and JWT-based authentication.

## Endpoints
| Method | Path | Body | Response | Notes |
|--------|------|------|----------|-------|
| POST | /auth/register | { email, password } | UserRead | 201 Created |
| POST | /auth/login | { email, password } | TokenPair | Issues access & refresh |
| POST | /auth/refresh | token (query) | TokenPair | Requires refresh token |

## Token Claims
- sub: user id
- exp: expiry (UTC)
- type: refresh (only for refresh tokens)

## Password Policy (Future)
- Minimum length 12
- At least 1 upper, 1 lower, 1 digit, 1 symbol

## Error Codes
- 400 email already registered
- 401 invalid credentials / invalid token

## Future Items
- Revoke / logout (refresh rotation)
- Email verification
- Password reset flow
