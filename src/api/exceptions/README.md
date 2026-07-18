# src/api/exceptions

[#src-api-exceptions](#src-api-exceptions)

Same pattern as every tier in this family: `APIException` + `ErrorCode` enum, one exception handler registered in `app.py`. This tier's enum adds auth-related codes (`TOKEN_EXPIRED`, `USER_NOT_FOUND`, `USER_ALREADY_EXISTS`) on top of the POC tier's set.

## Conventions

- Never raise a bare exception — always `APIException` with a code from `ErrorCode`.
- Add new codes to the enum rather than inlining strings.
