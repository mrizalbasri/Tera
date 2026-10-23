"""Immutable policy publications; drafts are replaced with compare-and-swap."""

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from pydantic import Field, model_validator

from app.errors import ApplicationError, ErrorCode, NotFoundError
from app.schemas.core import Policy, PolicyRule, SchemaBase
from app.audit.events import record_audit_event
from app.domain.enums import ActorType

POLICY_CATEGORIES = ("meals", "fuel", "hotel", "toll_parking", "other")
RULE_TYPES = {"max_amount", "max_amount_per_person", "receipt_required", "vendor_required",
              "evidence_required", "amount_matches_declared", "prohibited_items"}


class PolicyDraft(SchemaBase):
    category: Literal["meals", "fuel", "hotel", "toll_parking", "other"]
    effective_from: date
    effective_to: date | None = None
    source: str = Field(min_length=1, max_length=20000)
    rules: list[PolicyRule] = Field(max_length=50)

    @model_validator(mode="after")
    def valid_rules(self):
        if not self.source.strip() or (self.effective_to is not None and self.effective_to < self.effective_from):
            raise ValueError("Source and effective dates must be valid")
        ids = [r.rule_id for r in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("Rule IDs must be unique")
        if not self.rules and self.category != "other":
            raise ValueError("This category requires at least one rule")
        for rule in self.rules:
            if rule.rule_type not in RULE_TYPES or rule.currency != "IDR":
                raise ValueError("Unsupported rule or currency")
            if rule.rule_type.startswith("max_amount") and (rule.limit is None or not rule.limit.is_finite() or rule.limit <= 0):
                raise ValueError("Amount limits must be finite and positive")
            if rule.rule_type in ("vendor_required", "evidence_required") and not rule.required_terms:
                raise ValueError("Required terms must not be empty")
            if rule.rule_type == "prohibited_items" and not rule.prohibited_terms:
                raise ValueError("Prohibited terms must not be empty")
            if any(not term.strip() or len(term) > 255 for term in [*rule.required_terms, *rule.prohibited_terms]):
                raise ValueError("Terms must contain 1 to 255 characters")
            rule.required_terms = [term.strip().lower() for term in rule.required_terms]
            rule.prohibited_terms = [term.strip().lower() for term in rule.prohibited_terms]
        return self


class PolicyVersionService:
    def __init__(self, backend, resources) -> None:
        self.backend, self.store, self.resources = backend, backend.operational, resources

    def list(self, *, limit: int = 100, offset: int = 0) -> list[dict]:
        return self.store.list("policy_versions", limit=limit, offset=offset)

    def create(self, draft: PolicyDraft, actor: str) -> dict:
        now = datetime.now(UTC).isoformat()
        with self.resources.transaction():
            record = self.store.insert({"id": str(uuid4()), "namespace": "policy_versions", "owner": "company",
                                  "aggregate_id": draft.category, "created_at": now, "revision": 1,
                                  "payload": {"draft": draft.model_dump(mode="json"), "status": "draft",
                                              "created_by": actor, "published_by": None, "published_at": None}})
            self._audit(record, "policy.draft_created", actor)
            return record

    def _audit(self, record: dict, event: str, actor: str) -> None:
        record_audit_event(self.backend.audit, aggregate_type="policy_version", aggregate_id=UUID(record["id"]),
            event_type=event, actor_type=ActorType.REVIEWER,
            safe_payload={"actor_reference": actor, "revision": record["revision"], "category": record["aggregate_id"],
                          "fingerprint": record["payload"].get("fingerprint")})

    def seed_baseline(self, actor: str) -> list[dict]:
        from app.integrations.policy_local import LocalPolicyRetriever

        records = []
        with self.resources.claim_lock(uuid5(NAMESPACE_URL, "tera:policy-publication")), self.resources.transaction():
            for category in POLICY_CATEGORIES:
                id = str(uuid5(NAMESPACE_URL, f"tera:baseline-policy:{category}:1"))
                existing = self.store.get(id)
                if existing is not None:
                    records.append(existing)
                    continue
                policy = LocalPolicyRetriever().retrieve(category=category, effective_date=date(2026, 1, 1))
                payload = policy.model_dump(mode="json")
                fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                now = datetime.now(UTC).isoformat()
                record = self.store.insert({"id": id, "namespace": "policy_versions", "owner": "company",
                    "aggregate_id": category, "created_at": now, "revision": 1, "payload": {
                        "draft": {"category": category, "effective_from": "2026-01-01", "effective_to": None,
                                  "rules": payload["rules"], "source": "Kebijakan awal dari konfigurasi Tera; isi asli dipertahankan."},
                        "status": "published", "created_by": actor, "published_by": actor, "published_at": now,
                        "policy": payload, "fingerprint": fingerprint}})
                self._audit(record, "policy.baseline_imported", actor)
                records.append(record)
        return records

    def get(self, id: UUID) -> dict:
        record = self.store.get(str(id))
        if record is None or record["namespace"] != "policy_versions":
            raise NotFoundError("Policy version", str(id))
        return record

    def edit(self, id: UUID, draft: PolicyDraft, revision: int, actor: str) -> dict:
        with self.resources.claim_lock(uuid5(NAMESPACE_URL, "tera:policy-publication")), self.resources.transaction():
            record = self.get(id)
            if record["payload"]["status"] != "draft":
                raise ApplicationError("policy_immutable", "Versi terbit tidak dapat diubah. Buat draft baru.", 409)
            if draft.category != record["aggregate_id"]:
                raise ApplicationError("invalid_policy", "Kategori draft tidak dapat diubah.", 422)
            saved = self.store.replace({**record, "payload": {**record["payload"], "draft": draft.model_dump(mode="json"),
                                                              "updated_by": actor}}, revision=revision)
            self._audit(saved, "policy.draft_updated", actor)
            return saved

    def publish(self, id: UUID, revision: int, actor: str) -> dict:
        with self.resources.claim_lock(uuid5(NAMESPACE_URL, "tera:policy-publication")), self.resources.transaction():
            record = self.get(id)
            if record["revision"] != revision or record["payload"]["status"] != "draft":
                raise ApplicationError("record_changed", "Draft sudah berubah atau diterbitkan. Muat ulang.", 409)
            draft = PolicyDraft.model_validate(record["payload"]["draft"])
            previous = [r for r in self.store.list("policy_versions", aggregate_id=draft.category, limit=10000)
                        if r["payload"]["status"] == "published"]
            for row in previous:
                policy = Policy.model_validate(row["payload"]["policy"])
                supersedes_open = policy.effective_to is None and draft.effective_from > policy.effective_from
                if not supersedes_open and draft.effective_from <= (policy.effective_to or date.max) and policy.effective_from <= (draft.effective_to or date.max):
                    raise ApplicationError("policy_dates_overlap", "Tanggal berlaku bertumpang tindih dengan versi terbit.", 409)
            version = max((r["payload"]["policy"]["version"] for r in previous), default=1) + 1
            policy = Policy(policy_id="expense-policy", version=version, category=draft.category,
                            effective_from=draft.effective_from, effective_to=draft.effective_to, rules=draft.rules)
            payload = policy.model_dump(mode="json")
            fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            saved = self.store.replace({**record, "payload": {**record["payload"], "status": "published", "policy": payload,
                "fingerprint": fingerprint, "published_by": actor, "published_at": datetime.now(UTC).isoformat()}}, revision=revision)
            self._audit(saved, "policy.published", actor)
            return saved

    def effective(self, category: str, effective_date: date) -> Policy | None:
        published = [r for r in self.store.list("policy_versions", aggregate_id=category, limit=10000)
                     if r["payload"]["status"] == "published"]
        policies = [Policy.model_validate(row["payload"]["policy"]) for row in published]
        started = sorted((p for p in policies if p.effective_from <= effective_date),
                         key=lambda p: (p.effective_from, p.version), reverse=True)
        if started and effective_date <= (started[0].effective_to or date.max):
            return started[0]
        if policies and effective_date >= min(p.effective_from for p in policies):
            raise ApplicationError("policy_date_gap", "Tidak ada versi kebijakan yang berlaku pada tanggal nota.", 503)
        return None


class VersionedPolicyRetriever:
    def __init__(self, versions: PolicyVersionService, fallback) -> None:
        self.versions, self.fallback = versions, fallback

    def retrieve(self, *, category: str, effective_date: date) -> Policy:
        return self.versions.effective(category, effective_date) or self.fallback.retrieve(category=category, effective_date=effective_date)

    def retrieve_with_provenance(self, *, category: str, effective_date: date, context):
        policy = self.versions.effective(category, effective_date)
        if policy is None and hasattr(self.fallback, "retrieve_with_provenance"):
            return self.fallback.retrieve_with_provenance(category=category, effective_date=effective_date, context=context)
        policy = policy or self.fallback.retrieve(category=category, effective_date=effective_date)
        return FullPolicySelection(policy)


class FullPolicySelection:
    def __init__(self, policy: Policy) -> None:
        self.policy = policy

    def require_policy(self) -> Policy:
        return self.policy

    def audit_payload(self) -> dict:
        return {"policy_id": self.policy.policy_id, "policy_version": self.policy.version,
                "category": self.policy.category, "source": "full_versioned_policy"}
