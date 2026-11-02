from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from app.errors import ApplicationError, NotFoundError

NAMESPACE = "notifications"
MESSAGES = {
    "needs_clarification": "Klaim membutuhkan informasi tambahan.",
    "escalated": "Klaim menunggu pemeriksaan finance.",
    "approved": "Klaim disetujui. Ini belum merupakan konfirmasi pembayaran.",
    "rejected": "Klaim ditolak. Buka detail untuk melihat alasan.",
}


def reconcile_notifications(settings) -> None:
    from app.api.deps import _backend
    from app.agent.runtime import graph_resources
    from app.repositories.query import ClaimFilter

    backend = _backend(settings)
    service = NotificationService(backend, settings)
    resources = graph_resources(backend, settings)
    for status in ("needs_clarification", "escalated"):
        offset = 0
        while batch := backend.claims.page(ClaimFilter(status=status), limit=200, offset=offset):
            for claim in batch:
                try:
                    with resources.claim_lock(claim.id, timeout=0), resources.transaction():
                        service.sync_claim(claim.id)
                except ApplicationError as exc:
                    if exc.code != "claim_busy":
                        raise
            offset += len(batch)


class NotificationService:
    def __init__(self, backend, settings) -> None:
        self.backend, self.settings = backend, settings
        self.store = backend.operational

    def sync_claim(self, claim_id: UUID, *, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        claim = self.backend.claims.get(claim_id)
        if claim is None:
            return
        status = str(claim.status)
        if status == "needs_clarification":
            question = self.backend.clarifications.latest_for_claim(claim.id)
            event = str(question.id) if question else str(claim.updated_at)
        elif status == "escalated":
            reviews = [r for r in self.backend.reviews.list_for_claim(claim.id) if r.status == "open"]
            event = str(reviews[-1].id) if reviews else str(claim.updated_at)
        else:
            event = str(claim.current_decision_id or claim.updated_at)
        for row in self.store.list(NAMESPACE, aggregate_id=str(claim_id), limit=10000):
            payload = row["payload"]
            if not payload["resolved"] and (payload["event"] != event or payload["status"] != status):
                self.store.replace({**row, "payload": {**payload, "resolved": True}}, revision=row["revision"])
        if status not in MESSAGES:
            return
        recipients = {claim.employee_id}
        if status == "escalated":
            recipients = {u.strip() for u in (self.settings.admin_users + "," + self.settings.clerk_admin_user_ids).split(",") if u.strip()}
            if self.settings.demo_mode:
                recipients.add("demo-reviewer")
        for recipient in recipients:
            self._insert(claim, recipient, status, event, now, reminder=False)
            if status in ("needs_clarification", "escalated") and now - claim.updated_at >= timedelta(hours=24):
                self._insert(claim, recipient, status, event, now, reminder=True)

    def _insert(self, claim, recipient: str, status: str, event: str, now: datetime, *, reminder: bool) -> None:
        key = f"{claim.id}:{recipient}:{event}:{status}"
        if reminder:
            key += f":reminder:{now.date()}"
        self.store.insert({
            "id": str(uuid5(NAMESPACE_URL, key)), "namespace": NAMESPACE, "owner": recipient,
            "aggregate_id": str(claim.id), "created_at": now.isoformat(), "revision": 1,
            "payload": {"claim_id": str(claim.id), "event": event, "status": status,
                        "message": MESSAGES[status], "reminder": reminder, "read_at": None, "resolved": False},
        })

    def inbox(self, user_id: str, *, limit: int = 50, offset: int = 0) -> list[dict]:
        return self.store.list(NAMESPACE, owner=user_id, limit=limit, offset=offset)

    def mark_read(self, user_id: str, notification_id: UUID) -> dict:
        from app.agent.runtime import graph_resources

        record = self.store.get(str(notification_id))
        if record is None or record["namespace"] != NAMESPACE or record["owner"] != user_id:
            raise NotFoundError("Notification", str(notification_id))
        with graph_resources(self.backend, self.settings).claim_lock(record["aggregate_id"]):
            record = self.store.get(str(notification_id))
            if record["payload"]["read_at"] is not None:
                return record
            return self.store.replace({**record, "payload": {**record["payload"], "read_at": datetime.now(UTC).isoformat()}},
                                      revision=record["revision"])
