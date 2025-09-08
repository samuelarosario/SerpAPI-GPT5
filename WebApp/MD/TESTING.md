# WebApp Testing Strategy (Bootstrap)

## Layers
- Unit: hashing, jwt helpers
- API: auth endpoints (register, login, refresh)

## Tools
- `pytest`
- `fastapi.testclient`

## Running Tests (after installing root requirements)
```
pytest WebApp/tests -q
```

## Future Enhancements
- Add negative tests (invalid email format, weak password policy once enforced)
- Add load tests for auth endpoints
- Add security tests for token tampering
