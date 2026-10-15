from functools import lru_cache
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

from app.config import Settings
from app.errors import ApplicationError


@lru_cache(maxsize=8)
def signing_keys(issuer: str) -> PyJWKClient:
    return PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_jwk_set=True, lifespan=300, timeout=5)


def verify_session(token: str, settings: Settings) -> str:
    issuer = settings.clerk_issuer.rstrip("/")
    parsed = urlparse(issuer)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/") or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ApplicationError("auth_not_configured", "Layanan login belum dikonfigurasi.", 503)
    try:
        # Resolve keys only from the configured instance, never from token headers.
        key = signing_keys(issuer).get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], issuer=issuer, options={
            "require": ["exp", "nbf", "iat", "iss", "sub", "sid", "azp"],
        }, leeway=5)
        if claims["azp"] != settings.frontend_origin.rstrip("/"):
            raise jwt.InvalidTokenError("Unexpected authorized party")
        if not isinstance(claims["sub"], str) or not claims["sub"].startswith("user_"):
            raise jwt.InvalidTokenError("User session required")
        if not isinstance(claims["sid"], str) or not claims["sid"].startswith("sess_"):
            raise jwt.InvalidTokenError("User session required")
        if claims.get("sts", "active") != "active":
            raise jwt.InvalidTokenError("Session tasks incomplete")
        return claims["sub"]
    except PyJWKClientConnectionError as exc:
        raise ApplicationError("auth_unavailable", "Layanan verifikasi login belum dapat dihubungi. Coba lagi.", 503) from exc
    except jwt.PyJWTError as exc:
        raise ApplicationError("authentication_required", "Sesi berakhir atau tidak valid. Silakan login kembali.", 401) from exc


def is_admin(user_id: str, settings: Settings) -> bool:
    allowed = {value.strip() for value in settings.clerk_admin_user_ids.split(",") if value.strip()}
    return user_id in allowed
