import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.claims import router as claims_router
from app.api.reviews import router as reviews_router
from app.config import get_settings
from app.errors import ApplicationError
from app.integrations.claim_graph import close_graph_resources
from app.api.deps import close_sql_repositories, _rag_policy_retriever
from app.integrations.rag.pgvector import close_policy_indexes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("expense_agent")

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        close_graph_resources()
        close_sql_repositories()
        close_policy_indexes()
        _rag_policy_retriever.cache_clear()


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version="0.1.0",
    description="API foundation for the Expense Reimbursement Agent.",
)
app.include_router(claims_router)
app.include_router(reviews_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "http request method=%s path=%s status=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        request_id,
    )
    return response


@app.exception_handler(ApplicationError)
async def application_error_handler(
    _request: Request, exc: ApplicationError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
