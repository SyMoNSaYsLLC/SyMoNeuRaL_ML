# Exclusive VRAM Handoff

SyMoNeuRaL Local ML 1.2 uses a manager-worker handoff instead of loading all models at once.

## Resident model

The resident idle model is:

```yaml
orchestration:
  exclusive_vram: true
  resident_engine: writer
```

The writer/manager answers normal prompts and classifies heavy prompts.

## Heavy work

For code and image jobs:

1. Writer Manager classifies and cleans the request.
2. Writer Manager stops itself.
3. The selected worker starts with the GPU available.
4. Worker produces artifact/image.
5. Worker stops.
6. Writer Manager restarts and quality-checks the result.
7. Approved result is returned to the user.

## User status message

During worker execution, the frontend displays:

```text
This task requires a lot of processing power, but please wait — your code/image is coming soon.
```

## APIs

```text
POST /api/v1/manager/submit
GET  /api/v1/manager/jobs
GET  /api/v1/manager/jobs/{job_id}
GET  /api/v1/manager/jobs/{job_id}/artifact
```
