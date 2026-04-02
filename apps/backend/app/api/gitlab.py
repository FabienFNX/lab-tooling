import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/gitlab", tags=["gitlab"])


def _require_config() -> tuple[str, dict[str, str]]:
    gitlab_url = os.getenv("GITLAB_URL", "")
    gitlab_token = os.getenv("GITLAB_TOKEN", "")
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
    return gitlab_url.rstrip("/"), {"PRIVATE-TOKEN": gitlab_token}


async def _fetch_all(path: str, extra_params: dict[str, Any] | None = None) -> list[Any]:
    """Fetch all paginated results from the GitLab API."""
    base_url, headers = _require_config()
    params: dict[str, Any] = {**(extra_params or {}), "per_page": 100, "page": 1}
    results: list[Any] = []

    async with httpx.AsyncClient() as client:
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
    base_url, headers = _require_config()
    async with httpx.AsyncClient() as client:
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
    base_url, headers = _require_config()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base_url}/api/v4/projects/{project_id}/members",
            headers=headers,
            json={"user_id": payload.user_id, "access_level": payload.access_level},
            timeout=30.0,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
