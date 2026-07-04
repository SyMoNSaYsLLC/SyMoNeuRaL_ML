# SyMoNeuRaL Frontend Port Layout

- `http://127.0.0.1:8000/` is the end-user SyMoNeuRaL frontend.
- `http://127.0.0.1:8080/` is the direct LLM engine/test UI.

The 8000 frontend is intentionally based on the llama-ui static build style. Extra console controls are not added to 8000.

The earlier experimental 8000 console files are preserved under:

- `frontend/symon-console-backup/`
- `static/symon-console-backup/`

Those can be reused later for an engine/test console or separate admin page, but they should not replace the main 8000 page.
