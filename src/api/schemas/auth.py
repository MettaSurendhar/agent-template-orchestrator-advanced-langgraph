from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    """New user registration payload. Creates the team if `team_name` doesn't exist yet,
    or joins it if it does — this is how multiple users end up sharing run visibility."""

    email: EmailStr
    password: str
    team_name: str


class LoginRequest(BaseModel):
    """Login payload (local auth only — SSO users authenticate via Azure AD directly)."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Returned after successful registration or login."""

    access_token: str
    token_type: str = "bearer"
    user_id: str
    team_id: str
