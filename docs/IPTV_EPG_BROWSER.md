# IPTV EPG-Style Browser

This adds a browser UI for the SyMoNeuRaL IPTV compatibility layer.

## Page

```text
http://127.0.0.1:8000/iptv
```

Aliases:

```text
/iptv/browser
/iptv/epg
/tv
```

## What it is

This is an EPG-style IPTV browser built from the local playlist index:

- live guide-style cards
- category sidebar
- search
- movies and series tabs
- item details
- optional local stream URL loading
- basic browser playback when the stream format/browser supports it

## What it is not yet

This is not a full XMLTV-backed EPG yet. The current playlist index has item names, categories, logos, and some event-style dates embedded in names. The browser extracts those dates when present and displays them like guide times.

A full EPG phase would add:

```text
scripts/import_iptv_epg_xmltv.py
app/services/iptv_epg.py
/api/iptv/epg/grid
XMLTV channel matching using tvg-id / tvg-name
multi-hour timeline rows
program descriptions
catch-up metadata if provided
```

## Backend safety

This update only adds static browser assets and route aliases. It does not touch:

```text
engines/symon-llm.cpp
engines/symon-image.cpp
app/services/process_manager.py
scripts/symon
config/rtx5070ti_14_15gb.env
```
