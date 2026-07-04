# IPTV Compatibility Migration

This migration integrates the uploaded SyMoNeuRaL-View IPTV project and supports the exploded M3U playlist without letting IPTV break the SyMoNeuRaL AI backend.

## What was added

```text
clients/iptv/symoneural-view/       existing IPTV GUI/client package
clients/iptv/README.md              IPTV layer notes
app/services/iptv_library.py         local index reader
app/routers/iptv.py                  read-only FastAPI router
scripts/build_iptv_index.py          stdlib M3U/zip/exploded playlist indexer
scripts/import_iptv_playlist_zip.sh  user-facing importer
scripts/run_symoneural_view.sh       project-local IPTV GUI launcher
```

## What was intentionally not changed

```text
engines/symon-llm.cpp
engines/symon-image.cpp
app/services/process_manager.py
scripts/symon
config/rtx5070ti_14_15gb.env
```

The IPTV layer does not start CUDA engines, does not touch VRAM profiles, and does not affect the LLM/image engine handoff.

## Playlist handling

The uploaded playlist is very large and contains local/provider stream data. It should not be committed into git.

Use:

```bash
./scripts/import_iptv_playlist_zip.sh /path/to/IPTV_Playlist.zip
```

The importer supports:

- `IPTV_Playlist.zip`
- an exploded `IPTV_Playlist/` folder
- a single `.m3u`/`.m3u8` file

The generated index is local-only:

```text
data/iptv/index/iptv_index.jsonl
data/iptv/index/summary.json
data/iptv/index/categories.json
```

## Backend compatibility

The new API is read-only and lazy-loads from files. If no IPTV index exists, `/api/iptv/status` returns a helpful setup message instead of breaking startup.

## Endpoint examples

```bash
curl http://127.0.0.1:8000/api/iptv/status
curl 'http://127.0.0.1:8000/api/iptv/search?q=canes&kind=live&limit=20'
curl 'http://127.0.0.1:8000/api/iptv/categories'
```

Stream URLs are hidden by default. Use `include_url=true` only on your trusted local machine/network.

## Packaging note

`clients/iptv/symoneural-view/` keeps its original Debian-style layout for compatibility, but SyMoNeuRaL launches it through:

```bash
./scripts/run_symoneural_view.sh
```

That avoids relying on `/usr/lib/symoneural-view` during development.
