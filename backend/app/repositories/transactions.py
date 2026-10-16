"""A request/node can group existing repository operations into one commit."""

from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterator

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine


class TransactionSession(Session):
    def commit(self) -> None:
        if self.info.get("managed_transaction"):
            self.flush()
        else:
            super().commit()

    def rollback(self) -> None:
        if self.info.get("managed_transaction"):
            self.info["transaction_failed"] = True
        super().rollback()


class SessionScope:
    def __init__(self, engine: Engine) -> None:
        self.factory = sessionmaker(engine, class_=TransactionSession, expire_on_commit=False)
        self.current: ContextVar[Session | None] = ContextVar("repository_session", default=None)

    @contextmanager
    def __call__(self) -> Iterator[Session]:
        active = self.current.get()
        if active is not None:
            yield active
        else:
            with self.factory() as session:
                yield session

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        if self.current.get() is not None:
            yield self.current.get()
            return
        with self.factory() as session:
            session.info["managed_transaction"] = True
            token = self.current.set(session)
            try:
                yield session
                if session.info.get("transaction_failed"):
                    raise RuntimeError("Repository transaction was rolled back and cannot be committed.")
                session.info["managed_transaction"] = False
                session.commit()
            except BaseException:
                session.rollback()
                raise
            finally:
                self.current.reset(token)
