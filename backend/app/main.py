import sys
import logging
import re
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.claims import router as claims_router
from app.api.auth import router as auth_router
from app.api.reviews import router as reviews_router
from app.api.reports import router as reports_router
from app.api.operations import router as operations_router
from app.api.workspace import router as workspace_router
from app.api.body_limit import BodyLimitMiddleware, RequestTooLarge
from app.config import get_settings
from app.errors import ApplicationError
from app.agent.runtime import close_graph_resources
from app.api.deps import close_sql_repositories, _rag_policy_retriever, _ml_anomaly_scorer
from app.integrations.rag.pgvector import close_policy_indexes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("expense_agent")

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    worker = None
    try:
        configured = _app.dependency_overrides.get(get_settings, get_settings)()
        if configured.environment == "production":
            from app.api.deps import _backend, get_policy_retriever, get_anomaly_scorer
            from app.agent.runtime import graph_resources

            backend = _backend(configured)
            backend.ready()
            graph_resources(backend, configured).ready()
            get_policy_retriever(configured)
            get_anomaly_scorer(configured)
        if configured.storage_backend == "sql":
            from app.services.recovery import RecoveryWorker

            worker = RecoveryWorker(configured)
            worker.start()
        elif configured.environment != "production" and "pytest" not in sys.modules:
            from app.api.deps import _backend
            from app.schemas.core import Claim
            from app.domain.enums import ClaimStatus
            from decimal import Decimal
            from datetime import datetime, timedelta, UTC

            repo = _backend(configured).claims
            if not repo.list(employee_id="karyawan@tera.id"):
                now = datetime.now(UTC)
                for amount, days_ago in [(Decimal("45000"), 8), (Decimal("55000"), 6), (Decimal("40000"), 4), (Decimal("50000"), 2)]:
                    sub_time = now - timedelta(days=days_ago)
                    repo.save(Claim(
                        id=uuid4(),
                        employee_id="karyawan@tera.id",
                        status=ClaimStatus.APPROVED,
                        submitted_at=sub_time,
                        currency="IDR",
                        declared_amount=amount,
                        receipt_revision=0,
                        created_at=sub_time,
                        updated_at=sub_time,
                    ))
        yield
    finally:
        if worker is not None:
            worker.close()
        close_graph_resources()
        close_sql_repositories()
        close_policy_indexes()
        _rag_policy_retriever.cache_clear()
        _ml_anomaly_scorer.cache_clear()


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version="0.1.0",
    description="API foundation for the Expense Reimbursement Agent.",
)
app.include_router(claims_router)
app.include_router(auth_router)
app.include_router(reviews_router)
app.include_router(reports_router)
app.include_router(operations_router)
app.include_router(workspace_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(BodyLimitMiddleware, settings_provider=lambda: app.dependency_overrides.get(get_settings, get_settings)())


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if re.fullmatch(r"[A-Za-z0-9._-]{1,100}", supplied) else str(uuid4())
    request.state.request_id = request_id
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("http request failed method=%s path=%s status=500 request_id=%s duration_ms=%s",
                     request.method, request.url.path, request_id, round((time.monotonic() - started) * 1000))
        raise
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path.startswith(("/claims", "/reviews", "/reports", "/operations", "/auth", "/notifications", "/policies")):
        response.headers["Cache-Control"] = "no-store"
    logger.info(
        "http request method=%s path=%s status=%s request_id=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        request_id,
        round((time.monotonic() - started) * 1000),
    )
    return response


@app.exception_handler(ApplicationError)
async def application_error_handler(
    _request: Request, exc: ApplicationError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        headers={"Retry-After": str((exc.details or {}).get("retry_after", 1))} if exc.status_code in (429, 503) else None,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestTooLarge)
async def request_too_large_handler(_request: Request, _exc: RequestTooLarge):
    return JSONResponse({"code": "request_too_large", "message": "Request exceeds the maximum allowed size."}, status_code=413)


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, _exc: Exception):
    return JSONResponse({"code": "internal_error", "message": "An unexpected error occurred."}, status_code=500,
                        headers={"X-Request-ID": getattr(request.state, "request_id", str(uuid4())), "Cache-Control": "no-store"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/ready")
def readiness(response: Response, configured=Depends(get_settings)):
    from app.api.deps import _backend, get_policy_retriever, get_anomaly_scorer
    from app.agent.runtime import graph_resources

    response.headers["Cache-Control"] = "no-store"
    try:
        backend = _backend(configured)
        if hasattr(backend, "ready"):
            backend.ready()
        graph_resources(backend, configured).ready()
        get_policy_retriever(configured)
        get_anomaly_scorer(configured)
    except Exception as exc:
        logger.warning("readiness check failed error_type=%s", type(exc).__name__)
        response.status_code = 503
        return {"status": "unavailable"}
    return {"status": "ready"}
