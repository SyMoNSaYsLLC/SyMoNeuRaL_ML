from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Job:
    id: str
    type: str
    status: str = "queued"
    payload: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class JobManager:
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.q: queue.Queue[tuple[str, Callable[[dict], Any]]] = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def submit(self, job_type: str, payload: dict, fn: Callable[[dict], Any]) -> Job:
        job = Job(id=str(uuid.uuid4()), type=job_type, payload=payload)
        self.jobs[job.id] = job
        self.q.put((job.id, fn))
        return job

    def _run(self):
        while True:
            job_id, fn = self.q.get()
            job = self.jobs[job_id]
            job.status = "running"; job.updated_at = time.time()
            try:
                job.result = fn(job.payload)
                job.status = "done"
            except Exception as exc:
                job.error = repr(exc)
                job.status = "failed"
            job.updated_at = time.time()
            self.q.task_done()

    def list(self):
        return [job.__dict__ for job in self.jobs.values()]

    def get(self, job_id: str):
        return self.jobs[job_id].__dict__


JOB_MANAGER = JobManager()
