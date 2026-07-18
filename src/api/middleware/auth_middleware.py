"""Dual-mode auth: local JWT (HS256, issued by /auth/login) or Azure AD SSO (RS256,
verified against the tenant's JWKS endpoint). Both paths resolve to the same thing —
`request.state.user_id` and `request.state.team_id` — so routers don't need to care
which auth mode a given request used.

SSO users are auto-onboarded into `settings.default_team_id` on first login — there's no
separate "register" step for them, unlike local auth.
"""

import jwt
from fastapi.responses import JSONResponse
from jwt import PyJWKClient

from api import settings
from api.exceptions.custom_exceptions import APIException, ErrorCode
from api.utils import pg_util

PUBLIC_PATHS = ["/ping", "/docs", "/openapi.json", "/redoc", "/auth/register", "/auth/login"]

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/discovery/v2.0/keys"
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


async def auth_middleware(request, call_next):
    """Verify the bearer token (local or SSO) and attach user_id/team_id to request.state."""
    if request.method == "OPTIONS" or any(request.url.path.startswith(p) for p in PUBLIC_PATHS):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return _error_response(401, ErrorCode.UNAUTHORIZED, "Missing bearer token.")

    token = auth_header.removeprefix("Bearer ").strip()
    pool = request.app.state.pg_pool

    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg")

        if alg == "HS256":
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            user = await pg_util.get_user_by_id(pool, payload["user_id"])
            if not user:
                return _error_response(401, ErrorCode.USER_NOT_FOUND, "Token refers to an unknown user.")

        elif alg == "RS256":
            if not settings.azure_tenant_id or not settings.azure_client_id:
                return _error_response(401, ErrorCode.UNAUTHORIZED, "Azure AD SSO is not configured on this server.")

            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token, signing_key.key, algorithms=["RS256"], audience=settings.azure_client_id
            )
            email = payload.get("preferred_username") or payload.get("email") or payload.get("upn")
            if not email:
                return _error_response(401, ErrorCode.UNAUTHORIZED, "SSO token has no usable identity claim.")

            user = await pg_util.get_or_create_sso_user(pool, email, settings.default_team_id)

        else:
            return _error_response(401, ErrorCode.UNAUTHORIZED, f"Unsupported token algorithm: {alg}")

    except jwt.ExpiredSignatureError:
        return _error_response(401, ErrorCode.TOKEN_EXPIRED, "Token has expired. Please log in again.")
    except jwt.InvalidTokenError as e:
        return _error_response(401, ErrorCode.UNAUTHORIZED, "Invalid token.", str(e))
    except Exception as e:
        return _error_response(401, ErrorCode.UNAUTHORIZED, "Token verification failed.", str(e))

    request.state.user_id = user["user_id"]
    request.state.team_id = user["team_id"]

    return await call_next(request)


def _error_response(status_code: int, error_code: ErrorCode, message: str, details: str | None = None) -> JSONResponse:
    exc = APIException(status_code=status_code, error_code=error_code, message=message, details=details)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code.value, "message": exc.message, "details": exc.details},
    )
