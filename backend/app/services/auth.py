from datetime import UTC, datetime, timedelta
import jwt

from app.config import Settings
from app.errors import ApplicationError


def create_session_token(
    user_id: str,
    role: str,
    settings: Settings,
    expires_in_days: int = 7,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=expires_in_days)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_session(token: str, settings: Settings) -> str:
    if not settings.secret_key:
        raise ApplicationError("auth_not_configured", "Layanan login belum dikonfigurasi.", 503)
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub"]},
            leeway=5,
        )
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub.strip():
            raise jwt.InvalidTokenError("User session required")
        return sub.strip()
    except jwt.ExpiredSignatureError as exc:
        raise ApplicationError("authentication_required", "Sesi berakhir atau tidak valid. Silakan login kembali.", 401) from exc
    except jwt.PyJWTError as exc:
        raise ApplicationError("authentication_required", "Sesi berakhir atau tidak valid. Silakan login kembali.", 401) from exc


def get_token_role(token: str, settings: Settings) -> str:
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub"]},
            leeway=5,
        )
        return str(claims.get("role", "member"))
    except jwt.PyJWTError:
        return "member"


def is_admin(user_id: str, settings: Settings) -> bool:
    if settings.demo_mode:
        return True
    admin_spec = getattr(settings, "admin_users", "") or getattr(settings, "clerk_admin_user_ids", "")
    allowed = {value.strip().lower() for value in admin_spec.split(",") if value.strip()}
    norm_user = user_id.strip().lower()
    if norm_user in allowed:
        return True
    return any(norm_user.startswith(prefix) for prefix in ("admin", "reviewer", "finance"))
