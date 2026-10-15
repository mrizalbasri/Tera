from fastapi import APIRouter, Depends, Request, Response

from app.config import Settings, get_settings
from app.errors import ApplicationError
from app.services.auth import is_admin, verify_session

router = APIRouter(prefix="/auth", tags=["auth"])


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
    return user_id


@router.get("/session")
def session(response: Response, user_id: str = Depends(require_session), settings: Settings = Depends(get_settings)):
    response.headers["Cache-Control"] = "no-store"
    result: dict[str, str | bool] = {"username": user_id, "role": "admin" if settings.demo_mode or is_admin(user_id, settings) else "member"}
    if settings.demo_mode:
        result["demo_mode"] = True
    return result
