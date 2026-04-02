import json
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BulkAddSelection

router = APIRouter(prefix="/api/gitlab", tags=["gitlab"])


def _require_config() -> tuple[str, dict[str, str], bool]:
    gitlab_url = os.getenv("GITLAB_URL", "")
    gitlab_token = os.getenv("GITLAB_TOKEN", "")
    ssl_verify = os.getenv("GITLAB_SSL_VERIFY", "true").lower() not in ("false", "0", "no")
    if not gitlab_url:
        raise HTTPException(
            status_code=503,
            detail="GITLAB_URL environment variable is not configured",
        )
    if not gitlab_token:
        raise HTTPException(
            status_code=503,
            detail="GITLAB_TOKEN environment variable is not configured",
        )
    return gitlab_url.rstrip("/"), {"PRIVATE-TOKEN": gitlab_token}, ssl_verify


async def _fetch_all(path: str, extra_params: dict[str, Any] | None = None) -> list[Any]:
    """Fetch all paginated results from the GitLab API."""
    base_url, headers, ssl_verify = _require_config()
    params: dict[str, Any] = {**(extra_params or {}), "per_page": 100, "page": 1}
    results: list[Any] = []

    async with httpx.AsyncClient(verify=ssl_verify) as client:
        while True:
            resp = await client.get(
                f"{base_url}/api/v4{path}",
                headers=headers,
                params=params,
                timeout=30.0,
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            page_data: list[Any] = resp.json()
            results.extend(page_data)
            total_pages = int(resp.headers.get("X-Total-Pages", "1"))
            if params["page"] >= total_pages or not page_data:
                break
            params["page"] += 1

    return results


# ── Users ────────────────────────────────────────────────────────────────────


@router.get("/users")
async def list_users() -> list[Any]:
    return await _fetch_all("/users", {"active": "true"})


@router.get("/users/by-username/{username}")
async def get_user_by_username(username: str) -> Any:
    """Return the GitLab profile for a single user by username."""
    users = await _fetch_all("/users", {"username": username})
    if not users:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    return users[0]


# ── Groups ───────────────────────────────────────────────────────────────────


@router.get("/groups")
async def list_groups() -> list[Any]:
    return await _fetch_all("/groups", {"all_available": "true"})


@router.get("/groups/{group_id}/members")
async def list_group_members(group_id: int) -> list[Any]:
    return await _fetch_all(f"/groups/{group_id}/members/all")


# ── Projects ─────────────────────────────────────────────────────────────────


@router.get("/projects")
async def list_projects() -> list[Any]:
    return await _fetch_all("/projects", {"simple": "true"})


@router.get("/projects/{project_id}/members")
async def list_project_members(project_id: int) -> list[Any]:
    return await _fetch_all(f"/projects/{project_id}/members/all")


# ── Membership management ────────────────────────────────────────────────────


class AddMemberPayload(BaseModel):
    user_id: int
    access_level: int


@router.post("/groups/{group_id}/members", status_code=201)
async def add_group_member(group_id: int, payload: AddMemberPayload) -> Any:
    base_url, headers, ssl_verify = _require_config()
    async with httpx.AsyncClient(verify=ssl_verify) as client:
        resp = await client.post(
            f"{base_url}/api/v4/groups/{group_id}/members",
            headers=headers,
            json={"user_id": payload.user_id, "access_level": payload.access_level},
            timeout=30.0,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


@router.post("/projects/{project_id}/members", status_code=201)
async def add_project_member(project_id: int, payload: AddMemberPayload) -> Any:
    base_url, headers, ssl_verify = _require_config()
    async with httpx.AsyncClient(verify=ssl_verify) as client:
        resp = await client.post(
            f"{base_url}/api/v4/projects/{project_id}/members",
            headers=headers,
            json={"user_id": payload.user_id, "access_level": payload.access_level},
            timeout=30.0,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()


# ── Bulk membership ──────────────────────────────────────────────────────────


class AddEverywherePayload(BaseModel):
    access_level: int
    group_ids: list[int] | None = None    # None = use all groups
    project_ids: list[int] | None = None  # None = use all projects


class EntityResult(BaseModel):
    total: int = 0
    added: int = 0
    skipped: int = Field(default=0, description="Already a member (HTTP 409)")
    failed: int = 0


class AddEverywhereResult(BaseModel):
    groups: EntityResult
    projects: EntityResult


# ── Bulk selection (saved group/project filter) ───────────────────────────────


class BulkSelectionPayload(BaseModel):
    group_ids: list[int]
    project_ids: list[int]


class BulkSelectionResponse(BaseModel):
    saved: bool
    group_ids: list[int]
    project_ids: list[int]


@router.get("/bulk-selection", response_model=BulkSelectionResponse)
def get_bulk_selection(db: Session = Depends(get_db)) -> BulkSelectionResponse:
    row = db.query(BulkAddSelection).first()
    if row is None:
        return BulkSelectionResponse(saved=False, group_ids=[], project_ids=[])
    return BulkSelectionResponse(
        saved=True,
        group_ids=json.loads(row.group_ids),
        project_ids=json.loads(row.project_ids),
    )


@router.put("/bulk-selection", response_model=BulkSelectionResponse)
def save_bulk_selection(
    payload: BulkSelectionPayload, db: Session = Depends(get_db)
) -> BulkSelectionResponse:
    row = db.query(BulkAddSelection).first()
    if row is None:
        row = BulkAddSelection()
        db.add(row)
    row.group_ids = json.dumps(payload.group_ids)
    row.project_ids = json.dumps(payload.project_ids)
    db.commit()
    return BulkSelectionResponse(
        saved=True, group_ids=payload.group_ids, project_ids=payload.project_ids
    )


@router.post("/users/{user_id}/add-everywhere", response_model=AddEverywhereResult)
async def add_user_everywhere(user_id: int, payload: AddEverywherePayload) -> AddEverywhereResult:
    """Add a user to every (or selected) group and project with the given access level."""
    base_url, headers, ssl_verify = _require_config()

    all_groups = await _fetch_all("/groups", {"all_available": "true"})
    all_projects = await _fetch_all("/projects", {"simple": "true"})

    if payload.group_ids is not None:
        wanted = set(payload.group_ids)
        groups = [g for g in all_groups if g["id"] in wanted]
    else:
        groups = all_groups

    if payload.project_ids is not None:
        wanted = set(payload.project_ids)
        projects = [p for p in all_projects if p["id"] in wanted]
    else:
        projects = all_projects

    groups_result = EntityResult(total=len(groups))
    projects_result = EntityResult(total=len(projects))

    async with httpx.AsyncClient(verify=ssl_verify) as client:
        for group in groups:
            resp = await client.post(
                f"{base_url}/api/v4/groups/{group['id']}/members",
                headers=headers,
                json={"user_id": user_id, "access_level": payload.access_level},
                timeout=30.0,
            )
            if resp.status_code in (200, 201):
                groups_result.added += 1
            elif resp.status_code == 409:
                groups_result.skipped += 1
            else:
                groups_result.failed += 1

        for project in projects:
            resp = await client.post(
                f"{base_url}/api/v4/projects/{project['id']}/members",
                headers=headers,
                json={"user_id": user_id, "access_level": payload.access_level},
                timeout=30.0,
            )
            if resp.status_code in (200, 201):
                projects_result.added += 1
            elif resp.status_code == 409:
                projects_result.skipped += 1
            else:
                projects_result.failed += 1

    return AddEverywhereResult(groups=groups_result, projects=projects_result)
