from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import iptv_library

router = APIRouter(prefix="/api/iptv", tags=["iptv"])


@router.get("/status")
def iptv_status():
    return iptv_library.status()


@router.get("/categories")
def iptv_categories():
    return iptv_library.categories()


@router.get("/search")
def iptv_search(
    q: str = "",
    kind: str | None = Query(default=None, description="live, movie, series, or unknown"),
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    include_url: bool = Query(default=False, description="Return stream URLs only for trusted local use"),
):
    return iptv_library.search(q=q, kind=kind, category=category, limit=limit, include_url=include_url)


@router.get("/item/{item_id}")
def iptv_item(item_id: str, include_url: bool = False):
    return iptv_library.get_item(item_id, include_url=include_url)
