# SyMoNeuRaL true single-server mode

SyMoNeuRaL now uses exactly one HTTP listener:

```text
http://127.0.0.1:8000
```

The SyMoNeuRaL-branded llama-ui frontend and OpenAI-compatible API are both served by FastAPI/uvicorn. The backend does not start `symon-llm-server`, `llama-server`, `sd-server`, `8080`, or `18080` as HTTP listeners. Text generation is executed by the FastAPI backend through the local llama CLI binary.
