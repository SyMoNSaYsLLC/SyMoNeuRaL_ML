# PHP Migration Notes

Python is currently the control plane because FastAPI is fast to iterate and already wraps the local C/C++ CUDA engines. The actual inference performance still comes from `llama.cpp` and `stable-diffusion.cpp`.

A future production PHP version should not rewrite inference either. It should replace the web/API control plane while keeping:

```text
PHP/FPM or RoadRunner
  → process manager / queue
  → llama.cpp server
  → stable-diffusion.cpp server
  → artifacts and billing
```

## Recommended migration phases

1. Keep this Python app as the reference implementation.
2. Freeze API schema under `/api/v1`.
3. Generate OpenAPI from FastAPI.
4. Reimplement `/api/v1/manager/submit`, `/api/v1/manager/jobs`, billing, and Cloudflare endpoints in PHP.
5. Keep CUDA/model build tools as shell/CMake tools.
6. Keep `symon-*` CLI wrappers stable so PHP and Python both use the same engine paths.

## PHP bridge skeleton

A minimal PHP bridge is included under:

```text
php_bridge/
```

It is not the active app yet. It is a future migration reference.
