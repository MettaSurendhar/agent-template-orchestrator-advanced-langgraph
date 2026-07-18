from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Request

from api import settings
from api.exceptions.custom_exceptions import APIException, ErrorCode
from api.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from api.utils import pg_util
from api.utils.password_util import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


def _issue_token(user_id: str) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    return jwt.encode({"user_id": user_id, "exp": expiry}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/register", response_model=AuthResponse)
async def register(request: Request, body: RegisterRequest):
    """Create a new local user account, creating or joining a team by name, and return a bearer token."""
    pool = request.app.state.pg_pool

    if await pg_util.get_user_by_email(pool, body.email):
        raise APIException(
            status_code=409, error_code=ErrorCode.USER_ALREADY_EXISTS, message="An account with this email already exists."
        )

    team_id = await pg_util.get_or_create_team(pool, body.team_name)
    password_hash, salt = hash_password(body.password)
    user_id = await pg_util.create_local_user(pool, email=body.email, password_hash=password_hash, salt=salt, team_id=team_id)
    await pg_util.log_event(pool, team_id, user_id, None, "REGISTER", f"New account registered: {body.email}")

    return AuthResponse(access_token=_issue_token(user_id), user_id=user_id, team_id=team_id)


@router.post("/login", response_model=AuthResponse)
async def login(request: Request, body: LoginRequest):
    """Authenticate a local user and return a bearer token."""
    pool = request.app.state.pg_pool
    user = await pg_util.get_user_by_email(pool, body.email)

    if not user or user["auth_provider"] != "local" or not verify_password(body.password, user["password_hash"], user["salt"]):
        raise APIException(status_code=401, error_code=ErrorCode.UNAUTHORIZED, message="Invalid email or password.")

    await pg_util.log_event(pool, user["team_id"], user["user_id"], None, "LOGIN", f"User logged in: {body.email}")

    return AuthResponse(access_token=_issue_token(user["user_id"]), user_id=user["user_id"], team_id=user["team_id"])
