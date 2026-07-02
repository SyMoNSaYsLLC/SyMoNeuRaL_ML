# Background Coder Workflow

The visible coding workflow is intentionally removed.

1. User types to **Gemma Writer**.
2. Gemma Writer creates the user-facing decision/spec.
3. If the request is software-related, the frontend automatically submits the request + writer response to `/api/v1/coder/background`.
4. The hidden **Qwen Code Agent** builds inside `data/symoneural_coder_jobs/<job>/workspace`.
5. The worker writes files, optionally runs test commands from the code manifest, and creates `<job>_code_package.tar.gz`.
6. The frontend shows a download link when ready.

The hidden coder is instructed to never ask questions and to fully trust the writer plan.
