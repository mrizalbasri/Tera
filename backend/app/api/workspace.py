from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from app.agent.runtime import graph_resources
from app.api.auth import require_admin
from app.api.claim_access import ClaimActor, get_claim_actor
from app.api.deps import _backend
from app.config import Settings, get_settings
from app.errors import ApplicationError
from app.repositories.query import ClaimFilter
from app.schemas.core import SchemaBase
from app.services.notifications import NotificationService
from app.services.policy_versions import PolicyDraft, PolicyVersionService

router = APIRouter(tags=["workspace"])


def notifications(settings: Settings = Depends(get_settings)) -> NotificationService:
    return NotificationService(_backend(settings), settings)


def policies(settings: Settings = Depends(get_settings)) -> PolicyVersionService:
    backend = _backend(settings)
    return PolicyVersionService(backend, graph_resources(backend, settings))


@router.get("/notifications")
def inbox(actor: ClaimActor = Depends(get_claim_actor), service: NotificationService = Depends(notifications),
          limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> dict:
    items = service.inbox(actor.user_id, limit=limit, offset=offset)
    return {"items": items, "limit": limit, "offset": offset}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: UUID, actor: ClaimActor = Depends(get_claim_actor),
              service: NotificationService = Depends(notifications)) -> dict:
    return service.mark_read(actor.user_id, notification_id)


@router.get("/policies")
def list_versions(actor: str = Depends(require_admin), service: PolicyVersionService = Depends(policies),
                  limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0)) -> dict:
    return {"items": service.list(limit=limit, offset=offset), "limit": limit, "offset": offset}


@router.post("/policies", status_code=201)
def create_version(draft: PolicyDraft, actor: str = Depends(require_admin), service: PolicyVersionService = Depends(policies)) -> dict:
    return service.create(draft, actor)


@router.post("/policies/import-baseline")
def import_baseline(actor: str = Depends(require_admin), service: PolicyVersionService = Depends(policies)) -> dict:
    return {"items": service.seed_baseline(actor)}


@router.get("/policies/{version_id}/audit")
def policy_audit(version_id: UUID, actor: str = Depends(require_admin), service: PolicyVersionService = Depends(policies)) -> dict:
    service.get(version_id)
    return {"items": service.backend.audit.list_for_aggregate("policy_version", version_id)}


class DraftEdit(SchemaBase):
    draft: PolicyDraft
    revision: int = Field(ge=1)


class PublishRequest(SchemaBase):
    revision: int = Field(ge=1)


@router.put("/policies/{version_id}")
def edit_version(version_id: UUID, body: DraftEdit, actor: str = Depends(require_admin),
                 service: PolicyVersionService = Depends(policies)) -> dict:
    return service.edit(version_id, body.draft, body.revision, actor)


@router.post("/policies/{version_id}/publish")
def publish_version(version_id: UUID, body: PublishRequest, actor: str = Depends(require_admin),
                    service: PolicyVersionService = Depends(policies)) -> dict:
    return service.publish(version_id, body.revision, actor)
