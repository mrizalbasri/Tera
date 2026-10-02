from collections.abc import Sequence
from threading import RLock
from uuid import UUID

from app.schemas.core import Claim, Receipt


class InMemoryClaimStore:
    def __init__(self) -> None:
        self._claims: dict[UUID, Claim] = {}
        self._receipts: dict[UUID, list[Receipt]] = {}
        self._idempotency: dict[str, UUID] = {}
        self._content_hashes: dict[str, UUID] = {}
        self._content: dict[str, bytes] = {}
        self._lock = RLock()

    def get(self, claim_id: UUID) -> Claim | None:
        with self._lock:
            return self._claims.get(claim_id)

    def list(self, *, employee_id: str | None = None) -> Sequence[Claim]:
        with self._lock:
            claims = tuple(self._claims.values())
        if employee_id is None:
            return claims
        return tuple(claim for claim in claims if claim.employee_id == employee_id)

    def save_claim(self, claim: Claim, *, idempotency_key: str | None = None) -> Claim:
        with self._lock:
            self._claims[claim.id] = claim
            self._receipts.setdefault(claim.id, [])
            if idempotency_key:
                self._idempotency[idempotency_key] = claim.id
        return claim

    def save_receipt(self, receipt: Receipt, *, content: bytes) -> Receipt:
        with self._lock:
            self._receipts.setdefault(receipt.claim_id, []).append(receipt)
            self._content_hashes[receipt.content_hash] = receipt.claim_id
            self._content[receipt.storage_reference] = content
        return receipt

    def list_receipts(self, claim_id: UUID) -> Sequence[Receipt]:
        with self._lock:
            return tuple(self._receipts.get(claim_id, ()))

    def get_by_idempotency_key(self, key: str) -> Claim | None:
        with self._lock:
            claim_id = self._idempotency.get(key)
            return self._claims.get(claim_id) if claim_id else None

    def get_claim_by_content_hash(self, content_hash: str) -> UUID | None:
        with self._lock:
            return self._content_hashes.get(content_hash)

    def get_content(self, storage_reference: str) -> bytes | None:
        with self._lock:
            return self._content.get(storage_reference)
