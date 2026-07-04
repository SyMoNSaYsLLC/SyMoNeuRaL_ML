from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX_DIR = ROOT / "data" / "iptv" / "index"


def index_dir() -> Path:
    return Path(os.environ.get("SYMON_IPTV_INDEX_DIR", str(DEFAULT_INDEX_DIR))).expanduser().resolve()


def _summary_path() -> Path:
    return index_dir() / "summary.json"


def _jsonl_path() -> Path:
    return index_dir() / "iptv_index.jsonl"


def _categories_path() -> Path:
    return index_dir() / "categories.json"


def status() -> dict[str, Any]:
    sp = _summary_path()
    jp = _jsonl_path()
    if not sp.exists() or not jp.exists():
        return {
            "ok": False,
            "configured": False,
            "message": "No IPTV index found. Run ./scripts/import_iptv_playlist_zip.sh /path/to/IPTV_Playlist.zip",
            "index_dir": str(index_dir()),
        }
    try:
        summary = json.loads(sp.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "configured": False, "message": f"Could not read IPTV summary: {exc}", "index_dir": str(index_dir())}
    summary.update({"configured": True, "index_dir": str(index_dir())})
    return summary


def categories() -> dict[str, Any]:
    cp = _categories_path()
    if not cp.exists():
        return {"ok": False, "categories": {}, "message": "No categories index found."}
    return {"ok": True, "categories": json.loads(cp.read_text(encoding="utf-8"))}


def _redact(item: dict[str, Any], include_url: bool = False) -> dict[str, Any]:
    clean = dict(item)
    if not include_url:
        clean.pop("url", None)
    return clean


def search(q: str = "", kind: str | None = None, category: str | None = None, limit: int = 50, include_url: bool = False) -> dict[str, Any]:
    jp = _jsonl_path()
    if not jp.exists():
        return {"ok": False, "items": [], "message": "No IPTV index found."}
    q_norm = (q or "").lower().strip()
    kind_norm = (kind or "").lower().strip()
    cat_norm = (category or "").lower().strip()
    limit = max(1, min(int(limit or 50), 500))
    items: list[dict[str, Any]] = []
    scanned = 0
    with jp.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            scanned += 1
            try:
                item = json.loads(line)
            except Exception:
                continue
            if kind_norm and (item.get("kind") or "").lower() != kind_norm:
                continue
            if cat_norm and cat_norm not in (item.get("category") or "").lower():
                continue
            if q_norm:
                hay = " ".join(str(item.get(k) or "") for k in ("name", "tvg_name", "tvg_id", "group", "category", "source_path")).lower()
                if q_norm not in hay:
                    continue
            items.append(_redact(item, include_url=include_url))
            if len(items) >= limit:
                break
    return {"ok": True, "count": len(items), "scanned": scanned, "items": items}


def get_item(item_id: str, include_url: bool = False) -> dict[str, Any]:
    jp = _jsonl_path()
    if not jp.exists():
        return {"ok": False, "item": None, "message": "No IPTV index found."}
    with jp.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                item = json.loads(line)
            except Exception:
                continue
            if item.get("id") == item_id:
                return {"ok": True, "item": _redact(item, include_url=include_url)}
    return {"ok": False, "item": None, "message": "Item not found."}
