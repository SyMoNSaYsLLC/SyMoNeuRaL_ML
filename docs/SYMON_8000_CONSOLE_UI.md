# SyMoNeuRaL 8000 Console UI

`http://127.0.0.1:8000/` is the end-user SyMoNeuRaL console.

The LLM engine on `http://127.0.0.1:8080/` remains available as a direct engine/testing UI, but users should normally use port `8000`.

The console includes:

- sidebar
- new chat
- local chat search
- MCP server search/toggles
- settings panel
- prompt library panel
- tools panel
- file picker UI
- reasoning level selector
- model/router selector
- send button

The UI submits through `/api/v1/manager/submit` and polls `/api/v1/manager/jobs/{id}` so the existing backend/routing system remains intact.
