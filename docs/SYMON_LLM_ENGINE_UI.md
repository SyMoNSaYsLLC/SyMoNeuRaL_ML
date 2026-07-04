# SyMoNeuRaL LLM Engine UI

The local LLM engine on port `8080` should not show the upstream/default `llama-ui` page.

SyMoNeuRaL now provides a project-owned static UI at:

```text
frontend/symon-llm-ui/index.html
```

The process manager automatically launches SyMoNeuRaL LLM engine commands with:

```text
--path <repo>/frontend/symon-llm-ui
```

This changes only the browser page served at:

```text
http://127.0.0.1:8080/
```

It does not change the OpenAI-compatible API endpoints used by SyMoNeuRaL:

```text
/v1/models
/v1/chat/completions
/completion
/health
```

## Runtime controls

Disable the branded engine UI:

```bash
export SYMON_LLAMA_UI_DISABLE=1
```

Use a different local UI directory:

```bash
export SYMON_LLAMA_UI_PATH=/absolute/path/to/static/ui
```

The main SyMoNeuRaL app remains on port `8000`.
