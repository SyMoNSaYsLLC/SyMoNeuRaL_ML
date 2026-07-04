# SyMoNeuRaL single public server layout

SyMoNeuRaL now uses one public local server:

```text
http://127.0.0.1:8000
```

The main page is the SyMoNeuRaL-branded llama-ui-style frontend. The LLM engine is no longer public on `8080`; it is started as a private loopback worker on `127.0.0.1:18080` and proxied through port `8000`.

Do not start a separate `8080` browser UI. Use `./scripts/symon` and open `http://127.0.0.1:8000/`.
