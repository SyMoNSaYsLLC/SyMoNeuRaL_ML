# SyMoNeuRaL IPTV Compatibility Layer

This folder keeps IPTV compatibility separate from the AI backend runtime.

- `clients/iptv/symoneural-view/` contains the existing SyMoNeuRaL-View IPTV client/server package.
- `app/routers/iptv.py` exposes read-only local IPTV index endpoints.
- `app/services/iptv_library.py` reads the local generated playlist index.
- `data/iptv/` is runtime/local data and is ignored by git.

This does not replace or modify:

- `engines/symon-llm.cpp`
- `engines/symon-image.cpp`
- `scripts/symon`
- the exclusive VRAM handoff engine manager

## Import local playlist data

From repo root:

```bash
./scripts/import_iptv_playlist_zip.sh /path/to/IPTV_Playlist.zip
```

The script builds:

```text
data/iptv/index/summary.json
data/iptv/index/categories.json
data/iptv/index/iptv_index.jsonl
```

The generated index may contain provider URLs, so it stays local and ignored.

## Run the IPTV client

```bash
./scripts/run_symoneural_view.sh
```

## API endpoints

After `./scripts/symon` is running:

```text
GET /api/iptv/status
GET /api/iptv/categories
GET /api/iptv/search?q=espn&kind=live&limit=25
GET /api/iptv/item/{id}
```

URLs are redacted by default. For trusted local use only:

```text
GET /api/iptv/search?q=espn&include_url=true
```
