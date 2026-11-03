from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.errors import ApplicationError
from app.services.auth import create_session_token, is_admin, verify_session

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(default="", max_length=100)
    role: str = Field(default="member")


class LoginResponse(BaseModel):
    username: str
    role: str
    token: str


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    username = body.username.strip()
    if not body.password:
        raise ApplicationError("invalid_credentials", "Username atau password salah.", 401)
    # ponytail: password checked against hardcoded demo credentials only;
    # upgrade to hashed-password store when real user management is added.
    _verify_credentials(username, body.password, settings)
    role = "admin" if is_admin(username, settings) else "member"
    token = create_session_token(username, role, settings)
    response.set_cookie(
        key="__session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=7 * 86400,
        path="/",
    )
    return LoginResponse(username=username, role=role, token=token)


# ponytail: replace with DB-backed credential store when needed.
_DEMO_CREDENTIALS: dict[str, str] = {
    "admin": "demo123",
    "reviewer": "demo123",
    "finance": "demo123",
    "salesman-001": "demo123",
    "finance@tera.id": "demo123",
    "karyawan@tera.id": "demo123",
}


def _verify_credentials(username: str, password: str, settings: Settings) -> None:
    if settings.environment != "production":
        if password in ("demo123", "any") or _DEMO_CREDENTIALS.get(username) == password:
            return
    elif _DEMO_CREDENTIALS.get(username) == password:
        return
    raise ApplicationError("invalid_credentials", "Username atau password salah.", 401)


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(key="__session", path="/")
    return {"ok": True}


def require_session(request: Request, settings: Settings = Depends(get_settings)) -> str:
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin != settings.frontend_origin.rstrip("/"):
            raise ApplicationError("invalid_origin", "Permintaan tidak diizinkan.", 403)
    if settings.demo_mode:
        return "demo-reviewer"
    authorization = request.headers.get("authorization")
    if authorization is not None:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token or " " in token:
            raise ApplicationError("authentication_required", "Silakan login kembali.", 401)
    else:
        token = request.cookies.get("__session", "")
    if not token:
        raise ApplicationError("authentication_required", "Silakan login ke Tera.", 401)
    return verify_session(token, settings)


def require_admin(request: Request, user_id: str = Depends(require_session), settings: Settings = Depends(get_settings)) -> str:
    if not settings.demo_mode and not is_admin(user_id, settings):
        raise ApplicationError("admin_access_required", "Akun ini belum memiliki akses admin.", 403)
    from app.services.rate_limit import enforce_write_limit

    enforce_write_limit(request, user_id, settings)
    return user_id


@router.get("/session")
def session(response: Response, user_id: str = Depends(require_session), settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    response.headers["Cache-Control"] = "no-store"
    result: dict[str, str | bool] = {"username": user_id, "role": "admin" if settings.demo_mode or is_admin(user_id, settings) else "member"}
    if settings.demo_mode:
        result["demo_mode"] = True
    return result
