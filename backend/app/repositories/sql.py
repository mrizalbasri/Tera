"""SQL persistence for the memory-backed protocols (M6 / FR-11).

Design: each table stores a few indexed query columns plus the FULL schema
payload as JSON. Repositories reconstruct domain schemas with
``model_validate``, so SQL stays a drop-in behind the same protocols and
Pydantic remains the single source of shape truth.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, BLOB, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.schemas.core import (
    AuditEvent,
    Claim,
    Clarification,
    ConversationEntry,
    Decision,
    ExtractionAttempt,
    ExtractionResult,
    PolicyEvaluation,
    ProcessingRun,
    Receipt,
    Review,
    Signal,
    ValidationFinding,
)

_ID_LENGTH = 36


class Base(DeclarativeBase):
    pass


class ClaimRow(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(_ID_LENGTH), primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ReceiptRow(Base):
    __tablename__ = "receipts"
    id: Mapped[str] = mapped_column(String(_ID_LENGTH), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(_ID_LENGTH), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ReceiptContentRow(Base):
    __tablename__ = "file_storage"
    reference: Mapped[str] = mapped_column(String(200), primary_key=True)
    content: Mapped[bytes] = mapped_column(BLOB)


class ProcessingRunRow(Base):
    __tablename__ = "processing_runs"
    id: Mapped[str] = mapped_column(String(_ID_LENGTH), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(_ID_LENGTH), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ChildRow(Base):
    """Shared shape for per-claim child records keyed by their own id."""

    __tablename__ = "domain_records"
    id: Mapped[str] = mapped_column(String(_ID_LENGTH), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(_ID_LENGTH), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)


class ConversationRow(Base):
    __tablename__ = "conversation_context"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(String(_ID_LENGTH), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class IdempotencyRow(Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(_ID_LENGTH))


_KINDS = {
    "extraction": ExtractionResult,
    "attempt": ExtractionAttempt,
    "finding": ValidationFinding,
    "evaluation": PolicyEvaluation,
    "signal": Signal,
    "decision": Decision,
    "clarification": Clarification,
    "review": Review,
    "audit": AuditEvent,
}


class SqlRepositories:
    """Bundle of SQL-backed repositories behind the same protocols."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, future=True)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(self._engine, expire_on_commit=False)
        self.claims = SqlClaimRepository(self._session_factory)
        self.receipts = SqlReceiptRepository(self._session_factory)
        self.runs = SqlProcessingRunRepository(self._session_factory)
        self.file_storage = SqlFileStorage(self._session_factory)
        self.extractions = SqlChildRepository(
            self._session_factory, "extraction", ExtractionResult
        )
        self.attempts = SqlChildRepository(
            self._session_factory, "attempt", ExtractionAttempt
        )
        self.findings = SqlChildRepository(
            self._session_factory, "finding", ValidationFinding
        )
        self.evaluations = SqlChildRepository(
            self._session_factory, "evaluation", PolicyEvaluation
        )
        self.signals = SqlChildRepository(self._session_factory, "signal", Signal)
        self.decisions = SqlChildRepository(
            self._session_factory, "decision", Decision
        )
        self.clarifications = SqlChildRepository(
            self._session_factory, "clarification", Clarification
        )
        self.reviews = SqlChildRepository(self._session_factory, "review", Review)
        self.audit = SqlAuditRepository(self._session_factory)
        self.context = SqlConversationRepository(self._session_factory)


def _now() -> datetime:
    return datetime.now(UTC)


class SqlClaimRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sessions = session_factory

    def get(self, claim_id: UUID) -> Claim | None:
        with Session(self._sessions.engine) as session:
            row = session.get(ClaimRow, str(claim_id))
            return Claim.model_validate(row.payload) if row else None

    def save(self, claim: Claim) -> Claim:
        payload = claim.model_dump(mode="json")
        with Session(self._sessions.engine) as session:
            row = session.get(ClaimRow, str(claim.id))
            if row is None:
                row = ClaimRow(
                    id=str(claim.id),
                    employee_id=claim.employee_id,
                    status=str(claim.status),
                    payload=payload,
                )
                session.add(row)
            else:
                row.employee_id = claim.employee_id
                row.status = str(claim.status)
                row.payload = payload
            session.commit()
        return claim

    def list(self, *, employee_id: str | None = None) -> Sequence[Claim]:
        with Session(self._sessions.engine) as session:
            statement = select(ClaimRow).order_by(ClaimRow.rowid)
            if employee_id is not None:
                statement = statement.where(ClaimRow.employee_id == employee_id)
            return tuple(
                Claim.model_validate(row.payload) for row in session.scalars(statement)
            )

    def get_by_idempotency_key(self, key: str) -> Claim | None:
        with Session(self._sessions.engine) as session:
            row = session.get(IdempotencyRow, key)
            if row is None:
                return None
            claim_row = session.get(ClaimRow, row.claim_id)
            return Claim.model_validate(claim_row.payload) if claim_row else None

    def register_idempotency_key(self, key: str, claim_id: UUID) -> None:
        with Session(self._sessions.engine) as session:
            if session.get(IdempotencyRow, key) is None:
                session.add(IdempotencyRow(key=key, claim_id=str(claim_id)))
                session.commit()


class SqlReceiptRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sessions = session_factory

    def save(self, receipt: Receipt) -> Receipt:
        with Session(self._sessions.engine) as session:
            if session.get(ReceiptRow, str(receipt.id)) is None:
                session.add(
                    ReceiptRow(
                        id=str(receipt.id),
                        claim_id=str(receipt.claim_id),
                        content_hash=receipt.content_hash,
                        payload=receipt.model_dump(mode="json"),
                    )
                )
                session.commit()
        return receipt

    def list_for_claim(self, claim_id: UUID) -> Sequence[Receipt]:
        with Session(self._sessions.engine) as session:
            statement = (
                select(ReceiptRow)
                .where(ReceiptRow.claim_id == str(claim_id))
                .order_by(ReceiptRow.rowid)
            )
            return tuple(
                Receipt.model_validate(row.payload) for row in session.scalars(statement)
            )

    def find_claim_id_by_content_hash(self, content_hash: str) -> UUID | None:
        with Session(self._sessions.engine) as session:
            statement = (
                select(ReceiptRow)
                .where(ReceiptRow.content_hash == content_hash)
                .order_by(ReceiptRow.rowid)
                .limit(1)
            )
            row = session.scalars(statement).first()
            return UUID(row.claim_id) if row else None


class SqlProcessingRunRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sessions = session_factory

    def save(self, run: ProcessingRun) -> ProcessingRun:
        with Session(self._sessions.engine) as session:
            row = session.get(ProcessingRunRow, str(run.id))
            if row is None:
                session.add(
                    ProcessingRunRow(
                        id=str(run.id),
                        claim_id=str(run.claim_id),
                        payload=run.model_dump(mode="json"),
                    )
                )
            else:
                row.payload = run.model_dump(mode="json")
            session.commit()
        return run

    def get(self, run_id: UUID) -> ProcessingRun | None:
        with Session(self._sessions.engine) as session:
            row = session.get(ProcessingRunRow, str(run_id))
            return ProcessingRun.model_validate(row.payload) if row else None

    def list_for_claim(self, claim_id: UUID) -> Sequence[ProcessingRun]:
        with Session(self._sessions.engine) as session:
            statement = (
                select(ProcessingRunRow)
                .where(ProcessingRunRow.claim_id == str(claim_id))
                .order_by(ProcessingRunRow.rowid)
            )
            return tuple(
                ProcessingRun.model_validate(row.payload)
                for row in session.scalars(statement)
            )

    def latest_for_claim(self, claim_id: UUID) -> ProcessingRun | None:
        runs = self.list_for_claim(claim_id)
        return runs[-1] if runs else None


