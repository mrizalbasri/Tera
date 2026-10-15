from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from fastapi import Depends, Request

from app.api.auth import require_session
from app.api.deps import get_claim_repository
from app.config import Settings, get_settings
from app.errors import NotFoundError
from app.repositories.protocols import ClaimRepository
from app.services.auth import is_admin


@dataclass(frozen=True)
class ClaimActor:
    user_id: str
    admin: bool = False
    demo: bool = False

    def employee_id(self, supplied: str | None) -> str:
        return (supplied or "") if self.demo else self.user_id

    def idempotency_key(self, key: str | None, operation: str) -> str | None:
        if key is None or self.demo:
            return key
        digest = sha256(f"{self.user_id}\0{operation}\0{key}".encode()).hexdigest()
        return f"actor:{digest}"


def get_claim_actor(
    request: Request,
    user_id: str = Depends(require_session),
    settings: Settings = Depends(get_settings),
) -> ClaimActor:
    return ClaimActor(user_id, settings.demo_mode or is_admin(user_id, settings), settings.demo_mode)


def require_claim_access(
    claim_id: UUID,
    actor: ClaimActor = Depends(get_claim_actor),
    claims: ClaimRepository = Depends(get_claim_repository),
) -> None:
    claim = claims.get(claim_id)
    # Foreign identifiers have the same response as missing claims.
    if claim is None or (not actor.admin and claim.employee_id != actor.user_id):
        raise NotFoundError("Claim", str(claim_id))
