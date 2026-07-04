#!/usr/bin/env python3
"""Build a local SyMoNeuRaL IPTV index from an exploded M3U folder or zip.

The generated files live under data/iptv/index/ and are intended to stay local.
They may contain playlist URLs, so data/iptv is ignored by git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator

EXTINF_RE = re.compile(r"#EXTINF:(.*?),(.*)")
ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')


def _parse_extinf(line: str) -> dict:
    item = {
        "name": "Unknown",
        "tvg_id": None,
        "tvg_name": None,
        "logo": None,
        "group": "Uncategorized",
    }
    m = EXTINF_RE.search(line)
    if not m:
        return item
    attrs, name = m.group(1), m.group(2).strip()
    item["name"] = name or "Unknown"
    for k, v in ATTR_RE.findall(attrs):
        if k == "tvg-id":
            item["tvg_id"] = v
        elif k == "tvg-name":
            item["tvg_name"] = v
        elif k == "tvg-logo":
            item["logo"] = v
        elif k == "group-title":
            item["group"] = v or "Uncategorized"
    return item


def _kind_from_path(rel: str) -> str:
    parts = rel.replace("\\", "/").split("/")
    for p in parts:
        low = p.lower()
        if low in {"live_tv", "live tv", "livetv"}:
            return "live"
        if low == "movies":
            return "movie"
        if low == "series":
            return "series"
    return "unknown"


def _category_from_path(rel: str, fallback: str | None = None) -> str:
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    for idx, p in enumerate(parts):
        if p.lower() in {"live_tv", "live tv", "livetv", "movies", "series"} and idx + 1 < len(parts):
            return parts[idx + 1]
    return fallback or "Uncategorized"


def _read_records_from_lines(lines: Iterable[str], rel: str) -> Iterator[dict]:
    current = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            current = _parse_extinf(line)
            continue
        if line.startswith("#"):
            continue
        if current:
            item = dict(current)
            item["url"] = line
            item["source_path"] = rel
            item["kind"] = _kind_from_path(rel)
            item["category"] = _category_from_path(rel, item.get("group"))
            item["group"] = item.get("group") or item["category"]
            seed = "|".join([item.get("kind") or "", item.get("category") or "", item.get("name") or "", item.get("url") or ""])
            item["id"] = hashlib.sha1(seed.encode("utf-8", "ignore")).hexdigest()[:16]
            yield item
            current = None


def _iter_m3u_from_dir(root: Path) -> Iterator[tuple[str, Iterable[str]]]:
    for path in root.rglob("*.m3u"):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            try:
                yield rel, path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception as exc:
                print(f"WARN: failed to read {path}: {exc}", file=sys.stderr)


def _iter_m3u_from_zip(zip_path: Path) -> Iterator[tuple[str, Iterable[str]]]:
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".m3u"):
                continue
            try:
                data = zf.read(info.filename).decode("utf-8", errors="ignore").splitlines()
                yield info.filename, data
            except Exception as exc:
                print(f"WARN: failed to read {info.filename}: {exc}", file=sys.stderr)


def _iter_items(source: Path) -> Iterator[dict]:
    if source.is_dir():
        pairs = _iter_m3u_from_dir(source)
    elif source.is_file() and source.suffix.lower() == ".zip":
        pairs = _iter_m3u_from_zip(source)
    elif source.is_file() and source.suffix.lower() in {".m3u", ".m3u8"}:
        pairs = [(source.name, source.read_text(encoding="utf-8", errors="ignore").splitlines())]
    else:
        raise SystemExit(f"Unsupported source: {source}. Use a .zip, .m3u, or exploded playlist directory.")

    for rel, lines in pairs:
        yield from _read_records_from_lines(lines, rel)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="IPTV_Playlist.zip, playlist.m3u, or exploded IPTV_Playlist directory")
    ap.add_argument("--out", default="data/iptv/index", help="output index directory")
    ap.add_argument("--limit", type=int, default=0, help="debug limit")
    args = ap.parse_args()

    source = Path(args.source).expanduser().resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    jsonl = out / "iptv_index.jsonl"
    name_tsv = out / "name_index.tsv"
    summary_path = out / "summary.json"
    cats_path = out / "categories.json"

    counts = Counter()
    cat_counts = Counter()
    group_counts = Counter()
    started = time.time()
    total = 0

    with jsonl.open("w", encoding="utf-8") as jf, name_tsv.open("w", encoding="utf-8") as nf:
        for item in _iter_items(source):
            jf.write(json.dumps(item, ensure_ascii=False) + "\n")
            nf.write("\t".join([
                item["id"], item.get("kind") or "", item.get("category") or "", item.get("group") or "", (item.get("name") or "").replace("\t", " "),
            ]) + "\n")
            total += 1
            counts[item.get("kind") or "unknown"] += 1
            cat_counts[f"{item.get('kind') or 'unknown'}/{item.get('category') or 'Uncategorized'}"] += 1
            group_counts[item.get("group") or "Uncategorized"] += 1
            if total % 25000 == 0:
                print(f"indexed {total} items...")
            if args.limit and total >= args.limit:
                break

    summary = {
        "ok": True,
        "source": str(source),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_items": total,
        "counts_by_kind": dict(counts),
        "top_categories": cat_counts.most_common(100),
        "top_groups": group_counts.most_common(100),
        "files": {
            "jsonl": str(jsonl),
            "name_index": str(name_tsv),
            "categories": str(cats_path),
        },
        "elapsed_seconds": round(time.time() - started, 3),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    cats = defaultdict(Counter)
    for full, count in cat_counts.items():
        kind, category = full.split("/", 1)
        cats[kind][category] = count
    cats_json = {kind: dict(counter.most_common()) for kind, counter in cats.items()}
    cats_path.write_text(json.dumps(cats_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