class SqlChildRepository:
    """Generic child-record repository (findings, signals, decisions, ...)."""

    def __init__(self, session_factory: sessionmaker, kind: str, schema: type) -> None:
        self._sessions = session_factory
        self._kind = kind
        self._schema = schema

    def save(self, record) -> object:
        claim_id = self._claim_id_for(record)
        created_at = str(
            getattr(record, "created_at", None) or getattr(record, "timestamp", "")
        )
        with Session(self._sessions.engine) as session:
            if session.get(ChildRow, str(record.id)) is None:
                session.add(
                    ChildRow(
                        id=str(record.id),
                        claim_id=claim_id,
                        kind=self._kind,
                        created_at=created_at,
                        payload=record.model_dump(mode="json"),
                    )
                )
                session.commit()
        return record

    def _claim_id_for(self, record) -> str:
        """Extraction results carry receipt_id; resolve the claim via receipt."""
        if hasattr(record, "claim_id"):
            return str(record.claim_id)
        if hasattr(record, "receipt_id"):
            with Session(self._sessions.engine) as session:
                row = session.get(ReceiptRow, str(record.receipt_id))
                return row.claim_id if row else ""
        return ""

    def list_for_claim(self, claim_id: UUID) -> Sequence:
        with Session(self._sessions.engine) as session:
            statement = (
                select(ChildRow)
                .where(ChildRow.claim_id == str(claim_id))
                .where(ChildRow.kind == self._kind)
                .order_by(ChildRow.rowid)
            )
            return tuple(
                self._schema.model_validate(row.payload)
                for row in session.scalars(statement)
            )

    def list_for_receipts(self, receipt_ids: Sequence[UUID]) -> Sequence:
        """Extraction lookup keyed by receipt ids stored inside the payload."""
        if not receipt_ids:
            return ()
        wanted = {str(receipt_id) for receipt_id in receipt_ids}
        with Session(self._sessions.engine) as session:
            statement = (
                select(ChildRow)
                .where(ChildRow.kind == self._kind)
                .order_by(ChildRow.rowid)
            )
            return tuple(
                self._schema.model_validate(row.payload)
                for row in session.scalars(statement)
                if row.payload.get("receipt_id") in wanted
            )


class SqlAuditRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sessions = session_factory

    def append(self, event: AuditEvent) -> AuditEvent:
        with Session(self._sessions.engine) as session:
            statement = (
                select(ChildRow)
                .where(ChildRow.kind == "audit")
                .where(ChildRow.claim_id == str(event.aggregate_id))
            )
            sequence = len(session.scalars(statement).all()) + 1
            stored = event.model_copy(update={"sequence_number": sequence})
            session.add(
                ChildRow(
                    id=str(stored.id),
                    claim_id=str(stored.aggregate_id),
                    kind="audit",
                    created_at=str(stored.timestamp),
                    payload=stored.model_dump(mode="json"),
                )
            )
            session.commit()
        return stored

    def list_for_aggregate(
        self, aggregate_type: str, aggregate_id: UUID
    ) -> Sequence[AuditEvent]:
        with Session(self._sessions.engine) as session:
            statement = (
                select(ChildRow)
                .where(ChildRow.kind == "audit")
                .where(ChildRow.claim_id == str(aggregate_id))
                .order_by(ChildRow.rowid)
            )
            return tuple(
                AuditEvent.model_validate(row.payload)
                for row in session.scalars(statement)
            )


class SqlConversationRepository:
    MAX_ENTRIES = 20

    def __init__(self, session_factory: sessionmaker) -> None:
        self._sessions = session_factory

    def append(self, entry: ConversationEntry) -> ConversationEntry:
        with Session(self._sessions.engine) as session:
            statement = (
                select(ConversationRow)
                .where(ConversationRow.claim_id == str(entry.claim_id))
                .order_by(ConversationRow.id)
            )
            rows = list(session.scalars(statement))
            if len(rows) >= self.MAX_ENTRIES:
                session.delete(rows[0])
            session.add(
                ConversationRow(
                    claim_id=str(entry.claim_id), payload=entry.model_dump(mode="json")
                )
            )
            session.commit()
        return entry

    def list_for_claim(self, claim_id: UUID) -> Sequence[ConversationEntry]:
        with Session(self._sessions.engine) as session:
            statement = (
                select(ConversationRow)
                .where(ConversationRow.claim_id == str(claim_id))
                .order_by(ConversationRow.id)
            )
            return tuple(
                ConversationEntry.model_validate(row.payload)
                for row in session.scalars(statement)
            )


class SqlFileStorage:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sessions = session_factory

    def put(self, content: bytes, *, filename: str, media_type: str) -> str:
        reference = f"sql://{uuid4()}"
        with Session(self._sessions.engine) as session:
            session.add(ReceiptContentRow(reference=reference, content=content))
            session.commit()
        return reference

    def get(self, reference: str) -> bytes | None:
        with Session(self._sessions.engine) as session:
            row = session.get(ReceiptContentRow, reference)
            return bytes(row.content) if row else None

    def delete(self, reference: str) -> None:
        with Session(self._sessions.engine) as session:
            row = session.get(ReceiptContentRow, reference)
            if row is not None:
                session.delete(row)
                session.commit()
